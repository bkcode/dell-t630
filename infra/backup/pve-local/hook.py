#!/usr/bin/python3
"""Guarded native vzdump hook. Metadata only stdout; archives remain PVE-private."""
from __future__ import annotations
import datetime,fcntl,hashlib,json,os,re,shutil,socket,stat,subprocess,sys,uuid
from pathlib import Path
POLICY=Path('/etc/dell-local-backup/policy.json')
PHASES={'job-init','job-start','job-end','job-abort','backup-start','backup-end','backup-abort','log-end','pre-stop','pre-restart','post-restart'}
TASK_PHASES=PHASES-{'job-init','job-start','job-end','job-abort'}

def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def require(value,message):
 if not value:raise RuntimeError(message)
def safe_path(path, *, existing=True):
 p=Path(path);require(p.is_absolute() and '..' not in p.parts,'absolute owned path required')
 for i in range(2,len(p.parts)+1):require(not Path(*p.parts[:i]).is_symlink(),'symlink refused')
 if existing:require(p.exists() and p.resolve()==p,'existing exact path required')
 return p
def atom(path,value):
 safe_path(path.parent);require(not path.is_symlink(),'state symlink refused');tmp=path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp');fd=os.open(tmp,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
 with os.fdopen(fd,'w') as f:json.dump(value,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
 os.replace(tmp,path);path.chmod(0o600)
def run(*args,timeout=30):return subprocess.run(list(args),check=True,capture_output=True,text=True,timeout=timeout).stdout

def load_policy():
 require(os.geteuid()==0 and socket.gethostname().split('.')[0]=='pve' and Path('/etc/pve').is_dir(),'PVE root only')
 p=safe_path(POLICY);s=p.stat();require(s.st_uid==0 and stat.S_IMODE(s.st_mode)==0o600,'private root policy required')
 v=json.loads(p.read_text());require(v['allowed_vmids']==[100,190,200,201,210,221,230,240,250,260,270] and v['excluded_vmids']==[220],'exact approved VM set required')
 require(v['mode']=='snapshot' and v['storage_id']=='dell-local-backup','approved snapshot storage required')
 return v

def preflight(p,phase):
 mount=safe_path(p['mountpoint']);fs=json.loads(run('findmnt','-J','-T',str(mount),'-o','TARGET,SOURCE,FSTYPE,UUID'))['filesystems'];require(len(fs)==1 and fs[0]['target']==str(mount) and fs[0]['uuid']==p['filesystem_uuid'] and fs[0]['fstype']=='ext4','store mount UUID mismatch; no root-disk fallback')
 if phase=='job-init':
  conf=Path('/etc/vzdump.conf')
  require(not conf.exists() or not any(l.strip().startswith('mailto:') for l in conf.read_text().splitlines() if not l.lstrip().startswith('#')),'global backup recipients changed; review notification contract')
 temp=safe_path(p['tmpdir']);st=temp.stat();require(temp.is_dir() and st.st_uid==0 and stat.S_IMODE(st.st_mode)==0o711,'native unprivileged-LXC staging parent must be root0711')
 for key in ['backup_root','dumpdir','state_dir']:
  d=safe_path(p[key]);s=d.stat();require(d.is_dir() and s.st_uid==0 and stat.S_IMODE(s.st_mode)==0o700,'private directory mode/owner mismatch')
 require(os.environ.get('STOREID')==p['storage_id'],'wrong storage invocation')
 if os.environ.get('DUMPDIR'):require(safe_path(os.environ['DUMPDIR'])==Path(p['dumpdir']),'unexpected dump directory')
 if phase in ['job-init','job-start','backup-start']:
  need=p['minimum_free_bytes']
  if phase=='backup-start' and len(sys.argv)==4:
   vmid=int(sys.argv[3]);prior=[]
   for f in Path(p['dumpdir']).glob('vzdump-*-'+str(vmid)+'-*.zst'):
    if not f.is_symlink() and f.is_file():prior.append(f.stat().st_size)
   if prior:need+=2*max(prior)
  require(shutil.disk_usage(mount).free>=need,'insufficient safety headroom compared with previous archive size')

def owned_archive(p,path,vmid,kind=None):
 q=safe_path(path);require(q.parent==Path(p['dumpdir']),'archive outside private namespace')
 match=re.fullmatch(r'vzdump-(qemu|lxc)-(\d+)-\d{4}_\d{2}_\d{2}-\d{2}_\d{2}_\d{2}\.(vma|tar)\.zst',q.name)
 require(match and int(match[2])==vmid,'unexpected archive name')
 require((match[1]=='lxc' and match[3]=='tar' and vmid==100) or (match[1]=='qemu' and match[3]=='vma' and vmid!=100),'archive type mismatch')
 s=q.stat();require(stat.S_ISREG(s.st_mode) and s.st_uid==0 and s.st_nlink==1,'root regular single-link archive required');q.chmod(0o600);return q,match[3]

def verify_archive(path,kind,timeout):
 subprocess.run(['zstd','-q','-t',str(path)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=timeout)
 dec=subprocess.Popen(['zstd','-q','-d','-c',str(path)],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
 try:
  command=['vma','verify','-'] if kind=='vma' else ['tar','-t','-f','-']
  check=subprocess.run(command,stdin=dec.stdout,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=timeout);dec.stdout.close();require(check.returncode==0,'archive native verification failed');require(dec.wait(timeout=15)==0,'decompression stream failed')
 finally:
  if dec.poll() is None:dec.kill();dec.wait()
 with path.open('rb') as f:digest=hashlib.file_digest(f,'sha256').hexdigest()
 return {'archive':path.name,'bytes':path.stat().st_size,'sha256':digest,'zstd_verified':True,'native_archive_verified':True,'mode':'0600','checked_at':now()}

def main():
 os.umask(0o077);require(len(sys.argv)>=2 and sys.argv[1] in PHASES,'unknown phase');phase=sys.argv[1];p=load_policy();preflight(p,phase);vmid=None
 if phase in TASK_PHASES:
  require(len(sys.argv)==4 and sys.argv[2]=='snapshot','snapshot mode only; hook never stops guests');vmid=int(sys.argv[3]);require(vmid in p['allowed_vmids'] and vmid!=220,'unapproved guest; private publisher excluded')
  require(os.environ.get('VMTYPE')==('lxc' if vmid==100 else 'qemu'),'guest type mismatch')
 state=Path(p['state_dir']);lock=state/'hook.lock';require(not lock.is_symlink(),'lock symlink refused')
 with lock.open('a') as fd:
  os.chmod(lock,0o600);fcntl.flock(fd,fcntl.LOCK_EX);current=state/'current.json'
  if phase=='job-init':
   print(json.dumps({'component':'local-backup','phase':phase,'mount_and_privacy_guard':'passed'}));return
  if phase=='job-start':
   job=json.loads(run('pvesh','get','/cluster/backup/'+p['job_id'],'--output-format','json'))
   require(set(map(int,re.split(r'[,\s]+',job['vmid'].strip())))==set(p['allowed_vmids']) and job.get('mode')=='snapshot'
           and job.get('storage')==p['storage_id'] and job.get('script')=='/usr/local/libexec/dell-local-backup/hook.py'
           and job.get('notification-mode')=='legacy-sendmail' and not job.get('mailto') and job.get('tmpdir')==p['tmpdir'],'native job contract changed')
   ledger={'run_id':uuid.uuid4().hex,'started_at':now(),'status':'running','results':{},'allowed_vmids':p['allowed_vmids']};atom(current,ledger)
  else:
   require(current.is_file() and not current.is_symlink(),'job-start ledger required');ledger=json.loads(current.read_text())
   if phase=='backup-start':ledger['results'][str(vmid)]={'status':'running','started_at':now()}
   elif phase=='backup-end':
    q,kind=owned_archive(p,os.environ.get('TARGET',''),vmid)
    try:proof=verify_archive(q,kind,p['verification_timeout_seconds'])
    except Exception as e:
     ledger['results'][str(vmid)]={'status':'verification-failed','error_type':type(e).__name__,'finished_at':now()};atom(current,ledger);raise RuntimeError('archive verification failed; no contents emitted') from None
    ledger['results'][str(vmid)]={**proof,'status':'verified'}
   elif phase=='backup-abort':ledger['results'][str(vmid)]={'status':'backup-failed','finished_at':now()}
   elif phase=='log-end':
    value=os.environ.get('LOGFILE')
    if value:
     try:
      q=safe_path(value);require(q.parent==Path(p['dumpdir']) and q.name.startswith(('vzdump-qemu-'+str(vmid)+'-','vzdump-lxc-'+str(vmid)+'-')),'unexpected logfile');q.chmod(0o600)
     except Exception:
      ledger['log_permission_error']=True;atom(current,ledger);raise
   elif phase in ['pre-stop','pre-restart','post-restart']:
    # Native PVE calls these labels in snapshot mode too. Never stop or start an app here.
    pass
   elif phase in ['job-end','job-abort']:
    success=set(ledger['results'])==set(map(str,p['allowed_vmids'])) and all(v.get('status')=='verified' for v in ledger['results'].values()) and not ledger.get('log_permission_error') and phase=='job-end'
    ledger.update(status='verified' if success else 'failed',finished_at=now());atom(current,ledger);atom(state/(ledger['run_id']+'.json'),ledger)
    if success:atom(state/'last-success.json',ledger)
    else:atom(state/'last-failure.json',{'run_id':ledger['run_id'],'failed_at':now(),'statuses':{k:v['status'] for k,v in ledger['results'].items()}})
    require(success,'job incomplete or contains failures; see private ledger')
   atom(current,ledger)
 print(json.dumps({'component':'local-backup','phase':phase,'vmid':vmid,'status':ledger.get('status'),'archive_contents_emitted':False}))

if __name__=='__main__':
 try:main()
 except Exception as e:
  # Report metadata even when the store guard fails; never write to a missing store.
  try:
   if os.geteuid()==0 and socket.gethostname().split('.')[0]=='pve':
    state=safe_path('/var/lib/dell-local-backup');st=state.stat()
    if st.st_uid==0 and stat.S_IMODE(st.st_mode)==0o700:
     atom(state/'last-failure.json',{'failed_at':now(),'phase':sys.argv[1] if len(sys.argv)>1 else 'invalid','error_type':type(e).__name__})
  except Exception:pass
  print(json.dumps({'component':'local-backup','status':'guard-or-verification-failed','error_type':type(e).__name__}),file=sys.stderr);raise SystemExit(1)
