#!/usr/bin/env python3
"""Read-only DATA001 target-environment audit; never accesses old Mac credentials."""
import datetime,hashlib,json,re,shlex,stat,sys,urllib.parse
from pathlib import Path
from zoneinfo import ZoneInfo
import yaml
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'scripts'));import control
E=ROOT/'evidence/implementation/data-environment-isolation-final.json'
B=ROOT/'private/data/bundles';J=ROOT/'private/java';NAMES=['finger-service-system','finger-service-coms','finger-auth','finger-bff-system','finger-gateway-mobile'];RELEASE='20261106T121030'
TARGETS={x['target']['vmid']:x['target'] for x in json.loads((ROOT/'evidence/implementation/private-guest-access.json').read_text())['roles']}
D={'started_at':datetime.datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),'status':'in-progress','scope':'new-target-prod-test-infrastructure-and-test-Java-runtime-only','source_Mac_credentials_read':False,'service_configuration_or_SQL_modified':False,'password_values_or_hashes_emitted':False,'cross_instance_negative_auth':[]}
def save():
 p=E.with_suffix('.tmp');p.write_text(json.dumps(D,ensure_ascii=False,indent=2)+'\n');p.replace(E)
def secret(p):
 s=p.lstat();assert stat.S_ISREG(s.st_mode) and stat.S_IMODE(s.st_mode)==0o600
 value=p.read_text().strip();assert value;return value
ENVS={r:dict(l.split('=',1) for l in (B/r/'.env').read_text().splitlines() if l and not l.startswith('#') and '=' in l) for r in ['prod-db','prod-infra','test-data']}
def call(v,code,data=None,timeout=75):
 # Secrets, if any, are stdin JSON. The command argument contains static code only.
 r=control.guest(v,'sudo -n python3 -c '+shlex.quote(code),data=json.dumps(data).encode() if data is not None else None,timeout=timeout,info=TARGETS[v]);assert r['exit_code']==0,('target metadata query failed',v,r['exit_code']);return json.loads(r['stdout'])
def flatten(x,p=''):
 if isinstance(x,dict):
  for k,v in x.items():yield from flatten(v,p+'.'+str(k) if p else str(k))
 elif isinstance(x,list):
  for i,v in enumerate(x):yield from flatten(v,p+'.'+str(i))
 else:yield p,x
SQLCODE=r'''
import json,socket,subprocess,pathlib,ipaddress
p=json.load(__import__('sys').stdin);assert socket.gethostname()==p['hostname'] and not pathlib.Path('/etc/pve').exists()
r=subprocess.run(['docker','ps','--quiet','--filter','label=com.docker.compose.service=mysql'],capture_output=True,text=True,timeout=10);ids=r.stdout.split();assert r.returncode==0 and len(ids)==1
# A shell variable and anonymous pipe FD3 hold the correct new target root credential.
# There is no credential environment variable, argv value, persisted config or DML.
cmd="IFS= read -r mysql_pw < /run/secrets/mysql-root-password; [[ $mysql_pw =~ ^[A-Za-z0-9_-]{16,256}$ ]] || exit 41; exec 3< <(builtin printf '[client]\\nuser=root\\npassword=%s\\nprotocol=socket\\n' \"$mysql_pw\"); unset mysql_pw; exec mysql --defaults-extra-file=/dev/fd/3 --batch --skip-column-names"
r=subprocess.run(['docker','exec','-i',ids[0],'/bin/bash','-c',cmd],input=p['sql'],capture_output=True,text=True,timeout=40);assert r.returncode==0
print(json.dumps({'rows':[json.loads(x) for x in r.stdout.splitlines() if x.strip()],'authentication':'own-new-target-root-via-anonymous-FD3','credential_values_in_argv_or_environment':False,'SQL_kind':'SELECT-only','password_or_hash_columns_selected':False}))
'''
def sql_for(db):
 assert db in ['nacos_prod','nacos_test']
 return "\n".join([
 "SELECT JSON_OBJECT('kind','nacos_user','username',username,'enabled',enabled) FROM `"+db+"`.users;",
 "SELECT JSON_OBJECT('kind','nacos_role','username',username,'role',`role`) FROM `"+db+"`.roles;",
 "SELECT JSON_OBJECT('kind','nacos_permission','role',`role`,'resource',resource,'action',action) FROM `"+db+"`.permissions;",
 "SELECT JSON_OBJECT('kind','nacos_namespace','namespace_id',tenant_id,'namespace_name',tenant_name) FROM `"+db+"`.tenant_info;",
 "SELECT JSON_OBJECT('kind','mysql_account','user',User,'host',Host) FROM mysql.user WHERE User IN ('nacos_prod','nacos_test','finger_auth_test','finger_system_test','finger_coms_test');",
 "SELECT JSON_OBJECT('kind','schema_privilege','grantee',GRANTEE,'schema',TABLE_SCHEMA,'privilege',PRIVILEGE_TYPE,'grantable',IS_GRANTABLE) FROM information_schema.SCHEMA_PRIVILEGES WHERE GRANTEE LIKE '%finger_%' OR GRANTEE LIKE '%nacos_%';",
 "SELECT JSON_OBJECT('kind','table_privilege','grantee',GRANTEE,'schema',TABLE_SCHEMA,'table',TABLE_NAME,'privilege',PRIVILEGE_TYPE,'grantable',IS_GRANTABLE) FROM information_schema.TABLE_PRIVILEGES WHERE GRANTEE LIKE '%finger_%' OR GRANTEE LIKE '%nacos_%';",
 "SELECT JSON_OBJECT('kind','global_privilege','grantee',GRANTEE,'privilege',PRIVILEGE_TYPE,'grantable',IS_GRANTABLE) FROM information_schema.USER_PRIVILEGES WHERE GRANTEE LIKE '%finger_%' OR GRANTEE LIKE '%nacos_%';"])+"\n"
RUNTIMECODE=r'''
import pathlib,json,hashlib,socket,sys,subprocess
p=json.load(sys.stdin);assert socket.gethostname()=='java-test-01' and not pathlib.Path('/etc/pve').exists();current=pathlib.Path('/opt/finger/current-test').resolve();assert current.name==p['release'];out=[]
for name,h in p['expected_config_digests'].items():
 f=current/name/'application.yaml';s=f.stat();r=subprocess.run(['systemctl','show','dell-finger-'+name+'.service','-p','ActiveState','-p','User'],capture_output=True,text=True);u=dict(x.split('=',1) for x in r.stdout.splitlines() if '=' in x);out.append({'service':name,'live_bytes_equal_new_target_prepared_config':hashlib.sha256(f.read_bytes()).hexdigest()==h,'root600':s.st_uid==0 and s.st_gid==0 and s.st_mode&0o777==0o600,'unit':u})
print(json.dumps({'release':current.name,'configs':out,'config_contents_or_digests_emitted':False}))
'''
NACOSREAD=r'''
import json,pathlib,socket,sys,urllib.request,urllib.parse,hashlib
p=json.load(sys.stdin);assert socket.gethostname()=='data-test' and not pathlib.Path('/etc/pve').exists()
b=pathlib.Path('/opt/dell/data/test-data');env=dict(l.split('=',1) for l in (b/'.env').read_text().splitlines() if l and not l.startswith('#') and '=' in l);assert env['SERVICE_IP']=='10.63.20.10' and env['NACOS_CLIENT_USER']=='finger_test'
class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,*a,**k):return None
op=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect());base='http://10.63.20.10:8848/nacos'
data=urllib.parse.urlencode({'username':env['NACOS_CLIENT_USER'],'password':(b/'secrets/nacos-client-password').read_text().strip()}).encode()
with op.open(urllib.request.Request(base+'/v1/auth/users/login',data=data,method='POST',headers={'Content-Type':'application/x-www-form-urlencoded'}),timeout=15) as r:token=json.loads(r.read())['accessToken']
rows=[]
for dataid,h in p['expected_config_digests'].items():
 query=urllib.parse.urlencode({'tenant':env['NACOS_NAMESPACE_ID'],'group':'DELL_TEST','dataId':dataid});request=urllib.request.Request(base+'/v1/cs/configs?'+query,headers={'Authorization':'Bearer '+token})
 with op.open(request,timeout=15) as r:body=r.read(1000000);rows.append({'data_id':dataid,'http_status':r.status,'live_bytes_equal_new_target_prepared_config':hashlib.sha256(body).hexdigest()==h})
print(json.dumps({'server':'10.63.20.10:8848','namespace':env['NACOS_NAMESPACE_ID'],'group':'DELL_TEST','client':'finger_test','client_login_succeeded':True,'configs':rows,'contents_or_tokens_or_digests_emitted':False}))
'''
NEGATIVE=r'''
import json,sys,socket,pathlib,urllib.request,urllib.parse,urllib.error
p=json.load(sys.stdin);assert socket.gethostname()==p['hostname'] and not pathlib.Path('/etc/pve').exists();assert (p['ip'],p['username']) in [('10.63.10.11','finger_test'),('10.63.20.10','finger_prod')]
class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,*a,**k):return None
request=urllib.request.Request('http://'+p['ip']+':8848/nacos/v1/auth/users/login',data=urllib.parse.urlencode({'username':p['username'],'password':p['password']}).encode(),method='POST',headers={'Content-Type':'application/x-www-form-urlencoded'});status=None;token=False
try:
 with urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect()).open(request,timeout=15) as r:status=r.status;body=r.read(65536);parsed=json.loads(body);token=bool(parsed.get('accessToken'))
except urllib.error.HTTPError as e:status=e.code;e.read(65536);e.close()
print(json.dumps({'http_status':status,'denied':status in [401,403] and not token,'access_token_returned':token,'attempt_count':1,'response_body_discarded':True,'credential_values_in_argv_environment_url_or_logs':False}))
'''
def main():
 global D
 resuming='--resume-retained-v1-candidate' in sys.argv
 if resuming:
  D=json.loads(E.read_text());assert D['status']=='stopped-on-error' and D.get('error_class')=='AssertionError' and not D['cross_instance_negative_auth'] and set(D.get('live_catalogs',{}))=={'200','210'} and D['negative_auth_safety_preconditions']['opposite_username_absent']
  D['audit_preparation_note']='Initial local assertion counted retained inactive gateway-v1 document. It is intentionally preserved; audit now selects the six documents imported by current release. No credential negative attempt had occurred.';D['status']='in-progress';D.pop('error_class',None);safe=True;save()
 else:
  assert not E.exists(),'refuse repeat audit/negative credential attempts without manager review'
  save()
  D['bundle_instances']=[{'role':r,'environment':e['ENVIRONMENT'],'service_ip':e['SERVICE_IP'],'mysql_host':e['MYSQL_HOST'],'nacos_db':e['NACOS_DB_NAME'],'nacos_db_user':e['NACOS_DB_USER'],'nacos_namespace':e['NACOS_NAMESPACE_ID'],'nacos_client_user':e['NACOS_CLIENT_USER'],'nacos_client_role':e['NACOS_CLIENT_ROLE'],'rabbit_admin_user':e['RABBIT_ADMIN_USER'],'rabbit_app_user':e['RABBIT_APP_USER'],'rabbit_vhost':e['RABBIT_VHOST']} for r,e in ENVS.items()]
  comparisons={}
  for name in ['mysql-root-password','nacos-db-password','redis-password','rabbit-admin-password','rabbit-app-password','nacos-admin-password','nacos-client-password','nacos-auth-token','nacos-identity-value']:
   prod='prod-db' if name=='mysql-root-password' else 'prod-infra';a=secret(B/prod/'secrets'/name);b=secret(B/'test-data/secrets'/name);comparisons[name]={'new_target_prod_test_different':a!=b,'both_nonempty':bool(a and b)}
  assert all(x['new_target_prod_test_different'] for x in comparisons.values());D['new_target_secret_separation']=comparisons;D['prod_db_infra_nacos_db_secret_expected_shared']=secret(B/'prod-db/secrets/nacos-db-password')==secret(B/'prod-infra/secrets/nacos-db-password');save()
  D['live_catalogs']={}
  for v,role,db in [(200,'data-prod-db','nacos_prod'),(210,'data-test','nacos_test')]:D['live_catalogs'][str(v)]=call(v,SQLCODE,{'hostname':role,'sql':sql_for(db)})
  # Confirm application account sets exactly; official nacos admin is expected.
  sets={v:{x['username'] for x in c['rows'] if x['kind']=='nacos_user' and x['username']!='nacos'} for v,c in D['live_catalogs'].items()};safe=sets=={'200':{'finger_prod'},'210':{'finger_test'}};D['negative_auth_safety_preconditions']={'prod_application_users':sorted(sets['200']),'test_application_users':sorted(sets['210']),'official_nacos_admin_excluded_from_application_set':True,'different_expected_usernames':ENVS['prod-infra']['NACOS_CLIENT_USER']=='finger_prod' and ENVS['test-data']['NACOS_CLIENT_USER']=='finger_test','opposite_username_absent':safe};save()
 configs={name:yaml.safe_load((J/'releases'/RELEASE/name/'application.yaml').read_text()) for name in NAMES};active_dataids={'finger-common.yaml','finger-auth.yaml','finger-service-system.yaml','finger-service-coms.yaml','finger-bff-system.yaml','finger-gateway-mobile-lan-v2.yaml'};nacosfiles={f.name:f for f in (J/'test-chain/nacos-configs/DELL_TEST').glob('*.yaml') if f.name in active_dataids};assert set(nacosfiles)==active_dataids;D['inactive_retained_nacos_candidate_documents']=[f.name for f in (J/'test-chain/nacos-configs/DELL_TEST').glob('*.yaml') if f.name not in active_dataids]
 nc={name:yaml.safe_load(p.read_text()) for name,p in nacosfiles.items()};ns=ENVS['test-data']['NACOS_NAMESPACE_ID'];runtime=[]
 for name,c in configs.items():
  spring=c['spring'];n=spring['cloud']['nacos'];ds=spring.get('datasource');d=None
  if ds:
   u=urllib.parse.urlsplit(ds['url'].removeprefix('jdbc:'));assert u.hostname=='10.63.20.10' and u.port==3306 and not u.username and not u.password;d={'host':u.hostname,'port':u.port,'schema':u.path.lstrip('/'),'user':ds['username'],'client_host':'10.63.20.20'}
  assert n['server-addr']=='10.63.20.10:8848' and n['username']=='finger_test' and all(n[x]['namespace']==ns and n[x]['group']=='DELL_TEST' for x in ['config','discovery'])
  assert all('group=DELL_TEST' in x and not x.startswith('optional:') for x in spring['config']['import'])
  runtime.append({'service':name,'datasource':d,'datasource_absent_when_not_required':ds is None,'nacos_server':n['server-addr'],'nacos_namespace':ns,'nacos_group':'DELL_TEST','nacos_user':n['username'],'all_config_imports_mandatory_test_group':True})
 common=nc['finger-common.yaml'];sms=common['sms'];sms_empty={provider:{k: v=='' for k,v in values.items()} for provider,values in sms.items()};assert all(v for x in sms_empty.values() for v in x.values());sargia=configs['finger-auth']['sargia']['accounts']['oauth'];u=urllib.parse.urlsplit(sargia['public-url']);assert u.hostname=='10.63.20.20' and u.port==9 and sargia['client-id']=='disabled-in-dell-test'
 approved={secret(B/'test-data/secrets'/n) for n in ['nacos-client-password','redis-password','rabbit-app-password']};approved.update(secret(J/'secrets'/n) for n in ['db-auth-password','db-system-password','db-coms-password','oauth-finger-admin-secret','oauth-finger-merchant-secret','oauth-finger-app-secret','oauth-finger-web-secret']);credential_fields=[];external_fields=[]
 for origin,c in list(configs.items())+list(nc.items()):
  for key,value in flatten(c):
   if re.search(r'(?i)(password|secret|token|access[-_]?key[-_]?id|access[-_]?key[-_]?secret|api[-_]?key)$',key.split('.')[-1]):
    empty=value in [None,''];known=empty or value in approved;credential_fields.append({'config':origin,'field':key,'empty':empty,'matches_explicit_new_target_credential_or_empty':known});assert known
   if re.search(r'(?i)(broker|mt4|mt5|payment|alipay|stripe|twilio|sendgrid)',key):external_fields.append({'config':origin,'field':key})
 D['java_runtime_configuration']={'services':runtime,'datasource_configured_count':sum(x['datasource'] is not None for x in runtime),'sms_keys_empty':sms_empty,'sargia_provider':{'host':u.hostname,'port':u.port,'explicitly_disabled_client':True},'credential_field_classification':credential_fields,'unknown_nonempty_credential_fields':0,'payment_broker_or_external_provider_config_fields':external_fields,'scope':'externalized new test runtime and six active Nacos documents; not a binary/code-wide secret scan'}
 dig={n:hashlib.sha256((J/'releases'/RELEASE/n/'application.yaml').read_bytes()).hexdigest() for n in NAMES};D['actual_runtime_readback']=call(240,RUNTIMECODE,{'release':RELEASE,'expected_config_digests':dig});assert all(x['live_bytes_equal_new_target_prepared_config'] and x['root600'] and x['unit']['ActiveState']=='active' and x['unit']['User']=='finger' for x in D['actual_runtime_readback']['configs'])
 D['actual_nacos_readback']=call(210,NACOSREAD,{'expected_config_digests':{n:hashlib.sha256(p.read_bytes()).hexdigest() for n,p in nacosfiles.items()}});assert all(x['live_bytes_equal_new_target_prepared_config'] and x['http_status']==200 for x in D['actual_nacos_readback']['configs']);save()
 if safe:
  for vmid,role,ip,other in [(201,'data-prod-infra','10.63.10.11','test-data'),(210,'data-test','10.63.20.10','prod-infra')]:
   row={'vmid':vmid,'target_ip':ip,'username':ENVS[other]['NACOS_CLIENT_USER'],'admin_account_tested':False,'attempt_count':1,'attempt_started_at':datetime.datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),'status':'attempt-recorded-no-retry'};D['cross_instance_negative_auth'].append(row);save();r=call(vmid,NEGATIVE,{'hostname':role,'ip':ip,'username':row['username'],'password':secret(B/other/'secrets/nacos-client-password')},timeout=35);row.update(result=r,status='passed' if r['denied'] else 'failed');save();assert r['denied']
 else:D['cross_instance_negative_auth_skipped']='Live application account set precondition not satisfied; no authentication attempt made.'
 save();print(json.dumps({'stage':'metadata-and-exact-auth-checks-complete','negative_attempts':len(D['cross_instance_negative_auth']),'cross_auth_denied':all(x.get('result',{}).get('denied') for x in D['cross_instance_negative_auth'])}))
if __name__=='__main__':
 if E.exists() and '--resume-retained-v1-candidate' not in sys.argv:
  print(json.dumps({'status':'refused-existing-evidence','evidence_unchanged':True,'authentication_attempts_repeated':False}));raise SystemExit(2)
 try:main()
 except Exception as e:
  D['status']='stopped-on-error';D['error_class']=type(e).__name__;save();print(json.dumps({'status':D['status'],'error_class':type(e).__name__,'negative_attempt_count':len(D['cross_instance_negative_auth'])}));raise SystemExit(1)
