import sys,json,base64,hashlib
from pathlib import Path
sys.path.insert(0,'scripts');import control
root=Path('.');e=root/'completion/20261109-prod-db-restore'
def payload(files):
 return {dest:{'data':base64.b64encode(Path(src).read_bytes()).decode(),'sha256':hashlib.sha256(Path(src).read_bytes()).hexdigest()}for src,dest in files}
guest=payload([('infra/backup/prod-db/restore/target-worker.py','/usr/local/libexec/dell-prod-db-restore/target-worker.py'),('infra/backup/full-snapshot-restore/sql_snapshot.py','/usr/local/libexec/dell-prod-db-restore/sql_snapshot.py')])
host=payload([('infra/backup/prod-db/restore/host-drill.py','/usr/local/libexec/dell-prod-db-restore/host-drill.py'),('infra/backup/prod-db/restore/qga-restore.pl','/usr/local/libexec/dell-prod-db-restore/qga-restore.pl')])
COMMON=r'''import os,pathlib,stat,json,base64,hashlib,socket,subprocess
assert os.geteuid()==0
for name in DIRS:
 p=pathlib.Path(name);assert not p.exists()and not p.is_symlink(),'new dir exists; inspect before retry';p.mkdir(mode=0o700,parents=True);p.chmod(0o700)
result={}
for name,v in FILES.items():
 p=pathlib.Path(name);assert p.parent.resolve()==p.parent and not p.exists()and not p.is_symlink()
 raw=base64.b64decode(v['data']);assert hashlib.sha256(raw).hexdigest()==v['sha256']
 if p.suffix=='.py':compile(raw,str(p),'exec')
 fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
 with os.fdopen(fd,'wb')as f:f.write(raw);f.flush();os.fsync(f.fileno())
 result[name]=v['sha256']
'''
imports='import os,pathlib,stat,json,base64,hashlib,socket,subprocess\nassert os.geteuid()==0\n'
g=imports+r'''assert socket.gethostname()=='data-test'and not pathlib.Path('/etc/pve').exists()
fs=json.loads(subprocess.check_output(['findmnt','-J','--mountpoint','/srv/dell-data','-o','TARGET,UUID'],text=True))['filesystems'];assert len(fs)==1 and fs[0]['uuid']=='dd1773f9-aa48-4401-a9c8-caf0f66845f3'
'''+COMMON.replace('DIRS',repr(['/usr/local/libexec/dell-prod-db-restore','/srv/dell-data/_prod_db_restore_drill','/srv/dell-data/_prod_db_restore_drill/reports'])).replace('FILES',repr(guest))+"\nprint(json.dumps({'status':'isolated-target-helper-installed-no-restore-yet','target_vmid':210,'public_source_SHA':result,'existing_services_changed':False}))"
compile(g,'restore-target-install','exec');info=next(r['target']for r in json.loads(Path('evidence/implementation/private-guest-access.json').read_text())['roles']if r['target']['vmid']==210)
r=control.guest(210,'sudo -n python3 -I -B -',data=g.encode(),info=info,timeout=60);assert r['exit_code']==0,'target installunconfirmed; no blind retry';e.joinpath('target-install.json').write_text(r['stdout']);print(r['stdout'])
h=imports+r'''assert socket.gethostname()=='pve'and pathlib.Path('/etc/pve').is_dir()
fs=json.loads(subprocess.check_output(['findmnt','-J','--mountpoint','/mnt/pve/store','-o','TARGET,UUID'],text=True))['filesystems'];assert len(fs)==1 and fs[0]['uuid']=='75e5b438-5ff3-4139-83d6-b6a6847aedac'
'''+COMMON.replace('DIRS',repr(['/usr/local/libexec/dell-prod-db-restore','/var/lib/dell-prod-db-restore','/root/dell-bootstrap/prod-db-restore-20261109'])).replace('FILES',repr(host))+r'''
p=subprocess.run(['perl','-c','/usr/local/libexec/dell-prod-db-restore/qga-restore.pl'],capture_output=True,text=True,timeout=30);assert p.returncode==0,'native QGA bridge syntax unconfirmed'
print(json.dumps({'status':'PVE-drill-control-and-transport-installed-no-restore-yet','public_source_SHA':result,'native_perl_check':True,'backup_schedule_changed':False,'database_payload_copied':False}))'''
compile(h,'restore-host-install','exec');r=control.pve('python3 -I -B -',data=h.encode(),timeout=60).decode();e.joinpath('host-install.json').write_text(r);print(r)
