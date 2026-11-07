#!/usr/bin/env python3
"""Guest-only staged install/activation/rollback for the approved five-service test chain."""
import argparse,hashlib,json,os,re,shutil,socket,subprocess,sys,time,urllib.request
from pathlib import Path
import yaml
NAMES=['finger-service-system','finger-service-coms','finger-auth','finger-bff-system','finger-gateway-mobile']
ROOT=Path('/opt/finger');RELEASES=ROOT/'releases/test';CURRENT=ROOT/'current-test'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(args):
 p=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,check=False)
 if p.returncode:raise RuntimeError('Command failed: '+args[0]+' '+(args[1] if len(args)>1 else ''))
 return p.stdout

def guard():
 assert os.geteuid()==0 and not Path('/etc/pve').exists(),'Guest root only; PVE refused'
 assert socket.gethostname().split('.')[0]=='java-test-01','Only assigned java-test-01 is supported'
 addresses=json.loads(run(['ip','-j','addr']))
 assert any(a.get('local')=='10.63.20.20' for n in addresses for a in n.get('addr_info',[])),'Wrong guest address'
 assert Path('/opt/finger/java/bin/java').is_file() and run(['id','-u','finger']).strip()!='0','Run guest JDK base preparation first'

def check_manifest(path):
 assert not path.is_symlink();m=json.loads((path/'manifest.json').read_text())
 assert m['target_hostname']=='java-test-01' and m['target_ip']=='10.63.20.20' and m['data_ip']=='10.63.20.10'
 assert m['issuer']=='http://192.168.21.22:19999' and m['profile']=='dell-test'
 assert re.fullmatch(r'[0-9]{8}T[0-9]{6}',m['release_id']) and {x['name'] for x in m['services']}==set(NAMES)
 for row in m['services']:
  for key in ['port','xms_mib','xmx_mib','metaspace_mib','memory_max_mib']:
   assert type(row[key]) is int and 0<row[key]<=65535,'Invalid numeric service parameter'
  assert row['xms_mib']==128 and row['xmx_mib'] in [512,768] and row['metaspace_mib']==256 and row['memory_max_mib'] in [1024,1536]
  for name,key in [('app.jar','jar_sha256'),('application.yaml','config_sha256')]:
   f=path/row['name']/name;assert f.is_file() and not f.is_symlink() and f.resolve().is_relative_to(path.resolve())
   assert sha(f)==row[key],'Release checksum mismatch'
  cfg=yaml.safe_load((path/row['name']/'application.yaml').read_text())
  assert cfg['spring']['application']['name']==row['name'] and cfg['spring']['profiles']['active']=='dell-test'
  assert cfg['server']['port']==row['port'] and cfg['server']['address']=='10.63.20.20'
  nacos=cfg['spring']['cloud']['nacos'];assert nacos['server-addr']=='10.63.20.10:8848'
  assert all(not x.startswith('optional:') for x in cfg['spring']['config']['import'])
  if 'datasource' in cfg['spring']:
   role='auth' if row['name']=='finger-auth' else 'system' if row['name']=='finger-service-system' else 'coms' if row['name']=='finger-service-coms' else None
   assert role and cfg['spring']['datasource']['username']=='finger_'+role+'_test'
   assert cfg['spring']['datasource']['url'].startswith('jdbc:mysql://10.63.20.10:3306/finger_'+role+'_test?')
  if row['name']=='finger-auth':assert cfg['finger']['auth']['bootstrap']['issuer']==m['issuer']
 return m

def unit(row):
 name=row['name'];return f'''[Unit]
Description=Dell isolated test {name}
Wants=network-online.target
After=network-online.target
StartLimitIntervalSec=120
StartLimitBurst=3

[Service]
Type=simple
User=finger
Group=finger
WorkingDirectory=/var/lib/finger/{name}
UMask=0077
LoadCredential=application.yaml:/opt/finger/current-test/{name}/application.yaml
Environment=AWS_EC2_METADATA_DISABLED=true
ExecStart=/opt/finger/java/bin/java -Xms{row['xms_mib']}m -Xmx{row['xmx_mib']}m -XX:MaxMetaspaceSize={row['metaspace_mib']}m -Dfile.encoding=UTF-8 -Duser.timezone=Asia/Shanghai -Djava.awt.headless=true -Duser.home=/var/lib/finger/{name} -jar /opt/finger/current-test/{name}/app.jar --spring.config.location=file:%d/application.yaml --spring.profiles.active=dell-test
Restart=on-failure
RestartSec=10
MemoryMax={row['memory_max_mib']}M
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
PrivateTmp=true
ReadWritePaths=/var/lib/finger /var/log/finger
StandardOutput=append:/var/log/finger/{name}/app.log
StandardError=append:/var/log/finger/{name}/app.log
TimeoutStopSec=45

[Install]
WantedBy=multi-user.target
'''

def stage(path,manifest):
 destination=RELEASES/manifest['release_id'];assert not destination.exists(),'Existing release immutable'
 assert shutil.disk_usage(ROOT).free>sum((path/r['name']/'app.jar').stat().st_size for r in manifest['services'])+1024**3
 destination.mkdir(parents=True,mode=0o750);shutil.chown(destination,user='root',group='finger')
 for row in manifest['services']:
  folder=destination/row['name'];folder.mkdir(mode=0o750);shutil.chown(folder,user='root',group='finger')
  for filename,mode,owner in [('app.jar',0o644,'root'),('application.yaml',0o600,'root')]:
   shutil.copyfile(path/row['name']/filename,folder/filename);os.chmod(folder/filename,mode);shutil.chown(folder/filename,user=owner,group='root' if filename=='application.yaml' else 'finger')
  (folder/'unit.service').write_text(unit(row));os.chmod(folder/'unit.service',0o644)
 shutil.copyfile(path/'manifest.json',destination/'manifest.json');os.chmod(destination/'manifest.json',0o600)
 return destination

def gates(path):
 assert path and path.is_file() and not path.is_symlink(),'Manager-combined readiness marker required'
 s=path.stat();assert s.st_uid==0 and not s.st_mode&0o077
 m=json.loads(path.read_text());assert m.get('target_ip')=='10.63.20.20'
 for key in ['database_schemas_ready','nacos_configs_ready','network_policy_ready','issuer_candidate_acknowledged']:
  assert m.get(key) is True,'Readiness gate not met: '+key

def pointer(destination):
 temporary=ROOT/'current-test.pending'
 if temporary.is_symlink():temporary.unlink()
 assert not temporary.exists()
 temporary.symlink_to(destination);os.replace(temporary,CURRENT)
 for name in NAMES:
  target=Path('/etc/systemd/system')/('dell-finger-'+name+'.service')
  if target.exists() and not target.is_symlink():raise RuntimeError('Refuse replacing an unmanaged systemd unit')
  if target.is_symlink():target.unlink()
  target.symlink_to(CURRENT/name/'unit.service')
 run(['systemctl','daemon-reload'])

def stop_all(strict=True):
 failed=[]
 for name in reversed(NAMES):
  try:
   p=subprocess.run(['systemctl','stop','dell-finger-'+name+'.service'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
   if p.returncode:failed.append(name)
  except OSError:failed.append(name)
 if failed and strict:raise RuntimeError('Managed service stop failed')
 return failed

class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,*args,**kwargs):return None

def start_all(manifest):
 opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
 for name in NAMES:
  row=next(r for r in manifest['services'] if r['name']==name)
  run(['systemctl','enable','--now','dell-finger-'+name+'.service'])
  deadline=time.monotonic()+120;healthy=False
  while time.monotonic()<deadline:
   try:
    with opener.open('http://10.63.20.20:'+str(row['port'])+'/actuator/health',timeout=3) as response:
     healthy=response.status==200 and json.loads(response.read(4096)).get('status')=='UP'
   except Exception:healthy=False
   if healthy:break
   time.sleep(2)
  if not healthy:raise RuntimeError('Health verification failed: '+name)

def check_staged_units(path,manifest):
 for row in manifest['services']:
  expected=path/row['name']/'unit.service'
  assert expected.is_file() and not expected.is_symlink() and expected.read_text()==unit(row),'Fixed LoadCredential unit missing or mismatched'

def transition(destination,manifest,previous):
 check_staged_units(destination,manifest)
 previous_manifest=None
 if previous:
  assert previous.is_dir() and not previous.is_symlink() and previous.resolve().parent==RELEASES.resolve(),'Previous release must be a managed recoverable sibling'
  previous_manifest=check_manifest(previous)  # Fail before stopping or changing any pointer.
  check_staged_units(previous,previous_manifest)
 try:
  stop_all()
  pointer(destination)
  start_all(manifest)
 except BaseException:
  stop_all(strict=False)
  if previous:
   try:
    pointer(previous)
    start_all(previous_manifest)
   except BaseException:raise RuntimeError('Transition and old release recovery failed') from None
  raise

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['check','stage','activate','rollback']);p.add_argument('--bundle',type=Path);p.add_argument('--release-id');p.add_argument('--ready-marker',type=Path);a=p.parse_args()
 guard()
 if a.action in ['check','stage']:
  assert a.bundle;m=check_manifest(a.bundle)
  if a.action=='stage':destination=stage(a.bundle,m)
  print(json.dumps({'status':'bundle-validated' if a.action=='check' else 'staged-not-activated','release_id':m['release_id'],'applications_started':False}));return
 assert a.release_id and re.fullmatch(r'[0-9]{8}T[0-9]{6}',a.release_id)
 destination=RELEASES/a.release_id;m=check_manifest(destination);gates(a.ready_marker)
 previous=CURRENT.resolve() if CURRENT.is_symlink() else None
 if previous:assert previous.is_relative_to(RELEASES),'Existing pointer is not a managed test release'
 for name in NAMES:
  target=Path('/etc/systemd/system')/('dell-finger-'+name+'.service')
  assert not target.exists() or target.is_symlink(),'Refuse replacing unmanaged units before stopping anything'
 transition(destination,m,previous)
 print(json.dumps({'status':'runtime-health-verified-business-acceptance-pending','action':a.action,'release_id':m['release_id'],'previous_release':previous.name if previous else None,'sql_executed':False,'database_rollback_performed':False}))
if __name__=='__main__':
 try:main()
 except Exception as e:print(json.dumps({'status':'failed','error_category':type(e).__name__,'message':'fixed test deployer failed; sensitive details suppressed'}));sys.exit(1)
