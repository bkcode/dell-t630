#!/usr/bin/env python3
"""POST-HANDOVER ONLY: GET-only same Nexus instance verification on220; no publish/init/repo writes."""
import json,sys
from pathlib import Path
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];sys.path.insert(0,str(ROOT/'scripts'));import control
control.BASE+=['-o','ForwardAgent=no'];info=json.loads((ROOT/'network19/evidence/migrated-access.json').read_text())['targets']['220'];nonce=json.loads((HERE/'standby-window.json').read_text())['nonce']
SCRIPT=r'''
import contextlib,hashlib,importlib.util,io,json,os,socket,sys,urllib.request,urllib.error
from pathlib import Path
sys.dont_write_bytecode=True
assert os.geteuid()==0 and socket.gethostname().split('.')[0]=='publish-service' and not Path('/etc/pve').exists()
BASE=Path('/opt/dell/nexus');sys.path.insert(0,str(BASE));s=importlib.util.spec_from_file_location('nexus',BASE/'application-import.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
assert m.ORIGIN=='http://192.168.19.31:8081'
original=m.API.request;counts={'GET':0}
def get_only(self,method,path,*args,**kwargs):
 if method!='GET':raise RuntimeError('Non-GET method rejected by consolidation verification')
 counts['GET']+=1;return original(self,method,path,*args,**kwargs)
m.API.request=get_only
folder=Path('/root/dell-nexus-merge')/NONCE;j=json.loads((folder/'relocation.json').read_text());assert j['phase']=='running-final-data-and-publisher-verification-required'
for key,path in [('secret/admin-password','/root/dell-nexus-secrets/admin-password'),('secret/reader-password','/root/dell-nexus-secrets/reader-password'),('secret/publisher-password','/root/dell-nexus-secrets/publisher-password')]:
 p=Path(path);assert p.stat().st_uid==0 and p.stat().st_mode&0o777==0o600 and hashlib.sha256(p.read_bytes()).hexdigest()==j['entries'][key]['sha256']
with contextlib.redirect_stdout(io.StringIO()):m.verify()
v=json.loads((m.STATE/'verification.json').read_text());api=m.API();assert api.json('GET','/system/eula')['accepted'] is True
config=api.json('GET','/repositories/maven/group/finger-public');assert config['group']['memberNames']==['finger-releases','finger-snapshots','imnull-releases']
users={u['userId']:u for u in api.json('GET','/security/users')}
for user,role in [('dell-reader','dell-artifact-reader'),('dell-publisher','dell-artifact-publisher')]:assert users[user]['roles']==[role] and users[user]['status']=='active'
roles={role:api.json('GET','/security/roles/'+role) for role in ['dell-artifact-reader','dell-artifact-publisher']}
for name,value in roles.items():
 priv=value['privileges'];assert all('nx-repository-view-maven2-imnull-releases-'+verb in priv for verb in ['read','browse'])
 assert not any('nx-repository-view-maven2-imnull-releases-'+verb in priv for verb in ['add','edit','delete'])
 if name=='dell-artifact-publisher':assert not any('nx-repository-view-maven2-finger-releases-'+verb in priv for verb in ['add','edit','delete'])
_,_,primary,_=m.manifest();item=next(x for x in primary if x['extension']=='jar');path=m.repo_path(item['normalized_path'])
for user,secret in [('dell-reader','reader-password'),('dell-publisher','publisher-password')]:
 _,body=m.API(user,secret).request('GET',path);assert hashlib.sha256(body).hexdigest()==item['sha256']
_,body=m.API('dell-reader','reader-password').request('GET','/repository/finger-public/'+item['normalized_path']);assert hashlib.sha256(body).hexdigest()==item['sha256']
class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,*args,**kwargs):return None
anonymous_opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
try:
 with anonymous_opener.open(m.ORIGIN+path,timeout=15) as response:anonymous_status=response.status;response.read(1)
except urllib.error.HTTPError as error:anonymous_status=error.code;error.close()
assert anonymous_status in (401,403),'anonymous access policy must remain disabled'
profile=json.loads(Path('/etc/dell-publisher/client-test240.json').read_text());assert profile=={'source_ip':'192.168.19.30','target_host':'192.168.19.45','target_user':'deployer','host_key_alias':'dell-test240-publisher'}
import subprocess
assert 'docker' not in subprocess.check_output(['/usr/bin/id','publisher'],text=True)
assert subprocess.run(['/usr/sbin/runuser','-u','publisher','--','/usr/bin/test','-w','/var/run/docker.sock']).returncode!=0
result={'role':220,'status':'same-instance-Nexus-GAV-data-identity-EULA-permissions-verified','origin':m.ORIGIN,'components':v['target_components'],'primary_SHA_verified':v['primary_assets'],'metadata_semantics_verified':len(v['regenerated_metadata']),'checksums_verified':len(v['generated_checksum_validation']),'source_GAV_equal':v['component_gav_sets_equal'],'all_primary_SHA_equal':v['primary_all_actual_sha256_equal'],'same_three_Nexus_secret_bytes_root600':True,'EULA_accepted':True,'same_user_roles_and_minimum_privileges':True,'reader_publisher_and_group_auth_read':True,'anonymous_read_status':anonymous_status,'publisher_profile_source30_target45_preserved':True,'publisher_not_docker_group_socket_denied':True,'publisher_key_contents_not_read_or_copied':True,'only_HTTP_method':'GET','API_GET_requests':counts['GET'],'repo_write_metadata_rebuild_or_init_requests':False}
p=folder/'verification-result.json';p.write_text(json.dumps(result,indent=2)+'\n');p.chmod(0o600)
print(json.dumps(result))
'''.replace('NONCE',repr(nonce))
res=control.guest(220,'sudo /usr/bin/python3 -I -B -',data=SCRIPT.encode(),timeout=600,info=info)
if res['exit_code']:raise SystemExit('Post-handover220 GET-only verification unconfirmed; no raw values emitted')
value=json.loads(res['stdout']);(HERE/'verification220-result.json').write_text(json.dumps(value,indent=2)+'\n');print(json.dumps({'role':220,'status':value['status']}))
