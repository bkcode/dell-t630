#!/usr/bin/env python3
"""Static and offline ops checks. Does not pull or run a Docker image."""
import ast,hashlib,hmac,importlib.util,json,os,re,stat,subprocess,sys
from pathlib import Path
import yaml
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
BUNDLE=ROOT/'private'/'ops'/'bundle'

def validate_notification_contract(am,model,bundle=BUNDLE,primary=None):
    marker=bundle/'lark-notify-state.json'
    if not marker.exists() and not marker.is_symlink():
        assert am['receivers']==[{'name':'local-only'}] and am['route']['receiver']=='local-only','unmarked configuration must stay local-only'
        return None
    assert not marker.is_symlink() and marker.resolve()==marker and marker.stat().st_mode&0o777==0o600,'notification marker must be regular private600'
    state=json.loads(marker.read_text());assert isinstance(state,dict),'notification state must be an object'
    mode=state.get('mode')
    assert mode in ('acceptance','active') and state=={'mode':mode,'owner':'native-lark-notify','generic_prepare':'refuse-reset'},'notification marker schema/owner rejected'
    sys.path.insert(0,str(HERE/'lark-notify'))
    try:
        import configuration
        expected=configuration.render(mode)
    finally:sys.path.pop(0)
    assert am==expected,'configured notifications must exactly match the reviewed renderer'
    expected_source=str((bundle/'secrets/lark-bridge-token').resolve())
    assert model['services']['alertmanager'].get('secrets') in ([{'source':'lark-bridge-token','target':'lark-bridge-token'}],[{'source':'lark-bridge-token','target':'/run/secrets/lark-bridge-token'}]),'only the reviewed AM secret mount is allowed'
    assert model.get('secrets',{}).get('lark-bridge-token',{}).get('file')==expected_source,'stable Compose secret source rejected'
    primary=primary or ROOT/'private/ops/lark-bridge-token'
    values=[]
    for file in [primary,bundle/'secrets/lark-bridge-token']:
        st=file.lstat()
        assert not file.is_symlink() and file.resolve()==file and stat.S_ISREG(st.st_mode) and st.st_nlink==1 and st.st_mode&0o777==0o600,'token must be separate regular private600'
        value=file.read_bytes();assert re.fullmatch(rb'[A-Za-z0-9_-]{64}\n',value),'stable token format rejected';values.append(value)
    assert hmac.compare_digest(*values),'stable source/bundle tokens differ; refuse rotation'
    return mode

def main():
    for p in [HERE/'prepare.py',HERE/'validate.py',HERE/'validate-native.py',*HERE.glob('test_*.py'),*HERE.joinpath('scripts').glob('*.py'),*HERE.joinpath('guest-baseline').glob('*.py')]:ast.parse(p.read_text())
    tests=0
    for name in ['test_safety.py','test_probe.py','test_guest_baseline.py']:
        p=subprocess.run([sys.executable,str(HERE/name)],capture_output=True,text=True,timeout=30)
        if p.returncode:raise RuntimeError('offline test failure: '+name)
        tests+=int(re.search(r'Ran (\d+) tests',p.stderr).group(1))
    p=subprocess.run(['docker','compose','--env-file',str(BUNDLE/'.env'),'-f',str(BUNDLE/'compose.yaml'),'config','--format','json'],capture_output=True,text=True,timeout=30)
    if p.returncode:raise RuntimeError('Compose parse failed; values suppressed')
    d=json.loads(p.stdout);assert set(d['services'])=={'prometheus','grafana','alertmanager','blackbox'}
    total=0
    for name,s in d['services'].items():
        assert '@sha256:' in s['image'] and s['platform']=='linux/amd64'
        assert s['restart']=='no' and s.get('healthcheck')
        total+=int(s['mem_limit'])
        for v in s.get('volumes',[]):assert v['type']=='bind' and v.get('bind',{}).get('create_host_path') is False
        for port in s.get('ports',[]):assert port['host_ip']=='10.63.30.40'
    assert total==int(2.625*1024**3) and total<4*1024**3
    assert not d['services']['blackbox'].get('ports')
    gf=d['services']['grafana']['environment']
    assert gf['GF_SMTP_ENABLED']=='false' and gf['GF_UNIFIED_ALERTING_ENABLED']=='false'
    assert gf['GF_AUTH_ANONYMOUS_ENABLED']=='false' and gf['GF_SECURITY_ADMIN_PASSWORD__FILE'].startswith('/run/secrets/')
    assert 'GF_SECURITY_ADMIN_PASSWORD' not in gf
    assert (BUNDLE/'secrets/grafana-admin-password').stat().st_mode&0o777==0o600
    assert (BUNDLE/'.env').stat().st_mode&0o777==0o600
    am=yaml.safe_load((BUNDLE/'config/alertmanager/alertmanager.yml').read_text())
    notification_mode=validate_notification_contract(am,d)
    for p in (BUNDLE/'config').rglob('*.yml'):yaml.safe_load(p.read_text())
    catalog=json.loads((BUNDLE/'config/candidates/catalog.json').read_text());plan=json.loads((ROOT/'plan.json').read_text())
    assert {x['role'] for x in catalog['roles']}=={x['name'] for x in plan['roles']} and len(catalog['roles'])==13
    assert catalog['pve_metrics']['included_in_scrape_targets'] is False
    active=json.loads((BUNDLE/'config/prometheus/targets/guest-node.json').read_text())
    meta=json.loads((BUNDLE/'bundle.json').read_text())
    assert {x['labels']['role'] for x in active}==set(meta['active_guest_roles'])
    assert all(plan['pve']['host'] not in t for x in active for t in x['targets'])
    http_targets=json.loads((BUNDLE/'config/prometheus/targets/http-services.json').read_text())
    assert {x['labels']['role'] for x in http_targets if x['labels'].get('scope')=='endpoint-only'}==set(meta.get('active_http_roles',[]))
    report={'status':'static-and-offline-passed','offline_tests':tests,'services':sorted(d['services']),'container_memory_limits_gib':total/1024**3,'guest_budget_gib':4,'native_notification_memory_limit_mib':96 if notification_mode else 0,'os_runtime_headroom_gib':4-total/1024**3-(96/1024 if notification_mode else 0),'candidate_roles':13,'active_guest_roles':meta['active_guest_roles'],'filesystem_uuid':'configured' if meta['data_fs_uuid'] else 'pending','external_notifications':('configured-lark-'+notification_mode+'; runtime not requeried by validator') if notification_mode else 'not-configured-not-tested','notification_config_only_evidence':'infra/ops/lark-notify/validation.json' if notification_mode else None,'notification_runtime_evidence':'evidence/implementation/lark-notify-implementation-summary.json' if notification_mode else None,'pve_host_metrics':'runtime freshness is reported by guest manage.health; not requeried by static validator','native_promtool_amtool':'pending-on-assigned-AMD64-guest','source_docker_services_touched':False,'mac_background_scheduler_installed':False,'guest_baseline_preparation':{'status':'scripts-only-not-installed','targets':12,'offline_tests':33,'guest_or_host_commands_executed':False,'collector_started':False}}
    baseline_path=ROOT/'evidence/implementation/guest-monitoring-install.json'
    if baseline_path.exists():
        baseline=json.loads(baseline_path.read_text())
        guests=baseline.get('guests',[])
        done=[x for x in guests if x.get('status')=='installed-parked-verified']
        report['guest_baseline_preparation']={'status':baseline['status'],'as_of':baseline.get('finished_at') or baseline['started_at'],'scope':'install-only snapshot; later activation requires separate verification','targets':12,'installed_parked_count':len(done),'activated_count_during_install':0,'offline_tests':33,'guest_commands_executed':bool(guests),'pve_host_mutated':baseline['host_mutated'],'network_changed':baseline['network_changed'],'collector_started_during_install':baseline['collector_started'],'evidence':'evidence/implementation/guest-monitoring-install.json','current_guest_state_requeried':False}
    previous=json.loads((HERE/'validation.json').read_text()) if (HERE/'validation.json').exists() else {}
    native=previous.get('native_config_only')
    if native:
        current=all((HERE/name).exists() and hashlib.sha256((HERE/name).read_bytes()).hexdigest()==digest for name,digest in native['input_sha256'].items())
        report['native_config_only']=native
        if not current:
            report['native_config_only']=dict(native,result='stale-inputs-recheck-required')
        report['native_promtool_amtool']='config-only-'+report['native_config_only']['result']+'-local-cached-amd64-tools'
        report['target_native_configuration_validation']='pending-on-assigned-guest'
    (HERE/'validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))

if __name__=='__main__':main()
