#!/usr/bin/env python3
"""Prepared full-scope local backup tools. No export, credentials archive or CF support."""
import argparse,datetime,gzip,hashlib,importlib.util,json,os,re,shlex,shutil,socket,subprocess,sys,threading,time,uuid
from pathlib import Path
sys.dont_write_bytecode=True
HOSTS={'data-prod-db':'prod-db','data-prod-infra':'prod-infra'}

def context():
 host=socket.gethostname().split('.')[0]
 if os.geteuid()!=0 or host not in HOSTS or Path('/etc/pve').exists():raise RuntimeError('full data backup restricted to assigned200/201 guests')
 bundle=Path('/opt/dell/data')/HOSTS[host]
 def load(name,path):
  s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
 a=load('backup_acceptance',bundle/'scripts/acceptance.py');c=a.m.cfg();a.m.preflight(c)
 return bundle,a,c

def private(path,data):path.write_bytes(data);path.chmod(0o600)
def digest(path):
 with path.open('rb') as file:return hashlib.file_digest(file,'sha256').hexdigest()

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('component',choices=['mysql','nacos','redis','rabbit-topology']);p.add_argument('--database',action='append',default=[]);p.add_argument('--execute-local-backup',action='store_true');p.add_argument('--ack-sensitive-local-output',action='store_true');p.add_argument('--confirm-no-ddl',action='store_true');p.add_argument('--confirm-redis-fork-headroom',action='store_true');p.add_argument('--confirm-stable-topology',action='store_true');args=p.parse_args()
 if not args.execute_local_backup or not args.ack_sensitive_local_output:raise RuntimeError('explicit local-backup intent required; flags do not replace approval policy')
 os.umask(0o077);bundle,a,c=context();role=c['ROLE']
 if (args.component in ('mysql','nacos'))!=(role=='prod-db'):raise RuntimeError('component not owned by this guest')
 nonce=uuid.uuid4().hex;parent=Path(c['DATA_MOUNTPOINT'])/'_app_backups'
 if shutil.disk_usage(c['DATA_MOUNTPOINT']).free<2*1024**3:raise RuntimeError('at least2GiB staging safety headroom required')
 if parent.resolve(strict=False)!=parent:raise RuntimeError('backup directory symlink rejected')
 parent.mkdir(mode=0o700,exist_ok=True);out=parent/nonce;out.mkdir(mode=0o700,exist_ok=False)
 manifest={'format':'dell-app-backup-v1','component':args.component,'role':role,'created_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'sensitive':True,'exported':False,'cf_included':False,'credentials_files_included':False,'files':{},'coverage':None,'restored_or_RPO_validated':False}
 if args.component in ('mysql','nacos'):
  if not args.confirm_no_ddl:raise RuntimeError('DDL-free window confirmation required for InnoDB logical consistency')
  databases=[c['NACOS_DB_NAME']] if args.component=='nacos' else args.database
  if not databases or len(databases)>32 or any(not re.fullmatch('[A-Za-z0-9_]+',db) or db in ('mysql','sys','performance_schema','information_schema') for db in databases):raise RuntimeError('explicit non-system databases required')
  quoted=','.join("'"+x+"'" for x in databases)
  estimate=int(a.mysql(c,"SELECT COALESCE(SUM(data_length+index_length),0) FROM information_schema.tables WHERE table_schema IN ("+quoted+");")[1])
  if shutil.disk_usage(c['DATA_MOUNTPOINT']).free<estimate*3+512*1024**2:raise RuntimeError('insufficient conservative staging space; no backup started')
  sql="SELECT COUNT(*) FROM information_schema.tables WHERE table_schema IN ("+quoted+") AND table_type='BASE TABLE' AND engine<>'InnoDB';"
  if a.mysql(c,sql)[1]!='0':raise RuntimeError('non-InnoDB data cannot use this hot logical backup path')
  shell='export MYSQL_PWD="$(cat /run/secrets/mysql-root-password)"; exec mysqldump "$@"'
  command=['docker','--host','unix:///var/run/docker.sock','compose','--env-file',str(bundle/'.env'),'-f',str(bundle/'compose.yaml'),'exec','-T','mysql','sh','-c',shell,'dump','--single-transaction','--quick','--routines','--triggers','--events','--hex-blob','--no-tablespaces','--set-gtid-purged=OFF','--databases',*databases]
  target=out/'mysql.sql.gz'
  fd=os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
  with os.fdopen(fd,'wb') as raw:
   process=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
   expired=[]
   def abort():expired.append(True);process.kill()
   timer=threading.Timer(1800,abort);timer.start()
   try:
    with gzip.GzipFile(fileobj=raw,mode='wb') as zipped:
     while True:
      block=process.stdout.read(1024*1024)
      if not block:break
      zipped.write(block)
    code=process.wait(timeout=30)
   finally:timer.cancel()
   if expired:raise RuntimeError('dump client timed out; partial private output retained')
  if code:raise RuntimeError('logical dump failed; partial private output retained, no export')
  manifest.update(databases=databases,coverage='selected InnoDB logical snapshot; application/DDL window required; routine/event SQL retained; no global accounts outside selected DBs')
  if args.component=='nacos':manifest['coverage']='complete selected Nacos external-MySQL metadata DB snapshot, including config/users/roles/permissions; secret files retained separately in controlled vault'
  manifest['files'][target.name]=digest(target)
 elif args.component=='redis':
  if not args.confirm_redis_fork_headroom:raise RuntimeError('full RDB sync can fork; measured headroom acknowledgement required')
  client=a.Redis(c)
  try:
   info=client.call('INFO','persistence');memory=client.call('INFO','memory')
  finally:client.close()
  pinfo=dict(x.split(':',1) for x in info.splitlines() if ':' in x);minfo=dict(x.split(':',1) for x in memory.splitlines() if ':' in x)
  if pinfo.get('rdb_bgsave_in_progress')!='0' or pinfo.get('aof_rewrite_in_progress')!='0':raise RuntimeError('existing persistence operation busy')
  limits=json.loads(a.m.compose('config','--format','json'))['services']['redis']['mem_limit']
  if int(minfo['used_memory_rss'])*2+64*1024*1024>int(limits):raise RuntimeError('insufficient conservative COW headroom; use replica/approved maintenance plan')
  remote='/data/.dell-rdb-backup-'+nonce+'.rdb';shell='export REDISCLI_AUTH="$(cat /run/secrets/redis-password)"; redis-cli --no-auth-warning --rdb '+remote+' >/dev/null 2>/dev/null && cat '+remote
  target=out/'redis.rdb';fd=os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
  base=['docker','--host','unix:///var/run/docker.sock','compose','--env-file',str(bundle/'.env'),'-f',str(bundle/'compose.yaml'),'exec','-T','redis']
  try:
   with os.fdopen(fd,'wb') as file:result=subprocess.run(base+['sh','-c',shell],stdout=file,stderr=subprocess.PIPE,timeout=1800)
   if result.returncode:raise RuntimeError('RDB sync failed; partial private output retained')
  finally:subprocess.run(base+['rm','-f',remote],capture_output=True,timeout=30)
  manifest.update(coverage='Redis RDB point-in-time data only; ACL/password/config files are not included; fork latency/RPO not guaranteed');manifest['files'][target.name]=digest(target)
 else:
  if not args.confirm_stable_topology:raise RuntimeError('stable topology window confirmation required')
  definitions=a.Rabbit(c).api('GET','/api/definitions');target=out/'rabbit-definitions.json';private(target,json.dumps(definitions).encode());manifest['files'][target.name]=digest(target)
  manifest.update(coverage='Rabbit definitions/topology only; includes sensitive password hashes/possible runtime parameters; NO QUEUE MESSAGES or transactional message snapshot',messages_included=False)
 private(out/'manifest.json',json.dumps(manifest,indent=2).encode())
 print(json.dumps({'status':'local-sensitive-backup-created-not-exported','component':args.component,'private_directory':str(out),'coverage':manifest['coverage'],'files':sorted(manifest['files']),'RPO_RTO_verified':False,'cf_included':False}))

if __name__=='__main__':
 try:main()
 except Exception as error:raise SystemExit('APP BACKUP ERROR: '+str(error))
