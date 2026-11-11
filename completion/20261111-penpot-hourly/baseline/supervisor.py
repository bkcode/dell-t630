#!/usr/bin/env python3
"""Fixed VM250 Penpot supervisor. No source/identity/data mutation, builds or pulls."""
import argparse,fcntl,hashlib,json,os,platform,signal,socket,stat,subprocess,sys,time
from pathlib import Path
BASE=Path('/opt/dell/penpot');HERE=BASE/'runtime/health-supervision';LOCK=HERE/'deployment-lock.json'
D=['docker','--host','unix:///var/run/docker.sock'];STATE=Path('/run/dell-penpot-supervision-state.json')
EXPECTED={'penpot-'+x for x in ['frontend','backend','exporter','admin-console','dns','mcp','worker','import','postgres','valkey','mailpit']}
SHUTDOWN=False
class Failure(RuntimeError):pass
class StopRequested(Exception):pass

def run(args,timeout=30,check=True):
 p=subprocess.run(args,capture_output=True,text=True,timeout=timeout,env={'PATH':'/usr/sbin:/usr/bin:/sbin:/bin','HOME':'/root','LANG':'C.UTF-8'})
 if check and p.returncode:raise Failure('fixed-command-failed')
 return p

def docker(*args,**kw):return run(D+list(args),**kw)
def sha(path):
 with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def owned(path,directory=False):
 if path.resolve()!=path or not path.exists():raise Failure('trusted-path-missing-or-symlink')
 s=path.stat()
 if s.st_uid!=0 or s.st_mode&0o022 or (directory and not path.is_dir()):raise Failure('trusted-root-ownership-required')
 return path

def load_lock():
 for path in [Path('/opt'),Path('/opt/dell'),BASE,BASE/'runtime',HERE]:owned(path,True)
 owned(LOCK)
 lock=json.loads(LOCK.read_text())
 if lock['guest']!={'vmid':250,'hostname':'penpot-service','ip':'192.168.19.50','arch':'amd64'} or set(lock['services'])!=EXPECTED:raise Failure('fixed-contract-identity-rejected')
 return lock

def guest_guard():
 if os.geteuid()!=0 or Path('/etc/pve').exists() or platform.machine() not in ('x86_64','amd64') or socket.gethostname().split('.')[0]!='penpot-service':raise Failure('assigned250-root-guest-only')
 rows=json.loads(run(['ip','-j','address','show']).stdout)
 if not any(a.get('local')=='192.168.19.50' for row in rows for a in row.get('addr_info',[])):raise Failure('assigned-IP-missing')
 sock=Path('/var/run/docker.sock')
 if not sock.exists() or not stat.S_ISSOCK(sock.stat().st_mode):raise Failure('local-Docker-socket-missing')

def validate_storage(lock,fs,daemon):
 s=lock['storage']
 if fs.get('target')!=s['mountpoint'] or fs.get('uuid')!=s['filesystem_uuid'] or fs.get('fstype')!='ext4':raise Failure('data-mount-UUID-mismatch')
 if daemon['root_dir']!=s['docker_root_dir'] or daemon['driver']!='overlay2' or daemon['name']!='penpot-service' or daemon['arch'] not in ('x86_64','amd64') or daemon['os']!='linux':raise Failure('local-Docker-storage-or-identity-mismatch')

def storage_guard(lock):
 fs=json.loads(run(['findmnt','--json','--mountpoint','/srv/penpot','--output','TARGET,SOURCE,FSTYPE,UUID']).stdout)['filesystems']
 if len(fs)!=1:raise Failure('data-mount-missing')
 daemon=json.loads(docker('info','--format','{"root_dir":{{json .DockerRootDir}},"driver":{{json .Driver}},"name":{{json .Name}},"arch":{{json .Architecture}},"os":{{json .OSType}}}').stdout)
 validate_storage(lock,fs[0],daemon)
 if Path('/srv/penpot/docker').resolve()!=Path('/srv/penpot/docker'):raise Failure('DockerRootDir-symlink-rejected')

def validate_image_metadata(expected,actual):
 if actual!={'id':expected,'arch':'amd64','os':'linux'}:raise Failure('image-ID-or-AMD64-lock-mismatch')

def verify_files_and_images(lock):
 for relative,digest in lock['package_file_sha256'].items():
  p=BASE/relative;owned(p)
  if sha(p)!=digest:raise Failure('existing-package-hash-changed')
 for relative,digest in lock['supervision_file_sha256'].items():
  p=HERE/relative;owned(p)
  if sha(p)!=digest:raise Failure('supervision-file-hash-changed')
 head=run(['git','--no-optional-locks','-C',str(BASE/'source'),'rev-parse','HEAD']).stdout.strip()
 dirty=run(['git','--no-optional-locks','-C',str(BASE/'source'),'status','--porcelain=v1']).stdout.strip()
 if head!=lock['Git']['HEAD'] or dirty:raise Failure('clean-Git-ff1783e-required')
 for marker in ['fresh-instance.json','automation-ready.json']:
  owned(Path('/etc/penpot')/marker)  # Presence/ownership only; no identity values read.
 for spec in lock['services'].values():
  for reference in [spec['image_reference_before'],spec['image_id']]:
   m=json.loads(docker('image','inspect','--format','{"id":{{json .Id}},"arch":{{json .Architecture}},"os":{{json .Os}}}',reference).stdout)
   validate_image_metadata(spec['image_id'],m)

def compose(args):
 return D+['compose','--project-directory',str(BASE),'--env-file','/etc/penpot/.env','-f',str(BASE/'compose.fresh.yaml'),'-f',str(HERE/'compose.health-supervision.yaml'),*args]

def check_config(lock):
 names=run(compose(['config','--services'])).stdout.split()
 if len(names)!=11 or set(names)!=EXPECTED:raise Failure('compose-exact11-services-required')
 # Only service names/images are requested, never full config/Env/secret values.
 images=run(compose(['config','--images'])).stdout.split()
 approved={v['image_id'] if n in ('penpot-frontend','penpot-worker','penpot-import') else v['image_reference_before'] for n,v in lock['services'].items()}
 if len(images)!=11 or set(images)!=approved:raise Failure('compose-locked-images-required')

def scan():
 ids=docker('ps','-aq','--no-trunc').stdout.split();result={}
 fmt='{"id":{{json .Id}},"name":{{json .Name}},"image":{{json .Image}},"status":{{json .State.Status}},"running":{{json .State.Running}},"oom":{{json .State.OOMKilled}},"health":{{if (index .State "Health")}}{{json .State.Health.Status}}{{else}}null{{end}},"pids":{{json .HostConfig.PidsLimit}},"memory":{{json .HostConfig.Memory}},"nano_cpus":{{json .HostConfig.NanoCpus}},"restart":{{json .HostConfig.RestartPolicy.Name}},"mounts":[{{range $i,$m:=.Mounts}}{{if $i}},{{end}}{"source":{{json $m.Source}},"destination":{{json $m.Destination}},"rw":{{json $m.RW}}}{{end}}]}'
 for cid in ids:
  c=json.loads(docker('inspect','--format',fmt,cid).stdout);name=c['name'].lstrip('/')
  # Never silently accept unknown containers in this assigned single-stack guest.
  if not name.startswith('penpot-penpot-') or not name.endswith('-1'):raise Failure('unexpected-container-on-assigned-guest')
  service=name[len('penpot-'):-2]
  if service in result:raise Failure('duplicate-service-container')
  result[service]=c
 return result

def validate_frame(frame,lock,starting=False):
 if set(frame)-EXPECTED:raise Failure('unexpected-service-container')
 if set(frame)!=EXPECTED:
  if starting:return False
  raise Failure('required-service-missing')
 ready=True
 for name,c in frame.items():
  s=lock['services'][name]
  if c['image']!=s['image_id'] or c['pids']!=s['pids_limit_proposed'] or c['memory']!=s['memory_bytes'] or c['nano_cpus']!=s['nano_cpus'] or c['restart']!='no':raise Failure('runtime-image-resource-restart-contract-changed')
  actual={(m['source'],m['destination'],m['rw']) for m in c['mounts']};expected={(m['source'],m['destination'],m['rw']) for m in s['expected_mounts']}
  if actual!=expected:raise Failure('runtime-mount-contract-changed')
  if c['oom'] or c['status'] in ('dead','exited','removing') or (not starting and not c['running']):raise Failure('managed-container-stopped-or-OOM')
  ready=ready and c['running'] and c['health']=='healthy'
 return ready

class Monitor:
 def __init__(self,threshold=3):self.threshold=threshold;self.consecutive_bad=0
 def update(self,ready):
  self.consecutive_bad=0 if ready else self.consecutive_bad+1
  if self.consecutive_bad>=self.threshold:raise Failure('consecutive-health-failure')

def notify(message):
 address=os.environ.get('NOTIFY_SOCKET')
 if not address:raise Failure('systemd-notify-socket-required')
 if address.startswith('@'):address='\0'+address[1:]
 with socket.socket(socket.AF_UNIX,socket.SOCK_DGRAM) as sock:sock.connect(address);sock.sendall(message.encode())

def state(phase,**values):
 out={'phase':phase,'time_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),**values};temp=STATE.with_name(STATE.name+'.'+str(os.getpid())+'.tmp')
 fd=os.open(temp,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
 with os.fdopen(fd,'w') as f:json.dump(out,f)
 os.replace(temp,STATE)

def stop_group(lock):
 # Safe after disk/daemon loss: no compose/config/data mount access is needed.
 names={s['container_name'] for s in lock['services'].values()};p=docker('ps','-q','--no-trunc',check=False,timeout=10)
 if p.returncode:return False
 ids=[]
 for cid in p.stdout.split():
  q=docker('inspect','--format','{{.Name}}',cid,check=False,timeout=10)
  if q.returncode==0 and q.stdout.strip().lstrip('/') in names:ids.append(cid)
 if not ids:return True
 return docker('stop','--time','30',*ids,check=False,timeout=120).returncode==0

def wait_tick(seconds):
 deadline=time.monotonic()+seconds
 while not SHUTDOWN and time.monotonic()<deadline:time.sleep(min(.2,max(0,deadline-time.monotonic())))
def shutdown(signum,frame):
 global SHUTDOWN
 SHUTDOWN=True

def supervise(lock):
 if not os.environ.get('INVOCATION_ID') or os.environ.get('DELL_MOUNT_GATED')!='1' or not os.environ.get('NOTIFY_SOCKET'):raise Failure('systemd-invocation-required')
 outcome=1;began=False;failure={}
 try:
  guest_guard();storage_guard(lock);verify_files_and_images(lock);check_config(lock)
  existing=scan()
  if set(existing)-EXPECTED:raise Failure('unexpected-prestart-container')
  if SHUTDOWN:return 0
  began=True;state('starting',ready=False,expected_services=11);deadline=time.monotonic()+550
  run(compose(['up','-d','--no-build','--pull','never']),timeout=240)
  while not SHUTDOWN:
   storage_guard(lock)
   if validate_frame(scan(),lock,starting=True):break
   if time.monotonic()>=deadline:raise Failure('startup-readiness-deadline')
   wait_tick(5)
  if SHUTDOWN:raise StopRequested()
  notify('READY=1\nSTATUS=Penpot 11 of 11 healthy; mount and image contracts verified')
  state('ready',ready=True,healthy_services=11);monitor=Monitor();last_static=time.monotonic()
  while not SHUTDOWN:
   wait_tick(5)
   if SHUTDOWN:break
   storage_guard(lock);monitor.update(validate_frame(scan(),lock))
   if time.monotonic()-last_static>=60:verify_files_and_images(lock);last_static=time.monotonic()
   state('ready' if monitor.consecutive_bad==0 else 'degraded',ready=monitor.consecutive_bad==0,consecutive_bad=monitor.consecutive_bad)
  outcome=0
 except StopRequested:
  outcome=0
 except Exception as error:
  failure={'error_category':type(error).__name__,'reason':str(error) if isinstance(error,Failure) else 'details-suppressed'}
  state('failed',ready=False,**failure)
 finally:
  if began:
   stopped=stop_group(lock)
   if not stopped:outcome=1
   state('stopped' if stopped and outcome==0 else 'failed-stopped',ready=False,group_stopped=stopped,**failure)
 return outcome

def main():
 p=argparse.ArgumentParser();p.add_argument('action',choices=['check','supervise','stop']);args=p.parse_args();guest_guard();lock=load_lock()
 if args.action=='check':storage_guard(lock);verify_files_and_images(lock);check_config(lock);print(json.dumps({'status':'checked-not-started','expected_services':11,'credentials_emitted':False}));return 0
 if args.action=='stop':return 0 if stop_group(lock) else 1
 fd=os.open('/run/lock/dell-penpot-supervision.lock',os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW,0o600)
 try:
  if os.fstat(fd).st_uid!=0 or os.fstat(fd).st_mode&0o022:raise Failure('unsafe-supervisor-lock')
  fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB);signal.signal(signal.SIGTERM,shutdown);signal.signal(signal.SIGINT,shutdown)
  return supervise(lock)
 finally:os.close(fd)
if __name__=='__main__':
 try:sys.exit(main())
 except Exception as error:
  print(json.dumps({'status':'failed','error_category':type(error).__name__,'details':'suppressed'}));sys.exit(1)
