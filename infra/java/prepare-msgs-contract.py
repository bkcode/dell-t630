#!/usr/bin/env python3
"""Compile-current-source substitution for ambiguous MSGS API, private copies only."""
import hashlib,json,os,shutil,sys
from pathlib import Path
sys.dont_write_bytecode=True
from importlib.util import module_from_spec,spec_from_file_location
BASE=Path(__file__).resolve().parents[2];WORK=BASE/'private/java-build'
spec=spec_from_file_location('offline_builder',Path(__file__).with_name('offline-build.py'));builder=module_from_spec(spec);spec.loader.exec_module(builder)
source=Path('/Users/yangzhaohui/work/www/finger/finger-master/projects/finger-service-msgs');target=WORK/'repos/finger-service-msgs-api-contract'
if target.exists():raise SystemExit('Contract snapshot exists; refuse overwrite')
before=builder.git_state(source);records=[];target.mkdir(mode=0o700)
for current,dirs,files in os.walk(source):
 current=Path(current);rd=current.relative_to(source)
 dirs[:]=[n for n in dirs if not builder.excluded(current/n,rd/n) and (rd.parts or n in {'gradle','msgs-api'})]
 for name in files:
  f=current/name;r=f.relative_to(source)
  if len(r.parts)==1 and name not in builder.ROOT_FILES:continue
  if builder.excluded(f,r):continue
  if not (r.parts[0] in {'gradle','msgs-api'} or name in builder.ROOT_FILES):continue
  out=target/r;out.parent.mkdir(parents=True,exist_ok=True,mode=0o700);shutil.copyfile(f,out);out.chmod(0o700 if name=='gradlew' else 0o600)
  records.append({'path':str(r),'sha256':hashlib.sha256(out.read_bytes()).hexdigest()})
assert builder.git_state(source)==before
settings=target/'settings.gradle.kts';text=settings.read_text();text=text.replace('include(":msgs-boot")','')
assert 'include(":msgs-api")' in text
uri=(WORK/'plugin-file-repo').as_uri()
for block,repo_name,content in [('pluginManagement {','dellOfflineValidatedPlugin','includeGroup("com.sargia.finger.gradle-conventions"); includeModule("com.sargia.finger", "gradle-conventions")'),('dependencyResolutionManagement {','dellOfflineInternalArtifacts','includeGroup("com.sargia.finger")')]:
 pos=text.index('repositories {',text.index(block))+len('repositories {')
 text=text[:pos]+'\n        maven { name = "'+repo_name+'"; url = uri('+json.dumps(uri)+'); content { '+content+' } }\n'+text[pos:]
settings.write_text(text)
system=WORK/'repos/finger-service-system/settings.gradle.kts';text=system.read_text()
text+='''\n// Current source API contract; no API publication or MSGS runtime involved.
includeBuild("../finger-service-msgs-api-contract") {
    dependencySubstitution {
        substitute(module("com.sargia.finger:msgs-api")).using(project(":msgs-api"))
    }
}
'''
system.write_text(text)
result={'status':'prepared-not-compiled','source':str(source),'git':before,'source_git_state_unchanged':True,'files':records,'isolated_changes':['omit msgs-boot project from API-only snapshot settings','validated file repositories first','System composite dependencySubstitution for msgs-api'],'runtime_profiles_copied':False,'source_repositories_modified':False,'publish_executed':False}
p=WORK/'msgs-source-contract-manifest.json';p.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');p.chmod(0o600)
print(json.dumps({'status':'prepared','source_files':len(records),'source_head':before['head'],'source_repositories_modified':False,'publish_executed':False}))
