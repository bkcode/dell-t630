#!/usr/bin/env python3
"""Prepared Data/Ops guest helper; default inspect, explicit root receipt for stage/commit."""
import argparse,hashlib,json,os,socket,stat,subprocess,sys,tempfile
from pathlib import Path
class Refused(RuntimeError):pass

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def trusted(p,private=False):
 if p.resolve()!=p or not p.is_file():raise Refused('canonical-file-required')
 st=p.stat()
 if st.st_uid!=0 or st.st_mode&(0o077 if private else 0o022):raise Refused('root-owner-mode-required')
 return st

def render(data,keys):
 # Preserve original bytes/newlines/quotes on all other keys, including credentials/namespace/vhost.
 result=[];found=set()
 for line in data.decode().splitlines(keepends=True):
  if '=' in line and not line.startswith('#'):
   key,value=line.rstrip('\r\n').split('=',1)
   if key in keys:
    expected,new=keys[key]['old'],keys[key]['new'];quote=value[:1] if value[:1] in ["'",'"'] else ''
    clean=value[1:-1] if quote and value.endswith(quote) else value
    if clean!=expected or key in found:raise Refused('exact-old-env-key-value-differs')
    ending='\r\n' if line.endswith('\r\n') else '\n' if line.endswith('\n') else ''
    line=key+'='+quote+new+quote+ending;found.add(key)
  result.append(line)
 if found!=set(keys):raise Refused('env-key-missing')
 return ''.join(result).encode()

def main():
 p=argparse.ArgumentParser();p.add_argument('--vmid',type=int,required=True);p.add_argument('--contract-dir',type=Path,required=True);p.add_argument('--mode',choices=['inspect','stage-private','commit-active'],default='inspect');p.add_argument('--root-receipt',type=Path);p.add_argument('--stage-root',type=Path,default=Path('/root/dell-network19/service-env'));a=p.parse_args()
 if a.vmid not in [200,201,210,270]:raise Refused('only-data-ops-env')
 recipe=next(r for r in json.loads((a.contract_dir/'data-ops-patch-contract.json').read_text())['files'] if r['vmid']==a.vmid and r['path'].endswith('/.env'))
 role={200:'data-prod-db',201:'data-prod-infra',210:'data-test',270:'ops-service'}[a.vmid]
 if os.geteuid()!=0 or Path('/etc/pve').exists() or socket.gethostname().split('.')[0]!=role:raise Refused('assigned-guest-only')
 active=Path(recipe['path']);st=trusted(active,True)
 if digest(active)!=recipe['source_sha256']:raise Refused('active-source-SHA-changed')
 old=active.read_bytes();new=render(old,recipe['exact_env_keys'])
 if a.mode=='inspect':print(json.dumps({'status':'inspected-no-write','vmid':a.vmid,'changed_keys':sorted(recipe['exact_env_keys']),'other_bytes_unchanged':True,'writes':0}));return
 if not a.root_receipt:raise Refused('explicit-window-receipt-required')
 trusted(a.root_receipt,True);r=json.loads(a.root_receipt.read_text())
 if r.get('migration')!='network19' or r.get('vmid')!=a.vmid or r.get('phase')!=a.mode or r.get('parent_window_open') is not True:raise Refused('root-window-mismatch')
 folder=a.stage_root/str(a.vmid)
 if not str(folder).startswith('/root/dell-network19/') or folder.resolve(strict=False)!=folder:raise Refused('fixed-private-stage-root-required')
 if a.mode=='stage-private':
  folder.mkdir(mode=0o700,parents=True,exist_ok=False)
  for name,data in [('old.env',old),('new.env',new)]:
   file=folder/name;file.write_bytes(data);file.chmod(0o600)
  state={'old_SHA256':digest(active),'new_SHA256':hashlib.sha256(new).hexdigest(),'active_path':str(active),'uid':st.st_uid,'gid':st.st_gid,'mode':stat.S_IMODE(st.st_mode),'changed_keys':sorted(recipe['exact_env_keys'])};file=folder/'stage.json';file.write_text(json.dumps(state));file.chmod(0o600)
  print(json.dumps({'status':'private-env-staged-not-committed','vmid':a.vmid,'credential_namespace_vhost_other_bytes_unchanged':True,'services_changed':False}));return
 metadata=folder/'stage.json';trusted(metadata,True);m=json.loads(metadata.read_text());pending=folder/'new.env';trusted(pending,True)
 if digest(pending)!=m['new_SHA256'] or digest(active)!=m['old_SHA256']:raise Refused('stage-active-integrity-conflict')
 newip=recipe['exact_env_keys']['SERVICE_IP']['new'];p=subprocess.run(['ip','-j','addr'],capture_output=True,text=True,timeout=10)
 if p.returncode or not any(a.get('local')==newip and a.get('prefixlen')==24 for link in json.loads(p.stdout) if 'UP' in link.get('flags',[]) for a in link.get('addr_info',[])):raise Refused('new-IP-not-UP-OScommit-required')
 unit={200:'dell-data-prod-db.service',201:'dell-data-prod-infra.service',210:'dell-data-test-data.service',270:'dell-ops.service'}[a.vmid]
 state=subprocess.run(['systemctl','is-active',unit],capture_output=True,text=True,timeout=10).stdout.strip()
 if state not in ['inactive','failed']:raise Refused('root-must-quiesce-role-before-env-commit')
 fd,tmp=tempfile.mkstemp(prefix='.network19-env-',dir=active.parent)
 try:
  with os.fdopen(fd,'wb') as out:out.write(new);out.flush();os.fsync(out.fileno())
  os.chown(tmp,m['uid'],m['gid']);os.chmod(tmp,m['mode']);os.replace(tmp,active)
 finally:
  if Path(tmp).exists():Path(tmp).unlink()
 print(json.dumps({'status':'env-committed-role-still-quiesced','vmid':a.vmid,'credential_namespace_vhost_unchanged':True,'role_start_by_root_pending':True,'services_changed_by_helper':False}))
if __name__=='__main__':
 try:main()
 except Exception as e:print(json.dumps({'status':'refused-or-failed','error_category':type(e).__name__,'reason':str(e) if isinstance(e,Refused) else 'details-withheld'}));sys.exit(1)
