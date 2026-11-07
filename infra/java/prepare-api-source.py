#!/usr/bin/env python3
"""Snapshot approved API-only modules with ambiguous/incomplete cached contracts."""
import argparse,hashlib,json,os,re,shutil,sys
from pathlib import Path
from importlib.util import module_from_spec,spec_from_file_location
sys.dont_write_bytecode=True
BASE=Path(__file__).resolve().parents[2];WORK=BASE/'private/java-build'
MODULES={'finger-service-fds':'fds-api','finger-service-auds':'auds-api','finger-service-exs':'exs-api'}
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--service',choices=MODULES,required=True);a=p.parse_args()
spec=spec_from_file_location('offline_builder',Path(__file__).with_name('offline-build.py'));builder=module_from_spec(spec);spec.loader.exec_module(builder)
source=Path('/Users/yangzhaohui/work/www/finger/finger-master/projects')/a.service;module=MODULES[a.service];target=WORK/'repos'/(a.service+'-api-contract')
if target.exists():raise SystemExit('Contract snapshot exists; refusing overwrite')
before=builder.git_state(source);records=[];target.mkdir(mode=0o700)
for current,dirs,files in os.walk(source):
 current=Path(current);rd=current.relative_to(source)
 dirs[:]=[n for n in dirs if not builder.excluded(current/n,rd/n) and (rd.parts or n in {'gradle',module})]
 for name in files:
  f=current/name;r=f.relative_to(source)
  if len(r.parts)==1 and name not in builder.ROOT_FILES:continue
  if builder.excluded(f,r):continue
  if not(r.parts[0] in {'gradle',module} or name in builder.ROOT_FILES):continue
  out=target/r;out.parent.mkdir(parents=True,exist_ok=True,mode=0o700);shutil.copyfile(f,out);out.chmod(0o700 if name=='gradlew' else 0o600)
  records.append({'path':str(r),'sha256':hashlib.sha256(out.read_bytes()).hexdigest()})
assert builder.git_state(source)==before
settings=target/'settings.gradle.kts';text=settings.read_text()
text=re.sub(r'^include\(":(?!'+re.escape(module)+r'")[^"]+"\)\s*$', '', text, flags=re.M)
assert text.count('include(":'+module+'")')==1
for block,repotype,contents in [('pluginManagement {','plugin','includeGroup("com.sargia.finger.gradle-conventions"); includeModule("com.sargia.finger", "gradle-conventions")'),('dependencyResolutionManagement {','internal','includeGroup("com.sargia.finger")')]:
 pos=text.index('repositories {',text.index(block))+len('repositories {')
 additions='\n        maven { name = "dellOfflineValidated'+repotype+'"; url = uri('+json.dumps((WORK/'plugin-file-repo').as_uri())+'); content { '+contents+' } }\n'
 additions+='        maven { name = "dellOfflineApprovedPublic"; url = uri('+json.dumps((WORK/'public-file-repo').as_uri())+'); content { includeGroupByRegex("com[.]fasterxml[.]jackson.*") } }\n'
 text=text[:pos]+additions+text[pos:]
settings.write_text(text)
result={'status':'prepared-not-compiled','service':a.service,'module':module,'source':str(source),'git':before,'files':records,'isolated_changes':['only include approved API project','validated private repositories first'],'source_repositories_modified':False,'runtime_profiles_copied':False,'business_service_started':False,'publish_executed':False}
out=WORK/(module+'-source-contract-manifest.json');out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');out.chmod(0o600)
print(json.dumps({'status':'prepared','service':a.service,'source_files':len(records),'source_head':before['head']}))
