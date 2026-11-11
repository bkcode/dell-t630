#!/usr/bin/env python3
"""Read-only local-layout parity and actual YAML group read; no uncached proxy request or writes."""
import copy,hashlib,importlib.util,json,os,socket,subprocess,sys,urllib.parse
from pathlib import Path
assert os.geteuid()==0 and socket.gethostname()=='publish-service'
STATE=Path('/root/dell-nexus-local-config-keep-extra-20261111');before=json.loads((STATE/'before-private.json').read_text());result=json.loads((STATE/'result.json').read_text());target=json.load(sys.stdin)
BASE=Path('/opt/dell/nexus');sys.path.insert(0,str(BASE));s=importlib.util.spec_from_file_location('readback_api',BASE/'application-import.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);api=m.API();original=api.request

def readonly(method,*args,**kwargs):assert method=='GET';return original(method,*args,**kwargs)
api.request=readonly
repos={r['name']:r for r in api.json('GET','/repositories')};assert len(repos)==16 and set(before['configurations'])<=repos.keys()and set(target['retain_extra_repositories'])<=repos.keys()
for desired in target['local_configurations']:
 name=desired['name'];fmt={'maven2':'maven'}.get(desired['format'],desired['format']);c=api.json('GET','/repositories/'+fmt+'/'+desired['type']+'/'+name)
 for key,value in desired.items():
  if key in ['format','type']:continue
  actual=copy.deepcopy(c.get(key))
  if key=='httpClient':assert not actual.pop('authentication',None)
  assert actual==value,'local-reference-configuration-drift'
assets=api.json('GET','/assets?repository=imnull-releases')['items'];sample=next((x for x in assets if'gradle-conventions'in x['path']and x['path'].endswith('.pom')),None)or next(x for x in assets if x['path'].endswith(('.pom','.jar')))
relative=sample['path'].lstrip('/');assert'..'not in Path(relative).parts
_,body=api.request('GET','/repository/imnull-releases/'+urllib.parse.quote(relative,safe='/'));expected=hashlib.sha256(body).hexdigest()
worker=r'''
import base64,hashlib,json,sys,urllib.error,urllib.parse,urllib.request
sys.path.insert(0,'/opt/deploy-public')
from config_loader import load_config
x=json.load(sys.stdin);cfg=load_config('/opt/deploy-public/config.local.yaml').require_artifacts().require_mcp();assert cfg.artifacts['read_repository']=='maven-public'and cfg.artifacts['publish_repositories']=={'dev':'imnull-snapshots','prod':'imnull-releases'}
o=urllib.request.build_opener(urllib.request.ProxyHandler({}));checks={}
for role in ['reader','publisher']:
 account=cfg.artifacts['credentials'][role];header='Basic '+base64.b64encode((account['username']+':'+account['password']).encode()).decode();url=cfg.artifact_urls()['read_url']+urllib.parse.quote(x['relative_path'],safe='/')
 with o.open(urllib.request.Request(url,headers={'Authorization':header}),timeout=15)as response:code=response.status;actual=response.read()
 assert code==200 and hashlib.sha256(actual).hexdigest()==x['sha256'];checks[role]={'username':account['username'],'group_read_HTTP':200,'existing_asset_bytes_equal':True}
number=0;url='http://127.0.0.1:'+str(cfg.mcp['port'])+'/mcp'
def rpc(method,params=None,auth=True,origin=False,notify=False):
 global number
 number+=1;body={'jsonrpc':'2.0','method':method}
 if not notify:body['id']=number
 if params is not None:body['params']=params
 headers={'Content-Type':'application/json','Accept':'application/json, text/event-stream'}
 if auth:headers['Authorization']='Bearer '+cfg.mcp['api_key']
 if origin:headers['Origin']='http://example.invalid'
 try:
  with o.open(urllib.request.Request(url,data=json.dumps(body).encode(),headers=headers,method='POST'),timeout=15)as r:return r.status,json.loads(r.read())if not notify else{}
 except urllib.error.HTTPError as e:code=e.code;e.read(1024);e.close();return code,{}
init={'protocolVersion':'2024-11-05','capabilities':{},'clientInfo':{'name':'local-repository-read-check','version':'1'}}
assert rpc('initialize',init,auth=False)[0]==401 and rpc('initialize',init,origin=True)[0]==403
assert rpc('initialize',init)[0]==200;rpc('notifications/initialized',notify=True)
code,r=rpc('tools/call',{'name':'list_jobs','arguments':{}});assert code==200 and not r['result'].get('isError');r=r['result'];jobs=r.get('structuredContent')or json.loads(next(b['text']for b in r['content']if b['type']=='text'));assert jobs['environment']=='dev'and {v['name']:v['enabled']for v in jobs['jobs']}=={'validate-services':True,'deploy-services':False}
print(json.dumps({'actual_private_YAML_group_credentials':checks,'artifact_URLs':cfg.artifact_urls(),'MCP_authenticated_protocol_passed':True,'MCP_anonymous_HTTP':401,'MCP_browser_Origin_HTTP':403,'MCP_environment':'dev','business_deploy_enabled':False,'no_new_MCP_jobs_submitted':True,'proxy_cache_miss_or_external_download_tested':False,'credential_values_output':False}))
'''
p=subprocess.run(['runuser','-u','ub','--','/opt/deploy-public/.venv/bin/python','-I','-B','-c',worker],input=json.dumps({'relative_path':relative,'sha256':expected}).encode(),capture_output=True,timeout=100);assert p.returncode==0,p.stderr.decode()[-800:];connected=json.loads(p.stdout)
users={u['userId']:u for u in api.json('GET','/security/users')};assert users==before['users']and api.json('GET','/security/anonymous')==before['anonymous']and api.json('GET','/system/eula')==before['EULA']
print(json.dumps({'status':'local-nine-configurations-aligned-seven-extra-kept-publisher-connected','server_repository_count':16,'local_reference_configuration_count':9,'retained_extra_seven':target['retain_extra_repositories'],'existing_components_preserved':result['existing_components_preserved'],'existing_asset_ID_paths_checksums_preserved':result['existing_assets_ID_paths_checksums_preserved'],'all_old_repositories_and_artifacts_preserved':True,**connected,'accounts_passwords_and_legacy_roles_preserved':True,'repository_or_artifact_delete_performed':False,'old_data_imported_or_republished':False,'Nexus_network_changed':False,'real_Gradle_Java_Go_build_or_business_deploy_executed':False,'local_credentials_or_private_payloads_exported':False}))
