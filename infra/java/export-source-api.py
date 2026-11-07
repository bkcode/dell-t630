#!/usr/bin/env python3
"""Copy built API bytes and Gradle-generated metadata into the private file repo (no publish)."""
import argparse, hashlib, json, shutil, sys, xml.etree.ElementTree as ET
from pathlib import Path
BASE=Path(__file__).resolve().parents[2];WORK=BASE/'private/java-build';REPO=WORK/'plugin-file-repo'
NS={'m':'http://maven.apache.org/POM/4.0.0'}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--service',required=True,choices=['finger-service-system','finger-service-coms','finger-common-lib-sms-contract','finger-service-msgs-api-contract','finger-service-fds-api-contract','finger-service-auds-api-contract','finger-service-exs-api-contract']);a=p.parse_args()
 artifact={'finger-service-system':'system-api','finger-service-coms':'coms-api','finger-common-lib-sms-contract':'common-sms','finger-service-msgs-api-contract':'msgs-api','finger-service-fds-api-contract':'fds-api','finger-service-auds-api-contract':'auds-api','finger-service-exs-api-contract':'exs-api'}[a.service]
 project=WORK/'repos'/a.service/artifact;pub=project/'build/publications/mavenJava';pom=pub/'pom-default.xml';module=pub/'module.json'
 parsed=ET.fromstring(pom.read_text());metadata=json.loads(module.read_text())
 assert parsed.findtext('m:groupId',namespaces=NS)=='com.sargia.finger'
 assert parsed.findtext('m:artifactId',namespaces=NS)==artifact
 assert parsed.findtext('m:version',namespaces=NS)=='1.0.0'
 assert metadata['component']['group']=='com.sargia.finger' and metadata['component']['module']==artifact and metadata['component']['version']=='1.0.0'
 files=[(pom,artifact+'-1.0.0.pom'),(module,artifact+'-1.0.0.module')]
 seen=set()
 for variant in metadata['variants']:
  for entry in variant.get('files',[]):
   if entry['name'] in seen:continue
   seen.add(entry['name']);source=project/'build/libs'/entry['name']
   assert source.is_file(), 'Declared API artifact not built'
   assert source.stat().st_size==entry['size'] and sha(source)==entry['sha256']
   assert hashlib.sha512(source.read_bytes()).hexdigest()==entry['sha512']
   files.append((source,entry['name']))
 selected=[]
 for source,name in files:
  target=REPO/'com/sargia/finger'/artifact/'1.0.0'/name;target.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
  if target.exists():assert sha(target)==sha(source),'Existing coordinate bytes differ; stop for explicit selection'
  else:shutil.copyfile(source,target);target.chmod(0o400)
  selected.append({'name':name,'bytes':source.stat().st_size,'sha256':sha(source),'basis':'built from isolated current-source API; Gradle-generated module size/SHA256/SHA512 checked'})
 result={'status':'source-api-exported-private-file-copy','service':a.service,'coordinate':'com.sargia.finger:'+artifact+':1.0.0','selected':selected,'publish_task_executed':False,'external_network_used':False,'original_source_modified':False}
 target=WORK/'artifacts'/(artifact+'-source-export.json');target.parent.mkdir(parents=True,exist_ok=True,mode=0o700);target.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');target.chmod(0o600)
 print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':
 try:main()
 except Exception as e:
  print(json.dumps({'status':'failed','error_category':type(e).__name__,'message':str(e)}));sys.exit(1)
