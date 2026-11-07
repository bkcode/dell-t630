#!/usr/bin/env python3
"""Local-only publisher code/security report. Does not inspect keys or call guests."""
import ast,datetime,hashlib,importlib.util,json,re,subprocess,sys
from pathlib import Path
from zoneinfo import ZoneInfo
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.dont_write_bytecode=True

def load(name,file):
 s=importlib.util.spec_from_file_location(name,HERE/file);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def main():
 for p in HERE.glob('*.py'):ast.parse(p.read_text())
 tests=subprocess.run([sys.executable,str(HERE/'test_security.py')],capture_output=True,text=True,timeout=60)
 if tests.returncode:raise RuntimeError('publisher offline security regression failed')
 count=int(re.search(r'Ran (\d+) tests',tests.stderr).group(1))
 protocol=load('validation_protocol','publisher_protocol.py');fixed=load('validation_fixed','fixed-deploy-test-chain.py')
 policy=json.loads((HERE/'fixed-deployer-source.json').read_text());policy['prepared_sha256']=hashlib.sha256((HERE/'fixed-deploy-test-chain.py').read_bytes()).hexdigest();policy['changes']=['persistent YAML root:root0600','systemd LoadCredential with file:%d/application.yaml','sensitive errors suppressed','no redirect health','stop/pointer/start recovery transaction','precheck previous fixed units'];(HERE/'fixed-deployer-source.json').write_text(json.dumps(policy,indent=2)+'\n')
 release=ROOT/'private/java/releases/20261106T121030';manifest,namespace=protocol.check_release(release.resolve(),'20261106T121030')
 # Explicit offline fault trace, no actual systemctl or filesystem pointers.
 events=[]
 from unittest.mock import patch
 import tempfile
 with tempfile.TemporaryDirectory(prefix='review-fault-',dir=ROOT/'private/publisher') as temp:
  parent=Path(temp).resolve();old=parent/'20261106T110000';new=parent/'20261106T120000';old.mkdir();new.mkdir()
  def pointer(path):
   events.append({'step':'pointer','release':path.name})
   if path==new:raise RuntimeError('injected pointer failure')
  with patch.object(fixed,'RELEASES',parent),patch.object(fixed,'check_staged_units'),patch.object(fixed,'check_manifest',return_value={'release_id':old.name}),patch.object(fixed,'stop_all',side_effect=lambda *a,**k:events.append({'step':'stop','strict':k.get('strict',True)})),patch.object(fixed,'pointer',side_effect=pointer),patch.object(fixed,'start_all',side_effect=lambda m:events.append({'step':'start','release':m['release_id']})):
   try:fixed.transition(new,{'release_id':new.name},old)
   except RuntimeError:pass
 assert events[-2:]==[{'step':'pointer','release':'20261106T110000'},{'step':'start','release':'20261106T110000'}]
 report={'at':datetime.datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),'status':'code-prepared-offline-validated-awaiting-manager-window','offline_tests':count,'negative_cases':[node.name for node in ast.walk(ast.parse((HERE/'test_security.py').read_text())) if isinstance(node,ast.FunctionDef) and node.name.startswith('test_')],'target_scope':'220 publisher to test240 only','persistent_yaml':'root:root0600','runtime_credentials':'systemd LoadCredential; argv contains only file:%d path','canonical_archive':'manual512-byte USTAR parsing; exact11 regular; reject member12 before payload; no PAX/GNU/compressed processing','status_locking':'no modifying flock; filtered atomic receipt+busy','fault_injection':{'pointer_failure_attempted_rollback_and_old_start':True,'events':events,'actual_guest_or_service_called':False},'actual121030_contract':'passed without outputting config values','gateway_nacos_import':'finger-gateway-mobile-lan-v2.yaml','snowflake':'DC1; Gateway1/Auth2/System3/COMS4/BFF5','target240_modified':False,'target240_services_restarted':False,'A_metadata_migration':'pending-approved-window','sshd_sudoers_native_syntax':'pending-approved240-window','real_B_activate_and_A_rollback':'pending','raw_public_or_private_keys_in_report':False,'files_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in HERE.glob('*.py')}}
 (HERE/'review-evidence.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='files_sha256'},ensure_ascii=False))

if __name__=='__main__':main()
