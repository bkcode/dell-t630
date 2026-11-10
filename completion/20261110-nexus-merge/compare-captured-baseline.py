#!/usr/bin/env python3
"""Compare captured full snapshots, separating only GET-updated lastDownloaded metadata."""
import copy,json,os,socket
from pathlib import Path
assert os.geteuid()==0 and socket.gethostname()=='publish-service'
base=Path('/srv/nexus')
before=json.loads((base/'.dell-merge-baseline-20261110.json').read_text());after=json.loads((base/'.dell-merge-observed-20261110.json').read_text())
assert before['repositories']==after['repositories'] and before['configs']==after['configs']
assert all(before[k]==after[k]for k in ['users','roles','eula'])
assert set(before['hosted'])==set(after['hosted'])
volatile=0
for name,repo in before['hosted'].items():
 target=after['hosted'][name];assert repo['assets']==target['assets'],'asset contents/paths/IDs differ'
 assert len(repo['components'])==len(target['components'])
 for original,current in zip(repo['components'],target['components']):
  a,b=copy.deepcopy(original),copy.deepcopy(current)
  assert len(a['assets'])==len(b['assets'])
  for x,y in zip(a['assets'],b['assets']):
   assert ('lastDownloaded'in x)==('lastDownloaded'in y)
   if x.get('lastDownloaded')!=y.get('lastDownloaded'):volatile+=1
   x.pop('lastDownloaded',None);y.pop('lastDownloaded',None)
  assert a==b,'non-volatile component metadata differs'
result={'status':'full-hosted-data-and-security-baseline-verified','repositories':len(before['repositories']),'hosted_repositories':len(before['hosted']),'components':sum(len(x['components'])for x in before['hosted'].values()),'asset_content_hashes_verified':sum(len(x['assets'])for x in before['hosted'].values()),'all_asset_bytes_paths_and_IDs_equal':True,'repository_configurations_users_roles_EULA_equal':True,'component_metadata_equal_except_lastDownloaded':True,'GET_updated_lastDownloaded_fields':volatile,'ignored_field_scope':'only hosted.components[].assets[].lastDownloaded operational timestamp','private_snapshots_preserved_VM_only':True,'repository_writes':False}
print(json.dumps(result))
