#!/usr/bin/env python3
"""One temporary POM in existing acceptance-only repo; remove only its exact new component."""
import hashlib,importlib.util,json,os,socket,sys,time,urllib.parse,uuid
from pathlib import Path
assert os.geteuid()==0 and socket.gethostname()=='publish-service' and not Path('/etc/pve').exists()
base=Path('/opt/dell/nexus');sys.path.insert(0,str(base));spec=importlib.util.spec_from_file_location('nexus_canary',base/'application-import.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);api=m.API()
baseline=json.loads(Path('/srv/nexus/.dell-merge-baseline-20261110.json').read_text());repo='dell-acceptance';assert repo in baseline['hosted']
config=api.json('GET','/repositories/maven/hosted/'+repo);assert config['name']==repo and config['online'] is True
version='merge-'+uuid.uuid4().hex;name='nexus-merge-canary';path='/repository/'+repo+'/com/dell/'+name+'/'+version+'/'+name+'-'+version+'.pom'
status,_=api.request('GET',path,allowed=(404,));assert status==404
body=('<?xml version="1.0" encoding="UTF-8"?><project xmlns="http://maven.apache.org/POM/4.0.0"><modelVersion>4.0.0</modelVersion><groupId>com.dell</groupId><artifactId>'+name+'</artifactId><version>'+version+'</version><packaging>pom</packaging></project>').encode()
query='/search?'+urllib.parse.urlencode({'repository':repo,'group':'com.dell','name':name,'version':version})
record=Path('/root/dell-nexus-merge/cb01b8582f544381b0461001dfa3ccb4/write-canary.json');assert not record.exists();record.write_text(json.dumps({'repository':repo,'name':name,'version':version,'preexisting_asset':False,'phase':'intent'}));record.chmod(0o600)
created=False
try:
 code,_=api.request('PUT',path,body,content_type='application/xml',allowed=(201,204));created=True
 _,read=api.request('GET',path);assert read==body
finally:
 if created:
  items=[]
  for _ in range(20):
   result=api.json('GET','/components?'+urllib.parse.urlencode({'repository':repo}));items=[r for r in result['items']if r['group']=='com.dell'and r['name']==name and r['version']==version]
   if items:break
   time.sleep(1)
  assert len(items)==1
  item=items[0];assert item['repository']==repo and item['group']=='com.dell'and item['name']==name and item['version']==version
  api.request('DELETE','/service/rest/v1/components/'+urllib.parse.quote(item['id'],safe=''),allowed=(204,))
status,_=api.request('GET',path,allowed=(404,));assert status==404 and not api.json('GET',query)['items']
items=[];token=None
while True:
 q='/components?'+urllib.parse.urlencode({'repository':repo,**({'continuationToken':token}if token else{})});page=api.json('GET',q);items+=page['items'];token=page.get('continuationToken')
 if not token:break
assert {x['id']for x in items}=={x['id']for x in baseline['hosted'][repo]['components']}
record.write_text(json.dumps({'repository':repo,'name':name,'version':version,'phase':'verified-and-cleaned','original_component_IDs_preserved':True}));record.chmod(0o600)
print(json.dumps({'status':'acceptance-only-write-read-delete-canary-passed','repository':repo,'temporary_payload_bytes':len(body),'upload_HTTP':code,'readback_bytes_equal':True,'cleanup_HTTP':204,'after_cleanup_asset_HTTP':status,'original_component_IDs_preserved':True,'business_repositories_written':False,'passwords_changed':False,'Java_or_Go_build_or_publish':False}))
