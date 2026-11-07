#!/usr/bin/env python3
"""NAS260-only, explicitly approved old40->19 source allowlist adaptation via official OMV."""
import hashlib,importlib.util,json,os,subprocess,sys,time
from pathlib import Path
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('tx',HERE/'guest_transaction.py');tx=importlib.util.module_from_spec(s);s.loader.exec_module(tx)
OLD='192.168.21.0/24 10.63.40.0/24 127.0.0.1'
NEW='192.168.21.0/24 192.168.19.0/24 127.0.0.1'
SHARES={'media':('32e8c383-753a-48b4-b397-9adf490bb0e1','4d1b0107-5fdc-40d9-aad2-7f5726e2f43c'),'games':('86815a17-f9cd-4c0e-b548-4266949b75d4','75bc36d3-dcf6-4787-b6e2-779365b18cf8'),'incoming':('c9c8d068-e056-4ed3-be78-775118367582','0053215c-e4e3-4e83-b736-c23fdaba3d49')}
FIELDS=['hosts allow','hosts deny','valid users','read list','write list','read only','guest ok']


def read_objects():
 values=json.loads(tx.command(['/usr/sbin/omv-confdbadm','read','--prettify','conf.service.smb.share']).stdout);values=values if isinstance(values,list) else [values]
 return {name:next(x for x in values if x['uuid']==ids[0] and x['sharedfolderref']==ids[1]) for name,ids in SHARES.items()}


def effective():
 return {name:{key:tx.command(['/usr/bin/testparm','-s','--section-name='+name,'--parameter-name='+key]).stdout.decode().strip() for key in FIELDS} for name in SHARES}


def rpc(params):
 payload=json.dumps({'service':'SMB','method':'setShare','params':params}).encode()
 p=subprocess.run(['/usr/bin/php8.4','-c','/etc/openmediavault','/opt/dell/nas-stage/omv-rpc-stdin.php'],input=payload,capture_output=True,timeout=60,env=tx.ENV)
 try:reply=json.loads(p.stdout)
 except ValueError:raise RuntimeError('OMV SMB setter result unconfirmed') from None
 if p.returncode or reply.get('status')!='ok':raise RuntimeError('OMV SMB setter failed; details withheld')


def main():
 if sys.argv[1:]!=['--apply-reviewed-network19-allowlist']:raise RuntimeError('exact reviewed network-only action required')
 r=tx.guard(260,'new');nonce='1c97ce46e0e8494aa67f95768a818753';folder=Path('/root/dell-network19-media/260')/nonce
 j=json.loads(tx.read(folder/'journal.json'));tx.prove_protected(r,j)
 assert j['phase']=='runtime-ready-final-app-verification-pending'
 path=folder/'smb-network-policy.json'
 if path.exists():raise RuntimeError('policy transaction already exists; inspect instead of blindly retry')
 assert Path('/srv/salt/omv/deploy/samba').is_dir()
 model=json.loads(tx.read('/usr/share/openmediavault/datamodels/rpc.smb.json'));model=model if isinstance(model,list) else [model];schemas=[x for x in model if x.get('id')=='rpc.smb.setshare'];assert len(schemas)==1
 properties=schemas[0]['params']['properties'];assert 'hostsallow' in properties and properties['hostsallow']['type']=='string'
 old=read_objects();before=effective();params={};desired={}
 for name,obj in old.items():
  assert obj['hostsallow']==OLD and before[name]['hosts allow']==OLD
  assert before[name]['valid users']=='naswriter nasreader' and before[name]['read list']=='nasreader' and before[name]['write list']=='naswriter' and before[name]['guest ok']=='No'
  assert all(k in obj for k,v in properties.items() if v.get('required'))
  params[name]={k:obj[k] for k in properties if k in obj}
  desired[name]=dict(params[name],hostsallow=NEW)
 record={'phase':'prepared','role':260,'old_parameters':params,'new_parameters':desired,'effective_before':before,'protected_hashes':tx.protected(r),'at':time.time()};tx.save(path,record)
 changed=[]
 try:
  record['phase']='setting-official-OMV-network-allowlists';tx.save(path,record)
  for name in SHARES:rpc(desired[name]);changed.append(name)
  after_config=read_objects()
  for name in SHARES:
   candidate=dict(after_config[name]);candidate['hostsallow']=OLD
   assert candidate==old[name],'Non-network share field changed'
  tx.command(['/usr/sbin/omv-salt','deploy','run','samba'],timeout=240)
  after=effective()
  for name in SHARES:
   assert after[name]['hosts allow']==NEW
   assert all(after[name][k]==before[name][k] for k in FIELDS if k!='hosts allow')
  tx.prove_protected(r,j);record['phase']='applied-verified';tx.save(path,record)
 except Exception:
  current=read_objects()
  safe=all(dict(current[name],hostsallow=OLD)==old[name] and current[name]['hostsallow'] in [OLD,NEW] for name in SHARES)
  if safe:
   for name in changed:rpc(params[name])
   tx.command(['/usr/sbin/omv-salt','deploy','run','samba'],timeout=240);record['phase']='rolled-back-after-failure'
  else:record['phase']='unconfirmed-third-party-field-drift-no-overwrite'
  tx.save(path,record);raise RuntimeError('network policy adaptation unconfirmed; private backup retained') from None
 result={'role':260,'status':'official-SMB-network-allowlists-adapted-no-auth-or-permission-change','old_allowlist':OLD,'new_allowlist':NEW,'shareIDs':{name:ids[0] for name,ids in SHARES.items()},'all_other_OMV_share_fields_unchanged':True,'effective_users_groups_read_write_guest_policies_unchanged':True,'root_shadow_key_guard_bytes_unchanged':True,'official_setter_and_samba_Salt':True,'no_ALL_expansion_or_account_change':True,'private_backup_mode600':True}
 tx.save(folder/'smb-network-policy-result.json',result);print(json.dumps(result))


if __name__=='__main__':
 try:main()
 except Exception:
  print(json.dumps({'role':260,'status':'SMB-network-policy-adaptation-unconfirmed','raw_private_details_withheld':True}));raise SystemExit(1)
