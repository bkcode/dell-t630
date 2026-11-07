#!/usr/bin/env python3
"""Complete only the manager-approved remaining negative; never repeat VM201."""
import datetime,importlib.util,json,re,sys
from pathlib import Path
from zoneinfo import ZoneInfo
p=Path(__file__).with_name('audit.py');s=importlib.util.spec_from_file_location('audit',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
D=json.loads(m.E.read_text())
def now():return datetime.datetime.now(ZoneInfo('Asia/Shanghai')).isoformat()
def save():m.E.write_text(json.dumps(D,ensure_ascii=False,indent=2)+'\n')
HEALTH=r'''
import pathlib,socket,json,urllib.request,urllib.parse,urllib.error,sys
p=json.load(sys.stdin);assert socket.gethostname()==p['hostname'] and not pathlib.Path('/etc/pve').exists();b=pathlib.Path('/opt/dell/data')/p['role'];c=dict(l.split('=',1) for l in (b/'.env').read_text().splitlines() if l and not l.startswith('#') and '=' in l);assert c['SERVICE_IP']==p['ip'] and c['NACOS_CLIENT_USER']==p['username']
class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,*a,**k):return None
op=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect());base='http://'+p['ip']+':8848/nacos'
with op.open(base+'/v1/console/health/readiness',timeout=15) as r:ready=r.status;r.read(1024)
data=urllib.parse.urlencode({'username':c['NACOS_CLIENT_USER'],'password':(b/'secrets/nacos-client-password').read_text().strip()}).encode()
with op.open(urllib.request.Request(base+'/v1/auth/users/login',data=data,method='POST',headers={'Content-Type':'application/x-www-form-urlencoded'}),timeout=15) as r:status=r.status;token=json.loads(r.read(65536)).get('accessToken')
print(json.dumps({'readiness_http_status':ready,'own_environment_client_login_http_status':status,'own_environment_client_token_issued':bool(token),'username':p['username'],'credential_or_token_emitted':False,'passed':ready==200 and status==200 and bool(token)}))
'''
NEG=m.NEGATIVE.replace("except urllib.error.HTTPError as e:status=e.code;e.read(65536);e.close()", """except urllib.error.HTTPError as e:
 status=e.code;body=e.read(65536);header_token=bool(e.headers.get('Authorization'));e.close()
 try:parsed=json.loads(body);token=bool(parsed.get('accessToken')) or header_token
 except (ValueError,AttributeError):token=header_token
""")
def main():
 assert len(D['cross_instance_negative_auth'])==1 and D['cross_instance_negative_auth'][0]['vmid']==201 and D['cross_instance_negative_auth'][0]['attempt_count']==1 and D['cross_instance_negative_auth'][0]['result']['http_status']==500
 assert D['negative_auth_safety_preconditions']['opposite_username_absent'] and all(x['live_bytes_equal_new_target_prepared_config'] for x in D['actual_nacos_readback']['configs'])
 D['normal_nacos_health_before_remaining_negative']={}
 for v,host,role,ip,user in [(201,'data-prod-infra','prod-infra','10.63.10.11','finger_prod'),(210,'data-test','test-data','10.63.20.10','finger_test')]:
  r=m.call(v,HEALTH,{'hostname':host,'role':role,'ip':ip,'username':user});D['normal_nacos_health_before_remaining_negative'][str(v)]=r;save();assert r['passed']
 row={'vmid':210,'target_ip':'10.63.20.10','username':'finger_prod','admin_account_tested':False,'attempt_count':1,'attempt_started_at':now(),'status':'attempt-recorded-no-retry'};D['cross_instance_negative_auth'].append(row);save()
 r=m.call(210,NEG,{'hostname':'data-test','ip':'10.63.20.10','username':'finger_prod','password':m.secret(m.B/'prod-infra/secrets/nacos-client-password')},timeout=35);row.update(result=r,status='standard-auth-denied' if r['denied'] else 'nonstandard-error-no-successful-login' if r['http_status']==500 and not r['access_token_returned'] else 'inconclusive');row['error_body_and_header_token_presence_checked_in_memory']=True;save()
 assert r['denied'] or (r['http_status']==500 and not r['access_token_returned'])
 D['cross_instance_negative_auth'][0]['status']='nonstandard-error-no-successful-login';D['cross_instance_negative_auth'][0]['error_body_token_presence_not_parsed']='Original HTTP error body was discarded without JSON parsing; no successful login response observed. First request was not repeated.'
 D['authentication_response_semantics']={'standard_401_403_observed':[x['result']['http_status'] in [401,403] for x in D['cross_instance_negative_auth']],'actual_http_statuses':[x['result']['http_status'] for x in D['cross_instance_negative_auth']],'unexpected_cross_environment_login_succeeded':False,'no_repeat_attempts':True,'no_admin_cross_credential_test':True,'limitation':'Nacos 2.4.3 returns HTTP500 for unknown-user authentication path; this is not relabeled as401/403. Static source attribution is consistent, not a captured runtime stack trace. First error body was discarded without token-field parsing.'}
 D['upstream_500_static_attribution']={'version':'2.4.3','observed_missing_users_confirmed_by_live_SELECT':True,'runtime_exception_trace_read':False,'attribution_kind':'static-path-consistent-inference','sources':[
 {'url':'https://raw.githubusercontent.com/alibaba/nacos/2.4.3/plugin-default-impl/nacos-default-auth-plugin/src/main/java/com/alibaba/nacos/plugin/auth/impl/controller/UserController.java','local':'infra/data/audit-isolation/UserController.java','lines':[266,272,298],'finding':'NACOS system login calls authenticate outside the legacy BadCredentialsException catch.'},
 {'url':'https://raw.githubusercontent.com/alibaba/nacos/2.4.3/plugin-default-impl/nacos-default-auth-plugin/src/main/java/com/alibaba/nacos/plugin/auth/impl/authenticate/AbstractAuthenticationManager.java','local':'infra/data/audit-isolation/AbstractAuthenticationManager.java','lines':[56,60,62],'finding':'UserDetailsService lookup precedes the null/password guard.'},
 {'url':'https://raw.githubusercontent.com/alibaba/nacos/2.4.3/plugin-default-impl/nacos-default-auth-plugin/src/main/java/com/alibaba/nacos/plugin/auth/impl/users/NacosUserDetailsServiceImpl.java','local':'infra/data/audit-isolation/NacosUserDetailsServiceImpl.java','lines':[73,80,81],'finding':'Missing username raises UsernameNotFoundException.'},
 {'url':'https://raw.githubusercontent.com/alibaba/nacos/2.4.3/console/src/main/java/com/alibaba/nacos/console/exception/ConsoleExceptionHandler.java','local':'infra/data/audit-isolation/ConsoleExceptionHandler.java','lines':[45,48,62,70],'finding':'AccessException maps403; generic Exception maps500.'}]}
 # Summarize only SELECT privilege metadata. MySQL schema wildcards preserve their raw escaped representation.
 summary=[]
 for vmid,c in D['live_catalogs'].items():
  rows=c['rows']
  for account in [x for x in rows if x['kind']=='mysql_account']:
   grantee="'"+account['user']+"'@'"+account['host']+"'";privs=[x for x in rows if x.get('grantee')==grantee];tables=sorted({x['table'] for x in privs if x['kind']=='table_privilege'});schemas=sorted({x['schema'] for x in privs if 'schema' in x});tablep=sorted({x['privilege'] for x in privs if x['kind']=='table_privilege'});schemap=sorted({x['privilege'] for x in privs if x['kind']=='schema_privilege'});globalp=sorted({x['privilege'] for x in privs if x['kind']=='global_privilege'});business=account['user'].startswith('finger_')
   if business:assert vmid=='210' and account['host']=='10.63.20.20' and set(tablep)=={'SELECT','INSERT','UPDATE','DELETE'} and not schemap and globalp==['USAGE'] and all(x['grantable']=='NO' for x in privs) and schemas==[account['user']]
   summary.append({'vmid':int(vmid),'account':account['user'],'host':account['host'],'business_runtime_account':business,'schema_grants_raw_mysql_escaped':schemas,'table_names':tables,'table_DML':tablep,'schema_privileges':schemap,'global_privileges':globalp,'grant_option':False,'scope_note':'Nacos infrastructure DB owner within own schema, not a Java runtime user.' if not business else 'Exact Java240 host, per-table DML only; no runtime DDL or grant option.'})
 D['mysql_account_scope_summary']=summary
 D['namespace_roles_verified']=[]
 for vmid,env in [('200',m.ENVS['prod-infra']),('210',m.ENVS['test-data'])]:
  rows=D['live_catalogs'][vmid]['rows'];user=env['NACOS_CLIENT_USER'];roles=[x['role'] for x in rows if x['kind']=='nacos_role' and x['username']==user];assert roles==[env['NACOS_CLIENT_ROLE']];perms=[x for x in rows if x['kind']=='nacos_permission' and x['role'] in roles];assert perms and all(x['resource']==env['NACOS_NAMESPACE_ID']+':*:*' and x['action']=='rw' for x in perms);D['namespace_roles_verified'].append({'user':user,'role':roles[0],'namespace':env['NACOS_NAMESPACE_ID'],'resource':env['NACOS_NAMESPACE_ID']+':*:*','action':'rw','global_admin_role':False})
 network=json.loads((m.ROOT/'evidence/implementation/network-independent-verification.json').read_text());prod=json.loads((m.ROOT/'evidence/implementation/data-prod-final-inventory.json').read_text());rolling=json.loads((m.ROOT/'evidence/implementation/rolling-guest-reboot-acceptance.json').read_text());inits=json.loads((m.ROOT/'evidence/implementation/java-test-init.json').read_text())
 D['existing_evidence']={'network':{'path':'evidence/implementation/network-independent-verification.json','matrix':network['summary']['real_data_port_matrix']},'namespace_other_access_denied':{'paths':['evidence/implementation/data-deployment-acceptance.json','evidence/implementation/test-data-deployment.json','evidence/implementation/rolling-guest-reboot-acceptance.json'],'prod_and_test_verified':True},'test_runtime_SQL':{'path':'evidence/implementation/java-test-init.json','account_host':inits['sql']['accounts_host'],'runtime_privileges':inits['sql']['runtime_privileges'],'source_rows_copied':inits['sql']['source_rows_copied']},'formal_data_inventory':{'path':'evidence/implementation/data-prod-final-inventory.json','collected_at':prod['collected_at'],'formal_business_schema_count':next(x['formal_business_schema_count'] for x in prod['roles'] if x['vmid']==200)},'formal_runtime_only':{'user_scope':'Formal230-232 deliver cluster runtime only; business apps are first accepted on test240.','scope_reference':'AGENTS.md / plan.json latest user decision','latest_normal_reboot_evidence':'evidence/implementation/rolling-guest-reboot-acceptance.json','collected_at':rolling['completed_at'],'nodes':[{'vmid':x['vmid'],'nonroot_java_ok':x['after']['nonroot_java']['exit_code']==0,'active_business_units':x['after']['active_business_units']} for x in rolling['reboots'] if x['vmid'] in [230,231,232]]}}
 assert D['existing_evidence']['network']['matrix']=={'total':30,'allowed_pass':10,'denied_pass':20,'inconclusive_or_failed':0}
 D['result_summary']={'new_target_secret_separation':'passed','separate_instance_namespace_vhost_and_account_scope':'passed','actual_test_runtime_and_Nacos_config_binding':'passed','per_table_SQL_DML_and_exact_Java240_account_host':'passed','existing_30_case_network_isolation':'passed','cross_environment_auth_permission':'no-successful-login-observed-with-known-missing-account-and-nonstandard500-response','standard_auth_error_semantics':'limited-not-standard401403','manager_DATA001_signoff_required':True}
 D['scope_limits']=['No source business data migration is claimed.','No whole-source test-data sanitization is claimed; current test chain uses fresh schema and synthetic identities.','No formal business application was started or formal business schema initialized.','External credential conclusion covers checked new externalized runtime/Nacos documents, not every dependency binary or repository.','No source Mac credential file, Nacos administrator cross-credential trial, SQL write, service restart or configuration update was performed.','HTTP500 is preserved; its attribution is a static-source inference, not a captured server exception trace.']
 D['status']='completed-for-manager-signoff';D.pop('error_class',None);D['completed_at']=now();save();print(json.dumps({'status':D['status'],'negative_attempts':len(D['cross_instance_negative_auth']),'actual_statuses':D['authentication_response_semantics']['actual_http_statuses'],'sql_accounts':len(summary),'runtime_configured_datasources':D['java_runtime_configuration']['datasource_configured_count'],'service_or_SQL_changes':False}))
if __name__=='__main__':
 if len(D.get('cross_instance_negative_auth',[]))!=1 or D.get('status')=='completed-for-manager-signoff':
  print(json.dumps({'status':'refused-nonremaining-or-completed-audit','evidence_unchanged':True,'authentication_attempts_repeated':False}));raise SystemExit(2)
 try:main()
 except Exception as e:D['status']='stopped-on-error';D['error_class']=type(e).__name__;save();print(json.dumps({'status':D['status'],'error_class':type(e).__name__,'negative_attempt_count':len(D['cross_instance_negative_auth'])}));raise SystemExit(1)
