#!/usr/bin/env python3
"""Owned VM221 post-cutover GET-only data/identity/role verification, no repository writes."""
import json
from pathlib import Path
import sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts'));import control
control.BASE+=['-o','ForwardAgent=no']
info=json.loads((ROOT/'network19/evidence/migrated-access.json').read_text())['targets']['221']
assert info['ip']=='192.168.19.31'
nonce=json.loads(Path(__file__).with_name('stage-nonces.json').read_text())['221']
SCRIPT=r'''
import contextlib,hashlib,importlib.util,io,json,sys,urllib.request,urllib.error
from pathlib import Path
sys.dont_write_bytecode=True
B=Path('/opt/dell/nexus');sys.path.insert(0,str(B))
spec=importlib.util.spec_from_file_location('importer',B/'application-import.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
assert m.ORIGIN=='http://192.168.19.31:8081'
original=m.API.request
counts={'GET':0}
def get_only(self,method,path,*args,**kwargs):
 if method!='GET':raise RuntimeError('Non-GET operation rejected by post-network verification')
 counts['GET']+=1
 return original(self,method,path,*args,**kwargs)
m.API.request=get_only
spec=importlib.util.spec_from_file_location('tx',Path('/opt/dell/network19/services-media/guest_transaction.py'));tx=importlib.util.module_from_spec(spec);spec.loader.exec_module(tx)
r=tx.guard(221,'new');folder=Path('/root/dell-network19-media/221')/NONCE;j=json.loads(tx.read(folder/'journal.json'));assert j['phase']=='runtime-ready-final-app-verification-pending';tx.prove_protected(r,j)
old=m.STATE/'verification.json'
if not (folder/'pre-network-data-verification.json').exists():tx.atomic(folder/'pre-network-data-verification.json',old.read_bytes())
# Existing verifier may create a missing repository; GET-only enforcement turns that into a hard failure.
with contextlib.redirect_stdout(io.StringIO()):m.verify()
verification=json.loads(old.read_text());api=m.API()
config={'repo':api.json('GET','/repositories/maven/hosted/imnull-releases'),'group':api.json('GET','/repositories/maven/group/finger-public'),'roles':{role:api.json('GET','/security/roles/'+role) for role in ['dell-artifact-reader','dell-artifact-publisher']}}
assert config['group']['group']['memberNames']==['finger-releases','finger-snapshots','imnull-releases']
for role,value in config['roles'].items():
 privileges=value['privileges'];assert 'nx-repository-view-maven2-imnull-releases-read' in privileges and 'nx-repository-view-maven2-imnull-releases-browse' in privileges
 assert not any(x in privileges for x in ['nx-repository-view-maven2-imnull-releases-'+verb for verb in ['add','edit','delete']])
 if role=='dell-artifact-publisher':
  assert not any('finger-releases-'+verb in x for x in privileges for verb in ['add','edit','delete'])
  assert all('nx-repository-view-maven2-'+repo+'-'+verb in privileges for repo in ['finger-snapshots','dell-acceptance'] for verb in ['add','edit'])
eula=api.json('GET','/system/eula');assert eula['accepted'] is True
_,_,primary,_=m.manifest();first=next(x for x in primary if x['extension']=='jar');path=m.repo_path(first['normalized_path'])
reads={}
for who,secret in [('dell-reader','reader-password'),('dell-publisher','publisher-password')]:
 _,body=m.API(who,secret).request('GET',path);reads[who]=hashlib.sha256(body).hexdigest()==first['sha256'];assert reads[who]
_,group=m.API('dell-reader','reader-password').request('GET','/repository/finger-public/'+first['normalized_path']);assert hashlib.sha256(group).hexdigest()==first['sha256']
_,canary=api.request('GET','/repository/dell-acceptance/com/dell/acceptance/repo-persistence/20261106041801/repo-persistence-20261106041801.jar');assert hashlib.sha256(canary).hexdigest()=='baa80d112a9a144b7ffbb3e71bc202b0e231eb71c9a0ef0154dcc55b2865ea59'
class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,*args,**kwargs):return None
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
try:
 with opener.open(m.ORIGIN+path,timeout=15) as response:anonymous=response.status;response.read(1)
except urllib.error.HTTPError as error:anonymous=error.code;error.close()
assert anonymous in (401,403)
tx.prove_protected(r,j)
result={'role':221,'status':'new-network-GET-only-data-identity-roles-verified','public_uri':m.ORIGIN,'components':verification['target_components'],'primary_SHA_verified':verification['primary_assets'],'metadata_semantics_verified':len(verification['regenerated_metadata']),'checksums_verified':len(verification['generated_checksum_validation']),'source_GAV_sets_equal':verification['component_gav_sets_equal'],'all_primary_SHA_equal':verification['primary_all_actual_sha256_equal'],'metadata_regenerated_now':False,'EULA_accepted':True,'new_identity_secret_bytes_unchanged':True,'local_hosted_reader_and_publisher_read':reads,'legacy_and_formal_write_delete_denied_by_unchanged_roles':True,'negative_write_requests_executed':False,'group_members_preserved':True,'group_hosted_SHA_read':True,'unrelated_publish_canary_SHA_preserved':True,'anonymous_status':anonymous,'only_HTTP_method_executed':'GET','GET_request_count':counts['GET'],'proxy_config_or_upstream_requests':False,'containers':tx.state(r),'data_uuid':r['uuid']}
tx.save(folder/'network-data-verification.json',result)
print(json.dumps(result))
'''.replace('NONCE',repr(nonce))
res=control.guest(221,'sudo python3 -',data=SCRIPT.encode(),timeout=600,info=info)
if res['exit_code']:raise SystemExit('Nexus GET-only verification unconfirmed; no raw detail output')
value=json.loads(res['stdout']);Path(__file__).with_name('nexus-post-cutover-verification.json').write_text(json.dumps(value,indent=2)+'\n')
print(json.dumps({'role':221,'status':value['status']}))
