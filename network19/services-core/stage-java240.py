#!/usr/bin/env python3
"""Prepared on-guest private stage recipe. Default inspect; never activates/publishes/starts."""
import argparse,copy,hashlib,json,os,re,shutil,socket,subprocess,sys,urllib.parse,urllib.request
from pathlib import Path
import yaml
BASE=Path('/opt/finger');CURRENT=BASE/'current-test';OLD_JAVA='10.63.20.20';NEW_JAVA='192.168.19.45';OLD_DATA='10.63.20.10';NEW_DATA='192.168.19.20';OLD_ISSUER='http://192.168.21.22:19999';NEW_ISSUER='http://192.168.19.45:9999'
class Refused(RuntimeError):pass

def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def canonical(path):
 if path.resolve(strict=False)!=path:raise Refused('canonical-root-path-required')
 return path

def rewrite_endpoint(value):
 if value.startswith(OLD_ISSUER):return NEW_ISSUER+value[len(OLD_ISSUER):]
 for old,new in [(OLD_JAVA,NEW_JAVA),(OLD_DATA,NEW_DATA)]:
  if value==old:return new
  for prefix in ['http://','https://','jdbc:mysql://','']:
   marker=prefix+old
   if value.startswith(marker) and len(value)>len(marker) and value[len(marker)] in ':/?':return prefix+new+value[len(marker):]
 return value

def allowed(path):
 joined='.'.join(path)
 exact={'server.address','spring.cloud.nacos.server-addr','spring.cloud.nacos.discovery.server-addr','spring.cloud.nacos.config.server-addr','spring.cloud.nacos.discovery.ip','spring.datasource.url','spring.data.redis.host','spring.rabbitmq.host','finger.auth.bootstrap.issuer','file.upload.domain','sargia.accounts.oauth.public-url','redis.host','gateway.endpoint','nacos.server-addr','spring.security.oauth2.resourceserver.jwt.issuer-uri','spring.security.oauth2.resourceserver.jwt.jwk-set-uri'}
 if joined in exact:return True
 if len(path)==7 and path[:3]==['security','jwt','trustedIssuers'] and path[-1] in ['issuerUri','jwkSetUri']:return True
 if path[:4]==['finger','auth','bootstrap','clients'] and len(path)==7 and path[-2] in ['redirect-uris','post-logout-redirect-uris']:return True
 # Actual gateway trustedIssuers path is security.jwt.trustedIssuers.0.issuerUri.
 return len(path)==5 and path[:3]==['security','jwt','trustedIssuers'] and path[-1] in ['issuerUri','jwkSetUri']

def transform(model,dataids):
 out=copy.deepcopy(model);changed=[]
 def visit(x,path):
  if isinstance(x,dict):
   for key,val in x.items():
    if any(word in str(key).lower() for word in ['password','secret','token','credential']):continue
    if isinstance(val,(dict,list)):visit(val,path+[str(key)])
    elif isinstance(val,str):
     new=rewrite_endpoint(val)
     if new!=val:
      p=path+[str(key)]
      if not allowed(p):raise Refused('unapproved-active-config-address-key:'+'.'.join(p))
      x[key]=new;changed.append(p)
  elif isinstance(x,list):
   for i,val in enumerate(x):
    if isinstance(val,(dict,list)):visit(val,path+[str(i)])
    elif isinstance(val,str):
     new=rewrite_endpoint(val)
     if new!=val:
      p=path+[str(i)]
      if not allowed(p):raise Refused('unapproved-active-config-list-address-key:'+'.'.join(p))
      x[i]=new;changed.append(p)
 visit(out,[])
 imports=out.get('spring',{}).get('config',{}).get('import')
 if imports is not None:
  if not isinstance(imports,list) or len(imports)!=2:raise Refused('mandatory-two-imports-required')
  values=[]
  for value in imports:
   u=urllib.parse.urlsplit(value)
   if u.scheme!='nacos' or u.path not in dataids:raise Refused('only-active-import-dataId-map-allowed')
   values.append('nacos:'+dataids[u.path]+('?' +u.query if u.query else ''))
  out['spring']['config']['import']=values;changed.append(['spring','config','import'])
 return out,changed

def secret_leaves(model):
 result={}
 def visit(x,path):
  if isinstance(x,dict):
   for k,v in x.items():
    p=path+[str(k)]
    if any(s in str(k).lower() for s in ['password','secret','token','credential']):result[tuple(p)]=v
    else:visit(v,p)
  elif isinstance(x,list):
   for i,v in enumerate(x):visit(v,path+[str(i)])
 visit(model,[]);return result

def root_receipt(path):
 if path is None or canonical(path).stat().st_uid!=0 or path.stat().st_mode&0o077:raise Refused('explicit-root600-stage-window-required')
 x=json.loads(path.read_text())
 if x.get('migration')!='network19' or x.get('target_vmid')!=240 or x.get('allowed_phase')!='stage-private' or x.get('parent_window_open') is not True:raise Refused('stage-window-not-approved')

class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,*args,**kwargs):return None

def get_nacos(runtime,dataid):
 n=runtime['spring']['cloud']['nacos'];host=n['server-addr']
 if host not in ['10.63.20.10:8848','192.168.19.20:8848']:raise Refused('Nacos-endpoint-outside-owned-test')
 root='http://'+host+'/nacos';opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
 body=urllib.parse.urlencode({'username':n['username'],'password':n['password']}).encode()
 with opener.open(urllib.request.Request(root+'/v1/auth/login',data=body,method='POST'),timeout=10) as r:token=json.load(r)['accessToken']
 query=urllib.parse.urlencode({'dataId':dataid,'group':n['config']['group'],'tenant':n['config']['namespace'],'accessToken':token})
 with opener.open(root+'/v1/cs/configs?'+query,timeout=15) as r:return r.read()

def write(path,data,mode):path.write_bytes(data);path.chmod(mode)
def main():
 p=argparse.ArgumentParser();p.add_argument('--contract-dir',type=Path,required=True);p.add_argument('--release-id',required=True);p.add_argument('--rollback-release-id',required=True);p.add_argument('--stage-private',action='store_true');p.add_argument('--root-receipt',type=Path);p.add_argument('--output',type=Path,default=Path('/root/dell-network19/private-stage'));a=p.parse_args()
 if os.geteuid()!=0 or socket.gethostname().split('.')[0]!='java-test-01' or Path('/etc/pve').exists():raise Refused('assigned240-only')
 for identity in [a.release_id,a.rollback_release_id]:
  if not re.fullmatch('[0-9]{8}T[0-9]{6}',identity):raise Refused('timestamp-release-ID-required')
 if a.release_id==a.rollback_release_id:raise Refused('separate-new-network-rollback-release-required')
 contract=json.loads((a.contract_dir/'prepared-public-contract.json').read_text());patches=json.loads((a.contract_dir/'nacos-patch-contract.json').read_text());source=CURRENT.resolve()
 if str(source)!=contract['source_active_release'] or not source.is_relative_to(BASE/'releases/test'):raise Refused('active-release-changed-reinventory-first')
 manifest=json.loads((source/'manifest.json').read_text());services=manifest['services'];runtime={};plans=[]
 for row in services:
  name=row['name'];config=source/name/'application.yaml'
  if config.stat().st_uid!=0 or config.stat().st_mode&0o777!=0o600 or sha(config)!=row['config_sha256'] or sha(source/name/'app.jar')!=row['jar_sha256']:raise Refused('immutable-source-or-root600-contract-changed')
  original=yaml.safe_load(config.read_text());new,paths=transform(original,contract['Nacos_dataId_mapping'])
  if secret_leaves(original)!=secret_leaves(new):raise Refused('credential-values-changed')
  runtime[name]=new;plans.append({'service':name,'changed_paths':paths,'JAR_unchanged':True,'secrets_unchanged':True,'root600_LoadCredential_preserved':True})
 if not a.stage_private:
  print(json.dumps({'status':'inspect-no-write','release_pair':[a.release_id,a.rollback_release_id],'services':plans,'Nacos_new_IDs':list(contract['Nacos_dataId_mapping'].values()),'target_writes':0}));return
 if contract.get('java_application_deployment_allowed') is not True:raise Refused('user-scope-forbids-further-Java-stage-or-deploy')
 root_receipt(a.root_receipt);output=canonical(a.output)
 if not str(output).startswith('/root/dell-network19/') or output.exists():raise Refused('new-private-stage-path-required')
 output.mkdir(mode=0o700,parents=True);configs=output/'nacos-configs';configs.mkdir(mode=0o700)
 source_runtime=yaml.safe_load((source/'finger-auth/application.yaml').read_text())
 for item in patches['configs']:
  raw=get_nacos(source_runtime,item['source_dataId'])
  if hashlib.sha256(raw).hexdigest()!=item['source_content_sha256']:raise Refused('Nacos-source-SHA-changed')
  original=yaml.safe_load(raw);new,_=transform(original,contract['Nacos_dataId_mapping'])
  if secret_leaves(original)!=secret_leaves(new):raise Refused('Nacos-secret-change')
  write(configs/item['target_dataId'],yaml.safe_dump(new,sort_keys=False,allow_unicode=True).encode(),0o600)
 for identity in [a.release_id,a.rollback_release_id]:
  dest=output/identity;dest.mkdir(mode=0o700);m=copy.deepcopy(manifest);m.update(release_id=identity,target_ip=NEW_JAVA,data_ip=NEW_DATA,issuer=NEW_ISSUER)
  for row in m['services']:
   name=row['name'];folder=dest/name;folder.mkdir(mode=0o700);shutil.copyfile(source/name/'app.jar',folder/'app.jar');(folder/'app.jar').chmod(0o600)
   write(folder/'application.yaml',yaml.safe_dump(runtime[name],sort_keys=False,allow_unicode=True).encode(),0o600);row['config_sha256']=sha(folder/'application.yaml')
  write(dest/'manifest.json',json.dumps(m,indent=2).encode(),0o600)
 print(json.dumps({'status':'private-pair-staged-not-installed-published-or-started','release_pair':[a.release_id,a.rollback_release_id],'Nacos_new_configs':len(patches['configs']),'all_JARs_secrets_namespace_vhost_unchanged':True,'secret_values_emitted':False}))
if __name__=='__main__':
 try:main()
 except Exception as e:print(json.dumps({'status':'refused-or-failed','error_category':type(e).__name__,'reason':str(e) if isinstance(e,Refused) else 'details-withheld'}));sys.exit(1)
