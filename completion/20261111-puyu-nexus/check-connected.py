#!/usr/bin/env python3
"""Verify new YAML credentials and dev-only MCP in ub process; parent checks empty/old Nexus."""
import importlib.util,json,os,socket,subprocess,sys
from pathlib import Path
assert os.geteuid()==0 and socket.gethostname()=='publish-service'
ROOT=Path('/opt/deploy-public');STATE=Path('/root/dell-puyu-nexus-20261111')
worker=r'''
import base64,json,sys,urllib.error,urllib.request,uuid
from pathlib import Path
sys.path.insert(0,'/opt/deploy-public')
from config_loader import load_config
cfg=load_config('/opt/deploy-public/config.local.yaml').require_artifacts().require_mcp();o=urllib.request.build_opener(urllib.request.ProxyHandler({}));auth={}
for role in ['reader','publisher']:
 account=cfg.artifacts['credentials'][role];header='Basic '+base64.b64encode((account['username']+':'+account['password']).encode()).decode();url=cfg.artifact_urls()['read_url']+'connection-check-'+uuid.uuid4().hex+'.pom'
 q=urllib.request.Request(url,headers={'Authorization':header})
 try:
  with o.open(q,timeout=10)as response:status=response.status;response.read(1024)
 except urllib.error.HTTPError as e:status=e.code;e.read(1024);e.close()
 assert status==404,'expected authenticated missing-resource read';auth[role]={'username':account['username'],'authenticated_HTTP':status}
url='http://127.0.0.1:'+str(cfg.mcp['port'])+'/mcp';number=0

def rpc(method,params=None,authenticated=True,origin=False,notify=False):
 global number
 number+=1;body={'jsonrpc':'2.0','method':method}
 if not notify:body['id']=number
 if params is not None:body['params']=params
 headers={'Content-Type':'application/json','Accept':'application/json, text/event-stream'}
 if authenticated:headers['Authorization']='Bearer '+cfg.mcp['api_key']
 if origin:headers['Origin']='http://example.invalid'
 try:
  with o.open(urllib.request.Request(url,data=json.dumps(body).encode(),headers=headers,method='POST'),timeout=15)as r:return r.status,json.loads(r.read())if not notify else {}
 except urllib.error.HTTPError as e:code=e.code;e.read(1024);e.close();return code,{}
params={'protocolVersion':'2024-11-05','capabilities':{},'clientInfo':{'name':'Puyu-Nexus-config-readonly-check','version':'1'}}
assert rpc('initialize',params,authenticated=False)[0]==401 and rpc('initialize',params,origin=True)[0]==403
assert rpc('initialize',params)[0]==200;rpc('notifications/initialized',notify=True)
def call(name):
 code,body=rpc('tools/call',{'name':name,'arguments':{}});assert code==200 and'error'not in body;result=body['result'];assert not result.get('isError')
 if isinstance(result.get('structuredContent'),dict):return result['structuredContent']
 return json.loads(next(x['text']for x in result['content']if x.get('type')=='text'))
jobs=call('list_jobs');services=call('list_services');assert jobs['environment']=='dev'and {r['name']:r['enabled']for r in jobs['jobs']}=={'validate-services':True,'deploy-services':False};assert len(services['services'])==5 and all(x['source_ready']for x in services['details'])
print(json.dumps({'actual_YAML_scoped_credentials_authenticated':auth,'artifact_URLs':cfg.artifact_urls(),'MCP_authenticated_protocol_passed':True,'MCP_anonymous_HTTP':401,'MCP_browser_Origin_HTTP':403,'MCP_environment':jobs['environment'],'MCP_business_deploy_enabled':False,'MCP_registered_services':services['services'],'MCP_new_jobs_submitted':False,'prod_SSH_configured':bool(cfg.targets['puyu-prod']['ssh']),'new_credentials_printed':False}))
'''
r=subprocess.run(['runuser','-u','ub','--',str(ROOT/'.venv/bin/python'),'-I','-B','-c',worker],capture_output=True,text=True,timeout=100);assert r.returncode==0,r.stderr[-800:];connected=json.loads(r.stdout)
BASE=Path('/opt/dell/nexus');sys.path.insert(0,str(BASE));spec=importlib.util.spec_from_file_location('puyu_final_api',BASE/'application-import.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);api=m.API();before=json.loads((STATE/'before.json').read_text());repos={x['name']:x for x in api.json('GET','/repositories')};users={x['userId']:x for x in api.json('GET','/security/users')};roles={x['id']:x for x in api.json('GET','/security/roles')}
for key,after in [('repositories',repos),('users',users),('roles',roles)]:assert all(after[k]==v for k,v in before[key].items()),'old-Nexus-contract-drift'
for name,old in before['Maven_configurations'].items():
 row=repos[name];assert api.json('GET','/repositories/maven/'+row['type']+'/'+name)==old
for name in ['puyu-releases','puyu-snapshots']:
 for endpoint in ['components','assets']:
  value=api.json('GET','/'+endpoint+'?repository='+name);assert not value['items']and not value.get('continuationToken')
assert api.json('GET','/repositories/maven/group/puyu-public')['group']['memberNames']==['puyu-releases','puyu-snapshots']
start=json.loads((STATE/'provision-result.json').read_text());audit={}
for p in Path('/srv/dell-build/deploy-public/repos').iterdir():
 if not(p/'.git').is_dir():continue
 def git(*args):return subprocess.check_output(['runuser','-u','ub','--','git','-C',str(p),*args],stderr=subprocess.PIPE).decode().strip()
 audit[p.name]={'HEAD':git('rev-parse','HEAD'),'branch':git('branch','--show-current'),'clean':not git('status','--porcelain')}
assert len(audit)==6 and all(v['branch']=='main'and v['clean']for v in audit.values())
result={'status':'Puyu-empty-Nexus-and-private-publisher-config-connected',**connected,'existing_Nexus_repositories_users_roles_settings_unchanged':True,'Puyu_hosted_components_and_assets':0,'Puyu_group_only_own_hosted_members':True,'managed_backend_sources':audit,'backend_source_fetch_checkout_or_build':False,'old_data_migrated':False,'Nexus_restarted':False,'new_Java_or_Go_business_started':False,'credentials_exported':False}
print(json.dumps(result))
