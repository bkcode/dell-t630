#!/usr/bin/python3
"""PVE-local production DB-only backup. No VM snapshots or payload export."""
from __future__ import annotations
import datetime as dt,fcntl,gzip,hashlib,json,os,re,shutil,socket,stat,subprocess,sys,time,uuid
from pathlib import Path
from zoneinfo import ZoneInfo
POLICY=Path('/etc/dell-prod-db-backup/policy.json')
BRIDGE='/usr/local/libexec/dell-prod-db-backup/qga-bridge.pl'
STATUS=Path('/var/lib/dell-prod-db-backup/status.json')
RUN=re.compile(r'^[0-9a-f]{32}$')
FILES={'mysql.sql.gz','manifest.json','receipt.json'}

def now():return dt.datetime.now(dt.timezone.utc).isoformat()
def native(args,timeout=40):
 p=subprocess.run(args,capture_output=True,text=True,timeout=timeout)
 if p.returncode:raise RuntimeError('fixed native operation failed; private detail withheld')
 return p.stdout

def secure(p:Path,mode=None):
 assert p.is_absolute()and '..'not in p.parts
 for a in [*reversed(p.parents),p]:
  s=a.lstat();assert not stat.S_ISLNK(s.st_mode)and s.st_uid==0 and not s.st_mode&0o022
 if mode is not None:assert stat.S_IMODE(p.stat().st_mode)==mode
 return p

def load(p):
 secure(p,0o600);s=p.stat();assert stat.S_ISREG(s.st_mode)and s.st_nlink==1 and s.st_size<=65536
 def pairs(items):
  d={}
  for k,v in items:
   if k in d:raise ValueError('duplicate metadata key')
   d[k]=v
  return d
 return json.loads(p.read_text(),object_pairs_hook=pairs,parse_constant=lambda x:(_ for _ in()).throw(ValueError()))

def atomic(p,d):
 secure(p.parent,0o700);assert not p.is_symlink();tmp=p.with_name('.'+p.name+'.'+uuid.uuid4().hex)
 fd=os.open(tmp,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
 with os.fdopen(fd,'w')as f:json.dump(d,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
 os.replace(tmp,p)
 fd=os.open(p.parent,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
 try:os.fsync(fd)
 finally:os.close(fd)

def sha(p):
 with p.open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()

def retention_ids(runs,last=3,daily=7,weekly=4):
 rows=sorted(runs,key=lambda r:r['finished_at'],reverse=True);keep={r['run_id']for r in rows[:last]}
 for count,key in [(daily,lambda t:t.date().isoformat()),(weekly,lambda t:t.isocalendar()[:2])]:
  seen=set()
  for r in rows:
   t=dt.datetime.fromisoformat(r['finished_at']).astimezone(ZoneInfo('Asia/Shanghai'));k=key(t)
   if k in seen:continue
   if len(seen)>=count:break
   seen.add(k);keep.add(r['run_id'])
 return keep

def checked_run(p,expected_db):
 secure(p,0o700);assert RUN.fullmatch(p.name)and p.is_dir()
 assert {f.name for f in p.iterdir()}==FILES
 for f in p.iterdir():secure(f,0o600);s=f.stat();assert stat.S_ISREG(s.st_mode)and s.st_nlink==1
 r=load(p/'receipt.json');m=load(p/'manifest.json')
 assert r['run_id']==m['run_id']==p.name and r['status']=='verified'and m['databases']==expected_db
 assert r['archive_bytes']==(p/'mysql.sql.gz').stat().st_size and r['manifest_sha256']==sha(p/'manifest.json')
 assert r['archive_sha256']==m['sha256']==sha(p/'mysql.sql.gz')and m['status']=='complete'
 return r

def prune(base,p,current_run_id):
 candidates=[]
 # Unknown entries or partial runs are never deleted. Only owned verified successes count.
 for folder in base.iterdir():
  if not RUN.fullmatch(folder.name):continue
  candidates.append(checked_run(folder,p['databases']))
 keep=retention_ids(candidates,p['keep_last'],p['keep_daily'],p['keep_weekly']);keep.add(current_run_id);deleted=[]
 for r in candidates:
  if r['run_id']in keep:continue
  folder=base/r['run_id'];checked_run(folder,p['databases'])
  for name in sorted(FILES):(folder/name).unlink()
  folder.rmdir();deleted.append(r['run_id'])
 return len(deleted)

def main():
 os.umask(0o077);assert os.geteuid()==0 and socket.gethostname()=='pve'and Path('/etc/pve').is_dir()
 p=load(POLICY);assert p['vmid']==200 and p['databases']==['nacos_prod']and p['nacos_database']=='nacos_prod'
 assert p['backup_root']=='/mnt/pve/store/dell-artifacts/prod-db-backups'and p['state_dir']=='/var/lib/dell-prod-db-backup'
 assert p['schema_version']==1 and p['mountpoint']=='/mnt/pve/store'and p['filesystem_uuid']=='75e5b438-5ff3-4139-83d6-b6a6847aedac'
 assert all(type(p[k])is int and p[k]==v for k,v in {'keep_last':3,'keep_daily':7,'keep_weekly':4,'maximum_archive_bytes':1073741824,'minimum_free_bytes':107374182400}.items())
 assert p['schedule']=='03:30'and p['timezone']=='Asia/Shanghai'and p['whole_VM_backup']is False
 state=secure(Path(p['state_dir']),0o700);base=secure(Path(p['backup_root']),0o700)
 lockfd=os.open(state/'worker.lock',os.O_WRONLY|os.O_CREAT|os.O_NOFOLLOW,0o600)
 with os.fdopen(lockfd,'w')as lock:
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  prior=load(STATUS)if STATUS.exists()else{};runid=uuid.uuid4().hex
  status={'version':1,'source_vmid':200,'databases':p['databases'],'status':'running','run_id':runid,'started_at':now(),'last_success_timestamp':prior.get('last_success_timestamp',0),'last_run_success':prior.get('last_run_success',0),'archive_bytes':prior.get('archive_bytes',0)}
  atomic(STATUS,status)
  try:
   fs=json.loads(native(['findmnt','-J','-T',p['mountpoint'],'-o','TARGET,FSTYPE,UUID']))['filesystems'];assert len(fs)==1 and fs[0]['target']==p['mountpoint']and fs[0]['fstype']=='ext4'and fs[0]['uuid']==p['filesystem_uuid']
   assert shutil.disk_usage(p['mountpoint']).free>=p['minimum_free_bytes']+2*p['maximum_archive_bytes']
   assert not json.loads(native(['pvesh','get','/nodes/pve/tasks','--source','active','--typefilter','vzdump','--output-format','json']))
   old=json.loads(native(['pvesh','get','/cluster/backup/dell-local-nightly','--output-format','json']));assert old['enabled']==0
   partial=base/('.partial-'+runid);partial.mkdir(mode=0o700)
   native(['/usr/bin/perl',BRIDGE,'export',runid],timeout=2000)
   native(['/usr/bin/perl',BRIDGE,'pull',runid,'manifest.json'],timeout=90)
   m=load(partial/'manifest.json');assert m['status']=='complete'and m['run_id']==runid and m['databases']==p['databases']and m['nacos_database']==p['nacos_database']
   # Guest worker writes these proof fields only after a complete successful dump and CRC check.
   assert m['ddl_lock_held']is True and m['lock_released']is True and m['gzip_verified']is True
   assert type(m['compressed_bytes'])is int and 0<m['compressed_bytes']<=p['maximum_archive_bytes']and re.fullmatch('[0-9a-f]{64}',m['sha256'])
   native(['/usr/bin/perl',BRIDGE,'pull',runid,'mysql.sql.gz'],timeout=1900)
   archive=secure(partial/'mysql.sql.gz',0o600);assert archive.stat().st_size==m['compressed_bytes']and sha(archive)==m['sha256']
   tail=b'';expanded=0;verify_deadline=time.monotonic()+300
   with gzip.open(archive,'rb')as f:
    while b:=f.read(1048576):
     expanded+=len(b);assert expanded<=8*1024**3 and time.monotonic()<=verify_deadline,'bounded decompression validation exceeded'
     tail=(tail+b)[-4096:]
   assert b'-- Dump completed on' in tail,'logical dump completion footer absent'
   for f in [archive,partial/'manifest.json']:
    fd=os.open(f,os.O_RDONLY|os.O_NOFOLLOW)
    try:os.fsync(fd)
    finally:os.close(fd)
   finished=now();receipt={'format':'dell-prod-db-only-v1','status':'verified','run_id':runid,'started_at':status['started_at'],'finished_at':finished,'source_vmid':200,'databases':p['databases'],'archive_bytes':m['compressed_bytes'],'archive_sha256':m['sha256'],'manifest_sha256':sha(partial/'manifest.json'),'gzip_verified':True,'transport_SHA_verified':True,'restored':False,'whole_VM_backup':False}
   atomic(partial/'receipt.json',receipt);final=base/runid;assert not final.exists();os.rename(partial,final)
   fd=os.open(base,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
   try:os.fsync(fd)
   finally:os.close(fd)
   status.update(status='success',finished_at=finished,last_success_timestamp=dt.datetime.fromisoformat(finished).timestamp(),last_run_success=1,archive_bytes=m['compressed_bytes'],last_success_run_id=runid)
   atomic(state/'last-success.json',receipt)
   # A verified PVE copy precedes guest-spool removal and retention. Failure is still reported.
   native(['/usr/bin/perl',BRIDGE,'cleanup',runid],timeout=90)
   status['old_successes_pruned']=prune(base,p,runid);atomic(STATUS,status)
   print(json.dumps({'status':'production-DB-and-Nacos-backup-verified','run_id':runid,'archive_bytes':m['compressed_bytes'],'databases':p['databases'],'destination':str(final),'guest_spool_cleaned':True,'restored':False,'other_data_included':False}))
  except Exception as e:
   status.update(status='failed',finished_at=now(),last_run_success=0,error_type=type(e).__name__);atomic(STATUS,status)
   print(json.dumps({'status':'prod-db-backup-failed','error_type':type(e).__name__,'partial_private_files_preserved':True}),file=sys.stderr);raise SystemExit(1)
if __name__=='__main__':main()
