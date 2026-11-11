#!/usr/bin/env python3
"""Add missing local-named repo and align configuration only; DELETE is explicitly forbidden."""
import copy,datetime,hashlib,importlib.util,json,os,socket,subprocess,sys,urllib.parse
from pathlib import Path
from zoneinfo import ZoneInfo
assert os.geteuid()==0 and socket.gethostname()=='publish-service'and not Path('/etc/pve').exists();os.umask(0o077)
target=json.load(sys.stdin);assert target['no_repository_or_asset_deletion']is True and target['selected_by_user']=='only-align-configuration-keep-seven-extra-repositories'
STATE=Path('/root/dell-nexus-local-config-keep-extra-20261111');assert not STATE.exists(),'transaction-exists-review-before-resume'
BASE=Path('/opt/dell/nexus');sys.path.insert(0,str(BASE));s=importlib.util.spec_from_file_location('safe_parity_api',BASE/'application-import.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);api=m.API();original=api.request
allowed_put={'/service/rest/v1/repositories/maven/group/maven-public','/service/rest/v1/repositories/maven/hosted/imnull-releases','/service/rest/v1/security/roles/puyu-artifact-reader','/service/rest/v1/security/roles/puyu-artifact-publisher'}
writes=[]
def guarded(method,path,*args,**kwargs):
 assert method!='DELETE','all repository and asset DELETE operations forbidden'
 if method=='POST':
  body=args[0]if args else kwargs.get('body');assert path=='/service/rest/v1/repositories/maven/hosted'and body['name']=='imnull-snapshots';writes.append({'method':method,'path':path,'name':body['name']})
 elif method=='PUT':assert path in allowed_put;writes.append({'method':method,'path':path})
 else:assert method=='GET'
 return original(method,path,*args,**kwargs)
api.request=guarded
expected={r['name']:r for r in target['local_configurations']};assert len(expected)==9

def configurations():
 result={}
 for r in api.json('GET','/repositories'):
  fmt={'maven2':'maven'}.get(r['format'],r['format']);result[r['name']]={'format':r['format'],'type':r['type'],'configuration':api.json('GET','/repositories/'+fmt+'/'+r['type']+'/'+r['name'])}
 return result

def listed(endpoint,repo):
 values=[];token=None
 while True:
  q={'repository':repo}
  if token:q['continuationToken']=token
  page=api.json('GET','/'+endpoint+'?'+urllib.parse.urlencode(q));values+=page['items'];token=page.get('continuationToken')
  if not token:return values

def content_inventory(configs):
 result={}
 for name,r in configs.items():
  if r['type']!='hosted':continue
  result[name]={'components':sorted([{'id':c['id'],'group':c.get('group'),'name':c.get('name'),'version':c.get('version')}for c in listed('components',name)],key=lambda r:r['id']),'assets':sorted([{'id':a['id'],'path':a['path'],'checksums':a.get('checksum')}for a in listed('assets',name)],key=lambda r:r['id'])}
 return result
def comparable(configuration,key):
 value=copy.deepcopy(configuration.get(key))
 if key=='httpClient'and isinstance(value,dict):
  authentication=value.pop('authentication',None)
  assert not authentication,'server-upstream-auth-needs-review-not-copied'
 return value

before=configurations();assert set(target['retain_extra_repositories'])<=before.keys();assert set(expected)-before.keys()<={'imnull-snapshots'}
planned={}
for name,desired in expected.items():
 if name not in before:continue
 current=before[name];assert (current['format'],current['type'])==(desired['format'],desired['type']);changes={k:v for k,v in desired.items()if k not in ['format','type']and comparable(current['configuration'],k)!=v}
 assert set(changes)<=({'storage'}if name=='imnull-releases'else{'group'}if name=='maven-public'else set()),'unreviewed-common-repository-difference'
 if name=='imnull-releases'and changes:
  wanted=copy.deepcopy(current['configuration']['storage']);wanted['writePolicy']='ALLOW';assert changes['storage']==wanted and wanted['blobStoreName']=='default'
 if changes:planned[name]=changes
roles={x['id']:x for x in api.json('GET','/security/roles')};users={x['userId']:x for x in api.json('GET','/security/users')};anonymous=api.json('GET','/security/anonymous');eula=api.json('GET','/system/eula')
for name in ['puyu-artifact-reader','puyu-artifact-publisher']:
 assert name in roles and not roles[name]['roles']and all('delete'not in p and'admin'not in p and p!='nx-all'for p in roles[name]['privileges'])
contents=content_inventory(before);STATE.mkdir(mode=0o700)
def save(name,value):p=STATE/name;p.write_text(json.dumps(value,indent=2)+'\n');p.chmod(0o600)
save('before-private.json',{'configurations':before,'roles':roles,'users':users,'content_inventory':contents,'anonymous':anonymous,'EULA':eula});journal={'phase':'validated-safe-configuration-only','created':[],'updated':[],'delete_calls':0};save('journal.json',journal)
secret_hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in Path('/root/dell-nexus-secrets').iterdir()if p.is_file()}
service_pids={u:subprocess.check_output(['systemctl','show',u,'-p','MainPID','--value']).decode()for u in ['dell-nexus.service','dell-service-directory.service']};frame=subprocess.check_output(['docker','ps','--no-trunc','--format','{{.ID}} {{.Image}} {{.Names}}']).decode()
changed_roles=[]
try:
 if 'imnull-snapshots'not in before:
  desired=expected['imnull-snapshots'];body={k:v for k,v in desired.items()if k not in ['format','type']};api.json('POST','/repositories/maven/hosted',body);journal['created'].append('imnull-snapshots');save('journal.json',journal)
 for name,changes in planned.items():
  current=before[name];body=copy.deepcopy(current['configuration']);body.update(changes);api.json('PUT','/repositories/maven/'+current['type']+'/'+name,body);journal['updated'].append('repository:'+name);save('journal.json',journal)
 read_repos=['maven-public','imnull-releases','imnull-snapshots','maven-releases','maven-snapshots','maven-central'];read=['nx-repository-view-maven2-'+name+'-'+verb for name in read_repos for verb in ['browse','read']]
 for role_id,additions in [('puyu-artifact-reader',read),('puyu-artifact-publisher',read+['nx-repository-view-maven2-'+name+'-'+verb for name in ['imnull-releases','imnull-snapshots']for verb in ['add','edit']])]:
  role=roles[role_id];priv=list(dict.fromkeys(role['privileges']+additions));body={k:role[k]for k in ['id','name','description','roles']};body['privileges']=priv
  if priv!=role['privileges']:api.json('PUT','/security/roles/'+role_id,body);changed_roles.append(role_id);journal['updated'].append('append-role:'+role_id);save('journal.json',journal)
 after=configurations();assert set(before)<=after.keys()and set(after)==set(before)|set(expected)
 for name,desired in expected.items():
  actual=after[name];assert (actual['format'],actual['type'])==(desired['format'],desired['type'])
  for key,value in desired.items():
   if key not in ['format','type']:assert comparable(actual['configuration'],key)==value,'local-configuration-readback-mismatch'
 for name in target['retain_extra_repositories']:assert after[name]==before[name]
 after_contents=content_inventory(after);assert all(after_contents[k]==v for k,v in contents.items()),'existing-artifact-identity-or-checksum-drift'
 newroles={r['id']:r for r in api.json('GET','/security/roles')};assert set(newroles)==set(roles)
 for name,old in roles.items():
  if name not in changed_roles:assert newroles[name]==old
  else:assert set(old['privileges'])<=set(newroles[name]['privileges'])and not newroles[name]['roles']and all('delete'not in p and'admin'not in p and p!='nx-all'for p in newroles[name]['privileges'])
 assert {u['userId']:u for u in api.json('GET','/security/users')}==users and api.json('GET','/security/anonymous')==anonymous and api.json('GET','/system/eula')==eula
 assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==v for p,v in secret_hashes.items())
 assert subprocess.check_output(['docker','ps','--no-trunc','--format','{{.ID}} {{.Image}} {{.Names}}']).decode()==frame
 assert all(subprocess.check_output(['systemctl','show',u,'-p','MainPID','--value']).decode()==pid for u,pid in service_pids.items())
except Exception:
 # Revert only settings/permissions already present before; never delete the newly added empty repo.
 for name in changed_roles:
  old=roles[name];api.json('PUT','/security/roles/'+name,{k:old[k]for k in ['id','name','description','privileges','roles']})
 for name in planned:
  current=before[name];api.json('PUT','/repositories/maven/'+current['type']+'/'+name,current['configuration'])
 journal['phase']='failed-safe-original-settings-restored-no-deletion';save('journal.json',journal);raise
journal['phase']='local-configuration-aligned-all-extra-repositories-and-assets-retained';save('journal.json',journal)
result={'at':datetime.datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),'status':journal['phase'],'server_repository_count':len(after),'local_reference_repository_count':9,'all_repository_names':sorted(after),'extra_seven_retained':sorted(target['retain_extra_repositories']),'created_missing_repository':journal['created'],'updated_repositories':list(planned),'maven_public_members':expected['maven-public']['group']['memberNames'],'imnull_releases_writePolicy':'ALLOW','maven_releases_writePolicy':after['maven-releases']['configuration']['storage']['writePolicy'],'existing_components_preserved':sum(len(v['components'])for v in contents.values()),'existing_assets_ID_paths_checksums_preserved':sum(len(v['assets'])for v in contents.values()),'repository_or_artifact_DELETE_calls':0,'all_existing_account_passwords_unchanged':True,'original_Puyu_permissions_preserved_and_scoped_standard_Maven_permissions_appended':True,'other_roles_unchanged':True,'no_delete_or_admin_privileges_granted':True,'Nexus_and_navigation_PIDs_and_containers_unchanged':True,'Nexus_network_change':False,'historical_data_imported':False,'local_credentials_exported':False,'credential_values_or_private_hashes_output':False};save('result.json',result);print(json.dumps(result))
