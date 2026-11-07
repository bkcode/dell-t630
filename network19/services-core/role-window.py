#!/usr/bin/env python3
"""Manager opens only the explicitly authorized per-role action, with current trusted target."""
import argparse,datetime,json,shlex,sys
from pathlib import Path
sys.dont_write_bytecode=True
H=Path(__file__).resolve().parent;R=H.parents[1];sys.path.insert(0,str(R/'scripts'));import control
P=r'''import json,sys,subprocess,hashlib,os,socket
from pathlib import Path
v=json.loads(sys.stdin.read());vmid=v['vmid'];role=v['role'];action=v['action'];root=Path('/root/dell-network19/staged/services-core-v1')
if os.geteuid()!=0 or socket.gethostname().split('.')[0]!=role or Path('/etc/pve').exists():raise SystemExit('fixed-role-only')
backup_checks=[]
def lark_identity():
 p=subprocess.run(['systemctl','show','dell-lark-notify.service','--property=MainPID,ActiveState,SubState,NRestarts'],capture_output=True,text=True,timeout=10)
 identity={'unit':dict(l.split('=',1) for l in p.stdout.splitlines() if '=' in l),'public_files':{},'secret_metadata':{}}
 for path in ['/usr/local/libexec/dell-lark-notify/bridge.py','/etc/dell-lark-notify/policy.json','/opt/dell/ops/lark-notify-state.json','/opt/dell/ops/config/alertmanager/alertmanager.yml','/opt/dell/ops/compose.yaml']:
  identity['public_files'][path]=hashlib.sha256(Path(path).read_bytes()).hexdigest()
 for path in ['/etc/dell-lark-notify/secrets/lark-webhook','/opt/dell/ops/secrets/lark-bridge-token']:
  st=Path(path).stat();identity['secret_metadata'][path]={'inode':st.st_ino,'mtime_ns':st.st_mtime_ns,'uid':st.st_uid,'gid':st.st_gid,'mode':st.st_mode&0o777,'bytes_not_read':True}
 p=subprocess.run(['docker','--host','unix:///var/run/docker.sock','network','inspect','--format','{{json .IPAM.Config}}','dell-ops_default'],capture_output=True,text=True,timeout=10);identity['IPAM']=json.loads(p.stdout)
 return identity
if vmid==270 and action=='quiesce':
 identity=lark_identity();file=root/'ops-preservation-before.json'
 if file.exists():raise SystemExit('Ops preservation already exists; no overwrite')
 file.write_text(json.dumps(identity));file.chmod(0o600)
if action=='quiesce' and vmid in [200,201]:
 paths={200:['f106e23107d34c0bba39a4c006dd1891'],201:['6c706257613d40228cf2611d94276e26','b260debe1b5a4e0d9ea6657226a927cb']}[vmid]
 for name in paths:
  folder=Path('/srv/dell-data/_app_backups')/name;m=json.loads((folder/'manifest.json').read_text())
  for file,expected in m['files'].items():
   p=folder/file
   with p.open('rb') as f:matched=hashlib.file_digest(f,'sha256').hexdigest()==expected
   if not matched:raise SystemExit('existing-application-backup-integrity-failed')
   backup_checks.append({'component':m['component'],'file':file,'SHA_matches':True,'retained_in_place_not_exported':True})
identity_file=(Path('/srv/dell-data/prod-db/mysql/auto.cnf') if vmid==200 else Path('/srv/dell-data/test-data/mysql/auto.cnf') if vmid==210 else None)
identity_before=hashlib.sha256(identity_file.read_bytes()).hexdigest() if identity_file is not None and action=='commit-start' else None
receipt=root/('window-'+action+'.json');receipt.write_text(json.dumps({'migration':'network19','vmid':vmid,'action':action,'parent_window_open':True}));receipt.chmod(0o600)
if vmid==270 and action=='commit-start':
 gate=root/'window-commit-ops-targets.json';gate.write_text(json.dumps({'migration':'network19','vmid':270,'phase':'commit-ops-targets','parent_window_open':True}));gate.chmod(0o600)
 check=subprocess.run(['python3','-I','-B',str(root/'ops-targets-commit.py'),'--contract-dir',str(root),'--root-receipt',str(gate),'--apply-quiesced'],capture_output=True,text=True,timeout=30)
 if check.returncode:print(json.dumps({'status':'Ops-target-commit-failed-role-stays-quiesced'}));raise SystemExit(1)
p=subprocess.run(['python3','-I','-B',str(root/'core-role-executor.py'),'--vmid',str(vmid),'--action',action,'--contract-dir',str(root),'--root-receipt',str(receipt)],capture_output=True,text=True,timeout=420)
try:x=json.loads(p.stdout)
except Exception:x={'status':'no-sanitized-role-receipt'}
x['existing_app_backups_checked_before_quiesce']=backup_checks
if vmid==270:
 before=json.loads((root/'ops-preservation-before.json').read_text());x['long_lived_Lark_17218_public_config_secret_metadata_preserved']=lark_identity()==before
 if not x['long_lived_Lark_17218_public_config_secret_metadata_preserved']:p=type('R',(),{'returncode':1})()
if identity_before is not None:
 x['MySQL_persisted_server_identity_unchanged']=hashlib.sha256(identity_file.read_bytes()).hexdigest()==identity_before
 if not x['MySQL_persisted_server_identity_unchanged']:p=type('Result',(),{'returncode':1})()
print(json.dumps(x));raise SystemExit(p.returncode)
'''
def main():
 p=argparse.ArgumentParser();p.add_argument('--vmid',type=int,choices=[200,201,210,270],required=True);p.add_argument('--action',choices=['inspect','quiesce','commit-start','health','rollback-after-old-OS'],required=True);a=p.parse_args();role=next(r for r in json.loads((H/'contract.json').read_text())['roles'] if r['vmid']==a.vmid)
 migrated=json.loads((R/'network19/evidence/migrated-access.json').read_text())['targets'];old=next(x['target'] for x in json.loads((R/'evidence/implementation/private-guest-access.json').read_text())['roles'] if x['target']['vmid']==a.vmid);info=migrated.get(str(a.vmid),old)
 if a.action=='commit-start' and info['ip']!=role['new_ip']:raise SystemExit('root verified newtarget required')
 res=control.guest(a.vmid,'sudo -n python3 -I -B -c '+shlex.quote(P),data=json.dumps({'vmid':a.vmid,'role':role['role'],'action':a.action}).encode(),timeout=460,info=info)
 try:x=json.loads(res['stdout'])
 except Exception:raise SystemExit('no safe role receipt; do not retry blindly')
 (H/('role'+str(a.vmid)+'-'+a.action+'-evidence.json')).write_text(json.dumps({'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'exit_code':res['exit_code'],'target':info,'result':x},indent=2)+'\n');print(json.dumps(x));return res['exit_code']
if __name__=='__main__':raise SystemExit(main())
