#!/usr/bin/env python3
"""Fixed VM250 Penpot supervisor. No source/identity/data mutation, builds or pulls."""
import argparse,fcntl,hashlib,json,os,platform,re,signal,socket,stat,subprocess,sys,time
from pathlib import Path
BASE=Path('/opt/dell/penpot');HERE=BASE/'runtime/health-supervision';LOCK=HERE/'deployment-lock.json'
D=['docker','--host','unix:///var/run/docker.sock'];STATE=Path('/run/dell-penpot-supervision-state.json')
EXPECTED={'penpot-'+x for x in ['frontend','backend','exporter','admin-console','dns','mcp','worker','import','postgres','valkey','mailpit']}
SHUTDOWN=False
class Failure(RuntimeError):pass
class StopRequested(Exception):pass


# Diagnostic retention only. No settings here change readiness or remediation.
EVIDENCE_DIR = Path('/var/lib/dell-penpot-supervision')
EVIDENCE_UID = 0
LEDGER_MAX_BYTES = 64 * 1024
LEDGER_MAX_RECORD_BYTES = 8 * 1024
LEDGER_NAMES = ('failures.jsonl', 'failures.jsonl.1', 'failures.jsonl.2')
FAILURE_CODES = frozenset(['DNS-init-reaper-required', 'DockerRootDir-symlink-rejected', 'assigned-IP-missing', 'assigned250-root-guest-only', 'clean-Git-ff1783e-required', 'compose-exact11-services-required', 'compose-locked-images-required', 'consecutive-health-failure', 'data-mount-UUID-mismatch', 'data-mount-missing', 'duplicate-service-container', 'existing-package-hash-changed', 'fixed-command-failed', 'fixed-contract-identity-rejected', 'image-ID-or-AMD64-lock-mismatch', 'local-Docker-socket-missing', 'local-Docker-storage-or-identity-mismatch', 'managed-container-stopped-or-OOM', 'required-service-missing', 'runtime-image-resource-restart-contract-changed', 'runtime-mount-contract-changed', 'startup-readiness-deadline', 'supervision-file-hash-changed', 'systemd-invocation-required', 'systemd-notify-socket-required', 'trusted-path-missing-or-symlink', 'trusted-root-ownership-required', 'unexpected-container-on-assigned-guest', 'unexpected-prestart-container', 'unexpected-service-container', 'unsafe-supervisor-lock'])
_STATUS_VALUES = {'created', 'restarting', 'running', 'removing', 'paused', 'exited', 'dead'}
_HEALTH_VALUES = {'healthy', 'unhealthy', 'starting'}


def _utc_now():
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())


def _failure_fields(error):
    category = type(error).__name__
    if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]{0,63}', category):
        category = 'Exception'
    reason = 'details-suppressed'
    if isinstance(error, Failure):
        # Do not invoke a custom __str__ or persist arbitrary exception arguments.
        arguments = error.args
        reason = (arguments[0] if len(arguments) == 1 and type(arguments[0]) is str
                  and arguments[0] in FAILURE_CODES else 'unrecognized-failure-code')
    return {'error_category': category, 'reason': reason}


def _safe_journal(value):
    try:
        print(json.dumps(value, sort_keys=True, separators=(',', ':')), file=sys.stderr, flush=True)
    except Exception:
        pass  # Diagnostics must never replace the original failure or stop path.


def _ledger_warning():
    _safe_journal({'event': 'penpot-supervisor-failure-ledger-unavailable',
                   'reason': 'failure-evidence-write-failed'})


def _safe_services(frame):
    available = type(frame) is dict
    services = {}
    failed = []
    for name in sorted(EXPECTED):
        row = frame.get(name) if available else None
        if type(row) is not dict:
            services[name] = {'running': False if available else None,
                              'status': 'missing' if available else None,
                              'health': None, 'oom': None, 'failing_streak': None}
            if available:
                failed.append(name)
            continue
        status = row.get('status')
        status = status if type(status) is str and status in _STATUS_VALUES else 'unknown'
        health = row.get('health')
        health = health if type(health) is str and health in _HEALTH_VALUES else None
        running = row.get('running') if type(row.get('running')) is bool else None
        oom = row.get('oom') if type(row.get('oom')) is bool else None
        streak = row.get('failing_streak')
        streak = streak if type(streak) is int and 0 <= streak <= 2**31 - 1 else None
        services[name] = {'running': running, 'status': status, 'health': health,
                          'oom': oom, 'failing_streak': streak}
        if (running is not True or status != 'running' or oom is True or health != 'healthy'
                or (name == 'penpot-dns' and row.get('init') is not True)):
            failed.append(name)
    return services, failed, available


def _checked_ledger_entry(directory, name):
    try:
        metadata = os.stat(name, dir_fd=directory, follow_symlinks=False)
    except FileNotFoundError:
        return None
    if (not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != EVIDENCE_UID
            or stat.S_IMODE(metadata.st_mode) != 0o600 or metadata.st_nlink != 1
            or not 0 <= metadata.st_size <= LEDGER_MAX_BYTES):
        raise ValueError('unsafe-evidence-file')
    return metadata


def _append_failure_record(event):
    body = (json.dumps(event, sort_keys=True, separators=(',', ':')) + '\n').encode()
    if len(body) > LEDGER_MAX_RECORD_BYTES or len(body) > LEDGER_MAX_BYTES:
        raise ValueError('failure-record-too-large')
    directory = EVIDENCE_DIR
    if not directory.is_absolute() or directory.resolve() != directory:
        raise ValueError('unsafe-evidence-directory')
    parent = os.open(directory.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    descriptor = None
    try:
        metadata = os.fstat(parent)
        if metadata.st_uid != EVIDENCE_UID or metadata.st_mode & 0o022:
            raise ValueError('unsafe-evidence-parent')
        try:
            os.mkdir(directory.name, mode=0o700, dir_fd=parent)
        except FileExistsError:
            pass
        descriptor = os.open(directory.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
        metadata = os.fstat(descriptor)
        if metadata.st_uid != EVIDENCE_UID or stat.S_IMODE(metadata.st_mode) != 0o700:
            raise ValueError('unsafe-evidence-directory')
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        existing = {name: _checked_ledger_entry(descriptor, name) for name in LEDGER_NAMES}
        current = existing[LEDGER_NAMES[0]]
        if current is not None and current.st_size + len(body) > LEDGER_MAX_BYTES:
            if existing[LEDGER_NAMES[2]] is not None:
                os.unlink(LEDGER_NAMES[2], dir_fd=descriptor)
            if existing[LEDGER_NAMES[1]] is not None:
                os.replace(LEDGER_NAMES[1], LEDGER_NAMES[2], src_dir_fd=descriptor, dst_dir_fd=descriptor)
            os.replace(LEDGER_NAMES[0], LEDGER_NAMES[1], src_dir_fd=descriptor, dst_dir_fd=descriptor)
            current = None
        flags = os.O_WRONLY | os.O_APPEND | os.O_NOFOLLOW
        if current is None:
            flags |= os.O_CREAT | os.O_EXCL
        ledger = os.open(LEDGER_NAMES[0], flags, 0o600, dir_fd=descriptor)
        try:
            if current is None:
                os.fchmod(ledger, 0o600)
            opened = os.fstat(ledger)
            if (not stat.S_ISREG(opened.st_mode) or opened.st_uid != EVIDENCE_UID
                    or stat.S_IMODE(opened.st_mode) != 0o600 or opened.st_nlink != 1
                    or not 0 <= opened.st_size <= LEDGER_MAX_BYTES
                    or opened.st_size + len(body) > LEDGER_MAX_BYTES
                    or (current is not None and (opened.st_ino, opened.st_dev) != (current.st_ino, current.st_dev))):
                raise ValueError('unsafe-evidence-file')
            original_size = opened.st_size
            try:
                remaining = memoryview(body)
                while remaining:
                    written = os.write(ledger, remaining)
                    if not written:
                        raise OSError('short-evidence-write')
                    remaining = remaining[written:]
            except Exception:
                try:
                    os.ftruncate(ledger, original_size)
                except Exception:
                    pass
                raise
            os.fsync(ledger)
        finally:
            os.close(ledger)
        os.fsync(descriptor)
    finally:
        if descriptor is not None:
            os.close(descriptor)
        os.close(parent)


def record_failure(error, frame=None, observed_at=None):
    fields = _failure_fields(error)
    if observed_at is not None and (type(observed_at) is not str or not re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z', observed_at)):
        observed_at = None
    services, failed, available = _safe_services(frame)
    # The observed frame was already collected for normal validation. Do not run
    # Docker again here or delay the existing stop path on another daemon read.
    event = {'event': 'penpot-supervisor-failure', 'time_utc': _utc_now(), **fields,
             'frame_available': available, 'frame_observed_at_utc': observed_at,
             'services': services, 'failed_services': failed}
    _safe_journal({key: event[key] for key in ('event', 'time_utc', 'error_category', 'reason', 'failed_services')})
    try:
        _append_failure_record(event)
    except Exception:
        _ledger_warning()


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
 if lock['services']['penpot-dns'].get('require_init') is not True:raise Failure('DNS-init-reaper-required')
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
 fmt='{"id":{{json .Id}},"name":{{json .Name}},"image":{{json .Image}},"status":{{json .State.Status}},"running":{{json .State.Running}},"oom":{{json .State.OOMKilled}},"health":{{if (index .State "Health")}}{{json .State.Health.Status}}{{else}}null{{end}},"failing_streak":{{if (index .State "Health")}}{{json .State.Health.FailingStreak}}{{else}}0{{end}},"init":{{json (index .HostConfig "Init")}},"pids":{{json .HostConfig.PidsLimit}},"memory":{{json .HostConfig.Memory}},"nano_cpus":{{json .HostConfig.NanoCpus}},"restart":{{json .HostConfig.RestartPolicy.Name}},"mounts":[{{range $i,$m:=.Mounts}}{{if $i}},{{end}}{"source":{{json $m.Source}},"destination":{{json $m.Destination}},"rw":{{json $m.RW}}}{{end}}]}'
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
  if name=='penpot-dns' and c.get('init') is not True:raise Failure('DNS-init-reaper-required')
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
 outcome=1;began=False;failure={};last_frame=None;last_frame_at=None
 try:
  guest_guard();storage_guard(lock);verify_files_and_images(lock);check_config(lock)
  existing=scan();last_frame=existing;last_frame_at=_utc_now()
  if set(existing)-EXPECTED:raise Failure('unexpected-prestart-container')
  if SHUTDOWN:return 0
  began=True;state('starting',ready=False,expected_services=11);deadline=time.monotonic()+550
  run(compose(['up','-d','--no-build','--pull','never']),timeout=240)
  while not SHUTDOWN:
   storage_guard(lock)
   current=scan();last_frame=current;last_frame_at=_utc_now()
   if validate_frame(current,lock,starting=True):break
   if time.monotonic()>=deadline:raise Failure('startup-readiness-deadline')
   wait_tick(5)
  if SHUTDOWN:raise StopRequested()
  notify('READY=1\nSTATUS=Penpot 11 of 11 healthy; mount and image contracts verified')
  state('ready',ready=True,healthy_services=11);monitor=Monitor();last_static=time.monotonic()
  while not SHUTDOWN:
   wait_tick(5)
   if SHUTDOWN:break
   storage_guard(lock);current=scan();last_frame=current;last_frame_at=_utc_now();monitor.update(validate_frame(current,lock))
   if time.monotonic()-last_static>=60:verify_files_and_images(lock);last_static=time.monotonic()
   state('ready' if monitor.consecutive_bad==0 else 'degraded',ready=monitor.consecutive_bad==0,consecutive_bad=monitor.consecutive_bad)
  outcome=0
 except StopRequested:
  outcome=0
 except Exception as error:
  failure=_failure_fields(error)
  try:record_failure(error,last_frame,last_frame_at)
  except Exception:_ledger_warning()
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
