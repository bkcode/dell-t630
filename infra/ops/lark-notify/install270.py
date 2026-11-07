#!/usr/bin/python3 -I
"""Guest270-only reviewed-window installer. Secrets on stdin/LoadCredential only."""
import argparse,base64,hashlib,importlib.util,json,os,platform,re,secrets,socket,subprocess,sys,time,urllib.request
from pathlib import Path
HERE=Path(__file__).resolve().parent;DEST=Path('/usr/local/libexec/dell-lark-notify');ETC=Path('/etc/dell-lark-notify');SECRET=ETC/'secrets';OPS=Path('/opt/dell/ops');AM=OPS/'config/alertmanager';UNIT=Path('/etc/systemd/system/dell-lark-notify.service');NAME='dell-lark-notify.service';CONTAINER='dell-ops-alertmanager-1'
AM_IMAGE='prom/alertmanager:v0.34.2@sha256:7619e9399e623c9f99a40cb199c2bceb972cbf725598a51dcbde69d51dcaaedf'
LEGACY=b'''global:
  resolve_timeout: 5m
route:
  receiver: local-only
  group_by:
  - alertname
  - role
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h
receivers:
- name: local-only
'''
def run(args):
 r=subprocess.run(args,capture_output=True,timeout=60)
 if r.returncode:raise RuntimeError('fixed native action failed; raw output withheld')
 return r.stdout

def safe(path):
 if path.is_symlink() or path.resolve(strict=False)!=path:raise RuntimeError('symlink path rejected')
 return path

def put(path,data,mode=0o600,uid=0,gid=0):
 safe(path);tmp=path.with_name(path.name+'.new');safe(tmp)
 fd=os.open(tmp,os.O_WRONLY|os.O_CREAT|os.O_TRUNC|os.O_NOFOLLOW,mode)
 try:
  os.fchmod(fd,mode);os.fchown(fd,uid,gid)
  with os.fdopen(fd,'wb') as stream:stream.write(data);stream.flush();os.fsync(stream.fileno())
  os.replace(tmp,path)
 except BaseException:
  try:os.close(fd)
  except OSError:pass
  tmp.unlink(missing_ok=True);raise

def guard():
 if os.geteuid()!=0 or Path('/etc/pve').exists() or platform.system()!='Linux' or platform.machine() not in ('x86_64','amd64') or socket.gethostname().split('.')[0]!='ops-service':raise RuntimeError('assigned ops270 AMD64 guest root only')
 os_release=Path('/etc/os-release').read_text()
 if not re.search(r'^ID=debian$',os_release,re.M) or not re.search(r'^VERSION_ID="?13"?$',os_release,re.M):raise RuntimeError('Debian13 required')
 for path in [HERE,OPS,AM]:
  safe(path);st=path.stat()
  if not path.is_dir() or st.st_uid!=0 or st.st_mode&0o022:raise RuntimeError('trusted root directory required')
 addresses=json.loads(run(['ip','-j','addr']))
 found={x.get('local') for n in addresses for x in n.get('addr_info',[])}
 if not {'10.63.30.40','172.18.0.1'}.issubset(found):raise RuntimeError('assigned private IP and existing docker gateway required')
 network=json.loads(run(['docker','--host','unix:///var/run/docker.sock','network','inspect','dell-ops_default']))
 if len(network)!=1 or network[0]['IPAM']['Config']!=[{'Subnet':'172.18.0.0/16','Gateway':'172.18.0.1'}]:raise RuntimeError('existing ops IPAM differs')
 # Format emits no container environment or credential material.
 metadata=json.loads(run(['docker','--host','unix:///var/run/docker.sock','inspect','--format','{{json .}}',CONTAINER]))
 if metadata['Config']['Image']!=AM_IMAGE or metadata['Config']['Labels'].get('com.docker.compose.project')!='dell-ops' or metadata['Config']['Labels'].get('com.docker.compose.service')!='alertmanager' or metadata['NetworkSettings']['Networks']['dell-ops_default']['IPAddress']!='172.18.0.3':raise RuntimeError('fixed current Alertmanager identity/network required')
 if metadata['NetworkSettings']['Networks']['dell-ops_default'].get('IPAMConfig',{}).get('IPv4Address')!='172.18.0.3':raise RuntimeError('AM source must have a verified static address, not a transient dynamic allocation')
 if metadata['State']['Status']!='running' or metadata['State'].get('Health',{}).get('Status')!='healthy':raise RuntimeError('Alertmanager must already be healthy')
 if run(['docker','--host','unix:///var/run/docker.sock','exec',CONTAINER,'id','-u']).strip()!=b'65534':raise RuntimeError('measured Alertmanager UID differs')
 mounts=[x for x in metadata.get('Mounts',[]) if x.get('Destination')=='/run/secrets/lark-bridge-token']
 if len(mounts)!=1 or mounts[0].get('Source')!=str(OPS/'secrets/lark-bridge-token') or mounts[0].get('RW') is not False:raise RuntimeError('parent-reviewed Ops recreation must install the read-only Compose secret first')
 run(['docker','--host','unix:///var/run/docker.sock','exec',CONTAINER,'/bin/sh','-c','test -r /run/secrets/lark-bridge-token'])
 return {'id':metadata['Id'],'pid':metadata['State']['Pid'],'started_at':metadata['State']['StartedAt']}

def modules():
 for name in ['bridge.py','configuration.py','dell-lark-notify.service']:
  file=safe(HERE/name);st=file.stat()
  if not file.is_file() or st.st_uid!=0 or st.st_mode&0o022:raise RuntimeError('trusted reviewed source files required')
 sys.path.insert(0,str(HERE));import bridge,configuration
 return bridge,configuration

def credentials(bridge):
 raw=sys.stdin.buffer.read(4097)
 if len(raw)>4096:raise RuntimeError('private input size rejected')
 try:
  value=bridge.decode(raw)
  if set(value)!={'webhook_b64'}:raise ValueError()
  webhook=base64.b64decode(value['webhook_b64'],validate=True).decode('ascii').rstrip('\n');bridge.validate_url(webhook)
 except Exception:raise RuntimeError('private webhook input invalid; values withheld') from None
 for path,mode in [(ETC,0o755),(SECRET,0o700)]:
  safe(path);path.mkdir(mode=mode,exist_ok=True);os.chown(path,0,0);path.chmod(mode)
 file=SECRET/'lark-webhook';content=webhook.encode()+b'\n'
 if file.exists():
  st=file.stat()
  if file.read_bytes()!=content or st.st_uid!=0 or st.st_mode&0o777!=0o600:raise RuntimeError('existing webhook differs; silent rotation refused')
 else:put(file,content)
 file=OPS/'secrets/lark-bridge-token';safe(file);st=file.stat()
 if st.st_uid!=65534 or st.st_gid!=65534 or st.st_mode&0o777!=0o600 or not re.fullmatch(rb'[A-Za-z0-9_-]{64}\n',file.read_bytes()):raise RuntimeError('preexisting stable Compose bridge secret ownership/format invalid')

def reload_timestamp(opener):
 with opener.open('http://10.63.30.40:9093/metrics',timeout=3) as response:body=response.read(4*1024*1024).decode()
 ok=re.search(r'^alertmanager_config_last_reload_successful ([0-9.eE+-]+)$',body,re.M)
 stamp=re.search(r'^alertmanager_config_last_reload_success_timestamp_seconds ([0-9.eE+-]+)$',body,re.M)
 if not ok or not stamp:raise RuntimeError('native reload metrics absent')
 return float(ok[1])==1,float(stamp[1])

def bridge_ready():
 end=time.monotonic()+8
 while time.monotonic()<end:
  state=subprocess.run(['systemctl','is-active','--quiet',NAME],capture_output=True,timeout=5)
  listeners=subprocess.run(['ss','-H','-ltn','sport = :19093'],capture_output=True,text=True,timeout=5)
  local=[x.split()[3] for x in listeners.stdout.splitlines() if len(x.split())>=5]
  if state.returncode==0 and listeners.returncode==0 and local==['172.18.0.1:19093']:return
  time.sleep(.25)
 raise RuntimeError('bridge listener/active state was not verified')

def write_am(config):
 pending=AM/'lark-notify-pending.json';put(pending,config.encode(),0o644)
 try:run(['docker','--host','unix:///var/run/docker.sock','exec',CONTAINER,'/bin/amtool','check-config','/etc/alertmanager/lark-notify-pending.json'])
 finally:pending.unlink(missing_ok=True)
 opener=urllib.request.build_opener(urllib.request.ProxyHandler({}));_,old_timestamp=reload_timestamp(opener)
 put(AM/'alertmanager.yml',config.encode(),0o644)
 run(['docker','--host','unix:///var/run/docker.sock','kill','--signal=HUP',CONTAINER]);end=time.monotonic()+15
 while time.monotonic()<end:
  try:
   success,stamp=reload_timestamp(opener)
   if success and stamp>old_timestamp:return
  except Exception:pass
  time.sleep(.5)
 raise RuntimeError('fresh Alertmanager successful reload timestamp was not observed')

def install(bridge,configuration):
 before=guard();current=safe(AM/'alertmanager.yml').read_bytes()
 allowed=[LEGACY,configuration.dump('acceptance').encode()]
 if current not in allowed:raise RuntimeError('existing config is not reviewed local-only/acceptance baseline; refusing override')
 credentials(bridge);safe(DEST);DEST.mkdir(mode=0o755,parents=True,exist_ok=True)
 for name in ['bridge.py']:
  file=DEST/name;content=(HERE/name).read_bytes()
  if file.exists() and file.read_bytes()!=content:raise RuntimeError('existing installed code differs; update needs separate review')
  put(file,content,0o644)
 if UNIT.exists() and UNIT.read_bytes()!=(HERE/UNIT.name).read_bytes():raise RuntimeError('existing unit differs; separate review required')
 put(UNIT,(HERE/UNIT.name).read_bytes(),0o644)
 put(ETC/'policy.json',json.dumps(configuration.policy('acceptance')).encode()+b'\n',0o644)
 backup=SECRET/'alertmanager-before-lark.yml'
 if not backup.exists():put(backup,current)
 try:
  run(['systemd-analyze','verify',str(UNIT)]);run(['systemctl','daemon-reload']);run(['systemctl','enable','--now',NAME]);bridge_ready();write_am(configuration.dump('acceptance'))
 except BaseException:
  put(AM/'alertmanager.yml',current,0o644)
  subprocess.run(['docker','--host','unix:///var/run/docker.sock','kill','--signal=HUP',CONTAINER],capture_output=True,timeout=30)
  subprocess.run(['systemctl','disable','--now',NAME],capture_output=True,timeout=30)
  raise
 put(OPS/'lark-notify-state.json',json.dumps({'mode':'acceptance','owner':'native-lark-notify','generic_prepare':'refuse-reset'}).encode()+b'\n')
 after=guard()
 if before!=after:raise RuntimeError('Alertmanager identity/PID/start changed; expected reload only')
 return {'status':'acceptance-only-installed','mode':'acceptance','only_bind':'172.18.0.1:19093','alertmanager_container_unchanged':True,'lark_message_sent_by_installer':False,'secrets_in_argv_env_or_output':False,'bridge_code_sha256':hashlib.sha256((DEST/'bridge.py').read_bytes()).hexdigest()}

def enable(configuration):
 before=guard();safe(ETC/'policy.json');old=(ETC/'policy.json').read_bytes()
 if json.loads(old)!=configuration.policy('acceptance'):raise RuntimeError('acceptance policy baseline required')
 proof=SECRET/'acceptance-proof.json';safe(proof);st=proof.stat()
 if st.st_uid!=0 or st.st_mode&0o777!=0o600:raise RuntimeError('manager acceptance proof must be root600')
 value=json.loads(proof.read_text())
 if value.get('status')!='firing-and-resolved-acknowledged' or type(value.get('upstream_code')) is not int or value.get('upstream_code')!=0 or not re.fullmatch('[a-f0-9]{32}',value.get('acceptance_run','')):raise RuntimeError('real firing/resolved delivery proof required')
 for phase in ('firing','resolved'):
  row=value.get(phase,{})
  if row.get('phase')!=phase or type(row.get('upstream_code')) is not int or row['upstream_code']!=0 or not re.fullmatch('[a-f0-9]{64}',row.get('payload_sha256','')):raise RuntimeError('both phase acknowledgments required')
 if value.get('boot_id')!=Path('/proc/sys/kernel/random/boot_id').read_text().strip():raise RuntimeError('acceptance proof must be from current guest boot')
 original=(AM/'alertmanager.yml').read_bytes()
 if original!=configuration.dump('acceptance').encode():raise RuntimeError('acceptance-only AM config required')
 try:
  put(ETC/'policy.json',json.dumps(configuration.policy('active')).encode()+b'\n',0o644);run(['systemctl','restart',NAME]);bridge_ready();write_am(configuration.dump('active'))
 except BaseException:
  put(ETC/'policy.json',old,0o644);put(AM/'alertmanager.yml',original,0o644)
  subprocess.run(['systemctl','restart',NAME],capture_output=True,timeout=30);subprocess.run(['docker','--host','unix:///var/run/docker.sock','kill','--signal=HUP',CONTAINER],capture_output=True,timeout=30);raise
 if guard()!=before:raise RuntimeError('unexpected Alertmanager recreation/restart')
 put(OPS/'lark-notify-state.json',json.dumps({'mode':'active','owner':'native-lark-notify','generic_prepare':'refuse-reset'}).encode()+b'\n')
 return {'status':'real-whitelist-notifications-enabled','mode':'active','accepted_proof_run':value['acceptance_run'],'alertmanager_container_unchanged':True,'no_host_network_change':True}

def main():
 p=argparse.ArgumentParser();p.add_argument('action',choices=['install-acceptance-only','enable-live-after-maintenance']);p.add_argument('--reviewed-ops270-window',action='store_true');p.add_argument('--maintenance-complete',action='store_true');args=p.parse_args()
 if not args.reviewed_ops270_window:raise RuntimeError('manager reviewed ops270 window required')
 guard();bridge,configuration=modules()
 if args.action=='enable-live-after-maintenance' and not args.maintenance_complete:raise RuntimeError('explicit maintenance complete gate required')
 result=install(bridge,configuration) if args.action=='install-acceptance-only' else enable(configuration)
 print(json.dumps(result))
if __name__=='__main__':
 try:main()
 except Exception:print(json.dumps({'status':'failed','message':'fixed notification install rejected/failed; secret values and native output withheld'}));sys.exit(1)
