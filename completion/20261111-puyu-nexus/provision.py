#!/usr/bin/env python3
"""Create only new, empty Puyu Maven repositories and scoped identities. No old data import."""
import hashlib,importlib.util,json,os,secrets,socket,subprocess,sys,time
from pathlib import Path
assert os.geteuid()==0 and socket.gethostname()=='publish-service'and not Path('/etc/pve').exists()
os.umask(0o077);STATE=Path('/root/dell-puyu-nexus-20261111');assert not STATE.exists(),'transaction-exists-review-before-resume';STATE.mkdir(mode=0o700)
BASE=Path('/opt/dell/nexus');sys.path.insert(0,str(BASE));spec=importlib.util.spec_from_file_location('puyu_nexus',BASE/'application-import.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);api=m.API()
REPOS=['puyu-releases','puyu-snapshots','puyu-public'];ROLES=['puyu-artifact-reader','puyu-artifact-publisher'];USERS=['puyu-reader','puyu-publisher']
def capture():
 repos=api.json('GET','/repositories');configs={}
 for r in repos:
  if r['format']=='maven2':configs[r['name']]=api.json('GET','/repositories/maven/'+r['type']+'/'+r['name'])
 return {'repositories':{x['name']:x for x in repos},'Maven_configurations':configs,'roles':{x['id']:x for x in api.json('GET','/security/roles')},'users':{x['userId']:x for x in api.json('GET','/security/users')},'anonymous':api.json('GET','/security/anonymous'),'EULA':api.json('GET','/system/eula')}
def save(name,value):
 p=STATE/name;p.write_text(json.dumps(value,indent=2)+'\n');p.chmod(0o600)
before=capture();assert not(set(REPOS)&before['repositories'].keys())and not(set(ROLES)&before['roles'].keys())and not(set(USERS)&before['users'].keys()),'Puyu-name-conflict-no-overwrite'
assert before['anonymous']['enabled']is False and before['EULA']['accepted']is True
secrets_dir=Path('/root/dell-nexus-secrets');names=['puyu-reader-password','puyu-publisher-password'];assert all(not(secrets_dir/n).exists()for n in names)
old_secrets={str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in secrets_dir.iterdir()if p.is_file()}
frame=subprocess.check_output(['docker','ps','--no-trunc','--format','{{.ID}} {{.Image}} {{.Names}}']).decode();unit_pid=subprocess.check_output(['systemctl','show','dell-nexus.service','-p','MainPID','--value']).decode()
save('before.json',before);journal={'phase':'preflight-passed','created_repositories':[],'created_roles':[],'created_users':[],'data_migrated':False};save('journal.json',journal)
for name,version,write in [('puyu-releases','RELEASE','ALLOW_ONCE'),('puyu-snapshots','SNAPSHOT','ALLOW')]:
 api.json('POST','/repositories/maven/hosted',{'name':name,'online':True,'storage':{'blobStoreName':'default','strictContentTypeValidation':True,'writePolicy':write},'maven':{'versionPolicy':version,'layoutPolicy':'STRICT','contentDisposition':'INLINE'}});journal['created_repositories'].append(name);save('journal.json',journal)
api.json('POST','/repositories/maven/group',{'name':'puyu-public','online':True,'storage':{'blobStoreName':'default','strictContentTypeValidation':True},'group':{'memberNames':['puyu-releases','puyu-snapshots']}});journal['created_repositories'].append('puyu-public');save('journal.json',journal)
read=['nx-repository-view-maven2-'+name+'-'+action for name in REPOS for action in ['browse','read']]
publish=read+['nx-repository-view-maven2-'+name+'-'+action for name in REPOS[:2]for action in ['add','edit']]
for role,priv in zip(ROLES,[read,publish]):
 api.json('POST','/security/roles',{'id':role,'name':role,'description':'Scoped Puyu Maven '+('read-only'if role==ROLES[0]else'publication; no delete or administration'),'privileges':priv,'roles':[]});journal['created_roles'].append(role);save('journal.json',journal)
for user,role,name in zip(USERS,ROLES,names):
 value=secrets.token_urlsafe(36);p=secrets_dir/name;fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
 with os.fdopen(fd,'w')as f:f.write(value+'\n');f.flush();os.fsync(f.fileno())
 api.json('POST','/security/users',{'userId':user,'firstName':'Puyu','lastName':user,'emailAddress':user+'@dell.local','password':value,'status':'active','roles':[role]});journal['created_users'].append(user);save('journal.json',journal)
after=capture()
for category in ['repositories','Maven_configurations','roles','users']:
 assert all(after[category][k]==v for k,v in before[category].items()),'preexisting-Nexus-contract-drift'
assert after['anonymous']==before['anonymous']and after['EULA']==before['EULA']
assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==d for p,d in old_secrets.items())
assert subprocess.check_output(['docker','ps','--no-trunc','--format','{{.ID}} {{.Image}} {{.Names}}']).decode()==frame
assert subprocess.check_output(['systemctl','show','dell-nexus.service','-p','MainPID','--value']).decode()==unit_pid
for name in REPOS[:2]:
 for endpoint in ['components','assets']:
  page=api.json('GET','/'+endpoint+'?repository='+name);assert not page['items']and not page.get('continuationToken')
assert after['Maven_configurations']['puyu-public']['group']['memberNames']==REPOS[:2]
journal['phase']='empty-Puyu-repositories-and-scoped-identities-created';save('journal.json',journal)
result={'status':journal['phase'],'base_URL':'http://192.168.19.31:8081','repositories':REPOS,'hosted_components':0,'hosted_assets':0,'group_members':REPOS[:2],'roles':ROLES,'users':USERS,'reader_privileges':read,'publisher_privileges':publish,'publisher_delete_or_admin_privileges':False,'existing_repositories_users_roles_settings_and_passwords_unchanged':True,'Nexus_container_identity_and_service_PID_unchanged':True,'Nexus_restarted':False,'old_data_migrated':False,'anonymous_enabled':False,'credential_values_or_private_hashes_output':False,'scoped_secrets_VM220_root600_only':True}
save('provision-result.json',result);print(json.dumps(result))
