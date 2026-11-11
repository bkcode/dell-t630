#!/usr/bin/env python3
"""Read repository configurations and component identities; no payload export."""
import datetime,importlib.util,json,os,socket,sys,urllib.parse
from pathlib import Path
from zoneinfo import ZoneInfo
assert os.geteuid()==0 and socket.gethostname()=='publish-service'
base=Path('/opt/dell/nexus');sys.path.insert(0,str(base));s=importlib.util.spec_from_file_location('parity_api',base/'application-import.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);api=m.API()
def items(endpoint,repo):
 rows=[];token=None
 while True:
  q={'repository':repo}
  if token:q['continuationToken']=token
  page=api.json('GET','/'+endpoint+'?'+urllib.parse.urlencode(q));rows+=page['items'];token=page.get('continuationToken')
  if not token:return rows
rows=[]
for r in api.json('GET','/repositories'):
 fmt={'maven2':'maven'}.get(r['format'],r['format']);c=api.json('GET','/repositories/'+fmt+'/'+r['type']+'/'+r['name']);row={k:c[k]for k in ['name','online','storage','maven','group','proxy','negativeCache','nugetProxy']if k in c};row.update(format=r['format'],type=r['type'])
 if 'httpClient'in c:row['httpClient']={k:v for k,v in c['httpClient'].items()if k!='authentication'}
 if r['type']=='hosted':
  components=items('components',r['name']);assets=items('assets',r['name']);row.update(components=len(components),assets=len(assets));row['coordinates']=[{k:x.get(k)for k in ['group','name','version']}for x in components]if r['name']!='imnull-releases'else'not-exported-business-coordinate-list'
 rows.append(row)
print(json.dumps({'at':datetime.datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),'repositories':rows,'repository_mutations':False,'payload_or_credentials_exported':False}))
