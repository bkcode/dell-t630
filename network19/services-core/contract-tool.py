#!/usr/bin/env python3
"""Local only: canonical installed Publisher patches + explicit config migration plans."""
import ast,datetime,hashlib,io,json,re,tokenize
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parents[1]
I=json.loads((H/'inventory.json').read_text());ROWS={r['vmid']:r for r in I['roles']};M=json.loads((R/'network19/migration-plan.json').read_text());IP={r['old_ip']:r['new_ip'] for r in M['guest_addresses'] if r.get('old_ip','').startswith('10.63.')}
REV='network19-v1';COMMON='finger-common.'+REV+'.yaml'
DATAIDS={'finger-common.yaml':COMMON,**{x+'.yaml':x+'.'+REV+'.yaml' for x in ['finger-service-system','finger-service-coms','finger-auth','finger-bff-system']},'finger-gateway-mobile-lan-v2.yaml':'finger-gateway-mobile-lan-v2.'+REV+'.yaml'}
PUB={220:{'/usr/local/bin/dell-publish':'publisher_client220.py'},240:{'/usr/local/libexec/dell-publish-test240':'publisher_root.py','/usr/local/libexec/dell-publisher-dispatch':'publisher_dispatch.py','/usr/local/libexec/dell-publisher/publisher_protocol.py':'publisher_protocol.py','/usr/local/libexec/dell/deploy-test-chain.py':'fixed-deploy-test-chain.py'}}

def endpoint(value):
 # Only public installed-source literals or allowlisted config scalar values reach here.
 new=value.replace('http://192.168.21.22:19999','http://192.168.19.45:9999')
 for old,target in IP.items():new=re.sub(r'(?<![0-9])'+re.escape(old)+r'(?![0-9])',lambda _:target,new)
 return new

def patch_python(text,is_protocol=False):
 edits=[];stream=[]
 for tok in tokenize.generate_tokens(io.StringIO(text).readline):
  if tok.type==tokenize.STRING:
   try:value=ast.literal_eval(tok.string)
   except (ValueError,SyntaxError):value=None
   if isinstance(value,str):
    new=DATAIDS.get(value,endpoint(value))
    if new!=value:edits.append({'line':tok.start[0],'old':value,'new':new});tok=tok._replace(string=repr(new))
  stream.append(tok)
 output=tokenize.untokenize(stream)
 if is_protocol:
  old="CONFIG_IDS={name:name+'.yaml' for name in NAMES}\nCONFIG_IDS['finger-gateway-mobile']='"+DATAIDS['finger-gateway-mobile-lan-v2.yaml']+"'"
  mapping={name:DATAIDS['finger-gateway-mobile-lan-v2.yaml'] if name=='finger-gateway-mobile' else DATAIDS[name+'.yaml'] for name in ['finger-service-system','finger-service-coms','finger-auth','finger-bff-system','finger-gateway-mobile']}
  if output.count(old)!=1:raise RuntimeError('canonical CONFIG_IDS setup differs; no broad rewrite')
  output=output.replace(old,'CONFIG_IDS='+repr(mapping));edits.append({'structural_patch':'only CONFIG_IDS exact2-line setup→versioned whitelist; validation algorithm unchanged'})
 ast.parse(output)
 return output,edits

def main():
 outdir=H/'prepared/publisher';records=[]
 for vmid,files in PUB.items():
  for path,name in files.items():
   item=ROWS[vmid]['files'][path];source=H/item['captured_public_source'];data=source.read_bytes();deployed=R/'infra/publisher/deployed'/('vm'+str(vmid))/name
   if hashlib.sha256(data).hexdigest()!=item['sha256'] or data!=deployed.read_bytes():raise RuntimeError('installed/deployed canonical hash mismatch; pending candidates forbidden')
   output,edits=patch_python(data.decode(),name=='publisher_protocol.py');folder=outdir/('vm'+str(vmid));folder.mkdir(parents=True,exist_ok=True);p=folder/name;p.write_text(output)
   records.append({'vmid':vmid,'installed_path':path,'source_sha256':item['sha256'],'canonical_deployed_snapshot_equal':True,'prepared_path':str(p.relative_to(H)),'prepared_sha256':hashlib.sha256(output.encode()).hexdigest(),'edits':edits,'deployed':False})
 fixed=next(r['prepared_sha256'] for r in records if r['installed_path']=='/usr/local/libexec/dell/deploy-test-chain.py')
 plan={'status':'prepared-not-deployed','revision':REV,'source_active_release':ROWS[240]['current_release'],'new_issuer':'http://192.168.19.45:9999','new_COMS_domain':'http://192.168.19.45:9999/finger-bff-system/dell-test-files','Nacos_dataId_mapping':DATAIDS,'publisher_files':records,'new_policy_fields':{'target_ip':'192.168.19.45','fixed_deployer_sha256':fixed,'baseline_migrated':'false until fresh manager new-network baseline check; then true'},'policy_other_fields':'copy on guest unchanged; namespace never replaced','client_profile_patch':{'path':'/etc/dell-publisher/client-test240.json','target_host':{'old':'10.63.20.20','new':'192.168.19.45'},'source_ip':{'old':'10.63.30.10','new':'192.168.19.30'},'other_fields':'unchanged'},'authorized_key_patch':{'path':'/etc/ssh/authorized_keys/deployer','only_exact_from_option':{'old':'10.63.30.10','new':'192.168.19.30'},'key_bytes_forced_command_restrict':'unchanged'},'readiness':{'fixed_path':'/root/dell-java-test-readiness.json','new_target_ip':'192.168.19.45','recreate_after_new_network_validation':True,'do_not_relabel_old_proof':True},'no_pending_quiescence_code_used':True,'no_secret_values_or_target_writes':True}
 (H/'prepared-public-contract.json').write_text(json.dumps(plan,indent=2)+'\n')
 # Existing immutable release/config remains untouched; plan public-safe exact paths only.
 db=json.loads((H/'database-inventory.json').read_text());patches=[];active=set(DATAIDS)
 for row in next(x['Nacos_configs'] for x in db['results'] if x['vmid']==210):
  if row['data_id'] not in active:continue
  changes=[{'path':x['path'],'expected':x['value'],'new':endpoint(x['value'])} for x in row['safe_internal_endpoint_values'] if endpoint(x['value'])!=x['value']]
  patches.append({'source_dataId':row['data_id'],'target_dataId':DATAIDS[row['data_id']],'source_content_sha256':row['content_sha256'],'group_unchanged':row['group_id'],'namespace_preservation_sha256':row['namespace_sha256'],'allowed_changes':changes,'publish_mode':'new ID only; never overwrite source/historical ID'})
 (H/'nacos-patch-contract.json').write_text(json.dumps({'revision':REV,'status':'not-published','configs':patches,'all_secrets_and_other_values_copied_only_inside_guest':True,'Nacos_password_namespace_vhost_unchanged':True},indent=2)+'\n')
 print(json.dumps({'prepared_public_programs':len(records),'Nacos_fresh_IDs':len(patches),'new_fixed_deployer_SHA256':fixed,'installed_canonical_only':True,'target_writes':0}))
if __name__=='__main__':main()
