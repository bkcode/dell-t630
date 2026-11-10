#!/usr/bin/env python3
"""GET-only full hosted Nexus baseline. Details stay on the same data disk root600."""
import hashlib,importlib.util,json,os,socket,sys,urllib.parse
from pathlib import Path
assert os.geteuid()==0 and socket.gethostname() in ('artifact-service','publish-service') and not Path('/etc/pve').exists()
os.umask(0o077)
BASE=Path('/opt/dell/nexus');sys.path.insert(0,str(BASE))
spec=importlib.util.spec_from_file_location('nexus_baseline_api',BASE/'application-import.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
original=m.API.request
count=0
def only_get(self,method,path,*args,**kwargs):
 global count
 assert method=='GET','read-only API required'
 count+=1
 return original(self,method,path,*args,**kwargs)
m.API.request=only_get
api=m.API()
def items(endpoint,repo):
 values=[];token=None
 while True:
  query={'repository':repo}
  if token:query['continuationToken']=token
  page=api.json('GET','/'+endpoint+'?'+urllib.parse.urlencode(query));values.extend(page['items']);token=page.get('continuationToken')
  if not token:return values
repos=api.json('GET','/repositories');configs={x['name']:api.json('GET','/repositories/'+({'maven2':'maven'}.get(x['format'],x['format']))+'/'+x['type']+'/'+x['name']) for x in repos}
users=api.json('GET','/security/users');roles=api.json('GET','/security/roles');eula=api.json('GET','/system/eula')
snapshot={'repositories':sorted(repos,key=lambda x:x['name']),'configs':configs,'users':sorted(users,key=lambda x:x['userId']),'roles':sorted(roles,key=lambda x:x['id']),'eula':eula,'hosted':{}}
for repo in sorted(x['name'] for x in repos if x['type']=='hosted'):
 components=items('components',repo);assets=items('assets',repo);rows=[]
 for asset in sorted(assets,key=lambda x:x['path']):
  _,body=api.request('GET','/repository/'+urllib.parse.quote(repo,safe='')+'/'+urllib.parse.quote(asset['path'],safe='/'))
  rows.append({'path':asset['path'],'id':asset['id'],'size':len(body),'sha256':hashlib.sha256(body).hexdigest()})
 snapshot['hosted'][repo]={'components':sorted(components,key=lambda x:x['id']),'assets':rows}
path=Path('/srv/nexus/.dell-merge-baseline-20261110.json')
action=sys.argv[1]
if action=='snapshot':
 assert socket.gethostname()=='artifact-service' and not path.exists()
 path.write_text(json.dumps(snapshot,sort_keys=True));path.chmod(0o600)
else:
 assert action=='verify' and socket.gethostname()=='publish-service' and path.stat().st_mode&0o777==0o600
 before=json.loads(path.read_text())
 observed=path.with_name('.dell-merge-observed-20261110.json');observed.write_text(json.dumps(snapshot,sort_keys=True));observed.chmod(0o600)
 def changed(a,b,p=''):
  if type(a)!=type(b):return [p+':type']
  if isinstance(a,dict):
   return [p+':keys'] if set(a)!=set(b) else [z for k in a for z in changed(a[k],b[k],p+'/'+k)]
  if isinstance(a,list):
   return [p+':length'] if len(a)!=len(b) else [z for x,y in zip(a,b)for z in changed(x,y,p+'[]')]
  return [] if a==b else [p]
 differences=changed(before,snapshot)
 if differences:
  import copy,re
  allowed=re.compile(r'^/hosted/[^/]+/components\[\]/assets\[\]/lastDownloaded$')
  assert all(allowed.fullmatch(p)for p in differences),'non-operational baseline difference'
  a,b=copy.deepcopy(before),copy.deepcopy(snapshot)
  for value in [a,b]:
   for repo in value['hosted'].values():
    for component in repo['components']:
     for asset in component['assets']:asset.pop('lastDownloaded',None)
  assert a==b,'baseline differs beyond explicitly scoped lastDownloaded'
  print(json.dumps({'status':'GET-only-baseline-verify-passed','repositories':len(repos),'hosted_repositories':len(snapshot['hosted']),'components':sum(len(x['components'])for x in snapshot['hosted'].values()),'assets_read_and_hashed':sum(len(x['assets'])for x in snapshot['hosted'].values()),'all_asset_bytes_paths_IDs_and_repository_security_equal':True,'only_volatile_field':'hosted.components[].assets[].lastDownloaded','GET_updated_timestamp_count':len(differences),'API_GET_requests':count,'repository_writes':False,'private_details_retained_VM_only':True}));sys.exit(0)
summary={'status':'full-hosted-baseline-'+action+'-passed','repositories':len(repos),'hosted_repositories':len(snapshot['hosted']),'components':sum(len(x['components']) for x in snapshot['hosted'].values()),'assets_read_and_hashed':sum(len(x['assets'])for x in snapshot['hosted'].values()),'users':len(users),'roles':len(roles),'eula_accepted':eula['accepted'],'only_HTTP_method':'GET','requests':count,'baseline_details_retained_only_on_data_disk_root600':True,'credentials_output':False}
print(json.dumps(summary))
