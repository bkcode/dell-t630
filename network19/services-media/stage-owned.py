#!/usr/bin/env python3
"""Approved standby only: upload public tools, preflight, new private stage. No quiesce/commit."""
import argparse
import base64
import concurrent.futures
import datetime
import hashlib
import json
from pathlib import Path
import sys
import uuid

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'scripts'));import control
control.BASE+=['-o','ForwardAgent=no']
manifest=json.loads((HERE/'manifest.sha256.json').read_text());files={}
for name in ['guest_transaction.py','patches.py']:
 raw=(HERE/name).read_bytes()
 if hashlib.sha256(raw).hexdigest()!=manifest[name]:raise SystemExit('Reviewed public tool SHA differs')
 files[name]=base64.b64encode(raw).decode()
ROLE_NAMES={250:'penpot-service',221:'artifact-service',260:'nas-media'}
SCRIPT=r'''
import ast,base64,datetime,hashlib,importlib.util,json,os,socket,stat,subprocess,sys,tempfile
from pathlib import Path
sys.dont_write_bytecode=True
ROLE=NUMBER;NONCE=WINDOW;FILES=PUBLIC
if os.geteuid()!=0 or Path('/etc/pve').exists() or socket.gethostname().split('.')[0]!=EXPECTED:raise SystemExit('assigned guest only')
os.umask(0o077)
BASE=Path('/opt/dell/network19/services-media')
for path in [Path('/opt'),Path('/opt/dell')]:
 if path.resolve()!=path or path.stat().st_uid!=0 or path.stat().st_mode&0o022:raise SystemExit('trusted parent required')
for path in [Path('/opt/dell/network19'),BASE]:
 path.mkdir(mode=0o700,exist_ok=True)
 if path.resolve()!=path or path.stat().st_uid!=0 or stat.S_IMODE(path.stat().st_mode)!=0o700:raise SystemExit('private public-tool directory required')
if set(FILES)!={'guest_transaction.py','patches.py'}:raise SystemExit('public payload exact file set required')
for name,value in FILES.items():
 raw=base64.b64decode(value);ast.parse(raw.decode());path=BASE/name
 if path.exists() and hashlib.sha256(path.read_bytes()).digest()!=hashlib.sha256(raw).digest():raise SystemExit('existing public tool differs; no blind overwrite')
for name,value in FILES.items():
 raw=base64.b64decode(value);path=BASE/name
 if path.exists():continue
 fd,tmp=tempfile.mkstemp(prefix='.public-stage-',dir=BASE)
 with os.fdopen(fd,'wb') as stream:os.fchmod(stream.fileno(),0o555);stream.write(raw);stream.flush();os.fsync(stream.fileno())
 os.replace(tmp,path)
spec=importlib.util.spec_from_file_location('media_tx',BASE/'guest_transaction.py');tx=importlib.util.module_from_spec(spec);spec.loader.exec_module(tx)
r=tx.ROLES[ROLE]
def pid_metadata():
 fmt='{"id":{{json .Id}},"pid":{{json .State.Pid}},"started_at":{{json .State.StartedAt}}}'
 return [json.loads(tx.command(tx.D+['inspect','--type','container','--format',fmt,n]).stdout) for n in r['names']]
def hash_files(paths):return {x:hashlib.sha256(Path(x).read_bytes()).hexdigest() for x in paths}
before_files=hash_files(r['files']);before_protected=hash_files(r['protected']);before=tx.state(r);before_pids=pid_metadata()
result={'role':ROLE,'status':'standby-stage-started','tools_upload':'public-only','at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
if ROLE==250:
 head=subprocess.run(['git','--no-optional-locks','-C','/opt/dell/penpot/source','rev-parse','HEAD'],capture_output=True,text=True,check=True).stdout.strip()
 dirty=subprocess.run(['git','--no-optional-locks','-C','/opt/dell/penpot/source','status','--porcelain=v1'],capture_output=True,text=True,check=True).stdout.strip()
 if head!='ff1783e7865af7aae571c985f03e057631b7af63' or dirty:raise SystemExit('Git provenance differs')
 result['Git_HEAD']=head;result['Git_clean']=True
for action in ['preflight','stage']:
 args=['/usr/bin/python3','-I','-B',str(BASE/'guest_transaction.py'),action,'--role',str(ROLE)]
 if action=='stage':args+=['--window',NONCE]
 p=subprocess.run(args,capture_output=True,text=True,timeout=240)
 try:value=json.loads(p.stdout)
 except ValueError:value={}
 result[action]={'exit_code':p.returncode,'status':value.get('status','no-public-status')}
 if p.returncode:break
after=tx.state(r)
result['active_files_unchanged']=before_files==hash_files(r['files'])
result['protected_identity_bytes_unchanged']=before_protected==hash_files(r['protected'])
after_pids=pid_metadata()
result['production_container_PID_ID_startedAt_image_health_unchanged']=before==after and before_pids==after_pids
result['containers']=[{k:v for k,v in x.items() if k in ['name','id','image','running','health']} for x in after]
result['PID_metadata_before']=before_pids
result['PID_metadata_after']=after_pids
result['stage_directory']='/root/dell-network19-media/'+str(ROLE)+'/'+NONCE
result['private_backup_and_journal_permissions']=False
folder=Path(result['stage_directory'])
if (folder/'journal.json').is_file():
 j=json.loads((folder/'journal.json').read_text());result['journal_phase']=j['phase'];result['staged_files_count']=len(j['files'])
 result['private_backup_and_journal_permissions']=folder.stat().st_uid==0 and stat.S_IMODE(folder.stat().st_mode)==0o700 and all(x.is_file() and x.stat().st_uid==0 and stat.S_IMODE(x.stat().st_mode)==0o600 for x in folder.iterdir())
result['status']='standby-staged-no-active-change' if result.get('stage',{}).get('exit_code')==0 and all(result[k] for k in ['active_files_unchanged','protected_identity_bytes_unchanged','production_container_PID_ID_startedAt_image_health_unchanged','private_backup_and_journal_permissions']) else 'standby-stage-unconfirmed-no-cutover'
print(json.dumps(result))
'''

def run(role,targets,nonce):
 code=SCRIPT.replace('NUMBER',str(role)).replace('WINDOW',repr(nonce)).replace('EXPECTED',repr(ROLE_NAMES[role])).replace('PUBLIC',repr(files))
 value=control.guest(role,'sudo python3 -',data=code.encode(),timeout=330,info=targets[role])
 if value['exit_code']:return {'role':role,'status':'standby-stage-command-failed','raw_details_withheld':True}
 try:out=json.loads(value['stdout'])
 except ValueError:return {'role':role,'status':'standby-stage-no-public-receipt','raw_details_withheld':True}
 return out


def main():
 p=argparse.ArgumentParser();p.add_argument('--parent-approved-standby',action='store_true',required=True);p.add_argument('--roles',nargs='+',type=int,choices=list(ROLE_NAMES),default=list(ROLE_NAMES));p.add_argument('--reuse-existing-nonces',action='store_true');a=p.parse_args()
 targets={x['target']['vmid']:x['target'] for x in json.loads((ROOT/'evidence/implementation/private-guest-access.json').read_text())['roles']}
 if a.reuse_existing_nonces:
  nonces={int(k):v for k,v in json.loads((HERE/'stage-nonces.json').read_text()).items()}
 else:
  if (HERE/'stage-nonces.json').exists():raise SystemExit('Existing nonce ledger; do not silently create replacement windows')
  nonces={role:uuid.uuid4().hex for role in a.roles}
  (HERE/'stage-nonces.json').write_text(json.dumps({str(k):v for k,v in nonces.items()},indent=2)+'\n')
 # Read-only SHA/state + target-local private backup; no service/NIC operations.
 with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:results=list(pool.map(lambda role:run(role,targets,nonces[role]),a.roles))
 previous=json.loads((HERE/'standby-stage-result.json').read_text()) if (HERE/'standby-stage-result.json').exists() else {'roles':[]}
 byrole={x['role']:x for x in previous['roles']};byrole.update({x['role']:x for x in results})
 receipt={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'approved-standby-upload-preflight-private-stage-only','nonces':nonces,'roles':[byrole[k] for k in sorted(byrole)],'quiesce_commit_start_or_network_actions_executed':False,'secret_values_or_hashes_emitted':False}
 (HERE/'standby-stage-result.json').write_text(json.dumps(receipt,indent=2)+'\n')
 for result in results:print(json.dumps({'role':result['role'],'status':result['status']}))
 if any(x['status']!='standby-staged-no-active-change' for x in results):raise SystemExit(1)


if __name__=='__main__':main()
