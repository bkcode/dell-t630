#!/usr/bin/env python3
"""Validate offline per-machine repository contracts; no network, keys or server access."""
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]
def validate():
 errors=[]
 def need(value,message):
  if not value:errors.append(message)
 def read(p):
  try:return json.loads(p.read_text())
  except (OSError,ValueError):errors.append('missing/invalidJSON:'+str(p.relative_to(ROOT)));return{}
 c=read(ROOT/'machines/git-repositories.json');index=read(ROOT/'machines/index.json');repositories=c.get('repositories',{});rows=c.get('machines',[]);expected=index.get('machines',[]);mapping={r.get('path'):r for r in rows};need(len(rows)==len(expected)==len(mapping),'machine count and uniqueness differ')
 for e in expected:
  row=mapping.get(e['path'],{})
  for key in ['vmid','name','kind','ip']:need(row.get(key)==e.get(key),'identity differs:'+e['path']+':'+key)
  ids=[row.get('configuration_repository'),*row.get('application_repository_ids',[]),*row.get('dependency_repository_ids',[]),*row.get('upstream_repository_ids',[])]
  for ref in ids:need(ref in repositories,'undefined repository:'+str(ref))
  for path in row.get('configuration_paths',[]):
   p=Path(path);need(not p.is_absolute()and '..'not in p.parts and(ROOT/p).exists(),'invalid config path:'+path)
  folder=ROOT/e['path'];doc=folder/'GIT-REPOSITORIES.md';need(doc.is_file(),'machine Git document absent:'+e['path']);cfg=read(folder/'config.json');p=cfg.get('git_repository_mapping',{});need(p.get('catalog')=='machines/git-repositories.json'and p.get('machine_path')==e['path'],'machine mapping pointer differs:'+e['path'])
  need(p.get('catalog_machine_pointer')=='/machines/'+str(expected.index(e))and p.get('document_path')==e['path']+'/GIT-REPOSITORIES.md','exact catalog/document pointer differs:'+e['path'])
  need(p.get('git_usage_mode')==row.get('git_usage_mode')and p.get('direct_runtime_business_git_pull')is row.get('direct_runtime_business_git_pull')and p.get('source_role')=='docs-only','machine Git usage semantics differ:'+e['path'])
  need(p.get('configuration_repository_id')==row.get('configuration_repository'),'machine configuration repository differs:'+e['path'])
  for key in ['application_repository_ids','dependency_repository_ids','upstream_repository_ids']:need(p.get(key)==row.get(key),'machine repository refs differ:'+e['path']+':'+key)
  need('GIT-REPOSITORIES.md'in(folder/'README.md').read_text(),'machine README missing Git link:'+e['path'])
  if e['kind']=='template':need(not row.get('application_repository_ids')and not row.get('credential_references')and row.get('direct_runtime_business_git_pull')is False,'template contains business source/key/pull contract')
 for v in [230,240]:
  row=next((x for x in rows if x.get('vmid')==v),{});need(row.get('git_usage_mode')=='artifact-consumer-runtime-only'and row.get('direct_runtime_business_git_pull')is False and not row.get('credential_references'),'runtime must consume artifacts without repository keys');need('puyu-common-lib'in row.get('dependency_repository_ids',[])and'puyu-common-lib'not in row.get('application_repository_ids',[]),'sharedlibrary misclassified as runtime')
 pub=next((x for x in rows if x.get('vmid')==220),{});need(set(pub.get('application_repository_ids',[]))=={'deploy','puyu-auth','puyu-bff-web','puyu-common-lib','puyu-gateway','puyu-service-core'},'publisher backend source scope differs')
 need(repositories.get('jellyfin',{}).get('fork_parent_observed')=='jellyfin/jellyfin','Jellyfin server fork identity differs')
 for row in rows:
  for key in row.get('credential_references',[]):
   need(key.get('repository_id')in repositories,'credential references undefined repository');need(Path(key.get('key_basename','')).name==key.get('key_basename')and not str(key.get('key_basename','')).endswith('.pub'),'credential basename contract invalid');need('public_line'not in key and'private_key'not in key,'key body/path descriptor mixed into mapping')
 need(c.get('constraints',{}).get('existing_Java_business_remains_disabled')is True,'Java disabled scope missing')
 p=read(ROOT/'evidence/git-repositories-20261110/penpot-deploy-key-verification.json');need(p.get('repository_scoped_SSH_identity_verified')and p.get('temporary_full_worktree_checkout_verified')and p.get('temporary_checkout_removed')and p.get('server_code_build_or_runtime_modified')is False,'Penpot read-only clone evidence incomplete')
 return{'status':'failed'if errors else'passed','scope':'offline repository ownership/pointers and existing evidence only','stats':{'machine_documents':len(rows),'repository_definitions':len(repositories),'user_application_or_build_source_count':sum(r.get('repository','').startswith('bkcode/')and r.get('id')!='infra'for r in repositories.values())},'errors':errors,'live_or_secret_access':False}
if __name__=='__main__':
 result=validate();print(json.dumps(result,ensure_ascii=False,indent=2));sys.exit(result['status']!='passed')
