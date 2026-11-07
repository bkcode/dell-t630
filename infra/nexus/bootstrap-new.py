#!/usr/bin/env python3
"""Guest-local initialization with independent secrets from protected stdin; no upstream use."""
import sys,json,os,base64,urllib.request,urllib.error
from pathlib import Path
from target_guard import verify_target
BASE=Path(__file__).resolve().parent;c,d=verify_target();assert (BASE/'fresh-instance.json').is_file()
payload=json.load(sys.stdin);assert set(payload)=={'admin-password','publisher-password','reader-password'}
folder=Path('/root/dell-nexus-secrets');folder.mkdir(exist_ok=True,mode=0o700);folder.chmod(0o700)
for name,value in payload.items():
 assert len(value)>=40 and '\n' not in value
 f=folder/name
 if f.exists():assert f.read_text().strip()==value,'Existing target secret differs; refuse rotation'
 else:
  fd=os.open(f,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
  with os.fdopen(fd,'w') as o:o.write(value+'\n')
class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,*a,**k):return None
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect)
base='http://10.63.30.20:8081/service/rest/v1'
def request(method,path,body=None,password=None,content_type='application/json',user='admin',allowed=(200,201,204)):
 headers={'Authorization':'Basic '+base64.b64encode((user+':'+(password or payload['admin-password'])).encode()).decode()}
 if body is not None:
  headers['Content-Type']=content_type;body=(json.dumps(body).encode() if content_type=='application/json' else body.encode())
 try:
  with opener.open(urllib.request.Request(base+path,data=body,headers=headers,method=method),timeout=20) as r:status=r.status;data=r.read(4*1024*1024)
 except urllib.error.HTTPError as e:status=e.code;data=e.read(1024)
 assert status in allowed,'Nexus '+method+' '+path.split('?')[0]+' HTTP '+str(status)
 return json.loads(data) if data and content_type=='application/json' else data
try:request('GET','/security/users')
except AssertionError:
 initial=Path('/srv/nexus/data/admin.password');assert initial.is_file(),'Fresh initial admin password absent; do not guess'
 request('PUT','/security/users/admin/change-password',payload['admin-password'],password=initial.read_text().strip(),content_type='text/plain')
request('GET','/security/users')
settings=request('GET','/security/anonymous');settings['enabled']=False;request('PUT','/security/anonymous',settings)
existing={r['name']:r for r in request('GET','/repositories')}
repos=[('finger-releases','RELEASE','ALLOW_ONCE'),('finger-snapshots','SNAPSHOT','ALLOW'),('dell-acceptance','MIXED','ALLOW')]
for name,version,write in repos:
 if name not in existing:
  request('POST','/repositories/maven/hosted',{'name':name,'online':True,'storage':{'blobStoreName':'default','strictContentTypeValidation':True,'writePolicy':write},'maven':{'versionPolicy':version,'layoutPolicy':'STRICT','contentDisposition':'INLINE'}})
 else:assert existing[name]['format']=='maven2' and existing[name]['type']=='hosted'
if 'finger-public' not in existing:
 request('POST','/repositories/maven/group',{'name':'finger-public','online':True,'storage':{'blobStoreName':'default','strictContentTypeValidation':True},'group':{'memberNames':['finger-releases','finger-snapshots']}})
roles={r['id']:r for r in request('GET','/security/roles')}
repo_names=[r[0] for r in repos]+['finger-public']
if 'imnull-releases' in existing:
 assert existing['imnull-releases']['type']=='hosted' and existing['imnull-releases']['format']=='maven2'
 repo_names.append('imnull-releases')
read=['nx-repository-view-maven2-'+name+'-'+action for name in repo_names for action in ['browse','read']]
publish=read+['nx-repository-view-maven2-'+name+'-'+action for name,_,_ in repos if name in ('finger-snapshots','dell-acceptance') for action in ['add','edit']]
for name,privileges in [('dell-artifact-reader',read),('dell-artifact-publisher',publish)]:
 if name not in roles:request('POST','/security/roles',{'id':name,'name':name,'description':'Independent Dell '+name,'privileges':privileges,'roles':[]})
 else:assert set(roles[name]['privileges'])==set(privileges),'Existing managed role differs'
users={u['userId']:u for u in request('GET','/security/users')}
for user,role,secret in [('dell-reader','dell-artifact-reader','reader-password'),('dell-publisher','dell-artifact-publisher','publisher-password')]:
 if user not in users:
  request('POST','/security/users',{'userId':user,'firstName':'Dell','lastName':user,'emailAddress':user+'@example.invalid','password':payload[secret],'status':'active','roles':[role]})
 else:assert users[user]['roles']==[role],'Existing managed user role differs'
result={'status':'fresh-admin-and-scoped-repositories-initialized','new_identity_count':3,'hosted_repositories':[r[0] for r in repos],'group':'finger-public','anonymous_enabled':request('GET','/security/anonymous')['enabled'],'source_credentials_imported':False,'source_artifacts_imported':False,'public_upstream_used':False}
assert result['anonymous_enabled'] is False
(BASE/'new-instance-bootstrap.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
