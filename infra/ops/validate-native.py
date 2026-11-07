#!/usr/bin/env python3
"""Explicit opt-in local cached AMD64 config-only tools. Never starts business services."""
import argparse, datetime, hashlib, json, re, subprocess, uuid
from pathlib import Path
from zoneinfo import ZoneInfo
HERE=Path(__file__).resolve().parent

def cli(args):
    return subprocess.run(args,capture_output=True,text=True,timeout=30)

def source_snapshot(base):
    p=cli(base+['ps','--all','--format','{{.Names}}'])
    if p.returncode:raise RuntimeError('cannot record source container state')
    names=[n for n in p.stdout.splitlines() if n.startswith('penpot-') or n in {'nacos','mysql','redis','rabbitmq','nexus3','nginx'}]
    if not names:return {}
    fmt='{{.Name}}\t{{.Id}}\t{{.State.Status}}\t{{.State.Running}}'
    p=cli(base+['inspect','--format',fmt,*names])
    if p.returncode:raise RuntimeError('cannot read source identity/status allowlist')
    result={}
    for line in p.stdout.splitlines():
        name,cid,status,running=line.split('\t')
        result[name.lstrip('/')]=dict(container_id=cid,status=status,running=running=='true')
    return result

def image_only(meta):
    return meta['tag'].rsplit(':',1)[0]+'@'+meta['amd64_digest']

def summarize(record):
    if record['exit_code']!=0:return 'failed; inspect config-only tool output'
    if record['name']=='blackbox-help':return 'help advertises config.check' if supports_config_check(record['stdout']+record['stderr']) else 'static config flag not advertised'
    return '\n'.join((record['stdout']+record['stderr']).strip().splitlines()[-5:])

def supports_config_check(text):
    return re.search(r'--(?:\[no-\])?config\.check(?:\s|=|$)',text) is not None

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute-local-config-only',action='store_true')
    args=parser.parse_args()
    if not args.execute_local_config_only:parser.error('explicit --execute-local-config-only is required')
    p=cli(['docker','context','show'])
    if p.returncode:raise RuntimeError('cannot select local Docker context')
    context=p.stdout.strip();base=['docker','--context',context]
    p=cli(['docker','context','inspect',context])
    if p.returncode or not json.loads(p.stdout)[0]['Endpoints']['docker']['Host'].startswith('unix://'):
        raise RuntimeError('only a local Unix Docker endpoint is allowed')
    lock=json.loads((HERE/'images.lock.json').read_text())['images']
    for name in ['prometheus','alertmanager','blackbox']:
        p=cli(base+['image','inspect','--format','{{.Architecture}} {{.Os}}',image_only(lock[name])])
        if p.returncode or p.stdout.strip()!='amd64 linux':raise RuntimeError('locked AMD64 tool image not locally cached: '+name)
    report={'captured_at':datetime.datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),'mode':'config-only','execution':'local Docker cached linux/amd64 tools; not T630 deployment','context':context,'network':'none','pull':'never','published_ports':[],'secrets_mounted':False,'source_volumes_mounted':False,'checks':[]}
    before=source_snapshot(base);report['source_before']=before
    def tool(name,role,entrypoint,arguments,config_dir=None,target=None,memory='256m'):
        container='dell-ops-config-'+uuid.uuid4().hex[:12]
        command=base+['run','--name',container,'--pull=never','--platform=linux/amd64','--network=none','--rm','--read-only','--user','65534:65534','--cap-drop=ALL','--security-opt=no-new-privileges:true','--cpus=0.5','--memory='+memory,'--memory-swap='+memory,'--pids-limit=128','--tmpfs','/tmp:size=16m,mode=1777']
        if config_dir:command+=['--mount','type=bind,src='+str(config_dir.resolve())+',dst='+target+',readonly']
        command+=['--entrypoint',entrypoint,image_only(lock[role]),*arguments]
        try:p=subprocess.run(command,capture_output=True,text=True,timeout=120)
        except subprocess.TimeoutExpired:
            cli(base+['rm','--force',container])
            record={'name':name,'image':image_only(lock[role]),'exit_code':124,'stdout':'','stderr':'config-only tool timeout; own temporary container cleaned','arguments':arguments}
        else:record={'name':name,'image':image_only(lock[role]),'exit_code':p.returncode,'stdout':p.stdout[-20000:],'stderr':p.stderr[-20000:],'arguments':arguments}
        record['constraints']={'cpus':0.5,'memory':memory,'memory_swap':memory,'pids_limit':128,'read_only':True,'user':'65534:65534','network':'none','pull':'never','ports':[],'source_or_secret_mounts':False}
        record['summary']=summarize(record)
        report['checks'].append(record)
        print(json.dumps({'check':name,'exit_code':record['exit_code']}))
        return record
    try:
        helper=tool('blackbox-help','blackbox','/bin/blackbox_exporter',['--help'],memory='128m')
        tool('promtool-config','prometheus','/bin/promtool',['check','config','/etc/prometheus/prometheus.yml'],HERE/'config/prometheus','/etc/prometheus')
        tool('promtool-rules','prometheus','/bin/promtool',['check','rules','/etc/prometheus/rules/infra.yml'],HERE/'config/prometheus','/etc/prometheus')
        tool('amtool-config','alertmanager','/bin/amtool',['check-config','/etc/alertmanager/alertmanager.yml'],HERE/'config/alertmanager','/etc/alertmanager',memory='128m')
        if helper['exit_code']==0 and supports_config_check(helper['stdout']+helper['stderr']):
            tool('blackbox-static-config','blackbox','/bin/blackbox_exporter',['--config.file=/etc/blackbox_exporter/blackbox.yml','--config.check'],HERE/'config/blackbox','/etc/blackbox_exporter',memory='128m')
        else:report['blackbox_static_check']='not advertised by --help; no server-start fallback attempted'
    finally:
        after=source_snapshot(base);report['source_after']=after
        report['source_identity_and_running_state_unchanged']=set(before)==set(after) and all(all(before[n][k]==after[n][k] for k in ('container_id','status','running')) for n in before)
        paths=[HERE/'images.lock.json',*sorted((HERE/'config/prometheus').rglob('*')),*sorted((HERE/'config/alertmanager').rglob('*')),*sorted((HERE/'config/blackbox').rglob('*'))]
        report['input_sha256']={str(p.relative_to(HERE)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths if p.is_file()}
        report['monitoring_targets_verified']=False;report['notification_delivery_verified']=False;report['target_deployment_verified']=False
        report['result']='passed' if report['checks'] and all(x['exit_code']==0 for x in report['checks']) and report['source_identity_and_running_state_unchanged'] else 'failed'
        directory=HERE/'evidence';directory.mkdir(exist_ok=True)
        path=directory/'native-config-check.json';path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
        result=json.loads((HERE/'validation.json').read_text()) if (HERE/'validation.json').exists() else {}
        result['native_config_only']={k:report[k] for k in ['captured_at','mode','result','input_sha256','source_identity_and_running_state_unchanged','monitoring_targets_verified','notification_delivery_verified','target_deployment_verified']}
        result['native_config_only']['checks']=[{'name':x['name'],'exit_code':x['exit_code'],'summary':x['summary']} for x in report['checks']]
        result['native_promtool_amtool']='config-only-'+report['result']+'-local-cached-amd64-tools'
        result['target_native_configuration_validation']='pending-on-assigned-guest'
        (HERE/'validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'mode':'config-only','result':report['result'],'source_containers':len(before),'source_state_unchanged':report['source_identity_and_running_state_unchanged'],'evidence':str(path)}))
    return 0 if report['result']=='passed' else 1

if __name__=='__main__':raise SystemExit(main())
