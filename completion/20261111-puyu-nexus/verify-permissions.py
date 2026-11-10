#!/usr/bin/env python3
"""Scoped auth and two tiny owned POM fixtures, fully cleaned to keep new repos empty."""
import importlib.util,json,os,socket,sys,time,urllib.parse,uuid
from pathlib import Path
assert os.geteuid()==0 and socket.gethostname()=='publish-service'
BASE=Path('/opt/dell/nexus');sys.path.insert(0,str(BASE));spec=importlib.util.spec_from_file_location('puyu_roles_verify',BASE/'application-import.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
admin=m.API();reader=m.API('puyu-reader','puyu-reader-password');publisher=m.API('puyu-publisher','puyu-publisher-password')
STATE=Path('/root/dell-puyu-nexus-20261111');record=STATE/'permission-canary.json';assert not record.exists(),'canary-transaction-exists-review-before-resume'
nonce=uuid.uuid4().hex;artifact='configuration-check-'+nonce;prefix='com/puyu/acceptance/'+artifact+'/'
intent={'phase':'intent','artifact':artifact,'repositories':['puyu-releases','puyu-snapshots'],'before_empty':True};record.write_text(json.dumps(intent));record.chmod(0o600)
def items(endpoint,repo):
 rows=[];token=None
 while True:
  q={'repository':repo}
  if token:q['continuationToken']=token
  page=admin.json('GET','/'+endpoint+'?'+urllib.parse.urlencode(q));rows+=page['items'];token=page.get('continuationToken')
  if not token:return rows
for repo in intent['repositories']:assert not items('components',repo)and not items('assets',repo)
for client in [reader,publisher]:
 code,_=client.request('GET','/service/rest/v1/security/users',allowed=(403,));assert code==403
 code,_=client.request('GET','/repository/imnull-releases/',allowed=(403,));assert code==403
results=[]
try:
 for repo,version in [('puyu-releases','0.0.0-validation-'+nonce),('puyu-snapshots','0.0.0-SNAPSHOT')]:
  path='/repository/'+repo+'/'+prefix+version+'/'+artifact+'-'+version+'.pom'
  assert admin.request('GET',path,allowed=(404,))[0]==404
  body=('<project xmlns="http://maven.apache.org/POM/4.0.0"><modelVersion>4.0.0</modelVersion><groupId>com.puyu.acceptance</groupId><artifactId>'+artifact+'</artifactId><version>'+version+'</version><packaging>pom</packaging></project>').encode()
  code,_=publisher.request('PUT',path,body,content_type='application/xml',allowed=(201,204))
  assert reader.request('GET',path)[1]==body
  group='/repository/puyu-public/'+prefix+version+'/'+artifact+'-'+version+'.pom';assert reader.request('GET',group)[1]==body
  assert reader.request('PUT',path,body,content_type='application/xml',allowed=(403,))[0]==403
  assert publisher.request('DELETE',path,allowed=(403,))[0]==403
  immutable=None
  if repo=='puyu-releases':immutable=publisher.request('PUT',path,body+b'\n',content_type='application/xml',allowed=(400,409))[0];assert reader.request('GET',path)[1]==body
  results.append({'repository':repo,'publisher_upload_HTTP':code,'reader_and_group_read_bytes_equal':True,'reader_write_HTTP':403,'publisher_delete_HTTP':403,'release_redeploy_denied_HTTP':immutable})
finally:
 # Only known newly generated coordinates; no repository-wide deletion or old asset writes.
 for repo in intent['repositories']:
  owned=[]
  for _ in range(20):
   owned=[x for x in items('components',repo)if x['group']=='com.puyu.acceptance'and x['name']==artifact]
   if owned:break
   if not any(x['path'].lstrip('/').startswith(prefix)for x in items('assets',repo)):break
   time.sleep(1)
  for component in owned:
   assert component['repository']==repo and component['version']in ['0.0.0-validation-'+nonce,'0.0.0-SNAPSHOT']
   assert all(x['path'].lstrip('/').startswith(prefix)and'..'not in Path(x['path']).parts for x in component['assets'])
   admin.request('DELETE','/service/rest/v1/components/'+urllib.parse.quote(component['id'],safe=''),allowed=(204,))
  for asset in items('assets',repo):
   assert asset['repository']==repo and asset['path'].lstrip('/').startswith(prefix)and'..'not in Path(asset['path']).parts
   admin.request('DELETE','/service/rest/v1/assets/'+urllib.parse.quote(asset['id'],safe=''),allowed=(204,))
assert len(results)==2
for repo in intent['repositories']:assert not items('components',repo)and not items('assets',repo)
intent['phase']='permission-tests-passed-and-own-fixtures-cleaned';record.write_text(json.dumps(intent));record.chmod(0o600)
print(json.dumps({'status':intent['phase'],'results':results,'empty_hosted_repositories_after_test':True,'components_after_test':0,'assets_after_test':0,'cross_workspace_and_admin_access_denied_for_both_users':True,'old_repositories_written':False,'data_migrated':False,'real_Gradle_Java_or_Go_build_or_publish':False,'credential_values_output':False}))
