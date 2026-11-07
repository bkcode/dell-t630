#!/usr/bin/env python3
"""Explicit stage window only: private backups/candidates, never quiesce/commit/restart/publish."""
import argparse,base64,datetime,json,shlex,sys
from pathlib import Path
sys.dont_write_bytecode=True
H=Path(__file__).resolve().parent;R=H.parents[1];sys.path.insert(0,str(R/'scripts'));import control
TOOLS=['contract.json','prepared-public-contract.json','nacos-patch-contract.json','data-ops-patch-contract.json','stage-commit-env.py','stage-java240.py','commit-publisher.py','mysql-hosts.py','sql-host-contract.json','apply-monitoring.py','core-role-executor.py']
P=r'''import json,sys,base64,os,socket,subprocess,hashlib,datetime
from pathlib import Path
v=json.loads(sys.stdin.read());vmid=v['vmid'];role=v['role'];root=Path('/root/dell-network19/staged/services-core-v1')
if os.geteuid()!=0 or Path('/etc/pve').exists() or socket.gethostname().split('.')[0]!=role:raise SystemExit('assigned-core-role-only')
for p in [Path('/root/dell-network19'),root.parent]:
 if p.resolve(strict=False)!=p:raise SystemExit('private-stage-symlink')
 p.mkdir(mode=0o700,exist_ok=True)
root.mkdir(mode=0o700,exist_ok=False)
for name,encoded in v['files'].items():
 if name.startswith('/') or '..' in Path(name).parts:raise SystemExit('stage-member-scope')
 path=root/name;path.parent.mkdir(mode=0o700,parents=True,exist_ok=True);fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
 with os.fdopen(fd,'wb') as f:f.write(base64.b64decode(encoded))
backup=root/'private-backup';backup.mkdir(mode=0o700)
reports=[]
def invoke(args):
 p=subprocess.run(args,capture_output=True,text=True,timeout=240)
 try:x=json.loads(p.stdout)
 except Exception:x={'status':'no-sanitized-result'}
 reports.append({'tool':Path(args[3]).name if len(args)>3 else 'helper','exit_code':p.returncode,'status':x.get('status')})
 if p.returncode:raise RuntimeError('stage-helper-refused; private source intact')
 return x
if vmid in [200,201,210,270]:
 receipt=root/'stage-env-window.json';receipt.write_text(json.dumps({'migration':'network19','vmid':vmid,'phase':'stage-private','parent_window_open':True}));receipt.chmod(0o600)
 invoke(['python3','-I','-B',str(root/'stage-commit-env.py'),'--vmid',str(vmid),'--contract-dir',str(root),'--mode','stage-private','--root-receipt',str(receipt)])
if vmid in [220,240]:
 public=json.loads((root/'prepared-public-contract.json').read_text())
 for item in public['publisher_files']:
  if item['vmid']!=vmid:continue
  path=Path(item['installed_path'])
  if hashlib.sha256(path.read_bytes()).hexdigest()!=item['source_sha256']:raise RuntimeError('installed-publisher-baseline-changed')
  target=backup/path.name;target.write_bytes(path.read_bytes());target.chmod(0o600)
 for source in (['/etc/dell-publisher/client-test240.json'] if vmid==220 else ['/etc/dell-publisher/test240-policy.json','/root/dell-java-test-readiness.json','/etc/ssh/authorized_keys/deployer']):
  path=Path(source);target=backup/path.name;target.write_bytes(path.read_bytes());target.chmod(0o600)
 invoke(['python3','-I','-B',str(root/'commit-publisher.py'),'--vmid',str(vmid),'--contract-dir',str(root),'--mode','inspect'])
if vmid==240:
 receipt=root/'stage-java-window.json';receipt.write_text(json.dumps({'migration':'network19','target_vmid':240,'allowed_phase':'stage-private','parent_window_open':True}));receipt.chmod(0o600)
 ids=v['release_pair']
 x=invoke(['python3','-I','-B',str(root/'stage-java240.py'),'--contract-dir',str(root),'--release-id',ids[0],'--rollback-release-id',ids[1],'--root-receipt',str(receipt),'--stage-private'])
 reports.append({'private_release_pair':ids,'all_secrets_namespace_vhost_unchanged':x.get('all_JARs_secrets_namespace_vhost_unchanged',False),'published_or_started':False})
print(json.dumps({'status':'private-backups-and-candidates-staged','vmid':vmid,'path':str(root),'reports':reports,'active_files_addresses_services_unchanged':True,'formal_apps_started':False,'Nacos_published':False,'secret_values_emitted':False}))
'''
def main():
 p=argparse.ArgumentParser();p.add_argument('--vmid',type=int,required=True,choices=[200,201,210,220,240,270]);a=p.parse_args();vmid=a.vmid
 role=next(x for x in json.loads((H/'contract.json').read_text())['roles'] if x['vmid']==vmid)
 files={n:base64.b64encode((H/n).read_bytes()).decode() for n in TOOLS}
 for path in (H/'prepared/publisher').rglob('*.py'):files[str(path.relative_to(H))]=base64.b64encode(path.read_bytes()).decode()
 for path in (H/'prepared/ops').rglob('*.json'):files[str(path.relative_to(H))]=base64.b64encode(path.read_bytes()).decode()
 now=datetime.datetime.now(datetime.timezone.utc);from datetime import timedelta
 state=H/'proposed-release-pair.json'
 if not state.exists():state.write_text(json.dumps({'primary':now.strftime('%Y%m%dT%H%M%S'),'rollback':(now+timedelta(seconds=1)).strftime('%Y%m%dT%H%M%S'),'status':'private-candidates-not-active'},indent=2)+'\n')
 pair=json.loads(state.read_text());v={'vmid':vmid,'role':role['role'],'files':files,'release_pair':[pair['primary'],pair['rollback']]}
 migrated=json.loads((R/'network19/evidence/migrated-access.json').read_text())['targets'];old=next(x['target'] for x in json.loads((R/'evidence/implementation/private-guest-access.json').read_text())['roles'] if x['target']['vmid']==vmid);info=migrated.get(str(vmid),old)
 r=control.guest(vmid,'sudo -n python3 -I -B -c '+shlex.quote(P),data=json.dumps(v).encode(),timeout=350,info=info)
 try:x=json.loads(r['stdout'])
 except Exception:raise SystemExit('private stage failed; active state untouched; no blind rerun')
 (H/('stage'+str(vmid)+'-evidence.json')).write_text(json.dumps({'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'exit_code':r['exit_code'],'result':x},indent=2)+'\n');print(json.dumps(x));return r['exit_code']
if __name__=='__main__':raise SystemExit(main())
