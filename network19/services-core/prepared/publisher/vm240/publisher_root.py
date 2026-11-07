#!/usr/bin/python3 -I
"""Root-owned no-argv stdin-only RPC. Test240 only; never executes uploaded scripts."""
import fcntl,hashlib,importlib.util,json,os,pwd,select,shutil,signal,socket,subprocess,sys,tempfile,time,urllib.request,uuid
from pathlib import Path
CODE=Path('/usr/local/libexec/dell-publisher')
FIXED=Path('/usr/local/libexec/dell/deploy-test-chain.py')
POLICY=Path('/etc/dell-publisher/test240-policy.json')
MARKER=Path('/root/dell-java-test-readiness.json')
ROOT=Path('/opt/finger');RELEASES=ROOT/'releases/test';CURRENT=ROOT/'current-test'
STATE=ROOT/'publisher-state';INCOMING=ROOT/'publisher-incoming'

def owned(path,directory=False):
 if path.is_symlink() or not path.exists() or path.resolve()!=path:raise RuntimeError('trusted path missing/symlink')
 stat=path.stat()
 if stat.st_uid!=0 or stat.st_mode&0o022 or (directory and not path.is_dir()):raise RuntimeError('trusted root ownership required')
 return path

def load_protocol():
 owned(CODE,True);owned(CODE/'publisher_protocol.py')
 s=importlib.util.spec_from_file_location('trusted_publisher_protocol',CODE/'publisher_protocol.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def guard():
 if os.geteuid()!=0 or os.environ.get('SUDO_USER')!='deployer' or Path('/etc/pve').exists() or socket.gethostname().split('.')[0]!='java-test-01':raise RuntimeError('restricted test240 root caller required')
 p=subprocess.run(['ip','-j','addr'],capture_output=True,text=True,timeout=10)
 if p.returncode or not any(a.get('local')=='192.168.19.45' for n in json.loads(p.stdout) for a in n.get('addr_info',[])):raise RuntimeError('wrong test240 address')
 for path in [ROOT,ROOT/'releases',RELEASES]:owned(path,True)
 owned(FIXED);owned(POLICY)
 policy=json.loads(POLICY.read_text())
 if policy.get('target_hostname')!='java-test-01' or policy.get('target_ip')!='192.168.19.45' or not policy.get('baseline_migrated') or hashlib.sha256(FIXED.read_bytes()).hexdigest()!=policy.get('fixed_deployer_sha256'):raise RuntimeError('trusted fixed deployer/baseline policy not ready')
 return policy

def read_header(protocol):
 data=b'';deadline=time.monotonic()+30
 while not data.endswith(b'\n'):
  if len(data)>4096 or time.monotonic()>=deadline:raise RuntimeError('RPC header limit exceeded')
  ready=select.select([sys.stdin.fileno()],[],[],max(0,deadline-time.monotonic()))[0]
  if not ready:raise RuntimeError('RPC header timeout')
  value=os.read(sys.stdin.fileno(),1)
  if not value:raise RuntimeError('RPC header incomplete')
  data+=value
 return protocol.validate_header(protocol.json_read(data))

def receive_archive(header,path):
 remaining=header['archive_bytes'];digest=hashlib.sha256();deadline=time.monotonic()+300
 with path.open('xb') as out:
  path.chmod(0o600)
  while remaining:
   wait=min(30,max(0,deadline-time.monotonic()))
   if wait<=0 or not select.select([sys.stdin.fileno()],[],[],wait)[0]:raise RuntimeError('archive receive timeout')
   chunk=os.read(sys.stdin.fileno(),min(1024*1024,remaining))
   if not chunk:raise RuntimeError('archive truncated')
   out.write(chunk);digest.update(chunk);remaining-=len(chunk)
 if digest.hexdigest()!=header['archive_sha256']:raise RuntimeError('archive digest mismatch')
 if not select.select([sys.stdin.fileno()],[],[],5)[0] or os.read(sys.stdin.fileno(),1):raise RuntimeError('trailing or unterminated stage input')

def check_immutable(path,protocol,release_id,namespace):
 m,_=protocol.check_release(path,release_id,namespace)
 spec=importlib.util.spec_from_file_location('trusted_fixed_unit_checker',FIXED);fixed=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixed);fixed.check_staged_units(path,m)
 for file in path.rglob('*'):
  if file.is_symlink() or file.stat().st_uid!=0 or file.stat().st_mode&0o022:raise RuntimeError('release is not root-immutable')
  if file.name=='application.yaml' and (file.stat().st_mode&0o777!=0o600 or file.stat().st_gid!=0):raise RuntimeError('persistent credential config must be root:root600')
 return m

def call_fixed(action,*args):
 p=subprocess.run(['/usr/bin/python3','-I',str(FIXED),action,*args],capture_output=True,text=True,timeout=1500,env={'PATH':'/usr/sbin:/usr/bin:/sbin:/bin','HOME':'/root','LANG':'C.UTF-8'})
 if p.returncode:raise RuntimeError('fixed deployer '+action+' failed; no uploaded execution path accepted')
 return p.stdout

def current_id():
 if not CURRENT.is_symlink():return None
 path=CURRENT.resolve()
 if path.parent!=RELEASES or not path.is_dir():raise RuntimeError('current pointer outside managed test releases')
 return path.name

class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,*args,**kwargs):return None

def health(protocol):
 result=[];opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
 for name in protocol.NAMES:
  p=subprocess.run(['systemctl','is-active','dell-finger-'+name+'.service'],capture_output=True,text=True,timeout=10)
  up=False
  try:
   with opener.open('http://192.168.19.45:'+str(protocol.PORTS[name])+'/actuator/health',timeout=3) as r:up=r.status==200 and json.loads(r.read(4096)).get('status')=='UP'
  except Exception:pass
  result.append({'service':name,'systemd_active':p.stdout.strip()=='active','health_up':up})
 return result

def process_start_ticks(pid):
 try:
  text=Path('/proc')/str(pid)/'stat';raw=text.read_text();tail=raw[raw.rfind(')')+2:].split();return tail[19]
 except (OSError,ValueError,IndexError):return None

def transaction_state():
 result={'busy':False,'last_transaction':None}
 last=STATE/'last-transaction.json'
 if last.exists():
  owned(last);raw=json.loads(last.read_text())
  allowed={'action','release_id','status','target','previous_release','database_or_nacos_changed','received_executable_script','current_release_after_failure'}
  result['last_transaction']={k:v for k,v in raw.items() if k in allowed}
 marker=STATE/'busy.json'
 try:
  if marker.exists():
   owned(marker);raw=json.loads(marker.read_text())
   live=process_start_ticks(raw.get('pid'))
   result['busy']=live is not None and live==raw.get('process_start_ticks')
   result['busy_transaction']={k:raw.get(k) for k in ['transaction_id','action','release_id']}
   if not result['busy']:result['busy_marker_stale']=True
 except FileNotFoundError:pass  # Atomic completion may remove the marker during a read.
 return result

def status(protocol):
 staged=[]
 for path in sorted(RELEASES.iterdir()):
  if path.is_dir() and not path.is_symlink():
   try:protocol.release_id(path.name);staged.append(path.name)
   except ValueError:pass
 return {'current_release':current_id(),'managed_release_ids':staged,'services':health(protocol),'target':'test240','database_or_nacos_rollback':False,**transaction_state()}

def busy_begin(header):
 marker={'transaction_id':uuid.uuid4().hex,'pid':os.getpid(),'process_start_ticks':process_start_ticks(os.getpid()),'action':header['action'],'release_id':header.get('release_id')}
 path=STATE/'busy.json';temp=STATE/('busy-'+marker['transaction_id']+'.tmp');temp.write_text(json.dumps(marker));temp.chmod(0o600);os.replace(temp,path);return marker['transaction_id']

def busy_end(identifier):
 path=STATE/'busy.json'
 if path.exists() and json.loads(path.read_text()).get('transaction_id')==identifier:path.unlink()

def write_receipt(value):
 path=STATE/'last-transaction.json';temporary=STATE/('receipt-'+uuid.uuid4().hex+'.tmp');temporary.write_text(json.dumps(value,indent=2)+'\n');temporary.chmod(0o600);os.replace(temporary,path)

def execute(header,protocol,policy):
 action=header['action']
 if action=='status':return status(protocol)
 release=header['release_id'];destination=RELEASES/release
 for path in [STATE,INCOMING]:
  if path.exists():owned(path,True)
  else:path.mkdir(mode=0o700)
 receipt={'action':action,'release_id':release,'status':'running','target':'test240','database_or_nacos_changed':False,'received_executable_script':False}
 write_receipt(receipt)
 try:
  if action=='stage':
   if destination.exists() or destination.is_symlink():raise RuntimeError('release ID already exists; immutable stage refuses overwrite')
   if shutil.disk_usage(ROOT).free<header['archive_bytes']*3+1024**3:raise RuntimeError('insufficient conservative immutable-stage disk headroom')
   with tempfile.TemporaryDirectory(prefix='stage-',dir=INCOMING) as folder:
    folder=Path(folder);archive=folder/'bundle.tar';receive_archive(header,archive)
    pending=folder/'release';protocol.extract_archive(archive,pending,release,policy['namespace_id'])
    call_fixed('check','--bundle',str(pending));call_fixed('stage','--bundle',str(pending));check_immutable(destination,protocol,release,policy['namespace_id'])
   receipt['status']='staged-not-activated'
  else:
   check_immutable(destination,protocol,release,policy['namespace_id']);before=current_id()
   if not before:raise RuntimeError('recoverable previous baseline required')
   check_immutable(RELEASES/before,protocol,before,policy['namespace_id'])
   call_fixed(action,'--release-id',release,'--ready-marker',str(MARKER))
   checks=health(protocol)
   if current_id()!=release or not all(x['systemd_active'] and x['health_up'] for x in checks):raise RuntimeError('post-transition real health/pointer mismatch')
   receipt.update(status='activated-health-verified' if action=='activate' else 'rollback-health-verified',previous_release=before,services=checks)
 except Exception:
  receipt['status']='failed';receipt['current_release_after_failure']=current_id();write_receipt(receipt);raise
 write_receipt(receipt);return receipt

def main():
 if len(sys.argv)!=1:raise RuntimeError('root RPC accepts no argv')
 protocol=load_protocol();policy=guard();header=read_header(protocol)
 if header['action']=='status':
  response=status(protocol)  # No modifying flock: atomic filtered status remains available while busy.
 else:
  signal.signal(signal.SIGHUP,signal.SIG_IGN)
  lock=os.open('/run/lock/dell-publish-test240.lock',os.O_RDWR|os.O_CREAT,0o600);identifier=None
  try:
   try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
   except BlockingIOError:raise RuntimeError('another test240 publishing transaction is active') from None
   for path in [STATE,INCOMING]:
    if path.exists():owned(path,True)
    else:path.mkdir(mode=0o700)
   identifier=busy_begin(header)
   response=execute(header,protocol,policy)
  finally:
   if identifier:busy_end(identifier)
   os.close(lock)
 try:print(json.dumps({'ok':True,'result':response}))
 except BrokenPipeError:pass

if __name__=='__main__':
 try:main()
 except Exception as error:
  try:print(json.dumps({'ok':False,'error_category':type(error).__name__,'message':'restricted publish request rejected or fixed transition failed; no sensitive details emitted'}))
  except BrokenPipeError:pass
  sys.exit(1)
