#!/usr/bin/env python3
"""Prepared guest220/240 canonical IP-contract installer. Default inspect, no Java start."""
import argparse,fcntl,hashlib,json,os,socket,stat,subprocess,sys,tempfile
from pathlib import Path
class Refused(RuntimeError):pass

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def owned(p,private=False):
 if p.resolve()!=p or not p.is_file():raise Refused('trusted-canonical-file-required')
 s=p.stat()
 if s.st_uid!=0 or s.st_mode&(0o077 if private else 0o022):raise Refused('trusted-root-owner-mode-required')
 return s

def run(a):
 p=subprocess.run(a,capture_output=True,text=True,timeout=20)
 if p.returncode:raise Refused('native-check-failed:'+a[0])
 return p.stdout

def atomic(p,data,mode=0o600):
 fd,tmp=tempfile.mkstemp(prefix='.network19-publisher-',dir=p.parent)
 try:
  with os.fdopen(fd,'wb') as f:f.write(data);f.flush();os.fsync(f.fileno())
  os.chmod(tmp,mode);os.chown(tmp,0,0);os.replace(tmp,p)
 finally:
  if Path(tmp).exists():Path(tmp).unlink()

def marker(path,vmid,phase):
 if path is None:raise Refused('explicit-root600-window-required')
 owned(path,True);x=json.loads(path.read_text())
 if x.get('migration')!='network19' or x.get('vmid')!=vmid or x.get('phase')!=phase or x.get('parent_window_open') is not True or x.get('publisher_transactions_frozen') is not True:raise Refused('frozen-window-receipt-mismatch')
 return x

def check_release(root,identity,protocol,new):
 # Existing validated protocol is loaded only from the reviewed prepared SHA file.
 import importlib.util
 p=protocol;owned(p);s=importlib.util.spec_from_file_location('network19_protocol_check',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
 manifest,namespace=m.check_release(root,identity)
 for name in m.NAMES:
  cfg=root/name/'application.yaml';st=owned(cfg,True)
  if st.st_gid!=0 or st.st_mode&0o777!=0o600:raise Refused('release-config-root600-required')
 return manifest,namespace

def main():
 p=argparse.ArgumentParser();p.add_argument('--vmid',type=int,choices=[220,240],required=True);p.add_argument('--contract-dir',type=Path,required=True);p.add_argument('--mode',choices=['inspect','commit-fenced','enable-new-baseline'],default='inspect');p.add_argument('--root-receipt',type=Path);p.add_argument('--rollback-release-id');a=p.parse_args()
 role={220:'publish-service',240:'java-test-01'}[a.vmid];newip={220:'192.168.19.30',240:'192.168.19.45'}[a.vmid]
 if os.geteuid()!=0 or Path('/etc/pve').exists() or socket.gethostname().split('.')[0]!=role:raise Refused('assigned-publisher-role-only')
 contract=json.loads((a.contract_dir/'prepared-public-contract.json').read_text());files=[x for x in contract['publisher_files'] if x['vmid']==a.vmid]
 for item in files:
  candidate=a.contract_dir/item['prepared_path'];owned(candidate)
  if digest(candidate)!=item['prepared_sha256']:raise Refused('prepared-public-SHA-differs')
  active=Path(item['installed_path']);owned(active)
  expected=item['prepared_sha256'] if a.mode=='enable-new-baseline' else item['source_sha256']
  if digest(active)!=expected:raise Refused('actual-installed-canonical-SHA-changed')
 if a.mode=='inspect':print(json.dumps({'status':'inspected-no-target-write','vmid':a.vmid,'canonical_installed_files':len(files),'candidate_not_quiescence_source':True}));return
 receipt=marker(a.root_receipt,a.vmid,a.mode)
 addresses=json.loads(run(['ip','-j','addr']))
 if not any(x.get('local')==newip and x.get('prefixlen')==24 for r in addresses for x in r.get('addr_info',[])):raise Refused('new-role-IP-not-assigned')
 backup=Path('/root/dell-network19/publisher')/str(a.vmid);backup.mkdir(mode=0o700,parents=True,exist_ok=True)
 lock=None
 if a.vmid==240:
  lock=os.open('/run/lock/dell-publish-test240.lock',os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW,0o600);fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 try:
  if a.mode=='enable-new-baseline':
   if contract.get('java_application_deployment_allowed') is not True:raise Refused('user-scope-forbids-Java-baseline-enable')
   if a.vmid!=240 or not a.rollback_release_id:raise Refused('240-and-new-network-rollback-ID-required')
   readiness=Path('/root/dell-java-test-readiness.json');owned(readiness,True);ready=json.loads(readiness.read_text())
   required=['database_schemas_ready','nacos_configs_ready','network_policy_ready','issuer_candidate_acknowledged']
   if ready.get('target_ip')!='192.168.19.45' or ready.get('network_revision')!='network19' or not all(ready.get(k) is True for k in required) or not all(receipt.get(k) is True for k in ['new_DB_Host_validation','fresh_Nacos_dataIds_validation','new_issuer_metadata_validation','Java_5_service_functional_validation']):raise Refused('fresh-network19-ready-evidence-missing')
   current=Path('/opt/finger/current-test').resolve();releases=Path('/opt/finger/releases/test');rollback=releases/a.rollback_release_id
   if current.parent!=releases or rollback==current:raise Refused('distinct-managed-new-network-rollback-release-required')
   proto=next(a.contract_dir/x['prepared_path'] for x in contract['publisher_files'] if x['installed_path'].endswith('/publisher_protocol.py'))
   m,ns=check_release(current,current.name,proto,True);old,ns2=check_release(rollback,rollback.name,proto,True)
   if ns!=ns2:raise Refused('rollback-namespace-mismatch')
   for row in m['services']:
    try:
     import urllib.request
     with urllib.request.build_opener(urllib.request.ProxyHandler({})).open('http://192.168.19.45:'+str(row['port'])+'/actuator/health',timeout=3) as r:up=r.status==200 and json.load(r).get('status')=='UP'
    except Exception:up=False
    if not up:raise Refused('new-baseline-real-health-not-UP')
   path=Path('/etc/dell-publisher/test240-policy.json');owned(path,True);policy=json.loads(path.read_text())
   if policy['target_ip']!=newip or policy['fixed_deployer_sha256']!=contract['new_policy_fields']['fixed_deployer_sha256'] or policy['namespace_id']!=ns:raise Refused('new-policy-SHA-namespace-mismatch')
   policy['baseline_migrated']=True;atomic(path,(json.dumps(policy,indent=2)+'\n').encode());print(json.dumps({'status':'new-network-baseline-enabled','vmid':240,'same_environment_immutable_rollback_verified':True,'ready_proof_not_relabelled':True,'apps_started_by_helper':False}));return
  # Fence240 policy before changing any code. Existing immutable releases are never edited.
  if a.vmid==240:
   policy_path=Path('/etc/dell-publisher/test240-policy.json');owned(policy_path,True);policy=json.loads(policy_path.read_text());b=backup/'old-policy.json'
   if b.exists():raise Refused('publisher-backup-already-exists-no-blind-retry')
   atomic(b,policy_path.read_bytes());policy['baseline_migrated']=False;atomic(policy_path,(json.dumps(policy,indent=2)+'\n').encode())
  for item in files:
   active=Path(item['installed_path']);st=active.stat();b=backup/active.name
   if b.exists():raise Refused('installed-code-backup-exists')
   atomic(b,active.read_bytes());atomic(active,(a.contract_dir/item['prepared_path']).read_bytes(),stat.S_IMODE(st.st_mode))
  if a.vmid==220:
   path=Path('/etc/dell-publisher/client-test240.json');owned(path);x=json.loads(path.read_text())
   if x!={'target_host':'10.63.20.20','target_user':'deployer','host_key_alias':'dell-test240-publisher','source_ip':'10.63.30.10'}:raise Refused('old-client-profile-differs')
   atomic(backup/'old-client-profile.json',path.read_bytes());x.update(target_host='192.168.19.45',source_ip='192.168.19.30');atomic(path,(json.dumps(x,indent=2)+'\n').encode())
  else:
   policy.update(target_ip='192.168.19.45',fixed_deployer_sha256=contract['new_policy_fields']['fixed_deployer_sha256'],baseline_migrated=False);atomic(policy_path,(json.dumps(policy,indent=2)+'\n').encode())
   keys=Path('/etc/ssh/authorized_keys/deployer');owned(keys);text=keys.read_text();needle='from="10.63.30.10"'
   if text.count(needle)!=1:raise Refused('exact-authorized-key-from-option-differs')
   atomic(backup/'old-deployer-authorized_keys',keys.read_bytes());atomic(keys,text.replace(needle,'from="192.168.19.30"').encode());run(['sshd','-t']);run(['visudo','-cf','/etc/sudoers.d/dell-publisher-test240'])
  print(json.dumps({'status':'public-IP-contract-committed-fenced-until-fresh-baseline','vmid':a.vmid,'code_files':len(files),'actual_installed_source_only':True,'private_key_or_host_key_changed':False,'immutable_releases_DB_Nacos_or_apps_started_or_mutated':False,'secret_values_emitted':False}))
 finally:
  if lock is not None:os.close(lock)
if __name__=='__main__':
 try:main()
 except Exception as e:print(json.dumps({'status':'refused-or-failed','error_category':type(e).__name__,'reason':str(e) if isinstance(e,Refused) else 'details-withheld','rollback_requires_root_coordinated_network_contract':True}));sys.exit(1)
