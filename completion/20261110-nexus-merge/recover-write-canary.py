#!/usr/bin/env python3
"""Finish cleanup only for recorded newly created acceptance canary; never upload again."""
import importlib.util,json,os,socket,sys,time,urllib.parse
from pathlib import Path
assert os.geteuid()==0 and socket.gethostname()=='publish-service'
base=Path('/opt/dell/nexus');sys.path.insert(0,str(base));s=importlib.util.spec_from_file_location('canary_cleanup_api',base/'application-import.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);api=m.API()
record=Path('/root/dell-nexus-merge/cb01b8582f544381b0461001dfa3ccb4/write-canary.json');x=json.loads(record.read_text());assert x['phase']=='intent' and x['preexisting_asset'] is False and x['repository']=='dell-acceptance'and x['name']=='nexus-merge-canary'and x['version'].startswith('merge-')
repo=x['repository'];version=x['version'];name=x['name'];path='/repository/'+repo+'/com/dell/'+name+'/'+version+'/'+name+'-'+version+'.pom'
status,body=api.request('GET',path);assert version.encode()in body and ('<artifactId>'+name+'</artifactId>').encode()in body

def components():
 rows=[];token=None
 while True:
  query={'repository':repo}
  if token:query['continuationToken']=token
  page=api.json('GET','/components?'+urllib.parse.urlencode(query));rows+=page['items'];token=page.get('continuationToken')
  if not token:return rows
for _ in range(20):
 rows=components();owned=[r for r in rows if r['repository']==repo and r['group']=='com.dell'and r['name']==name and r['version']==version]
 if owned:break
 time.sleep(1)
assert len(owned)==1,'recorded owned component must be uniquely visible before deletion';item=owned[0]
assert all(a['path'].lstrip('/').startswith('com/dell/'+name+'/'+version+'/') and '..' not in Path(a['path']).parts for a in item['assets'])
api.request('DELETE','/service/rest/v1/components/'+urllib.parse.quote(item['id'],safe=''),allowed=(204,))
for _ in range(20):
 code,_=api.request('GET',path,allowed=(200,404))
 rows=components()
 if code==404 and all(r['id']!=item['id']for r in rows):break
 time.sleep(1)
assert code==404
old=json.loads(Path('/srv/nexus/.dell-merge-baseline-20261110.json').read_text())['hosted'][repo]['components'];assert {r['id']for r in rows}=={r['id']for r in old}
x.update(phase='verified-and-cleaned',index_visibility_required_retry=True);record.write_text(json.dumps(x));record.chmod(0o600)
print(json.dumps({'status':'acceptance-only-write-read-delete-canary-passed','repository':repo,'upload_and_readback_previously_succeeded':True,'cleanup_HTTP':204,'after_cleanup_asset_HTTP':code,'original_component_IDs_preserved':True,'repository_index_visibility_handled_by_bounded_components_listing':True,'business_repositories_written':False,'new_upload_during_cleanup':False,'passwords_changed':False}))
