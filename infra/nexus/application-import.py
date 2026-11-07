#!/usr/bin/env python3
"""Import hosted content into owned new Nexus. Admin secrets remain guest-local."""
import argparse
import base64
import collections
import datetime
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zipfile

BASE = Path(__file__).resolve().parent
from target_guard import verify_target
DATA = Path('/srv/nexus/application-import')
STATE = Path('/root/dell-nexus-import')
SECRET = Path('/root/dell-nexus-secrets')
REPO = 'imnull-releases'
ORIGIN = 'http://127.0.0.1:8081'


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):return None


class API:
    def __init__(self, user='admin', name='admin-password'):
        networks=json.loads(subprocess.run(['docker','inspect','nexus-nexus-1','--format','{{json .NetworkSettings.Networks}}'],capture_output=True,text=True,check=True).stdout)
        if set(networks)!={'nexus_backend'}:raise RuntimeError('Nexus must stay internal-only')
        network=json.loads(subprocess.run(['docker','network','inspect','nexus_backend'],capture_output=True,text=True,check=True).stdout)[0]
        if network['Internal'] is not True:raise RuntimeError('Nexus backend isolation was changed')
        path=SECRET/name
        if path.is_symlink() or path.stat().st_mode&0o777!=0o600:raise RuntimeError('Guest-local new credential file must be private')
        self.header={'Authorization':'Basic '+base64.b64encode((user+':'+path.read_text().strip()).encode()).decode()}
        self.opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())

    def request(self, method, path, body=None, content_type='application/json', allowed=(200,201,204)):
        if not path.startswith('/') or '://' in path:raise RuntimeError('Only target-local API paths are allowed')
        headers=dict(self.header)
        if body is not None:
            headers['Content-Type']=content_type
            if not isinstance(body,bytes):body=json.dumps(body).encode()
        request=urllib.request.Request(ORIGIN+path,data=body,headers=headers,method=method)
        try:
            with self.opener.open(request,timeout=60) as response:status=response.status;data=response.read()
        except urllib.error.HTTPError as error:status=error.code;data=error.read()
        if status not in allowed:raise RuntimeError('Target '+method+' '+path.split('?')[0]+' HTTP '+str(status))
        return status,data

    def json(self, method, path, body=None):
        _,raw=self.request(method,'/service/rest/v1'+path,body)
        return json.loads(raw) if raw.strip() else None


def save(name,value):
    STATE.mkdir(parents=True,exist_ok=True,mode=0o700);STATE.chmod(0o700)
    path=STATE/name;path.write_text(json.dumps(value,indent=2)+'\n');path.chmod(0o600)


def manifest():
    raw=(DATA/'assets.json').read_bytes();data=json.loads(raw)
    if not data['complete'] or data.get('source_credentials_or_H2_exported') is not False or data.get('proxy_or_group_requests')!=0:
        raise RuntimeError('Source must be a complete hosted-only application export without old identities/H2')
    assets=[x for x in data['assets'] if x['source_repository']==REPO]
    primary=[x for x in assets if x['classification']=='primary']
    if len(primary)!=234 or len({x['source_component_id'] for x in primary})!=49:raise RuntimeError('Unexpected source primary/component count')
    for item in primary:
        version=item.get('version');base=item.get('maven2',{}).get('version',version)
        if not version or 'snapshot' in version.lower() or 'snapshot' in str(base).lower() or re.search(r'-\d{8}\.\d{6}-\d+$',version):
            raise RuntimeError('Source has unknown/snapshot version; RELEASE policy cannot be assumed')
    for item in assets:
        path=DATA/item['file']
        if not path.resolve().is_relative_to(DATA) or path.is_symlink():raise RuntimeError('Unsafe source asset file')
        with path.open('rb') as stream:
            if hashlib.file_digest(stream,'sha256').hexdigest()!=item['sha256']:raise RuntimeError('Source export asset checksum mismatch')
    return data,assets,primary,hashlib.sha256(raw).hexdigest()


def repo_path(path):
    if path.startswith('/') or '..' in Path(path).parts:raise RuntimeError('Asset path must be normalized repository-relative')
    return '/repository/'+REPO+'/'+urllib.parse.quote(path,safe='/')


def ensure_repository(api):
    if api.json('GET','/system/eula')['accepted'] is not True:raise RuntimeError('EULA not accepted; no acceptance request is made by importer')
    repositories=api.json('GET','/repositories');existing=next((x for x in repositories if x['name']==REPO),None)
    if not existing:
        api.json('POST','/repositories/maven/hosted',{'name':REPO,'online':True,'storage':{'blobStoreName':'default','strictContentTypeValidation':True,'writePolicy':'ALLOW_ONCE'},'maven':{'versionPolicy':'RELEASE','layoutPolicy':'STRICT','contentDisposition':'INLINE'}})
    elif existing['format']!='maven2' or existing['type']!='hosted':raise RuntimeError('Existing destination is not Maven hosted')
    config=api.json('GET','/repositories/maven/hosted/'+REPO)
    if config['maven']['versionPolicy']!='RELEASE' or config['storage']['writePolicy']!='ALLOW_ONCE':
        raise RuntimeError('Destination policy differs; do not overwrite existing repository settings')
    return config


def upload():
    verify_target(data_path='/srv/nexus/data');_,assets,primary,request_id=manifest();api=API();config=ensure_repository(api)
    added,skipped=0,0;records=[]
    for item in primary:
        path=repo_path(item['normalized_path']);status,current=api.request('GET',path,allowed=(200,404))
        if status==200:
            if hashlib.sha256(current).hexdigest()!=item['sha256']:raise RuntimeError('Existing destination asset differs; never overwritten')
            skipped+=1
        else:
            api.request('PUT',path,(DATA/item['file']).read_bytes(),content_type='application/octet-stream')
            added+=1
        status,current=api.request('GET',path)
        actual=hashlib.sha256(current).hexdigest()
        if actual!=item['sha256']:raise RuntimeError('Destination primary bytes differ')
        records.append({'source_asset_id':item['source_asset_id'],'path':item['normalized_path'],'source_sha256':item['sha256'],'target_sha256':actual,'bytes':len(current),'component':{k:item.get(k) for k in ('group','name','version')},'extension':item['extension']})
        if len(records)%25==0:print(json.dumps({'primary_verified':len(records),'added':added,'already_matching':skipped}),flush=True)
    result={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_manifest_sha256':request_id,'request_id':request_id,'repository':REPO,'version_policy':'RELEASE','write_policy':'ALLOW_ONCE','source_versions':sorted({x['version'] for x in primary}),'primary_assets_verified':len(records),'added':added,'already_matching':skipped,'records':records,'old_h2_users_or_upstream_credentials_imported':False,'external_proxy_requests':0}
    first=STATE/'upload-first.json'
    if not first.exists():
        previous=STATE/'upload.json'
        save('upload-first.json',json.loads(previous.read_text()) if previous.exists() else result)
    history_path=STATE/'upload-history.json'
    history=json.loads(history_path.read_text()) if history_path.exists() else []
    history.append({k:v for k,v in result.items() if k!='records'})
    save('upload-history.json',history)
    save('upload.json',result);print(json.dumps({k:v for k,v in result.items() if k!='records'}),flush=True)


def wire():
    verify_target(data_path='/srv/nexus/data');api=API();ensure_repository(api)
    repositories={x['name']:x for x in api.json('GET','/repositories')}
    group=api.json('GET','/repositories/maven/group/finger-public')
    old=list(group['group']['memberNames'])
    if any(repositories[x]['type']!='hosted' for x in old):raise RuntimeError('Managed public group unexpectedly contains a proxy/group')
    members=['finger-releases','finger-snapshots']+[x for x in old if x not in ('finger-releases','finger-snapshots',REPO)]+[REPO]
    if old!=members:
        api.json('PUT','/repositories/maven/group/finger-public',{'name':'finger-public','online':group['online'],'storage':group['storage'],'group':{'memberNames':members}})
    changes=[]
    for role in ('dell-artifact-reader','dell-artifact-publisher'):
        item=api.json('GET','/security/roles/'+role)
        if item.get('roles'):raise RuntimeError('Managed role has unexpected inheritance')
        before=set(item['privileges']);append={'nx-repository-view-maven2-'+REPO+'-'+x for x in ('browse','read')}
        if any(x.startswith('nx-repository-view-maven2-'+REPO+'-') and x not in append for x in before):raise RuntimeError('Legacy repository already has excessive managed privileges')
        removed={'nx-repository-view-maven2-finger-releases-add','nx-repository-view-maven2-finger-releases-edit'} if role=='dell-artifact-publisher' else set()
        after=sorted((before|append)-removed)
        if set(after)!=before:api.json('PUT','/security/roles/'+role,{k:(after if k=='privileges' else item[k]) for k in ('id','name','description','privileges','roles')})
        changes.append({'role':role,'privileges_added':sorted(set(after)-before),'privileges_removed':sorted(before-set(after)),'delete_or_write_added':False})
    actual=api.json('GET','/repositories/maven/group/finger-public')['group']['memberNames']
    if actual!=members:raise RuntimeError('Group priority mismatch')
    save('group-and-roles.json',{'members':members,'roles':changes,'passwords_changed':False,'external_or_proxy_members_added':False});print(json.dumps({'group_members':members,'legacy_roles':'browse/read only','passwords_changed':False}))


def all_items(api,kind):
    result=[];token=None
    while True:
        values={'repository':REPO}
        if token:values['continuationToken']=token
        page=api.json('GET','/'+kind+'?'+urllib.parse.urlencode(values));result+=page['items'];token=page.get('continuationToken')
        if not token:return result


def metadata_view(data):
    root=ET.fromstring(data)
    return {key:root.findtext(key) for key in ('groupId','artifactId')}|{'versions':sorted(x.text for x in root.findall('versioning/versions/version')),'latest':root.findtext('versioning/latest'),'release':root.findtext('versioning/release'),'lastUpdated':root.findtext('versioning/lastUpdated')}


def verify():
    verify_target(data_path='/srv/nexus/data');_,assets,primary,request_id=manifest();api=API();ensure_repository(api)
    components=all_items(api,'components');current_assets=all_items(api,'assets')
    if len(components)!=49:raise RuntimeError('Imported component count is not 49')
    source_gav={(x['group'],x['name'],x['version']) for x in primary}
    target_gav={(x['group'],x['name'],x['version']) for x in components}
    if source_gav!=target_gav:raise RuntimeError('Source/target component GAV sets differ')
    target_index={x['path'].lstrip('/'):x for x in current_assets};mapping=[]
    for item in primary:
        _,data=api.request('GET',repo_path(item['normalized_path']));actual=hashlib.sha256(data).hexdigest()
        if actual!=item['sha256']:raise RuntimeError('Primary integrity check failed')
        target=target_index.get(item['normalized_path'])
        if not target:raise RuntimeError('Primary absent from target asset API')
        mapping.append({'source_asset_id':item['source_asset_id'],'target_asset_id':target['id'],'path':item['normalized_path'],'sha256':actual})
    regenerated=[];resource_hashes={}
    for item in assets:
        if item['classification']!='maven-metadata':continue
        status,data=api.request('GET',repo_path(item['normalized_path']),allowed=(200,404))
        if status!=200:raise RuntimeError('Service-generated Maven metadata missing: '+item['normalized_path'])
        original=(DATA/item['file']).read_bytes();old,new=metadata_view(original),metadata_view(data)
        if any(old[k]!=new[k] for k in ('groupId','artifactId','versions')):raise RuntimeError('Regenerated metadata coordinate/version set differs')
        regenerated.append({'path':item['normalized_path'],'source_sha256':item['sha256'],'target_sha256':hashlib.sha256(data).hexdigest(),'byte_equal':original==data,'coordinate_versions_equal':True,'source_last_updated':old['lastUpdated'],'target_last_updated':new['lastUpdated'],'source_latest_release':[old['latest'],old['release']],'target_latest_release':[new['latest'],new['release']]})
    checksum_records=[]
    for item in assets:
        if item['classification']!='checksum':continue
        path=item['normalized_path'];parent,algorithm=path.rsplit('.',1)
        if algorithm not in ('md5','sha1','sha256','sha512'):raise RuntimeError('Unknown generated checksum algorithm')
        status,value=api.request('GET',repo_path(path),allowed=(200,404))
        if status!=200:raise RuntimeError('Generated checksum missing')
        if parent not in resource_hashes:
            _,body=api.request('GET',repo_path(parent));resource_hashes[parent]={name:hashlib.new(name,body).hexdigest() for name in ('md5','sha1','sha256','sha512')}
        if value.decode().strip().lower()!=resource_hashes[parent][algorithm]:raise RuntimeError('Generated checksum does not match target resource')
        checksum_records.append({'path':path,'algorithm':algorithm,'target_resource_checksum_valid':True,'source_file_sha256':item['sha256'],'target_checksum_file_sha256':hashlib.sha256(value).hexdigest(),'byte_equal_to_source':hashlib.sha256(value).hexdigest()==item['sha256']})
    result={'source_manifest_sha256':request_id,'repository':REPO,'target_components':len(components),'component_gav_sets_equal':True,'primary_assets':len(mapping),'primary_all_actual_sha256_equal':True,'source_to_target_asset_id_mapping':mapping,'regenerated_metadata':regenerated,'generated_checksum_validation':checksum_records,'metadata_strategy':'service generated; semantic coordinate/version sets equal, bytes/timestamps separately compared','old_h2_users_or_upstream_credentials_imported':False,'external_proxy_requests':0}
    save('verification.json',result);print(json.dumps({'components':len(components),'primary_verified':len(mapping),'metadata_semantics_verified':len(regenerated),'checksum_target_resource_verified':len(checksum_records),'metadata_bytes_different':sum(not x['byte_equal'] for x in regenerated)}),flush=True)


def permissions():
    verify_target(data_path='/srv/nexus/data');_,_,primary,_=manifest();admin=API();first=next(x for x in primary if x['extension']=='jar');path=repo_path(first['normalized_path'])
    result={}
    for user,secret in [('dell-reader','reader-password'),('dell-publisher','publisher-password')]:
        client=API(user,secret);_,body=client.request('GET',path);assert hashlib.sha256(body).hexdigest()==first['sha256']
        denied_path='/repository/'+REPO+'/com/dell/acceptance/forbidden-legacy-write/0/forbidden-legacy-write-0.jar'
        buff=io.BytesIO()
        with zipfile.ZipFile(buff,'w') as jar:jar.writestr('fixture.txt','Dedicated denied-write acceptance')
        put,_=client.request('PUT',denied_path,buff.getvalue(),content_type='application/java-archive',allowed=(403,))
        delete,_=client.request('DELETE',denied_path,allowed=(403,))
        result[user]={'existing_primary_read_sha256_equal':True,'new_legacy_write_status':put,'nonexistent_canary_delete_status':delete}
    _,group=API('dell-reader','reader-password').request('GET','/repository/finger-public/'+urllib.parse.quote(first['normalized_path'],safe='/'))
    if hashlib.sha256(group).hexdigest()!=first['sha256']:raise RuntimeError('Managed group could not resolve legacy local hosted asset')
    save('permissions.json',{'users':result,'group_local_hosted_read':True,'passwords_changed':False,'other_repositories_written':False,'external_proxy_requests':0});print(json.dumps({'legacy_read_verified':True,'reader_and_publisher_legacy_write_delete_denied':True,'group_read_verified':True}))


if __name__=='__main__':
    os.umask(0o077)
    p=argparse.ArgumentParser();p.add_argument('action',choices=['upload','wire','verify','permissions']);args=p.parse_args()
    try:{'upload':upload,'wire':wire,'verify':verify,'permissions':permissions}[args.action]()
    except Exception as error:print('HOSTED IMPORT ERROR: '+str(error),file=__import__('sys').stderr);__import__('sys').exit(1)
