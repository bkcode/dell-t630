#!/usr/bin/env python3
"""VM210 only: secure bundle install and owned synthetic data acceptance."""
from pathlib import Path, PurePosixPath
import datetime
import hashlib
import importlib.util
import io
import json
import shlex
import sys
import tarfile

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'private/data/bundles/test-data'
OUT = ROOT / 'evidence/implementation/test-data-deployment.json'
spec = importlib.util.spec_from_file_location('dell_control', ROOT / 'scripts/control.py')
control = importlib.util.module_from_spec(spec);spec.loader.exec_module(control)
EXPECTED_UUID = 'dd1773f9-aa48-4401-a9c8-caf0f66845f3'
EXPECTED_CODE = {'scripts/manage.py':'b86e6c8339fc3ebc9151258849d78276d91e179692be588ce5bcdd344b341a10',
                 'scripts/acceptance.py':'79077300d3643f9b338da0858a8357b22e77a1bf2d9db50d2193f186555ae8c1',
                 'scripts/redis-entrypoint.sh':'bd98984ec702712d5222ed1f21f2956e1922f044e09ef44c9a3f924928fb6f88',
                 'compose.yaml':'6f5041cb3f2165d360864981a7357f9ab0bb5267cee31a36f7312b180fcfd93a'}

def clock():return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat()
def write(value):
    temp=OUT.with_suffix('.json.tmp');temp.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n');temp.chmod(0o600);temp.replace(OUT)

INSTALL = r'''
import os,sys,io,json,tarfile,hashlib,subprocess,socket,platform
from pathlib import Path,PurePosixPath
os.umask(0o077)
assert os.geteuid()==0 and socket.gethostname()=='data-test' and platform.machine() in ['x86_64','amd64'] and not Path('/etc/pve').exists()
ips={x.get('local') for row in json.loads(subprocess.check_output(['ip','-j','address'],text=True)) for x in row.get('addr_info',[]) if x.get('family')=='inet'};assert '10.63.20.10'in ips
mount=json.loads(subprocess.check_output(['findmnt','-J','-M','/srv/dell-data','-o','TARGET,SOURCE,UUID,FSTYPE,OPTIONS'],text=True))['filesystems'][0];assert mount['uuid']=='dd1773f9-aa48-4401-a9c8-caf0f66845f3' and mount['target']=='/srv/dell-data' and 'rw'in mount['options'].split(',')
state=subprocess.check_output(['systemctl','show','dell-data-test-data.service','-p','ActiveState','--value'],text=True).strip();assert state in ['inactive','failed',''],'Supervisor no longer paused'
root=Path('/opt/dell/data/test-data');assert root.resolve(strict=False)==root
assert not (root/'acceptance-fixture.json').exists(),'Existing fixture retained; stop'
data=sys.stdin.buffer.read(10*1024*1024+1);assert len(data)<=10*1024*1024
items=[]
with tarfile.open(fileobj=io.BytesIO(data),mode='r:') as archive:
 members=archive.getmembers();assert len(members)<200
 for member in members:
  relative=PurePosixPath(member.name);assert not relative.is_absolute() and '..'not in relative.parts and member.name and not member.issym() and not member.islnk()
  assert member.isdir() or member.isfile()
  dest=root.joinpath(*relative.parts);assert dest.resolve(strict=False)==dest
  payload=archive.extractfile(member).read() if member.isfile() else None
  if member.isfile() and relative.parts[0]=='secrets' and dest.exists():
   assert dest.is_file() and not dest.is_symlink() and dest.read_bytes()==payload,'Existing secret differs; refuse password rotation'
  items.append((member,dest,payload))
root.mkdir(mode=0o700,parents=True,exist_ok=True);root.chmod(0o700)
for member,dest,payload in items:
 if member.isdir():dest.mkdir(mode=0o700,parents=True,exist_ok=True);dest.chmod(0o700);continue
 dest.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
 mode=0o600 if PurePosixPath(member.name).parts[0]=='secrets' or member.name=='.env' else member.mode&0o777
 temporary=dest.with_name('.'+dest.name+'.bundle-install-tmp');assert not temporary.is_symlink()
 with temporary.open('wb') as stream:stream.write(payload)
 temporary.chmod(mode);os.chown(temporary,0,0);os.replace(temporary,dest)
print(json.dumps({'bundle_installed':True,'role':'test-data','hostname':'data-test','file_count':sum(x[0].isfile() for x in items),'payload_sha256':hashlib.sha256(data).hexdigest(),'secret_values_emitted':False,'existing_passwords_not_rotated':True,'data_uuid':mount['uuid']}))
'''
SNAPSHOT = r'''
import json,socket,subprocess
from pathlib import Path
assert socket.gethostname()=='data-test' and not Path('/etc/pve').exists()
root=Path('/opt/dell/data/test-data')
base=['docker','--host','unix:///var/run/docker.sock','compose','--env-file',str(root/'.env'),'-f',str(root/'compose.yaml')]
ids=subprocess.check_output(base+['ps','--all','--quiet'],text=True).split()
fmt='{"id":{{json .Id}},"service":{{json (index .Config.Labels "com.docker.compose.service")}},"started_at":{{json .State.StartedAt}},"state":{{json .State.Status}},"health":{{json .State.Health.Status}}}'
rows=[json.loads(l) for l in subprocess.check_output(['docker','--host','unix:///var/run/docker.sock','container','inspect','--format',fmt]+ids,text=True).splitlines()]
p=subprocess.check_output(['systemctl','show','dell-data-test-data.service','-p','ActiveState','-p','SubState','-p','MainPID','-p','NRestarts'],text=True)
print(json.dumps({'containers':rows,'supervisor':dict(l.split('=',1) for l in p.splitlines() if '='in l)}))
'''
RESTART = r'''
import importlib.util,subprocess,sys,socket
from pathlib import Path
sys.dont_write_bytecode=True
assert socket.gethostname()=='data-test' and not Path('/etc/pve').exists()
root=Path('/opt/dell/data/test-data')
subprocess.run(['systemctl','restart','dell-data-test-data.service'],check=True,capture_output=True,timeout=240)
spec=importlib.util.spec_from_file_location('test_data_manager',root/'scripts/manage.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
c=m.cfg();m.preflight(c);m.wait_healthy(startup_exit_grace=15);m.health(c)
'''

def main():
    assert len(sys.argv)==1
    report=json.loads(OUT.read_text());assert report['status']=='preflight-passed' and not report['stages'],'Prior attempt retained; do not blindly redeploy'
    roles=json.loads((ROOT/'evidence/implementation/private-guest-access.json').read_text())['roles'];assigned=next(x for x in roles if x['target']['vmid']==210);assert assigned['name']=='data-test' and assigned['target']['ip']=='10.63.20.10';target=assigned['target']
    for name,wanted in EXPECTED_CODE.items():assert hashlib.sha256((SOURCE/name).read_bytes()).hexdigest()==wanted,'Locked repair bundle changed'
    stream=io.BytesIO()
    with tarfile.open(fileobj=stream,mode='w') as archive:
        for path in sorted(SOURCE.rglob('*')):
            assert not path.is_symlink();relative=path.relative_to(SOURCE).as_posix();member=tarfile.TarInfo(relative);member.mtime=0;member.uid=member.gid=0
            if path.is_dir():member.type=tarfile.DIRTYPE;member.mode=0o700;archive.addfile(member)
            elif path.is_file():payload=path.read_bytes();member.size=len(payload);member.mode=path.stat().st_mode&0o777;archive.addfile(member,io.BytesIO(payload))
            else:raise RuntimeError('Unexpected bundle item type')
    payload=stream.getvalue();report['locked_code_sha256']=EXPECTED_CODE;report['status']='in-progress';write(report)
    def stage(name,command,data=None,timeout=120):
        entry={'name':name,'started_at':clock(),'status':'in-progress'};report['stages'].append(entry);write(report);print('STAGE_START '+name+' '+clock(),flush=True)
        result=control.guest(210,command,data=data,timeout=timeout,info=target)
        entry['exit_code']=result['exit_code'];entry['completed_at']=clock()
        if result['exit_code']:
            entry['status']='failed-private-output-suppressed';report['status']='failed-stopped-no-cleanup';write(report);raise RuntimeError('Guest210 '+name+' failed; sensitive output retained only in guest private logs')
        lines=[l for l in result['stdout'].splitlines() if l.strip()]
        value=json.loads(lines[-1]);entry['status']='passed';entry['result']=value;write(report);print('STAGE_OK '+name+' '+clock(),flush=True);return value
    def remote_python(code,timeout=120):return ('sudo -n python3 -',code.encode(),timeout)
    def script(action,acceptance=False):return shlex.join(['sudo','-n','python3','/opt/dell/data/test-data/scripts/'+('acceptance.py' if acceptance else 'manage.py'),action])
    try:
        install=stage('secure-bundle-install',shlex.join(['sudo','-n','python3','-c',INSTALL]),payload)
        assert install['payload_sha256']==hashlib.sha256(payload).hexdigest()
        stage('manager-preflight',script('check'))
        stage('deploy-health',script('deploy'),timeout=1800)
        stage('explicit-health',script('health'))
        stage('real-authentication',script('auth',True))
        print('INFRA_HEALTH_AND_AUTH_READY_CONTROLLED_RESTART_NEXT '+clock(),flush=True)
        stage('prepare-owned-fixture',script('prepare',True))
        stage('verify-fixture-before-restart',script('verify',True))
        before=stage('before-restart-processes',*remote_python(SNAPSHOT))
        stage('controlled-supervisor-restart-and-health',*remote_python(RESTART,900))
        after=stage('after-restart-processes',*remote_python(SNAPSHOT))
        before_by={r['service']:r for r in before['containers']};after_by={r['service']:r for r in after['containers']}
        assert len(before_by)==len(after_by)==4 and set(before_by)==set(after_by)
        assert all(after_by[k]['started_at']!=before_by[k]['started_at'] and after_by[k]['state']=='running' and after_by[k]['health']=='healthy' for k in before_by)
        report['controlled_restart_process_transition_verified']=True;write(report)
        verified=stage('verify-persistence-after-restart',script('verify',True))
        required=['mysql_fixture_persisted','redis_fixture_persisted','nacos_fixture_persisted','rabbit_durable_fixture_persisted'];assert all(verified['result'].get(k) is True for k in required)
        stage('cleanup-owned-fixture-only',script('cleanup',True))
        stage('final-health',script('health'))
        report['status']='test-data-ready-authenticated-persistence-restart-verified-fixture-cleaned';report['completed_at']=clock();report['secrets_values_emitted']=False;report['real_business_messages_sent']=False;report['source_business_data_imported']=False;write(report)
        print('TEST_DATA_FULLY_READY '+clock(),flush=True)
    except Exception as exc:
        report['status']='failed-stopped-no-cleanup';report['error_type']=type(exc).__name__;report['error_summary']='Target-only stage stopped; do not delete data or rotate credentials; inspect protected target logs';report['failed_at']=clock();write(report);raise

if __name__=='__main__':
    main()
