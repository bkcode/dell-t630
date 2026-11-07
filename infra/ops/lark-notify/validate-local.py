#!/usr/bin/env python3
"""Local loopback/mock tests and fixed digest native config-only tools. No live hook."""
import datetime,hashlib,importlib.util,json,os,subprocess,sys,tempfile,uuid
from pathlib import Path
sys.dont_write_bytecode=True;HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE));import configuration
IMAGE='prom/alertmanager@sha256:7619e9399e623c9f99a40cb199c2bceb972cbf725598a51dcbde69d51dcaaedf'
def main():
 report={'at':datetime.datetime.now().astimezone().isoformat(),'mode':'local-tests-and-config-only','real_webhook_read':False,'guest270_accessed':False,'external_messages_sent':False,'native_checks':[]};path=HERE/'validation.json'
 try:
  tests=subprocess.run([sys.executable,str(HERE/'test_bridge.py')],capture_output=True,text=True,timeout=120);report['tests']={'exit_code':tests.returncode,'output_summary':tests.stdout[-200:]+tests.stderr[-500:]}
  if tests.returncode:raise RuntimeError('local protocol/security test failure')
  context=subprocess.run(['docker','context','show'],capture_output=True,text=True,check=True,timeout=20).stdout.strip();metadata=json.loads(subprocess.run(['docker','context','inspect',context],capture_output=True,text=True,check=True,timeout=20).stdout)
  if not metadata[0]['Endpoints']['docker']['Host'].startswith('unix://'):raise RuntimeError('local Unix Docker only')
  base=['docker','--context',context];spec=importlib.util.spec_from_file_location('native_check',HERE.parent/'validate-native.py');native=importlib.util.module_from_spec(spec);spec.loader.exec_module(native);before=native.source_snapshot(base);report['source_before']=before
  with tempfile.TemporaryDirectory(prefix='config-only-',dir=HERE) as tmp:
   folder=Path(tmp);folder.chmod(0o755);config=folder/'config';config.mkdir(mode=0o755);secret=folder/'synthetic-placeholder';secret.write_text('SYNTHETIC_PLACEHOLDER_NOT_A_REAL_CREDENTIAL\n');secret.chmod(0o644)
   for mode in ['acceptance','active']:
    (config/'alertmanager.yml').write_text(configuration.dump(mode));(config/'alertmanager.yml').chmod(0o644);name='dell-lark-config-'+uuid.uuid4().hex[:12]
    args=base+['run','--name',name,'--rm','--pull=never','--platform=linux/amd64','--network=none','--read-only','--user=65534:65534','--cap-drop=ALL','--security-opt=no-new-privileges:true','--cpus=0.5','--memory=256m','--memory-swap=256m','--pids-limit=128','--mount','type=bind,src='+str(config)+',dst=/etc/alertmanager,readonly','--mount','type=bind,src='+str(secret)+',dst=/run/secrets/lark-bridge-token,readonly','--entrypoint=/bin/amtool',IMAGE,'check-config','/etc/alertmanager/alertmanager.yml']
    try:r=subprocess.run(args,capture_output=True,text=True,timeout=90)
    except subprocess.TimeoutExpired:
     subprocess.run(base+['rm','--force',name],capture_output=True,timeout=20);raise RuntimeError('own config tool timeout; own container cleaned') from None
    report['native_checks'].append({'mode':mode,'image':IMAGE,'exit_code':r.returncode,'network':'none','secrets_mounted':False,'synthetic_placeholder_only':True,'output_summary':r.stdout[-500:]+r.stderr[-500:]})
    if r.returncode:raise RuntimeError('fixed native config-only check failed')
  report['source_after']=native.source_snapshot(base);report['source_unchanged']=report['source_before']==report['source_after']
  if not report['source_unchanged']:raise RuntimeError('source state drift; do not claim unchanged')
  report['code_sha256']={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in HERE.iterdir() if f.is_file() and f.suffix in ('.py','.service')};report['status']='local-tests-and-native-config-passed-no-live-delivery'
 except Exception as error:report['status']='failed';report['error_category']=type(error).__name__;raise
 finally:path.write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps({'status':report['status'],'tests_exit':report['tests']['exit_code'],'native_modes':len(report['native_checks']),'source_containers_unchanged':report['source_unchanged'],'real_webhook_read':False,'external_messages_sent':False}))
if __name__=='__main__':main()
