#!/usr/bin/env python3
"""Build a private file Maven repository from validated, existing plugin cache bytes."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
import xml.etree.ElementTree as ET
import zipfile

BASE=Path(__file__).resolve().parents[2]
WORK=BASE/'private/java-build'
CACHE=WORK/'gradle-home/caches/modules-2/files-2.1'
REPO=WORK/'plugin-file-repo'
SERVICES=['finger-gateway-mobile','finger-auth','finger-service-system','finger-service-coms','finger-bff-system']
NS={'m':'http://maven.apache.org/POM/4.0.0'}
marker_group='com.sargia.finger.gradle-conventions'
marker_name='com.sargia.finger.gradle-conventions.gradle.plugin'
version='1.0.0'

def sha(path,kind='sha256'):
 return hashlib.new(kind,path.read_bytes()).hexdigest()

def main():
 if REPO.exists():raise RuntimeError('File repository already exists; refusing overwrite')
 valid=[];rejected=[]
 for f in (CACHE/marker_group/marker_name/version).rglob('*.pom'):
  try:
   tree=ET.fromstring(f.read_text())
   assert tree.tag=='{http://maven.apache.org/POM/4.0.0}project'
   assert tree.findtext('m:groupId',namespaces=NS)==marker_group
   assert tree.findtext('m:artifactId',namespaces=NS)==marker_name
   deps=tree.findall('m:dependencies/m:dependency',NS)
   assert len(deps)==1
   assert deps[0].findtext('m:groupId',namespaces=NS)=='com.sargia.finger'
   assert deps[0].findtext('m:artifactId',namespaces=NS)=='gradle-conventions'
   assert deps[0].findtext('m:version',namespaces=NS)==version
   valid.append(f)
  except (ET.ParseError,AssertionError,UnicodeError):
   rejected.append({'filename':f.name,'sha256':sha(f),'bytes':f.stat().st_size,
                    'reason':'not matching valid Maven marker POM','html_detected':b'<html' in f.read_bytes()[:256].lower() or b'<!doctype html' in f.read_bytes()[:256].lower()})
 assert len({sha(f) for f in valid})==1, 'Valid marker POM bytes are ambiguous or missing'
 implementation=CACHE/'com.sargia.finger/gradle-conventions'/version
 jars=list(implementation.rglob('gradle-conventions-1.0.0.jar'))
 poms=list(implementation.rglob('gradle-conventions-1.0.0.pom'))
 modules=list(implementation.rglob('gradle-conventions-1.0.0.module'))
 assert len(jars)==len(poms)==len(modules)==1, 'Implementation artifacts must be unique'
 jar,pom,module=jars[0],poms[0],modules[0]
 ET.fromstring(pom.read_text())
 metadata=json.loads(module.read_text())
 for variant in metadata['variants']:
  for f in variant.get('files',[]):
   assert f['name']==jar.name and f['size']==jar.stat().st_size
   assert f['sha256']==sha(jar) and f['sha512']==sha(jar,'sha512')
 with zipfile.ZipFile(jar) as z:
  assert 'META-INF/gradle-plugins/com.sargia.finger.gradle-conventions.properties' in z.namelist()
 mappings=[(valid[0],marker_group,marker_name),*[(f,'com.sargia.finger','gradle-conventions') for f in [jar,pom,module]]]
 selected=[]
 for source,group,name in mappings:
  target=REPO/group.replace('.','/')/name/version/source.name
  target.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
  shutil.copyfile(source,target);target.chmod(0o400)
  selected.append({'group':group,'artifact':name,'version':version,'filename':source.name,'sha256':sha(source),'bytes':source.stat().st_size})
 modified=[]
 for name in SERVICES:
  settings=WORK/'repos'/name/'settings.gradle.kts'
  text=settings.read_text()
  first=text.index('repositories {',text.index('pluginManagement {'))
  insert=first+len('repositories {')
  uri=REPO.as_uri()
  addition='\n        maven {\n            name = "dellOfflineValidatedPlugin"\n            url = uri('+json.dumps(uri)+')\n            content {\n                includeGroup("com.sargia.finger.gradle-conventions")\n                includeModule("com.sargia.finger", "gradle-conventions")\n            }\n        }\n'
  settings.write_text(text[:insert]+addition+text[insert:])
  modified.append({'service':name,'path':str(settings),'sha256':sha(settings),'scope':'isolated-copy-only'})
 output={'status':'prepared-not-resolved','repository':str(REPO),'selection_rule':'Exactly one valid matching marker POM; unique implementation checked against module SHA256/SHA512 and plugin descriptor','selected':selected,'rejected':rejected,'isolated_settings_modified':modified,'source_repositories_modified':False,'network_used':False,'publish_executed':False}
 path=WORK/'plugin-file-repo-manifest.json';path.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n');path.chmod(0o600)
 print(json.dumps(output,ensure_ascii=False))

if __name__=='__main__':
 try:main()
 except Exception as e:
  print(json.dumps({'status':'failed','error_category':type(e).__name__,'message':str(e)}));sys.exit(1)
