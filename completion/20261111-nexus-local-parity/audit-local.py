#!/usr/bin/env python3
"""Read local loopback repository configuration only; no assets or credentials exported."""
import datetime,json,subprocess
from pathlib import Path
from zoneinfo import ZoneInfo
BASE='http://127.0.0.1:8081/service/rest/v1'
def get(path):
 p=subprocess.run(['curl','--noproxy','*','--connect-timeout','4','--max-time','15','-sS','-w','\n%{http_code}',BASE+path],capture_output=True,text=True);assert p.returncode==0
 body,status=p.stdout.rsplit('\n',1)
 if status!='200':return {'HTTP':int(status)}
 return json.loads(body)
repos=get('/repositories');assert isinstance(repos,list),'local-repository-list-not-readable'
rows=[]
for r in repos:
 row={k:r[k]for k in ['name','format','type']}
 if r['format']=='maven2':
  c=get('/repositories/maven/'+r['type']+'/'+r['name'])
  if 'HTTP'in c:row['configuration_HTTP']=c['HTTP']
  else:
   row['online']=c['online'];row['storage']={k:c['storage'][k]for k in ['blobStoreName','strictContentTypeValidation']if k in c['storage']}
   if r['type']=='hosted':row['storage']['writePolicy']=c['storage']['writePolicy'];row['maven']=c['maven']
   if r['type']=='group':row['members']=c['group']['memberNames']
   if r['type']=='proxy':
    # Print only public upstream origin/path without credentials/query, never authentication data.
    import urllib.parse
    u=urllib.parse.urlsplit(c['proxy']['remoteUrl']);row['proxy_remote_public_origin_path']=u.scheme+'://'+(u.hostname or'')+(':'+str(u.port)if u.port else'')+u.path
 rows.append(row)
out={'at':datetime.datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),'local_instance':'127.0.0.1:8081','repositories':rows,'local_instance_mutations':False,'artifact_data_exported':False,'credentials_output':False}
p=Path(__file__).with_name('local-repositories.json');p.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');print(json.dumps(out,ensure_ascii=False))
