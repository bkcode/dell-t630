#!/usr/bin/env python3
"""Verify dedicated acceptance repo assets; cleanup only newly generated canary metadata if present."""
import importlib.util,json,os,socket,sys,urllib.parse
from pathlib import Path
assert os.geteuid()==0 and socket.gethostname()=='publish-service'
base=Path('/opt/dell/nexus');sys.path.insert(0,str(base));s=importlib.util.spec_from_file_location('canary_asset_verify',base/'application-import.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);api=m.API()
record=json.loads(Path('/root/dell-nexus-merge/cb01b8582f544381b0461001dfa3ccb4/write-canary.json').read_text());assert record['phase']=='verified-and-cleaned'and record['repository']=='dell-acceptance'
repo=record['repository'];before=json.loads(Path('/srv/nexus/.dell-merge-baseline-20261110.json').read_text())['hosted'][repo]['assets'];oldids={x['id']for x in before};prefix='com/dell/'+record['name']+'/'
assert not any(x['path'].lstrip('/').startswith(prefix)for x in before)
def assets():
 rows=[];token=None
 while True:
  q={'repository':repo}
  if token:q['continuationToken']=token
  p=api.json('GET','/assets?'+urllib.parse.urlencode(q));rows+=p['items'];token=p.get('continuationToken')
  if not token:return rows
rows=assets();assert oldids<={x['id']for x in rows};extras=[x for x in rows if x['id']not in oldids]
for x in extras:
 assert x['repository']==repo and x['path'].lstrip('/').startswith(prefix)and '..'not in Path(x['path']).parts
 api.request('DELETE','/service/rest/v1/assets/'+urllib.parse.quote(x['id'],safe=''),allowed=(204,))
rows=assets();assert {x['id']for x in rows}==oldids
assert {x['path'].lstrip('/')for x in rows}=={x['path'].lstrip('/')for x in before}
print(json.dumps({'status':'acceptance-repository-original-asset-ID-set-restored','original_assets':len(before),'current_assets':len(rows),'owned_generated_metadata_assets_cleaned':len(extras),'other_assets_deleted':False,'business_repositories_written':False}))
