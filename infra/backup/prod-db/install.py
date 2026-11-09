import sys,json,base64,hashlib
from pathlib import Path
sys.path.insert(0,'scripts');import control
base=Path('infra/backup/prod-db');e=Path('completion/20261109-prod-db-scope')
def entries(mapping):return {dest:{'data':base64.b64encode((base/src).read_bytes()).decode(),'sha':hashlib.sha256((base/src).read_bytes()).hexdigest(),'mode':mode}for src,(dest,mode)in mapping.items()}
guest=entries({'guest-worker.py':('/usr/local/libexec/dell-prod-db-backup/guest-worker.py',0o600),'policy-guest.json':('/etc/dell-prod-db-backup/policy.json',0o600)})
host=entries({'host-worker.py':('/usr/local/libexec/dell-prod-db-backup/host-worker.py',0o600),'qga-bridge.pl':('/usr/local/libexec/dell-prod-db-backup/qga-bridge.pl',0o600),'policy-host.json':('/etc/dell-prod-db-backup/policy.json',0o600),'dell-prod-db-backup.service':('/etc/systemd/system/dell-prod-db-backup.service',0o644),'dell-prod-db-backup.timer':('/etc/systemd/system/dell-prod-db-backup.timer',0o644)})
COMMON=r'''import os,socket,pathlib,stat,json,base64,hashlib,subprocess
assert os.geteuid()==0
SPEC=PAYLOAD
DIRS=DIRECTORIES
for name in DIRS:
 p=pathlib.Path(name);assert not p.exists()and not p.is_symlink(), 'new owned dir already exists; inspect instead of rerun'
 p.mkdir(mode=0o700,parents=True);p.chmod(0o700)
result={}
for name,v in SPEC.items():
 p=pathlib.Path(name);assert p.parent.resolve()==p.parent and not p.exists()and not p.is_symlink()
 raw=base64.b64decode(v['data']);assert hashlib.sha256(raw).hexdigest()==v['sha']
 fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,v['mode'])
 with os.fdopen(fd,'wb')as f:f.write(raw);f.flush();os.fsync(f.fileno())
 result[name]=v['sha']
'''
G=r'''assert socket.gethostname()=='data-prod-db'and not pathlib.Path('/etc/pve').exists()
fs=json.loads(subprocess.check_output(['findmnt','-J','--mountpoint','/srv/dell-data','-o','TARGET,UUID'],text=True))['filesystems'];assert len(fs)==1 and fs[0]['uuid']=='d61c0e22-941e-447a-9e9a-1e9e50deb02f'
'''
# Identity and UUID are checked before mutations.
imports="import os,socket,pathlib,stat,json,base64,hashlib,subprocess\nassert os.geteuid()==0\n"
s=imports+G+COMMON.replace('PAYLOAD',repr(guest)).replace('DIRECTORIES',repr(['/usr/local/libexec/dell-prod-db-backup','/etc/dell-prod-db-backup','/srv/dell-data/_prod_db_backups']))+"\nprint(json.dumps({'status':'guest-fixed-logical-worker-installed-no-export-yet','public_SHA':result,'database_or_service_changes':False}))"
info=next(r['target']for r in json.loads(Path('evidence/implementation/private-guest-access.json').read_text())['roles']if r['target']['vmid']==200)
r=control.guest(200,'sudo -n python3 -I -B -',data=s.encode(),info=info,timeout=50);assert r['exit_code']==0,'guest installunconfirmed; inspect before retry';e.joinpath('guest-install.json').write_text(r['stdout']);print(r['stdout'])
H=r'''assert socket.gethostname()=='pve'and pathlib.Path('/etc/pve').is_dir()
fs=json.loads(subprocess.check_output(['findmnt','-J','--mountpoint','/mnt/pve/store','-o','TARGET,UUID'],text=True))['filesystems'];assert len(fs)==1 and fs[0]['uuid']=='75e5b438-5ff3-4139-83d6-b6a6847aedac'
j=json.loads(subprocess.check_output(['pvesh','get','/cluster/backup/dell-local-nightly','--output-format','json'],text=True));assert j['enabled']==0
'''
s=imports+H+COMMON.replace('PAYLOAD',repr(host)).replace('DIRECTORIES',repr(['/usr/local/libexec/dell-prod-db-backup','/etc/dell-prod-db-backup','/var/lib/dell-prod-db-backup','/mnt/pve/store/dell-artifacts/prod-db-backups']))+r'''
for args in [['perl','-c','/usr/local/libexec/dell-prod-db-backup/qga-bridge.pl'],['systemd-analyze','verify','/etc/systemd/system/dell-prod-db-backup.service','/etc/systemd/system/dell-prod-db-backup.timer'],['systemctl','daemon-reload']]:
 p=subprocess.run(args,capture_output=True,text=True,timeout=30);assert p.returncode==0,'native program/unit validation failed; inspect private sources'
print(json.dumps({'status':'PVE-logical-worker-and-disabled-timer-installed','public_SHA':result,'old_VM_job_enabled':False,'new_timer_enabled':False,'payload_exported':False}))
'''
r=control.pve('python3 -I -B -',data=s.encode(),timeout=90).decode();e.joinpath('host-install.json').write_text(r);print(r)
