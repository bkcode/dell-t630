#!/usr/bin/env python3
"""Manager-only explicitly approved test220->240 release exercise. No key/config stdout."""
import argparse,datetime,hashlib,importlib.util,json,os,shlex,shutil,subprocess,sys,time
from pathlib import Path
from zoneinfo import ZoneInfo
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent;E=ROOT/'evidence/implementation'
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
ctl=load('ctl',ROOT/'scripts/control.py');protocol=load('protocol',HERE/'publisher_protocol.py')
TARGETS={r['target']['vmid']:r['target'] for r in json.loads((E/'private-guest-access.json').read_text())['roles']}
REPORT=E/'publisher-release-exercise.json'
def save(v):REPORT.write_text(json.dumps(v,indent=2)+'\n')
def client(action,rid=None):
 cmd='sudo -n runuser --user publisher -- /usr/local/bin/dell-publish '+action
 if rid:cmd+=' --release-id '+shlex.quote(rid)
 if action=='stage':cmd+=' --bundle '+shlex.quote('/var/lib/dell-publisher/releases/'+rid)
 r=ctl.guest(220,cmd,timeout=1700,info=TARGETS[220])
 try:obj=json.loads(r['stdout'])
 except ValueError:obj={'ok':False,'message':'unstructured response withheld'}
 return {'exit_code':r['exit_code'],'response':obj}
def checked(r):
 if r['exit_code'] or r['response'].get('ok') is not True:raise RuntimeError('restricted client request failed; inspect structured evidence')
 return r
COPY=r'''import importlib.util,json,os,pwd,socket,sys,tempfile
from pathlib import Path
if os.geteuid()!=0 or socket.gethostname().split('.')[0]!='publish-service' or Path('/etc/pve').exists():raise SystemExit('220 required')
rid=RID
code=Path('/usr/local/libexec/dell-publisher/publisher_protocol.py');s=importlib.util.spec_from_file_location('trusted_protocol',code);p=importlib.util.module_from_spec(s);s.loader.exec_module(p)
base=Path('/var/lib/dell-publisher/releases')
if base.resolve(strict=False)!=base:raise SystemExit('symlink rejected')
base.mkdir(mode=0o700,exist_ok=True);who=pwd.getpwnam('publisher');os.chown(base,who.pw_uid,who.pw_gid)
dest=base/rid
if dest.exists():raise SystemExit('immutable client source already exists')
fd,name=tempfile.mkstemp(prefix='manager-bundle-',dir='/var/lib/dell-publisher');os.fchmod(fd,0o600)
try:
 with os.fdopen(fd,'wb') as out:
  count=0
  while True:
   block=sys.stdin.buffer.read(1024*1024)
   if not block:break
   count+=len(block)
   if count>p.MAX_ARCHIVE:raise SystemExit('archive cap')
   out.write(block)
 p.extract_archive(Path(name),dest,rid)
 for f in [dest,*dest.rglob('*')]:os.chown(f,who.pw_uid,who.pw_gid);f.chmod(0o700 if f.is_dir() else 0o600)
 print(json.dumps({'copied_to':'publisher220','release_id':rid,'members':11,'private_key_read':False,'config_values_emitted':False}))
finally:Path(name).unlink(missing_ok=True)
'''
def prepare_b(rid):
 original=ROOT/'private/java/releases/20261106T121030';dest=ROOT/'private/publisher/releases'/rid;dest.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
 if dest.exists():raise RuntimeError('local B already exists')
 dest.mkdir(mode=0o700)
 manifest=json.loads((original/'manifest.json').read_text());manifest['release_id']=rid
 (dest/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');(dest/'manifest.json').chmod(0o600)
 for name in protocol.NAMES:
  (dest/name).mkdir(mode=0o700)
  for file in ['app.jar','application.yaml']:
   shutil.copyfile(original/name/file,dest/name/file);(dest/name/file).chmod(0o600)
 archive=protocol.build_canonical_archive(dest,dest.parent/(rid+'.tar'),rid)
 target=TARGETS[220];proxy=shlex.join(ctl.BASE+['-W','%h:%p','root@192.168.21.22'])
 args=ctl.BASE+['-o','HostKeyAlias='+target['host_key_alias'],'-o','ProxyCommand='+proxy,'ub@'+target['ip'],'sudo -n python3 -c '+shlex.quote(COPY.replace('rid=RID','rid='+repr(rid)))]
 with archive.open('rb') as raw:r=subprocess.run(args,stdin=raw,capture_output=True,timeout=300)
 if r.returncode:raise RuntimeError('220 private source transfer failed; output withheld')
 same=all(protocol.sha(dest/name/file)==protocol.sha(original/name/file) for name in protocol.NAMES for file in ['app.jar','application.yaml'])
 return {'transfer':json.loads(r.stdout),'source_A_core_manifest_sha256':protocol.sha(original/'manifest.json'),'B_manifest_sha256':protocol.sha(dest/'manifest.json'),'jar_yaml_bytes_identical_to_A':same,'archive_bytes':archive.stat().st_size}
def main():
 p=argparse.ArgumentParser();p.add_argument('--apply-approved-exercise',action='store_true');p.add_argument('--release-id',required=True);a=p.parse_args()
 if not a.apply_approved_exercise:raise SystemExit('informed user and manager window required')
 protocol.release_id(a.release_id)
 v={'at':datetime.datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),'baseline_A':'20261106T121030','release_B':a.release_id,'target':'test240','database_or_nacos_rollback':False,'key_exported':False,'status':'running'};save(v)
 v['initial_status']=checked(client('status'));save(v)
 if v['initial_status']['response']['result']['current_release']!=v['baseline_A']:raise RuntimeError('A mismatch')
 v['B_preparation']=prepare_b(a.release_id);save(v)
 v['stage_B']=checked(client('stage',a.release_id));save(v)
 # The actual transition and concurrent read-only status prove the busy response without a modifying lock.
 from concurrent.futures import ThreadPoolExecutor
 with ThreadPoolExecutor(max_workers=2) as executor:
  future=executor.submit(client,'activate',a.release_id)
  time.sleep(3);v['status_during_activate']=checked(client('status'));save(v)
  v['activate_B']=checked(future.result());save(v)
 v['B_status']=checked(client('status'));save(v)
 v['rollback_A']=checked(client('rollback',v['baseline_A']));save(v)
 v['final_status']=checked(client('status'))
 final=v['final_status']['response']['result'];v['all_five_health_up']=len(final['services'])==5 and all(x['systemd_active'] and x['health_up'] for x in final['services']);v['returned_to_A']=final['current_release']==v['baseline_A'];v['status_busy_verified']=v['status_during_activate']['response']['result'].get('busy') is True
 v['status']='release-exercise-passed' if v['all_five_health_up'] and v['returned_to_A'] and v['status_busy_verified'] else 'release-exercise-incomplete';save(v)
 print(json.dumps({k:v[k] for k in ['status','baseline_A','release_B','all_five_health_up','returned_to_A','status_busy_verified','database_or_nacos_rollback','key_exported']}));return 0 if v['status']=='release-exercise-passed' else 1
if __name__=='__main__':raise SystemExit(main())
