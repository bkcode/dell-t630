#!/usr/bin/env python3
"""Add only unambiguous module-verified internal artifacts to the private file repo."""
import argparse, hashlib, json, shutil, sys, xml.etree.ElementTree as ET
from pathlib import Path
BASE=Path(__file__).resolve().parents[2];WORK=BASE/'private/java-build'
CACHE=WORK/'gradle-home/caches/modules-2/files-2.1/com.sargia.finger';REPO=WORK/'plugin-file-repo'
SERVICES=['finger-gateway-mobile','finger-auth','finger-service-system','finger-service-coms','finger-bff-system']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def unique(files):
 by={sha(p):p for p in files}
 if len(by)!=1:raise RuntimeError('Missing or ambiguous artifact; explicit semantic selection required')
 return next(iter(by.values()))
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('artifacts',nargs='+');args=p.parse_args()
 selected=[]
 for name in args.artifacts:
  if not name.replace('-','').isalnum():raise ValueError('invalid artifact name')
  b=CACHE/name/'1.0.0';module=unique(list(b.rglob('*.module')));pom=unique(list(b.rglob('*.pom')))
  ET.fromstring(pom.read_text());metadata=json.loads(module.read_text());files=[module,pom]
  for variant in metadata['variants']:
   if variant['name'] not in ['apiElements','runtimeElements']:continue
   for ref in variant.get('files',[]):
    binary=unique([f for f in b.rglob(ref['name']) if f.is_file() and sha(f)==ref['sha256']])
    assert binary.stat().st_size==ref['size']
    assert hashlib.sha512(binary.read_bytes()).hexdigest()==ref['sha512']
    files.append(binary)
  files=list({str(f):f for f in files}.values())
  for f in files:
   target=REPO/'com/sargia/finger'/name/'1.0.0'/f.name
   target.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
   if target.exists():
    assert sha(target)==sha(f),'Existing selected artifact differs'
   else:shutil.copyfile(f,target);target.chmod(0o400)
   selected.append({'coordinate':'com.sargia.finger:'+name+':1.0.0','file':f.name,'sha256':sha(f),'basis':'unique valid module/POM; referenced binary size/SHA256/SHA512 match'})
 for name in SERVICES:
  settings=WORK/'repos'/name/'settings.gradle.kts';text=settings.read_text()
  marker='name = "dellOfflineInternalArtifacts"'
  if marker in text:continue
  first=text.index('repositories {',text.index('dependencyResolutionManagement {'));insert=first+len('repositories {')
  addition='\n        maven {\n            name = "dellOfflineInternalArtifacts"\n            url = uri('+json.dumps(REPO.as_uri())+')\n            content { includeGroup("com.sargia.finger") }\n        }\n'
  settings.write_text(text[:insert]+addition+text[insert:])
 output={'status':'prepared-not-compiled','selected':selected,'source_repositories_modified':False,'network_used':False,'publish_executed':False}
 manifest=WORK/('file-repo-add-'+ '-'.join(args.artifacts)+'.json')
 if manifest.exists():raise RuntimeError('Selection manifest exists; keep previous evidence')
 manifest.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n');manifest.chmod(0o600)
 print(json.dumps(output,ensure_ascii=False))
if __name__=='__main__':
 try:main()
 except Exception as e:
  print(json.dumps({'status':'failed','error_category':type(e).__name__,'message':str(e)}));sys.exit(1)
