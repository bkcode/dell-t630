#!/usr/bin/python3 -I
"""Manager-only approved-window metadata migration; never callable through publisher sudo."""
import argparse,hashlib,importlib.util,json,os,shutil,socket,subprocess,sys,uuid
from pathlib import Path
ROOT=Path('/opt/finger');RELEASES=ROOT/'releases/test';CURRENT=ROOT/'current-test'
FIXED=Path('/usr/local/libexec/dell/deploy-test-chain.py');CODE=Path('/usr/local/libexec/dell-publisher');MARKER=Path('/root/dell-java-test-readiness.json');POLICY=Path('/etc/dell-publisher/test240-policy.json')

def load(name,path):
 if path.is_symlink() or path.stat().st_uid!=0 or path.stat().st_mode&0o022:raise RuntimeError('trusted root code required')
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def core_hashes(path,names):
 return {str(file.relative_to(path)):hashlib.sha256(file.read_bytes()).hexdigest() for file in [path/'manifest.json',*[path/name/file for name in names for file in ['app.jar','application.yaml']]]}

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--apply-reviewed240-window',action='store_true');p.add_argument('--expected-release',required=True);p.add_argument('--expected-manifest-sha256',required=True);args=p.parse_args()
 if not args.apply_reviewed240_window or os.geteuid()!=0 or socket.gethostname().split('.')[0]!='java-test-01' or Path('/etc/pve').exists():raise RuntimeError('manager approved test240 window required')
 if not CURRENT.is_symlink():raise RuntimeError('managed A current pointer required')
 path=CURRENT.resolve()
 if path.parent!=RELEASES or path.name!=args.expected_release or hashlib.sha256((path/'manifest.json').read_bytes()).hexdigest()!=args.expected_manifest_sha256:raise RuntimeError('baseline identity mismatch')
 fixed=load('fixed_credential_deployer',FIXED);protocol=load('fixed_protocol',CODE/'publisher_protocol.py')
 fixed.guard();fixed.gates(MARKER);manifest,namespace=protocol.check_release(path,args.expected_release)
 before=core_hashes(path,protocol.NAMES)
 metadata={}
 for name in protocol.NAMES:
  for file in ['application.yaml','unit.service']:
   target=path/name/file;stat=target.stat();metadata[str(target.relative_to(path))]={'uid':stat.st_uid,'gid':stat.st_gid,'mode':stat.st_mode&0o777}
  target=Path('/etc/systemd/system')/('dell-finger-'+name+'.service')
  if not target.is_symlink() or target.resolve()!=path/name/'unit.service':raise RuntimeError('baseline unit link is unmanaged')
 state=ROOT/'publisher-state';state.mkdir(mode=0o700,exist_ok=True);backup=state/('baseline-metadata-'+uuid.uuid4().hex);backup.mkdir(mode=0o700)
 for name in protocol.NAMES:
  shutil.copyfile(path/name/'unit.service',backup/(name+'.service'));(backup/(name+'.service')).chmod(0o600)
 (backup/'before.json').write_text(json.dumps({'release_id':path.name,'core_hashes':before,'metadata':metadata},indent=2));(backup/'before.json').chmod(0o600)
 try:
  fixed.stop_all()
  for row in manifest['services']:
   cfg=path/row['name']/'application.yaml';os.chown(cfg,0,0);cfg.chmod(0o600)
   unit=path/row['name']/'unit.service';unit.write_text(fixed.unit(row));os.chown(unit,0,0);unit.chmod(0o644)
  fixed.run(['systemctl','daemon-reload']);fixed.start_all(manifest)
  if core_hashes(path,protocol.NAMES)!=before:raise RuntimeError('JAR/YAML/manifest bytes changed during metadata migration')
 except BaseException:
  fixed.stop_all(strict=False)
  for name in protocol.NAMES:
   unit=path/name/'unit.service';shutil.copyfile(backup/(name+'.service'),unit)
  for relative,old in metadata.items():
   target=path/relative;os.chown(target,old['uid'],old['gid']);target.chmod(old['mode'])
  fixed.run(['systemctl','daemon-reload']);fixed.start_all(manifest);raise
 policy={'target_hostname':'java-test-01','target_ip':'10.63.20.20','namespace_id':namespace,'baseline_migrated':True,'baseline_release':path.name,'fixed_deployer_sha256':hashlib.sha256(FIXED.read_bytes()).hexdigest(),'persistent_secret_mode':'root:root0600','runtime_secret_transport':'systemd LoadCredential'}
 POLICY.parent.mkdir(mode=0o755,exist_ok=True);POLICY.write_text(json.dumps(policy,indent=2)+'\n');os.chown(POLICY,0,0);POLICY.chmod(0o600)
 result={'status':'baseline-metadata-migrated-health-verified','release_id':path.name,'core_bytes_unchanged':True,'namespace_id':namespace,'persistent_yaml_mode':'root:root0600','LoadCredential':True,'database_or_nacos_changed':False,'backup_metadata_directory':str(backup)}
 (state/'baseline-migration.json').write_text(json.dumps(result,indent=2)+'\n');(state/'baseline-migration.json').chmod(0o600);print(json.dumps(result))

if __name__=='__main__':
 try:main()
 except Exception:print(json.dumps({'status':'failed','message':'baseline metadata migration failed; no sensitive values emitted'}));sys.exit(1)
