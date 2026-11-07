#!/usr/bin/env python3
"""Prepare current common-sms library only; never starts or sends SMS."""
import hashlib,json,os,re,shutil,sys
from pathlib import Path
sys.dont_write_bytecode=True
from importlib.util import module_from_spec,spec_from_file_location
BASE=Path(__file__).resolve().parents[2];WORK=BASE/'private/java-build'
spec=spec_from_file_location('offline_builder',Path(__file__).with_name('offline-build.py'));builder=module_from_spec(spec);spec.loader.exec_module(builder)
source=Path('/Users/yangzhaohui/work/www/finger/finger-master/projects/finger-common-lib');target=WORK/'repos/finger-common-lib-sms-contract'
if target.exists():raise SystemExit('Existing SMS contract snapshot; refusing overwrite')
before=builder.git_state(source);records=[];target.mkdir(mode=0o700)
for current,dirs,files in os.walk(source):
 current=Path(current);rd=current.relative_to(source)
 dirs[:]=[n for n in dirs if not builder.excluded(current/n,rd/n) and (rd.parts or n in {'gradle','common-sms'})]
 for name in files:
  f=current/name;r=f.relative_to(source)
  if len(r.parts)==1 and name not in builder.ROOT_FILES:continue
  if builder.excluded(f,r):continue
  if not(r.parts[0] in {'gradle','common-sms'} or name in builder.ROOT_FILES):continue
  out=target/r;out.parent.mkdir(parents=True,exist_ok=True,mode=0o700);shutil.copyfile(f,out);out.chmod(0o700 if name=='gradlew' else 0o600)
  records.append({'path':str(r),'sha256':hashlib.sha256(out.read_bytes()).hexdigest()})
assert builder.git_state(source)==before
settings=target/'settings.gradle.kts';text=settings.read_text()
text=re.sub(r'^include\(":(?!common-sms")[^"]+"\)\s*$', '', text, flags=re.M)
assert text.count('include(":common-sms")')==1
uri=(WORK/'plugin-file-repo').as_uri()
for block,name,content in [('pluginManagement {','dellOfflineValidatedPlugin','includeGroup("com.sargia.finger.gradle-conventions"); includeModule("com.sargia.finger", "gradle-conventions")'),('dependencyResolutionManagement {','dellOfflineInternalArtifacts','includeGroup("com.sargia.finger")')]:
 i=text.index('repositories {',text.index(block))+len('repositories {')
 text=text[:i]+'\n        maven { name = "'+name+'"; url = uri('+json.dumps(uri)+'); content { '+content+' } }\n'+text[i:]
settings.write_text(text)
result={'status':'prepared-not-compiled','source':str(source),'git':before,'files':records,'isolated_changes':['only include common-sms module','validated file repositories first'],'reason':'Gradle cache has binary but no metadata; Maven-local source differs from current source, so rebuild current source instead of choosing by mtime','source_repositories_modified':False,'runtime_profiles_copied':False,'sms_sent':False,'publish_executed':False}
p=WORK/'sms-source-contract-manifest.json';p.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');p.chmod(0o600)
print(json.dumps({'status':'prepared','source_files':len(records),'source_head':before['head']}))
