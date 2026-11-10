#!/usr/bin/env python3
"""One owned server canary; existing clients only read/check metadata, never write."""
import concurrent.futures,datetime,json,sys,uuid
from pathlib import Path
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts'));import control
known=json.loads((ROOT/'evidence/implementation/private-guest-access.json').read_text())['roles']
targets={x['target']['vmid']:x['target'] for x in known if x.get('target',{}).get('vmid') in [230,240]}
targets[280]=json.loads((ROOT/'completion/20261109-resources/guest-access.json').read_text())['target']
nonce=uuid.uuid4().hex
folder='.nfs-only-acceptance-'+nonce
body='nfs-only-shared-read-acceptance-'+nonce+'\n'
SERVER=r'''
import json,os,socket,stat,subprocess
from pathlib import Path
ACTION=ACTION_VALUE;FOLDER=FOLDER_VALUE;BODY=BODY_VALUE
assert os.geteuid()==0 and socket.gethostname()=='resource-service'and not Path('/etc/pve').exists()
def run(args):return subprocess.check_output(args,stderr=subprocess.PIPE,text=True,timeout=10).strip()
assert json.loads(run(['python3','-I','-B','/opt/dell/resources/guard.py','--role','server']))['mount_guard']
base=Path('/srv/resources')/FOLDER;file=base/'canary.txt'
if ACTION=='create':
 assert not base.exists()and not base.is_symlink()
 base.mkdir(mode=0o2770);os.chown(base,999,2980);base.chmod(0o2770)
 fd=os.open(file,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o660)
 with os.fdopen(fd,'w')as stream:os.fchown(stream.fileno(),999,2980);os.fchmod(stream.fileno(),0o660);stream.write(BODY);stream.flush();os.fsync(stream.fileno())
 print(json.dumps({'owned_canary_created':True,'owner_UID':999,'group_GID':2980,'directory_mode':'2770','file_mode':'0660'}))
elif ACTION=='cleanup':
 assert base.is_dir()and not base.is_symlink()and base.stat().st_uid==999 and base.stat().st_gid==2980
 assert set(p.name for p in base.iterdir())=={'canary.txt'}and file.is_file()and not file.is_symlink()and file.read_text()==BODY
 file.unlink();base.rmdir();assert not base.exists()
 print(json.dumps({'owned_canary_cleaned':True}))
else:raise ValueError('fixed-action-required')
'''
CLIENT=r'''
import json,os,socket,subprocess
from pathlib import Path
ROLE=ROLE_VALUE;FOLDER=FOLDER_VALUE;BODY=BODY_VALUE
assert os.geteuid()==0 and socket.gethostname()=={230:'java-prod-01',240:'java-test-01'}[ROLE]and not Path('/etc/pve').exists()
def run(args):return subprocess.check_output(args,stderr=subprocess.PIPE,text=True,timeout=12).strip()
guard=json.loads(run(['python3','-I','-B','/opt/dell/resources/guard.py','--role','client-'+str(ROLE)]))
check="from pathlib import Path;import json,os;root=Path('/mnt/resources')/"+repr(FOLDER)+";p=root/'canary.txt';assert p.read_text()=="+repr(BODY)+";s=p.stat();assert s.st_uid==999 and s.st_gid==2980 and s.st_mode&0o777==0o660;assert os.access(root,os.W_OK);print(json.dumps({'finger_read_server_canary':True,'canary_UID':999,'canary_GID':2980,'canary_mode':'0660','write_permission_check_only':True,'client_file_writes':False}))"
value=json.loads(run(['runuser','-u','finger','--','python3','-c',check]))
rows=json.loads(run(['findmnt','-J','--mountpoint','/mnt/resources','-t','nfs4','-o','TARGET,SOURCE,FSTYPE,OPTIONS']))['filesystems'];assert len(rows)==1 and rows[0]['source']=='192.168.19.80:/'
print(json.dumps({'vmid':ROLE,'guard':guard,'real_NFS_mount':rows[0],**value,'client_services_restarted':False}))
'''
def invoke(role,code):
 r=control.guest(role,'sudo -n python3 -',data=code.encode(),timeout=90,info=targets[role])
 if r['exit_code']:raise RuntimeError('readonly-or-owned-canary-check-unconfirmed-'+str(role))
 return json.loads(r['stdout'])
def server(action):return invoke(280,SERVER.replace('ACTION_VALUE',repr(action)).replace('FOLDER_VALUE',repr(folder)).replace('BODY_VALUE',repr(body)))
created=False
try:
 create=server('create');created=True
 def one(role):return invoke(role,CLIENT.replace('ROLE_VALUE',str(role)).replace('FOLDER_VALUE',repr(folder)).replace('BODY_VALUE',repr(body)))
 with concurrent.futures.ThreadPoolExecutor(max_workers=2)as pool:clients=list(pool.map(one,[230,240]))
finally:
 if created:clean=server('cleanup')
result={'at':datetime.datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),'status':'current-NFS-mount-and-cross-client-read-verified','server_canary':create,'clients':clients,'cleanup':clean,'server_business_or_existing_files_read_modified':False,'client_file_writes':False,'NFS_or_client_service_restarts':False,'actual_client_write_test_performed':False,'historical_cross_client_write_acceptance':'completion/20261109-resources/native-acceptance.json','scope':'new owned server canary read by both real mounted NFS clients as finger; no client writes, no business file reads'}
Path(__file__).with_name('NFS-verification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
