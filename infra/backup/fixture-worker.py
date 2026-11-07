#!/usr/bin/env python3
"""Only200/201: synthetic fixture logical backup and fully isolated restore checks."""
import argparse,base64,datetime,gzip,hashlib,importlib.util,json,os,re,shlex,shutil,socket,subprocess,sys,tarfile,time,uuid
from pathlib import Path
sys.dont_write_bytecode=True
ROLE_BY_HOST={'data-prod-db':'prod-db','data-prod-infra':'prod-infra'}
BUNDLE=None;manager=None;acceptance=None;config=None

def init():
 global BUNDLE,manager,acceptance,config
 host=socket.gethostname().split('.')[0]
 if host not in ROLE_BY_HOST or Path('/etc/pve').exists() or os.geteuid()!=0:raise RuntimeError('backup fixture scope is only assigned200/201 guests')
 role=ROLE_BY_HOST[host];BUNDLE=Path('/opt/dell/data')/role
 def load(name,path):
  s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
 manager=load('fixture_manager',BUNDLE/'scripts/manage.py');acceptance=load('fixture_acceptance',BUNDLE/'scripts/acceptance.py');config=manager.cfg();manager.preflight(config)
 if config['ROLE']!=role or config['ENVIRONMENT']!='prod' or config['NACOS_DB_NAME']!='nacos_prod':raise RuntimeError('data role/meta database mismatch')

class Redis:
 def __init__(self):
  self.sock=socket.create_connection((config['SERVICE_IP'],6379),timeout=10);self.file=self.sock.makefile('rb');self.call('AUTH',manager.read_secret('redis-password'))
 def read(self):
  kind=self.file.read(1);line=self.file.readline().rstrip(b'\r\n')
  if kind==b'-':raise RuntimeError('Redis backup command rejected')
  if kind==b'+':return line
  if kind==b':':return int(line)
  if kind==b'$':
   n=int(line)
   if n==-1:return None
   out=self.file.read(n)
   if len(out)!=n or self.file.read(2)!=b'\r\n':raise RuntimeError('Redis backup protocol truncated')
   return out
  if kind==b'*':return [self.read() for _ in range(int(line))]
  raise RuntimeError('unexpected Redis backup protocol')
 def call(self,*args):
  values=[a if isinstance(a,bytes) else str(a).encode() for a in args]
  self.sock.sendall(b'*'+str(len(values)).encode()+b'\r\n'+b''.join(b'$'+str(len(v)).encode()+b'\r\n'+v+b'\r\n' for v in values));return self.read()
 def close(self):self.file.close();self.sock.close()

def run(args,data=None,timeout=120,check=True):
 p=subprocess.run(args,input=data,capture_output=True,timeout=timeout)
 if check and p.returncode:raise RuntimeError('isolated backup tool failed; output suppressed')
 return p

def docker(*args,**kwargs):return run(['docker','--host','unix:///var/run/docker.sock',*args],**kwargs)

def write(path,data):
 if path.is_symlink():raise RuntimeError('backup file symlink rejected')
 path.write_bytes(data);path.chmod(0o600)

def workspace(nonce,create=False):
 if not re.fullmatch('[a-f0-9]{32}',nonce):raise RuntimeError('invalid fixture identifier')
 parent=Path(config['DATA_MOUNTPOINT'])/'_dell_app_backup_fixture'
 if parent.resolve(strict=False)!=parent:raise RuntimeError('backup parent symlink rejected')
 work=parent/nonce
 if work.resolve(strict=False)!=work:raise RuntimeError('backup work path symlink rejected')
 if create:
  parent.mkdir(mode=0o700,exist_ok=True);work.mkdir(mode=0o700,exist_ok=False)
 if not work.is_dir():raise RuntimeError('fixture work directory missing')
 return work

def state_for(nonce):
 work=workspace(nonce);s=json.loads((work/'state.json').read_text())
 if s['nonce']!=nonce or s['role']!=config['ROLE'] or s['kind']!='synthetic-backup-fixtures-only':raise RuntimeError('fixture state identity rejected')
 expected={'payload':'backup-fixture:'+nonce,'database':'dell_backup_fixture_'+nonce[:12],'nacos_data_id':'dell_backup_fixture_'+nonce,'nacos_group':'DELL_BACKUP_VERIFY','redis_key':'dell:backup-fixture:'+nonce,'rabbit_vhost':'/dell-backup-fixture-'+nonce[:12],'rabbit_queue':'dell.backup.fixture'}
 if any(s.get(k)!=v for k,v in expected.items()) or s.get('contains_credentials') or s.get('contains_business_data'):raise RuntimeError('fixture object derivation/synthetic scope mismatch')
 return work,s

def mysql(sql):return acceptance.mysql(config,sql)[1]

def prepare(nonce):
 work=workspace(nonce,True);artifact=work/'artifact';artifact.mkdir(mode=0o700)
 s={'kind':'synthetic-backup-fixtures-only','role':config['ROLE'],'nonce':nonce,'payload':'backup-fixture:'+nonce,'database':'dell_backup_fixture_'+nonce[:12],'nacos_data_id':'dell_backup_fixture_'+nonce,'nacos_group':'DELL_BACKUP_VERIFY','redis_key':'dell:backup-fixture:'+nonce,'rabbit_vhost':'/dell-backup-fixture-'+nonce[:12],'rabbit_queue':'dell.backup.fixture','contains_credentials':False,'contains_business_data':False}
 write(work/'state.json',json.dumps(s).encode())
 if config['ROLE']=='prod-db':
  mysql('CREATE DATABASE `'+s['database']+'`; CREATE TABLE `'+s['database']+'`.fixture (id VARCHAR(64) PRIMARY KEY,payload VARCHAR(128)); INSERT INTO `'+s['database']+'`.fixture VALUES (\''+nonce+'\',\''+s['payload']+'\');')
 else:
  r=Redis()
  try:r.call('SET',s['redis_key'],s['payload'])
  finally:r.close()
  n=acceptance.nacos(config)
  if n.request('POST','/v1/cs/configs',{'tenant':config['NACOS_NAMESPACE_ID'],'dataId':s['nacos_data_id'],'group':s['nacos_group'],'content':s['payload'],'type':'text'}) is not True:raise RuntimeError('Nacos synthetic fixture create failed')
  rabbit=acceptance.Rabbit(config);v=__import__('urllib.parse',fromlist=['quote']).quote(s['rabbit_vhost'],safe='')
  rabbit.api('PUT','/api/vhosts/'+v,{})
  rabbit.api('PUT','/api/queues/'+v+'/'+s['rabbit_queue'],{'durable':True,'auto_delete':False,'arguments':{'x-message-ttl':3600000}})
 return {'fixture_prepared':True,'nonce':nonce,'role':config['ROLE'],'real_messages_published':0}

def dump(args):
 shell='export MYSQL_PWD="$(cat /run/secrets/mysql-root-password)"; exec mysqldump "$@"'
 base=['docker','--host','unix:///var/run/docker.sock','compose','--env-file',str(BUNDLE/'.env'),'-f',str(BUNDLE/'compose.yaml'),'exec','-T','mysql','sh','-c',shell,'dump']
 return run(base+['--single-transaction','--quick','--no-tablespaces','--set-gtid-purged=OFF','--skip-comments',*args],timeout=120).stdout

def snapshot(nonce):
 work,s=state_for(nonce);artifact=work/'artifact';files={}
 if config['ROLE']=='prod-db':
  found=mysql('SELECT payload FROM `'+s['database']+'`.fixture WHERE id=\''+nonce+'\';')
  if found!=s['payload']:raise RuntimeError('synthetic MySQL source value mismatch')
  raw=dump(['--databases',s['database']]);write(artifact/'mysql-fixture.sql',raw);files['mysql-fixture.sql']=hashlib.sha256(raw).hexdigest()
  where="tenant_id='"+config['NACOS_NAMESPACE_ID']+"' AND data_id='"+s['nacos_data_id']+"' AND group_id='"+s['nacos_group']+"'"
  value=mysql('SELECT content FROM `'+config['NACOS_DB_NAME']+'`.config_info WHERE '+where+';')
  if value!=s['payload']:raise RuntimeError('Nacos synthetic config row mismatch; no broader export permitted')
  raw=dump(['--no-create-info','--skip-add-drop-table','--skip-triggers','--where='+where,config['NACOS_DB_NAME'],'config_info'])
  write(artifact/'nacos-filtered-config.sql',raw);files['nacos-filtered-config.sql']=hashlib.sha256(raw).hexdigest()
 else:
  # Only own synthetic key; this does not trigger a full Redis snapshot/fork.
  r=Redis()
  try:
   if r.call('GET',s['redis_key'])!=s['payload'].encode():raise RuntimeError('synthetic Redis source mismatch')
   data,ttl=r.call('EVAL_RO',"return {redis.call('DUMP',KEYS[1]),redis.call('PTTL',KEYS[1])}",1,s['redis_key'])
   if ttl!=-1:raise RuntimeError('fixture key unexpectedly expires; no broader export permitted')
  finally:r.close()
  write(artifact/'redis-fixture.dump',data);files['redis-fixture.dump']=hashlib.sha256(data).hexdigest();s['redis_ttl_ms']=ttl
  rabbit=acceptance.Rabbit(config);v=__import__('urllib.parse',fromlist=['quote']).quote(s['rabbit_vhost'],safe='')
  q=rabbit.api('GET','/api/queues/'+v+'/'+s['rabbit_queue'])
  if not q.get('durable') or q.get('messages',0)!=0:raise RuntimeError('Rabbit fixture must be durable and empty')
  # Construct a minimal verified fixture topology: no users, permissions, parameters or messages.
  topology={'vhosts':[{'name':s['rabbit_vhost']}],'queues':[{'name':s['rabbit_queue'],'vhost':s['rabbit_vhost'],'durable':True,'auto_delete':False,'arguments':{'x-message-ttl':3600000}}],'exchanges':[],'bindings':[]}
  raw=json.dumps(topology).encode();write(artifact/'rabbit-fixture-definitions.json',raw);files['rabbit-fixture-definitions.json']=hashlib.sha256(raw).hexdigest()
 # Manifest contains only known synthetic payload/identifiers, never source credentials.
 manifest={**s,'files':files,'coverage':'MySQL synthetic fixture + one Nacos config_info row only (not complete config backup)' if config['ROLE']=='prod-db' else 'Redis single-key serialized value + empty Rabbit fixture topology only','nacos_fixture_on_201':config['ROLE']=='prod-infra','isolated_restore_verified':False}
 write(artifact/'manifest.json',json.dumps(manifest,indent=2).encode())
 return {'snapshot_prepared':True,'role':config['ROLE'],'files':sorted(files),'scope':manifest['coverage'],'contains_credentials':False}

def temp_container(image,name,data_dir,user,command,env=None,secret=None,memory='512m',socket_dir=None):
 if any(data_dir.iterdir()):raise RuntimeError('isolated restore data directory must be empty')
 uid,gid=user;os.chown(data_dir,uid,gid)
 args=['run','--detach','--name',name,'--pull=never','--platform=linux/amd64','--network=none','--read-only','--user',str(uid)+':'+str(gid),'--cap-drop=ALL','--security-opt=no-new-privileges:true','--cpus=1','--memory='+memory,'--memory-swap='+memory,'--pids-limit=256','--tmpfs','/tmp:size=32m,mode=1777','--mount','type=bind,src='+str(data_dir)+',dst='+('/var/lib/mysql' if socket_dir else '/var/lib/rabbitmq' if 'rabbitmq' in image else '/data')]
 if socket_dir:args+=['--tmpfs','/var/run/mysqld:size=16m,uid='+str(uid)+',gid='+str(gid)+',mode=0755']
 if 'rabbitmq' in image:args+=['--hostname','localhost']
 for key,value in (env or {}).items():args+=['--env',key+'='+value]
 if secret:
  source,target=secret;args+=['--mount','type=bind,src='+str(source)+',dst='+target+',readonly']
 args+=[image,*command]
 cid=docker(*args).stdout.decode().strip()
 if not re.fullmatch('[a-f0-9]{64}',cid):raise RuntimeError('isolated container identity missing')
 return cid

def temp_mysql_query(cid,sql,database=None):
 shell='export MYSQL_PWD="$(cat /run/secrets/verify-password)"; exec mysql --user=root --protocol=socket --batch --skip-column-names "$@"'
 args=['exec','-i',cid,'sh','-c',shell,'mysql']+(['--database='+database] if database else [])
 return docker(*args,data=sql if isinstance(sql,bytes) else sql.encode(),timeout=120).stdout.decode().strip()

def verify(nonce):
 work,s=state_for(nonce);artifact=work/'artifact';manifest=json.loads((artifact/'manifest.json').read_text())
 for name,sha in manifest['files'].items():
  if Path(name).name!=name or hashlib.sha256((artifact/name).read_bytes()).hexdigest()!=sha:raise RuntimeError('artifact checksum/path mismatch')
 manifest['isolated_restore_verified']=False;manifest['temporary_containers_removed']=False;write(artifact/'manifest.json',json.dumps(manifest,indent=2).encode())
 scratch=work/('verify-'+uuid.uuid4().hex[:8]);scratch.mkdir(mode=0o700,exist_ok=False);containers=[];result={}
 images=json.loads((BUNDLE/'images.lock.json').read_text())['images']
 try:
  if config['ROLE']=='prod-db':
   uid=manager.image_uid(images['mysql']['reference'],'mysql');pw=scratch/'mysql-password';write(pw,uuid.uuid4().hex.encode());os.chown(pw,*uid)
   data=scratch/'mysql-data';data.mkdir(mode=0o700)
   cid=temp_container(images['mysql']['reference'],'dell-app-verify-mysql-'+nonce[:12],data,uid,['--innodb-buffer-pool-size=128M','--performance-schema=OFF','--max-connections=10','--skip-log-bin','--event-scheduler=OFF','--local-infile=0','--secure-file-priv=NULL','--skip-networking'],env={'MYSQL_ROOT_PASSWORD_FILE':'/run/secrets/verify-password'},secret=(pw,'/run/secrets/verify-password'),memory='768m',socket_dir=True);containers.append(cid)
   for _ in range(90):
    try:temp_mysql_query(cid,'SELECT 1;');break
    except RuntimeError:time.sleep(1)
   else:raise RuntimeError('isolated MySQL readiness deadline')
   temp_mysql_query(cid,(artifact/'mysql-fixture.sql').read_bytes())
   value=temp_mysql_query(cid,'SELECT payload FROM `'+s['database']+'`.fixture WHERE id=\''+nonce+'\';')
   if value!=s['payload']:raise RuntimeError('isolated MySQL fixture restore mismatch')
   temp_mysql_query(cid,'CREATE DATABASE verify_nacos_meta;')
   temp_mysql_query(cid,(BUNDLE/'vendor/nacos-mysql-schema-2.4.3.sql').read_bytes(),database='verify_nacos_meta')
   temp_mysql_query(cid,(artifact/'nacos-filtered-config.sql').read_bytes(),database='verify_nacos_meta')
   row=temp_mysql_query(cid,"SELECT content FROM config_info WHERE data_id='"+s['nacos_data_id']+"' AND group_id='"+s['nacos_group']+"';",database='verify_nacos_meta')
   if row!=s['payload']:raise RuntimeError('isolated Nacos filtered row restore mismatch')
   result.update(mysql_isolated_restore=True,nacos_filtered_row_isolated_restore=True,complete_nacos_backup=False)
  else:
   uid=manager.image_uid(images['redis']['reference'],'redis');password=uuid.uuid4().hex;conf=scratch/'redis.conf';write(conf,('bind 127.0.0.1\nport 6379\ndir /data\nsave ""\nappendonly no\nrequirepass '+password+'\n').encode());os.chown(conf,*uid)
   data=scratch/'redis-data';data.mkdir(mode=0o700)
   cid=temp_container(images['redis']['reference'],'dell-app-verify-redis-'+nonce[:12],data,uid,['redis-server','/etc/redis/verify.conf'],secret=(conf,'/etc/redis/verify.conf'),memory='128m');containers.append(cid)
   shell='export REDISCLI_AUTH="$(sed -n \'s/^requirepass //p\' /etc/redis/verify.conf)"; exec redis-cli --no-auth-warning "$@"'
   for _ in range(30):
    p=docker('exec',cid,'sh','-c',shell,'redis-cli','PING',check=False)
    if p.returncode==0 and p.stdout.strip()==b'PONG':break
    time.sleep(1)
   else:raise RuntimeError('isolated Redis readiness deadline')
   restored=docker('exec','-i',cid,'sh','-c',shell,'redis-cli','-x','RESTORE',s['redis_key'],'0',data=(artifact/'redis-fixture.dump').read_bytes()).stdout.strip()
   value=docker('exec',cid,'sh','-c',shell,'redis-cli','--raw','GET',s['redis_key']).stdout.strip()
   if restored!=b'OK' or value!=s['payload'].encode():raise RuntimeError('isolated Redis restore mismatch')
   result['redis_isolated_restore']=True
   docker('rm','--force',cid);containers.remove(cid)
   uid=manager.image_uid(images['rabbitmq']['reference'],'rabbitmq');data=scratch/'rabbit-data';data.mkdir(mode=0o700)
   cid=temp_container(images['rabbitmq']['reference'],'dell-app-verify-rabbit-'+nonce[:12],data,uid,[],env={'RABBITMQ_NODENAME':'rabbit@localhost','RABBITMQ_SERVER_ADDITIONAL_ERL_ARGS':'+S 2:2'},memory='512m');containers.append(cid)
   for _ in range(90):
    p=docker('exec',cid,'rabbitmq-diagnostics','-q','check_running',check=False)
    if p.returncode==0:break
    time.sleep(1)
   else:raise RuntimeError('isolated Rabbit readiness deadline')
   shell='umask 077; cat >/tmp/fixture-definitions.json; exec rabbitmqctl import_definitions /tmp/fixture-definitions.json'
   docker('exec','-i',cid,'sh','-c',shell,data=(artifact/'rabbit-fixture-definitions.json').read_bytes(),timeout=90)
   p=docker('exec',cid,'rabbitmqctl','list_queues','--vhost',s['rabbit_vhost'],'name','durable','messages','--formatter','json')
   rows=json.loads(p.stdout)
   if not any(x.get('name')==s['rabbit_queue'] and x.get('durable') is True and x.get('messages')==0 for x in rows):raise RuntimeError('isolated Rabbit fixture topology mismatch')
   result['rabbit_empty_topology_isolated_restore']=True
  manifest['isolated_restore_verified']=True;manifest['verification']=result;write(artifact/'manifest.json',json.dumps(manifest,indent=2).encode())
  return {'role':config['ROLE'],'verified':result,'network':'none','ports_published':False,'source_volumes_mounted':False,'credentials_exported':False,'real_messages_sent':0}
 finally:
  failed=[]
  for cid in containers:
   if docker('rm','--force',cid,check=False).returncode:failed.append(cid)
  if failed:
   write(work/'verify-cleanup-pending.json',json.dumps({'own_container_ids':failed,'scratch':str(scratch)}).encode())
   raise RuntimeError('own isolated verifier cleanup incomplete; scratch retained')
  # Only this newly created owned scratch; artifacts are retained separately.
  if scratch.parent==work and scratch.name.startswith('verify-') and scratch.resolve()==scratch:shutil.rmtree(scratch)
  if manifest.get('isolated_restore_verified'):
   manifest['temporary_containers_removed']=True;write(artifact/'manifest.json',json.dumps(manifest,indent=2).encode())

def cleanup(nonce):
 work,s=state_for(nonce)
 if config['ROLE']=='prod-db':mysql('DROP DATABASE IF EXISTS `'+s['database']+'`;')
 else:
  r=Redis()
  try:r.call('DEL',s['redis_key'])
  finally:r.close()
  params=__import__('urllib.parse',fromlist=['urlencode']).urlencode({'tenant':config['NACOS_NAMESPACE_ID'],'dataId':s['nacos_data_id'],'group':s['nacos_group']})
  acceptance.nacos(config).request('DELETE','/v1/cs/configs?'+params)
  v=__import__('urllib.parse',fromlist=['quote']).quote(s['rabbit_vhost'],safe='');acceptance.Rabbit(config).api('DELETE','/api/vhosts/'+v,missing=True)
 return {'source_owned_fixtures_cleaned':True,'source_services_stopped':False,'business_data_modified':False}

def export(nonce):
 work,s=state_for(nonce);artifact=work/'artifact';manifest=json.loads((artifact/'manifest.json').read_text())
 if manifest['kind']!='synthetic-backup-fixtures-only' or not manifest['isolated_restore_verified'] or not manifest.get('temporary_containers_removed') or manifest['contains_credentials'] or manifest['contains_business_data']:raise RuntimeError('only verified pure synthetic artifacts may stream to Mac')
 names={'manifest.json',*manifest['files']}
 if names-{'manifest.json','mysql-fixture.sql','nacos-filtered-config.sql','redis-fixture.dump','rabbit-fixture-definitions.json'}:raise RuntimeError('artifact export whitelist rejected')
 with tarfile.open(fileobj=sys.stdout.buffer,mode='w|') as archive:
  for name in sorted(names):
   path=artifact/name
   if path.is_symlink() or not path.is_file():raise RuntimeError('artifact member is not a regular file')
   archive.add(path,arcname=name,recursive=False)

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('phase',choices=['prepare','snapshot','verify','cleanup','export']);p.add_argument('--work-id',required=True);args=p.parse_args();os.umask(0o077);init()
 if args.phase=='export':export(args.work_id);return
 result=globals()[args.phase](args.work_id);print(json.dumps({'phase':args.phase,'result':result,'cf_accessed':False,'source_business_data_exported':False}))

if __name__=='__main__':
 try:main()
 except Exception as error:raise SystemExit('FIXTURE BACKUP ERROR: '+str(error))
