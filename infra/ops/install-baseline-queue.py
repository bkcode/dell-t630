#!/usr/bin/env python3
"""Explicit new-guest install-only queue; does not change host network or business services."""
import datetime,hashlib,importlib.util,io,json,shlex,subprocess,sys,tarfile,time
from pathlib import Path
from zoneinfo import ZoneInfo
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[2]
TOOLS=ROOT/'infra/ops/guest-baseline'
EVIDENCE=ROOT/'evidence/implementation'
ALLOWED=[200,201,210,220,221,230,231,240,250,260,270,232]
FILES=['install-guest-baseline.py','collect-guest-health.py','guest-targets.json']
spec=importlib.util.spec_from_file_location('dell_control',ROOT/'scripts/control.py');control=importlib.util.module_from_spec(spec);spec.loader.exec_module(control)

def now():return datetime.datetime.now(ZoneInfo('Asia/Shanghai')).isoformat()

def save(path,data):
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')

META=r'''import os,json,socket,platform,subprocess,hashlib,stat
from pathlib import Path
p=Path('/usr/sbin/policy-rc.d');policy={'exists':p.exists() or p.is_symlink()}
if policy['exists']:
 s=p.lstat();policy.update(mode=stat.S_IMODE(s.st_mode),uid=s.st_uid,gid=s.st_gid,inode=s.st_ino,device=s.st_dev,kind='symlink' if p.is_symlink() else 'regular')
 policy['identity']=os.readlink(p) if p.is_symlink() else hashlib.sha256(p.read_bytes()).hexdigest()
def cmd(a):
 p=subprocess.run(a,capture_output=True,text=True,timeout=15);return p.returncode,p.stdout.strip()
values={}
for line in Path('/etc/os-release').read_text().splitlines():
 if '=' in line:
  k,v=line.split('=',1);values[k]=v.strip('"')
virt=cmd(['systemd-detect-virt','--vm'])
ips=json.loads(cmd(['ip','-j','address','show'])[1]);addresses=[x['local'] for a in ips for x in a.get('addr_info',[]) if x.get('family')=='inet']
docker=cmd(['dpkg-query','--show','--showformat=${binary:Package}=${Version}\n','docker-ce','docker-ce-cli','containerd.io'])
units={}
for unit in ['prometheus-node-exporter.service','prometheus-node-exporter.socket','dell-guest-health.service','dell-guest-health.timer','docker.service']:
 units[unit]={'active':cmd(['systemctl','is-active',unit])[1],'enabled':cmd(['systemctl','is-enabled',unit])[1]}
listen=cmd(['ss','--listening','--numeric','--tcp','--udp','--no-header'])[1]
listeners=sorted({t for line in listen.splitlines() for t in line.split() if ':' in t and t.rsplit(':',1)[-1]=='9100'})
state=Path('/var/lib/dell-guest-monitoring/state.json')
print(json.dumps({'hostname':socket.gethostname().split('.')[0],'os_id':values.get('ID'),'os_version':values.get('VERSION_ID'),'architecture':platform.machine(),'virtualization':virt[1],'product_uuid':Path('/sys/class/dmi/id/product_uuid').read_text().strip().lower(),'pve_filesystem_present':Path('/etc/pve').exists(),'ipv4_addresses':addresses,'policy':policy,'policy_recovery_records':[x.name for x in Path('/usr/sbin').glob('.policy-rc.d.dell-*')],'docker_packages':sorted(docker[1].splitlines()),'units':units,'listeners_9100':listeners,'installer_receipt':json.loads(state.read_text()) if state.exists() else None}))'''

TRANSFER=r'''import io,os,tarfile,json,hashlib
from pathlib import Path
names={'install-guest-baseline.py','collect-guest-health.py','guest-targets.json'}
raw=__import__('sys').stdin.buffer.read(131073)
if len(raw)>131072:raise SystemExit('public tool archive too large')
p=Path('/tmp/dell-monitoring-prep')
if p.resolve(strict=False)!=p or p.is_symlink():raise SystemExit('unsafe temporary tool directory')
p.mkdir(mode=0o700,exist_ok=True)
if p.stat().st_uid!=os.getuid():raise SystemExit('temporary tool directory owner mismatch')
p.chmod(0o700)
with tarfile.open(fileobj=io.BytesIO(raw),mode='r:') as archive:
 members=archive.getmembers()
 if len(members)!=3 or {x.name for x in members}!=names or any(not x.isfile() or x.size>65536 for x in members):raise SystemExit('unexpected public tool archive entries')
 hashes={}
 for item in members:
  data=archive.extractfile(item).read();target=p/item.name
  fd=os.open(target,os.O_WRONLY|os.O_CREAT|os.O_TRUNC|os.O_NOFOLLOW,0o700 if item.name.endswith('.py') else 0o600)
  with os.fdopen(fd,'wb') as out:out.write(data)
  target.chmod(0o700 if item.name.endswith('.py') else 0o600);hashes[item.name]=hashlib.sha256(data).hexdigest()
print(json.dumps({'directory':str(p),'files_sha256':hashes,'secrets_included':False}))'''

def remote_metadata(target):
    result=control.guest(target['vmid'],'sudo -n python3 -',data=META.encode(),timeout=60,info=target)
    if result['exit_code']!=0:return result,None
    return result,json.loads(result['stdout'])

def main():
    if sys.argv[1:]!=['--execute-authorized-install-only']:raise SystemExit('explicit authorized install-only flag required')
    stage=json.loads((EVIDENCE/'guest-staging-storage.json').read_text())
    records={x['target']['vmid']:x for x in stage['roles']}
    if set(records)!=set(ALLOWED):raise RuntimeError('staging target scope differs from exact approved VM set')
    plan=json.loads((ROOT/'plan.json').read_text());plan_roles={r.get('vmid') or r.get('planned_vmid'):r['name'] for r in plan['roles'] if r['kind']=='vm'}
    if any(records[v]['name']!=plan_roles[v] for v in ALLOWED):raise RuntimeError('plan and staging role mismatch')
    hashes={name:hashlib.sha256((TOOLS/name).read_bytes()).hexdigest() for name in FILES}
    stream=io.BytesIO()
    with tarfile.open(fileobj=stream,mode='w') as tar:
        for name in FILES:
            data=(TOOLS/name).read_bytes();item=tarfile.TarInfo(name);item.mode=0o700 if name.endswith('.py') else 0o600;item.size=len(data);tar.addfile(item,io.BytesIO(data))
    archive=stream.getvalue()
    ids=json.dumps(ALLOWED)
    pve_script="import subprocess,json\nids="+ids+"\nout={}\nfor vmid in ids:\n p=subprocess.run(['qm','config',str(vmid)],capture_output=True,text=True,check=True)\n values=dict(x.split(': ',1) for x in p.stdout.splitlines() if ': ' in x)\n status=subprocess.run(['qm','status',str(vmid)],capture_output=True,text=True,check=True).stdout.strip()\n out[vmid]={'name':values.get('name'),'smbios1':values.get('smbios1'),'template':values.get('template','0'),'status':status}\nprint(json.dumps(out))"
    pve=json.loads(control.pve('python3 - <<\'PY\'\n'+pve_script+'\nPY',timeout=120))
    report={'started_at':now(),'scope':'new-guest-install-only','allowed_vmids':ALLOWED,'concurrency':1,'host_mutated':False,'network_changed':False,'activate_requested':False,'collector_started':False,'source_mac_scheduler_installed':False,'tool_sha256':hashes,'guests':[],'status':'running'}
    summary=EVIDENCE/'guest-monitoring-install.json';save(summary,report)
    for index,vmid in enumerate(ALLOWED):
        record=records[vmid];role=record['name'];target=record['target'];entry={'vmid':vmid,'role':role,'target':target,'started_at':now(),'status':'running'}
        report['guests'].append(entry);save(summary,report)
        print(json.dumps({'vmid':vmid,'role':role,'stage':'identity-preflight'}),flush=True)
        try:
            host=pve[str(vmid)]
            if host['name']!=role or host['template']!='0' or host['status']!='status: running':raise RuntimeError('PVE readonly role/running/instance verification failed')
            identity=next(x.split('=',1)[1] for x in host['smbios1'].split(',') if x.startswith('uuid=')).lower()
            response,before=remote_metadata(target);entry['preflight_result']=response
            if before is None and vmid==232 and response['exit_code']==255 and not any(x in response['stderr'] for x in ['REMOTE HOST IDENTIFICATION','Host key verification failed']):
                entry['approved_ssh_recheck']=True;print(json.dumps({'vmid':vmid,'stage':'single-approved-SSH-ready-recheck'}),flush=True);time.sleep(10)
                response,before=remote_metadata(target);entry['preflight_result']=response
            if before is None:raise RuntimeError('guest SSH preflight failed; queue stopped')
            entry['before']=before
            if before['hostname']!=role or before['product_uuid']!=identity or before['os_id']!='debian' or before['os_version']!='13' or before['architecture']!='x86_64' or before['virtualization'] not in ('kvm','qemu') or before['pve_filesystem_present'] or target['ip'] not in before['ipv4_addresses']:raise RuntimeError('guest role/VM/OS/virtualization identity mismatch')
            if before['policy_recovery_records']:raise RuntimeError('guest has unfinished policy recovery state; queue stopped')
            copied=control.guest(vmid,'python3 -c '+shlex.quote(TRANSFER),data=archive,timeout=60,info=target);entry['copy_result']=copied
            if copied['exit_code'] or json.loads(copied['stdout'])['files_sha256']!=hashes:raise RuntimeError('public tool transfer/checksum failed')
            print(json.dumps({'vmid':vmid,'role':role,'stage':'install-only'}),flush=True)
            cmd=shlex.join(['sudo','-n','python3','/tmp/dell-monitoring-prep/install-guest-baseline.py','--install-only','--role',role])
            result=control.guest(vmid,cmd,timeout=1800,info=target);entry['install_result']=result
            post,after=remote_metadata(target);entry['postflight_result']=post;entry['after']=after
            if result['exit_code']!=0:raise RuntimeError('install-only command failed; queue stopped without retry')
            if after is None:raise RuntimeError('post-install SSH readback failed')
            if before['policy']!=after['policy'] or after['policy_recovery_records']:raise RuntimeError('original policy object was not restored')
            if before['docker_packages']!=after['docker_packages'] or before['units']['docker.service']['active']!=after['units']['docker.service']['active']:raise RuntimeError('Docker package or service state changed')
            if after['hostname']!=role or after['product_uuid']!=identity or target['ip'] not in after['ipv4_addresses']:raise RuntimeError('guest identity/address changed')
            units=after['units'];receipt=after['installer_receipt']
            if after['listeners_9100'] or units['prometheus-node-exporter.service']['enabled']!='masked' or units['prometheus-node-exporter.service']['active'] not in ('inactive','failed','unknown') or units['prometheus-node-exporter.socket']['enabled']!='masked' or units['dell-guest-health.timer']['enabled'] not in ('disabled','masked') or units['dell-guest-health.timer']['active'] not in ('inactive','failed','unknown') or units['dell-guest-health.service']['active'] not in ('inactive','failed','unknown') or not receipt or receipt['mode']!='install-only' or receipt['vmid']!=vmid or receipt['exporter_enablement_links'] or receipt['socket_enablement_links']:raise RuntimeError('monitoring parked-state verification failed')
            entry.update(status='installed-parked-verified',finished_at=now(),policy_restored=True,docker_unchanged=True,port9100_listening=False,collector_timer_activated=False)
            print(json.dumps({'vmid':vmid,'role':role,'status':entry['status'],'package_version':receipt['package_version']}),flush=True)
        except Exception as error:
            entry.update(status='failed-stopped-queue',finished_at=now(),error=str(error));report.update(status='stopped-on-error',remaining_vmids=ALLOWED[index+1:])
            print(json.dumps({'vmid':vmid,'status':entry['status'],'error':str(error)}),flush=True)
            save(EVIDENCE/('guest-monitoring-vm'+str(vmid)+'.json'),entry);save(summary,report);return 1
        save(EVIDENCE/('guest-monitoring-vm'+str(vmid)+'.json'),entry);save(summary,report)
    report.update(status='12-new-guests-installed-parked-verified',finished_at=now());save(summary,report)
    print(json.dumps({'status':report['status'],'guest_count':len(report['guests']),'host_or_network_changed':False}),flush=True);return 0

if __name__=='__main__':raise SystemExit(main())
