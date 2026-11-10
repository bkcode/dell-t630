#!/usr/bin/env python3
"""Read-only source/config compatibility audit; no Gradle, Git fetch or branch changes."""
import json,os,re,socket,subprocess
from pathlib import Path
assert os.geteuid()==0 and socket.gethostname()=='publish-service'
repos=Path('/srv/dell-build/deploy-public/repos');result={}
for p in repos.iterdir():
 if not(p/'.git').is_dir():continue
 versions=set();private_plugin=False
 for f in [*p.glob('build.gradle.kts'),*p.glob('*/build.gradle.kts')]:
  s=f.read_text();versions.update(re.findall(r'(?m)^version\s*=\s*"([^"\r\n]+)"',s));private_plugin|='libs.plugins.finger.gradle.conventions'in s
 result[p.name]={'literal_versions':sorted(versions),'private_gradle_conventions_alias_used':private_plugin,'source_branch':subprocess.check_output(['runuser','-u','ub','--','git','-C',str(p),'branch','--show-current']).decode().strip(),'clean':not subprocess.check_output(['runuser','-u','ub','--','git','-C',str(p),'status','--porcelain']).decode().strip()}
print(json.dumps({'managed_source_readonly':result,'Gradle_or_build_executed':False,'branch_created_or_changed':False,'current_release_versions_cannot_be_published_to_snapshot_policy_without_future_version_preparation':True,'private_gradle_plugin_not_imported_into_new_empty_group':True}))
