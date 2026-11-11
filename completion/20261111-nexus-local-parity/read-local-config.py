#!/usr/bin/env python3
"""Use existing local Gradle Nexus credentials in memory for read-only configuration queries."""
import base64,datetime,json,re,urllib.error,urllib.parse,urllib.request
from pathlib import Path
from zoneinfo import ZoneInfo
wanted={}
for line in (Path.home()/'.gradle/gradle.properties').read_text().splitlines():
 m=re.match(r'^\s*(nexusUsername|nexusPassword)\s*[=:]\s*(.*)$',line)
 if m:wanted[m.group(1)]=m.group(2)
assert all(wanted.get(k)for k in ['nexusUsername','nexusPassword']),'local-Nexus-credential-properties-unavailable'
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}));header='Basic '+base64.b64encode((wanted['nexusUsername']+':'+wanted['nexusPassword']).encode()).decode();BASE='http://127.0.0.1:8081/service/rest/v1'
def get(path):
 try:
  with opener.open(urllib.request.Request(BASE+path,headers={'Authorization':header}),timeout=15)as r:return json.loads(r.read())
 except urllib.error.HTTPError as e:raise RuntimeError('local-config-GET-HTTP-'+str(e.code))from None
repos=get('/repositories');rows=[]
for row in repos:
 fmt={'maven2':'maven'}.get(row['format'],row['format']);c=get('/repositories/'+fmt+'/'+row['type']+'/'+row['name']);safe={k:c[k]for k in ['name','online','storage','maven','group','negativeCache','nugetProxy']if k in c};safe.update(format=row['format'],type=row['type'])
 if 'proxy'in c:
  remote=c['proxy']['remoteUrl'];u=urllib.parse.urlsplit(remote);assert u.scheme in ['http','https']and not u.username and not u.password and not u.query and not u.fragment,'private-upstream-URL-needs-separate-handling';safe['proxy']=c['proxy']
 if 'httpClient'in c:
  http=c['httpClient'];assert not http.get('authentication'),'local-upstream-auth-not-exported';safe['httpClient']={k:v for k,v in http.items()if k!='authentication'}
 rows.append(safe)
out={'at':datetime.datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),'local_instance':'127.0.0.1:8081','repositories':rows,'local_username_or_password_exported':False,'repository_or_artifact_mutations':False,'artifact_data_exported':False}
p=Path(__file__).with_name('local-repository-configs.json');p.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');print(json.dumps(out,ensure_ascii=False))
