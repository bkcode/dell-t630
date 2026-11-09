#!/usr/bin/python3
"""One isolated VM210 restore of a verified PVE-local Nacos backup; no source writes."""
import datetime as dt,fcntl,gzip,hashlib,json,os,re,socket,stat,subprocess,sys,time,uuid
from pathlib import Path
STATE=Path('/var/lib/dell-prod-db-restore')
BASE=Path('/mnt/pve/store/dell-artifacts/prod-db-backups')
BRIDGE='/usr/local/libexec/dell-prod-db-restore/qga-restore.pl'
IMAGE='sha256:a0f6c7786c75739bd76a37b4b85e0f47b7c5d5a17a094bdd522412fb464d5cbe'
RUN=re.compile('[0-9a-f]{32}\\Z')

def native(args,timeout=40):
 p=subprocess.run(args,capture_output=True,text=True,timeout=timeout)
 if p.returncode:raise RuntimeError('fixed drill step failed; details remain private')
 return p.stdout

def secure(p,mode):
 assert p.is_absolute()and '..'not in p.parts
 for a in [*reversed(p.parents),p]:
  s=a.lstat();assert not stat.S_ISLNK(s.st_mode)and s.st_uid==0 and not s.st_mode&0o022
 assert stat.S_IMODE(p.stat().st_mode)==mode
 return p

def load(p):
 secure(p,0o600);assert stat.S_ISREG(p.stat().st_mode)and p.stat().st_size<65536 and p.stat().st_nlink==1
 return json.loads(p.read_text())

def sha(p):
 with p.open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()

def atom(p,d):
 assert not p.exists()and not p.is_symlink();fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
 with os.fdopen(fd,'w')as f:json.dump(d,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())

def main():
 os.umask(0o077);assert os.geteuid()==0 and socket.gethostname()=='pve'and Path('/etc/pve').is_dir();secure(STATE,0o700);secure(BASE,0o700)
 fd=os.open(STATE/'drill.lock',os.O_WRONLY|os.O_CREAT|os.O_NOFOLLOW,0o600)
 with os.fdopen(fd,'w')as lock:
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  fs=json.loads(native(['findmnt','-J','--mountpoint','/mnt/pve/store','-o','TARGET,UUID']))['filesystems'];assert len(fs)==1 and fs[0]['uuid']=='75e5b438-5ff3-4139-83d6-b6a6847aedac'
  props=native(['systemctl','show','dell-prod-db-backup.service','--property=ActiveState']).strip();assert props=='ActiveState=inactive'
  timer_before=native(['systemctl','show','dell-prod-db-backup.timer','--property=ActiveState,UnitFileState,NextElapseUSecRealtime'])
  assert 'ActiveState=active'in timer_before and 'UnitFileState=enabled'in timer_before
  receipt=load(Path('/var/lib/dell-prod-db-backup/last-success.json'));source=receipt['run_id'];assert RUN.fullmatch(source)and receipt['status']=='verified'and receipt['databases']==['nacos_prod']
  parent=secure(BASE/source,0o700);archive=secure(parent/'mysql.sql.gz',0o600);m=load(parent/'manifest.json');assert m['status']=='complete'and m['databases']==['nacos_prod']and m['table_counts']=={'nacos_prod':12}
  assert stat.S_ISREG(archive.stat().st_mode)and archive.stat().st_nlink==1 and archive.stat().st_size>0
  digest=sha(archive);assert digest==receipt['archive_sha256']==m['sha256']and archive.stat().st_size==receipt['archive_bytes']==m['compressed_bytes']<=1073741824
  length=0
  with gzip.open(archive,'rb')as f:
   while b:=f.read(1048576):length+=len(b);assert length<=64*1024**2
  run=uuid.uuid4().hex;work=STATE/run;work.mkdir(mode=0o700)
  expected={'version':1,'run_id':run,'source_run_id':source,'archive_bytes':archive.stat().st_size,'archive_sha256':digest,'image_id':IMAGE,'databases':['nacos_prod'],'table_counts':{'nacos_prod':12}}
  atom(work/'expected.json',expected);started=dt.datetime.now(dt.timezone.utc).isoformat();clock=time.monotonic();prepared=False;error=None;cleanup=True
  try:
   prepared=True;native(['perl',BRIDGE,'prepare',run],timeout=60)
   native(['perl',BRIDGE,'write-expected',run],timeout=120);native(['perl',BRIDGE,'write-archive',run,source],timeout=950)
   native(['perl',BRIDGE,'restore',run],timeout=1050)
  except Exception as e:error=type(e).__name__
  finally:
   if prepared:
    try:native(['perl',BRIDGE,'cleanup',run],timeout=120)
    except Exception:cleanup=False
  report=None
  if prepared:
   try:native(['perl',BRIDGE,'read-report',run],timeout=90);report=load(work/'guest-report.json')
   except Exception:error=error or 'ReportUnavailable'
  source_unchanged=sha(archive)==digest and archive.stat().st_size==expected['archive_bytes']
  timer_after=native(['systemctl','show','dell-prod-db-backup.timer','--property=ActiveState,UnitFileState,NextElapseUSecRealtime'])
  result={'version':1,'run_id':run,'source_run_id':source,'started_at':started,'finished_at':dt.datetime.now(dt.timezone.utc).isoformat(),'elapsed_seconds':round(time.monotonic()-clock,3),'target_vmid':210,'source_vmid':200,'source_archive_bytes':expected['archive_bytes'],'source_backup_SHA_unchanged':source_unchanged,'backup_timer_unchanged':timer_after==timer_before,'cleanup_command_succeeded':cleanup,'error_type':error,'guest_report':report,'SQL_or_credentials_exported_to_Mac':False,'production_import_performed':False,'business_RPO_RTO_verified':False}
  # Guest report is sanitized by the reviewed target worker. Do not print its private input metadata.
  passed = (not error and cleanup and source_unchanged and timer_after == timer_before
            and report and report.get('status') == 'passed'
            and report.get('cleanup_failed') is False
            and report.get('source_containers_unchanged') is True
            and report.get('restart_persistence_verified') is True
            and report.get('row_digests_match') is True
            and report.get('full_table_DDL_match') is True
            and report.get('table_count') == 12)
  result['status'] = 'passed' if passed else 'failed'
  atom(work/'host-result.json',result)
  public={k:v for k,v in result.items()if k!='guest_report'};public['guest_report']=report
  print(json.dumps(public));raise SystemExit(result['status']!='passed')
if __name__=='__main__':main()
