#!/usr/bin/env python3
"""Version target config to match existing client-route contract, preserving all old dataIds/releases."""
from pathlib import Path
import json,yaml,hashlib,datetime
BASE=Path(__file__).resolve().parents[3];root=BASE/'private/java/test-chain';name='finger-gateway-mobile-lan-v2.yaml'
p=root/'nacos-configs/DELL_TEST'/name;assert not p.exists()
old=root/'nacos-configs/DELL_TEST/finger-gateway-mobile.yaml';cfg=yaml.safe_load(old.read_text());routes=cfg['spring']['cloud']['gateway']['server']['webflux']['routes']
for route in routes:
 if route['id']=='dell-test-files':route.update(predicates=['Path=/finger-bff-system/dell-test-files/**','Method=GET'],filters=['StripPrefix=2'])
 if route['id']=='dell-test-system-read':route.update(predicates=['Path=/finger-bff-system/sys-api/v1/role/get-list,/finger-bff-system/sys-api/v1/role/get-role-permissions,/finger-bff-system/sys-api/v1/employee/get-list','Method=POST'],filters=['StripPrefix=1'])
routes.append({'id':'dell-test-auth-prefix','uri':'lb://finger-auth','predicates':['Path=/finger-auth/api/v1/auth/captcha,/finger-auth/oauth2/token,/finger-auth/oauth2/jwks','Method=GET,POST'],'filters':['StripPrefix=1']})
cfg['security']['whitelist-paths']+=['/finger-auth/api/v1/auth/captcha','/finger-auth/oauth2/token','/finger-auth/oauth2/jwks']
assert 'clientRouteMap' not in cfg['security'] and 'client-route-map' not in cfg['security']
p.write_text(yaml.safe_dump(cfg,allow_unicode=True,sort_keys=False));p.chmod(0o600)
for service in ['finger-gateway-mobile','finger-service-coms']:
 f=root/'runtime'/service/'application.yaml';saved=f.with_name('application.before-lan-v2.yaml');assert not saved.exists();saved.write_bytes(f.read_bytes());saved.chmod(0o600);runtime=yaml.safe_load(f.read_text())
 if service=='finger-gateway-mobile':runtime['spring']['config']['import']=[x.replace('nacos:finger-gateway-mobile.yaml?','nacos:'+name+'?') for x in runtime['spring']['config']['import']]
 else:runtime['file']['upload']['domain']='http://192.168.21.22:19999/finger-bff-system/dell-test-files'
 f.write_text(yaml.safe_dump(runtime,allow_unicode=True,sort_keys=False));f.chmod(0o600)
meta=root/'metadata.json';data=json.loads(meta.read_text());saved=root/'metadata.before-lan-v2.json';saved.write_bytes(meta.read_bytes());saved.chmod(0o600)
for row in data['services']:
 if row['name']=='finger-gateway-mobile':row['nacos_data_id']=name
data.update(status='target-test-initialized-config-versioned',sql_execution='executed-on-test210',runtime_started=True,nacos_config_publication='initial-v1-executed-v2-awaiting-publish',config_revision='lan-v2-real-client-prefix-contract');meta.write_text(json.dumps(data,indent=2)+'\n');meta.chmod(0o600)
receipt={'at':datetime.datetime.now().isoformat(),'data_id':name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'routes':routes,'security_change':'only aliases for existing public captcha/OAuth; default client-route map and JWT checks preserved','old_nacos_data_id_preserved':True,'SQL_or_secrets_rotated':False,'new_upload_domain':'http://192.168.21.22:19999/finger-bff-system/dell-test-files'}
(BASE/'evidence/implementation/java-lan-v2-config-preparation.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({'data_id':name,'sha256':receipt['sha256'],'old_data_id_preserved':True}))
