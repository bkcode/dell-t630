#!/usr/bin/env python3
"""Package already-built test JARs and private external configuration; never deploys or starts."""
import datetime as dt,hashlib,json,os,shutil,sys
from pathlib import Path
from zoneinfo import ZoneInfo
BASE=Path(__file__).resolve().parents[3];OUT=BASE/'private/java';META=OUT/'test-chain/metadata.json'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 meta=json.loads(META.read_text());assert meta['status'] in ['prepared-not-executed','target-test-initialized-config-versioned'] and meta['issuer']=='http://192.168.21.22:19999'
 build=json.loads((BASE/'infra/java/build-status.json').read_text());assert len(build['services'])==5 and build['same_internal_dependencies_consistent']
 patch=BASE/'private/java-build/auth-deployment-patch-manifest.json';assert patch.exists()
 release_id=dt.datetime.now(ZoneInfo('Asia/Shanghai')).strftime('%Y%m%dT%H%M%S')
 dest=OUT/'releases'/release_id;assert not dest.exists();dest.mkdir(parents=True,mode=0o700)
 records=[]
 heaps={'finger-gateway-mobile':512,'finger-auth':768,'finger-service-system':512,'finger-service-coms':768,'finger-bff-system':768}
 for item in meta['services']:
  name=item['name'];artifact=next(r['artifact'] for r in build['services'] if r['service']==name);jar=Path(artifact['path']);assert sha(jar)==artifact['sha256'],'Artifact manifest stale'
  cfg=Path(item['runtime_config']);target=dest/name;target.mkdir(mode=0o700)
  shutil.copyfile(jar,target/'app.jar');os.chmod(target/'app.jar',0o600)
  shutil.copyfile(cfg,target/'application.yaml');os.chmod(target/'application.yaml',0o600)
  records.append({'name':name,'port':item['port'],'jar_sha256':sha(target/'app.jar'),'config_sha256':sha(target/'application.yaml'),'xms_mib':128,'xmx_mib':heaps[name],'metaspace_mib':256,'memory_max_mib':1024 if heaps[name]==512 else 1536})
 manifest={'schema_version':1,'release_id':release_id,'target_hostname':'java-test-01','target_ip':'10.63.20.20','data_ip':'10.63.20.10','issuer':meta['issuer'],'profile':'dell-test','services':records,'deployment_status':'packaged-not-deployed','sql_executed':False,'context_tests_status':'blocked-missing-isolated-test-config','auth_deployment_patch_manifest_sha256':sha(patch)}
 p=dest/'manifest.json';p.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n');p.chmod(0o600)
 print(json.dumps({'status':'packaged-not-deployed','release_id':release_id,'services':len(records),'path':str(dest),'new_secrets_embedded_in_jars':False}))
if __name__=='__main__':
 try:main()
 except Exception as e:print(json.dumps({'status':'failed','error_category':type(e).__name__,'message':str(e)}));sys.exit(1)
