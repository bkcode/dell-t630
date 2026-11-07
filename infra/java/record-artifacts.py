#!/usr/bin/env python3
"""Record isolated build inputs and boot JAR/internal dependency digests; never executes apps."""
import datetime as dt, hashlib, json, os, sys, zipfile
from pathlib import Path
from zoneinfo import ZoneInfo
from importlib.util import module_from_spec,spec_from_file_location
sys.dont_write_bytecode=True
BASE=Path(__file__).resolve().parents[2];WORK=BASE/'private/java-build'
spec=spec_from_file_location('builder',Path(__file__).with_name('offline-build.py'));builder=module_from_spec(spec);spec.loader.exec_module(builder)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def source_tree(repo):
 records=[]
 for f in repo.rglob('*'):
  if not f.is_file() or any(p in {'build','.gradle','.git'} for p in f.relative_to(repo).parts):continue
  records.append({'path':str(f.relative_to(repo)),'sha256':sha(f)})
 records.sort(key=lambda x:x['path'])
 return hashlib.sha256(json.dumps(records,sort_keys=True,separators=(',',':')).encode()).hexdigest(),records

def main():
 source_manifest=json.loads((WORK/'snapshot.json').read_text());source_states={x['service']:x for x in source_manifest['source_snapshots']}
 known=set(p.name for p in (WORK/'gradle-home/caches/modules-2/files-2.1/com.sargia.finger').iterdir())
 all_variants={};reports=[]
 contracts=[]
 for manifest in sorted(WORK.glob('*source-contract-manifest.json')):
  state=json.loads(manifest.read_text());source=Path(state['source'])
  contracts.append({'manifest':str(manifest),'source':str(source),'git':state['git'],'git_state_unchanged':builder.git_state(source)==state['git'],'snapshot_input_records_sha256':hashlib.sha256(json.dumps(state.get('files',[]),sort_keys=True,separators=(',',':')).encode()).hexdigest()})
 for service in builder.SERVICES:
  repo=WORK/'repos'/service;artifacts=[]
  for path in repo.glob('**/build/libs/*.jar'):
   with zipfile.ZipFile(path) as z:
    mf=z.read('META-INF/MANIFEST.MF').decode() if 'META-INF/MANIFEST.MF' in z.namelist() else ''
    if 'Start-Class:' not in mf:continue
    embedded=[]
    for name in z.namelist():
     filename=name.split('/')[-1]
     if name.startswith('BOOT-INF/lib/') and any(filename.startswith(n+'-') for n in known):
      digest=hashlib.sha256(z.read(name)).hexdigest();embedded.append({'name':filename,'sha256':digest});all_variants.setdefault(filename,{}).setdefault(digest,[]).append(service)
    artifacts.append({'path':str(path),'bytes':path.stat().st_size,'sha256':sha(path),'embedded_internal_dependencies':embedded})
  assert len(artifacts)==1,service+' must have exactly one boot artifact'
  input_hash,records=source_tree(repo)
  logs=[]
  for p in (WORK/'logs').glob(service+'-*.json'):
   value=json.loads(p.read_text())
   if value.get('action') in ['compile','bootjar'] and value.get('status')=='passed':logs.append(value)
  assert any(v['action']=='compile' for v in logs) and any(v['action']=='bootjar' for v in logs)
  report={'service':service,'build_status':'compile-and-bootjar-passed-offline','tests_status':'blocked-missing-isolated-test-config','runtime_status':'not-started','target_amd64_runtime_verified':False,'original_git':source_states[service]['git'],'source_git_state_unchanged':builder.git_state(Path(source_states[service]['source']))==source_states[service]['git'],'source_snapshot_content_sha256':input_hash,'source_snapshot_files':records,'artifact':artifacts[0],'successful_build_logs':[v['private_log'] for v in logs],'runtime_profiles_copied':False,'publish_executed':False}
  if service=='finger-auth':
   import xml.etree.ElementTree as ET
   tests=repo/'build/test-results/test/TEST-com.sargia.finger.gateway.auth.config.AuthBootstrapPropertiesTest.xml'
   assert tests.exists()
   suite=ET.parse(tests).getroot()
   report['deployment_config_unit_tests']={'tests':int(suite.attrib['tests']),'failures':int(suite.attrib['failures']),'errors':int(suite.attrib['errors']),'skipped':int(suite.attrib['skipped']),'status':'passed','evidence':str(tests),'spring_context_started':False}
   assert report['deployment_config_unit_tests']['tests']==5 and not any(report['deployment_config_unit_tests'][k] for k in ['failures','errors','skipped'])
   report['deployment_patch_manifest']=str(WORK/'auth-deployment-patch-manifest.json')
  private=WORK/'artifacts'/(service+'-build-manifest.json');private.parent.mkdir(mode=0o700,exist_ok=True);private.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');private.chmod(0o600)
  reports.append({k:v for k,v in report.items() if k!='source_snapshot_files'})
 mismatch={name:variants for name,variants in all_variants.items() if len(variants)>1}
 result={'schema_version':1,'recorded_at':dt.datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),'status':'five-boot-artifacts-built-not-runtime-accepted','services':reports,'contract_source_snapshots':contracts,'same_internal_filename_different_sha256':mismatch,'same_internal_dependencies_consistent':not mismatch,'original_sources_unchanged':all(r['source_git_state_unchanged'] for r in reports) and all(r['git_state_unchanged'] for r in contracts),'tests_status':'blocked-missing-isolated-test-config','public_downloads':'Only approved official Maven Central Jackson2.19.0, unauthenticated, SHA1 and SHA256 recorded','gradle_network':'external denied, loopback only','publish_executed':False}
 (BASE/'infra/java/build-status.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({'status':result['status'],'services':len(reports),'internal_filename_hash_mismatches':list(mismatch),'original_sources_unchanged':result['original_sources_unchanged'],'tests_status':result['tests_status']}))
 if mismatch:sys.exit(1)
if __name__=='__main__':main()
