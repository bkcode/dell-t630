#!/usr/bin/env python3
"""Fixed existing local snapshot restore; never contacts live application endpoints."""
import argparse,datetime,gzip,hashlib,json,os,re,shutil,socket,subprocess,sys,time,uuid
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parent))
import sql_snapshot
SPECS={
'nacos':(200,'data-prod-db','10.63.10.10','prod-db','f106e23107d34c0bba39a4c006dd1891','mysql.sql.gz','mysql','mysql:8.4.5@sha256:bd045a5ea8c8d25f497731fea5c50c3aceae7bb22bff543c424bb60052d55840'),
'redis':(201,'data-prod-infra','10.63.10.11','prod-infra','6c706257613d40228cf2611d94276e26','redis.rdb','redis','redis:7.4.4@sha256:bf8a5a417fa9b88aadf569fc16934c574be29386c126bf706063c4d95670440a'),
'rabbit-topology':(201,'data-prod-infra','10.63.10.11','prod-infra','b260debe1b5a4e0d9ea6657226a927cb','rabbit-definitions.json','rabbitmq','rabbitmq:3.13.7-management@sha256:9cfb7e92ae7d296aec4d1ae799e431209f7ed57d55f9c929d95667d0ccf1c920')}
BASE=Path('/srv/dell-data');DOCKER=['docker','--host','unix:///var/run/docker.sock'];REPORT=None
class Rejected(RuntimeError):pass

def run(args,data=None,timeout=60,check=True):
 p=subprocess.run(args,input=data,capture_output=True,timeout=timeout)
 if check and p.returncode:raise Rejected('isolated tool failure; raw output retained only inside guest if required')
 return p

def docker(*args,**kw):return run(DOCKER+list(args),**kw)
def private(path,data):
 fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
 with os.fdopen(fd,'wb') as f:f.write(data)
def digest(path):
 with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def trusted(path):
 if path.resolve()!=path or not path.is_file() or path.stat().st_uid!=0 or path.stat().st_mode&0o077:raise Rejected('private root-owned nonsymlink input required')

def live_metadata():
 ids=docker('ps','-aq').stdout.decode().split();rows={}
 for cid in ids:
  c=json.loads(docker('inspect',cid).stdout)[0]
  if c['Name'].startswith('/dell-full-restore-'):continue
  state=c['State'];rows[cid]={'name':c['Name'],'running':state['Running'],'started_at':state['StartedAt'],'pid':state['Pid'],'health':state.get('Health',{}).get('Status')}
 if not rows or any(not x['running'] or x['health'] not in (None,'healthy') for x in rows.values()):raise Rejected('existing container health not ready; no restore started')
 return rows

def preflight(component):
 spec=SPECS[component];vmid,host,ip,role,folder,filename,key,image=spec
 if os.geteuid()!=0 or socket.gethostname().split('.')[0]!=host or Path('/etc/pve').exists():raise Rejected('fixed200/201 guest only')
 addresses=json.loads(run(['ip','-j','addr']).stdout)
 if not any(a.get('local')==ip for n in addresses for a in n.get('addr_info',[])):raise Rejected('wrong private address')
 mount=json.loads(run(['findmnt','--json','--mountpoint',str(BASE)]).stdout)['filesystems'][0]
 if mount['target']!=str(BASE) or mount['source']==json.loads(run(['findmnt','--json','--target','/']).stdout)['filesystems'][0]['source']:raise Rejected('independent data mount required')
 snapshot=BASE/'_app_backups'/folder;source=snapshot/filename;manifest=snapshot/'manifest.json';trusted(source);trusted(manifest)
 m=json.loads(manifest.read_text())
 if m['component']!=component or m['role']!=role or m.get('cf_included') or m.get('exported') or set(m['files'])!={filename} or digest(source)!=m['files'][filename]:raise Rejected('snapshot manifest identity/hash mismatch')
 lock=json.loads((Path('/opt/dell/data')/role/'images.lock.json').read_text())
 if lock['images'][key]['reference']!=image:raise Rejected('image lock differs from approved digest')
 meta=json.loads(docker('image','inspect',image).stdout)[0]
 if meta['Architecture']!='amd64':raise Rejected('existing amd64 image required')
 if shutil.disk_usage(BASE).free<3*1024**3+source.stat().st_size*5:raise Rejected('insufficient disk safety headroom')
 mem=int(re.search(r'^MemAvailable:\s+(\d+)',Path('/proc/meminfo').read_text(),re.M)[1])*1024
 need=(1536 if component=='nacos' else 1024)*1024**2
 if mem<need:raise Rejected('insufficient MemAvailable; serialize with other tasks')
 before=live_metadata()
 return spec,source,m,before,{'vmid':vmid,'component':component,'input_bytes':source.stat().st_size,'input_hash_matches':True,'image':image,'platform':'linux/amd64','free_bytes':shutil.disk_usage(BASE).free,'mem_available_bytes':mem,'live_container_count':len(before)}

def image_uid(image,user):
 p=docker('run','--rm','--pull=never','--network=none','--read-only','--cap-drop=ALL','--security-opt=no-new-privileges:true','--cpus=0.25','--memory=32m','--pids-limit=16','--entrypoint','/bin/sh',image,'-c','id -u '+user+'; id -g '+user)
 values=p.stdout.decode().split()
 if len(values)!=2 or any(not x.isdigit() for x in values) or int(values[0])==0:raise Rejected('nonroot image identity missing')
 return tuple(map(int,values))

def temp_container(component,image,work,data,uid,command,secret=None,env=None):
 if any(data.iterdir()):raise Rejected('new empty scratch required')
 os.chown(data,*uid);name='dell-full-restore-'+component+'-'+work.name[:12]
 dst={'nacos':'/var/lib/mysql','redis':'/data','rabbit-topology':'/var/lib/rabbitmq'}[component];memory={'nacos':'768m','redis':'256m','rabbit-topology':'512m'}[component]
 args=['run','--detach','--name',name,'--label','dell.full.restore='+work.name,'--pull=never','--platform=linux/amd64','--network=none','--read-only','--user',str(uid[0])+':'+str(uid[1]),'--cap-drop=ALL','--security-opt=no-new-privileges:true','--cpus=1','--memory='+memory,'--memory-swap='+memory,'--pids-limit=256','--tmpfs','/tmp:size=32m,mode=1777','--mount','type=bind,src='+str(data)+',dst='+dst]
 if component=='nacos':args+=['--tmpfs','/var/run/mysqld:size=16m,uid='+str(uid[0])+',gid='+str(uid[1])+',mode=0755']
 if component=='rabbit-topology':args+=['--hostname','localhost']
 for key,value in (env or {}).items():args+=['--env',key+'='+value]
 for source,target in (secret or []):args+=['--mount','type=bind,src='+str(source)+',dst='+target+',readonly']
 cid=docker(*args,image,*command).stdout.decode().strip()
 if not re.fullmatch('[a-f0-9]{64}',cid):raise Rejected('temporary container identity missing')
 return cid

def isolation(cid,work):
 c=json.loads(docker('inspect',cid).stdout)[0];h=c['HostConfig'];uid=c['Config']['User'].split(':')[0]
 mounts=c['Mounts'];own=all(x.get('Type')=='tmpfs' or (x.get('Type')=='bind' and Path(x['Source']).is_relative_to(work)) for x in mounts)
 result={'network_none':h['NetworkMode']=='none','no_published_ports':not h.get('PortBindings') and not any(c['NetworkSettings']['Ports'].values()),'nonroot':uid.isdigit() and int(uid)>0,'read_only_root':h['ReadonlyRootfs'],'not_privileged':not h['Privileged'],'cap_drop_all':'ALL' in h['CapDrop'],'only_own_scratch_mounts':own,'no_host_network':not c['NetworkSettings']['Networks'].get('host')}
 if not all(result.values()):raise Rejected('actual container isolation mismatch')
 return result

def mysql(cid,sql):
 shell='export MYSQL_PWD="$(cat /run/secrets/restore-password)"; exec mysql --user=root --protocol=socket --batch --raw --skip-column-names'
 return docker('exec','-i',cid,'sh','-c',shell,data=sql.encode() if isinstance(sql,str) else sql,timeout=180).stdout.decode().rstrip('\n')

def mysql_ready(cid):
 for _ in range(100):
  try:
   if mysql(cid,'SELECT 1;')=='1':return
  except Rejected:pass
  time.sleep(1)
 raise Rejected('isolated MySQL readiness timeout')

def nacos_rows(cid,expected):
 found=mysql(cid,"SELECT table_name FROM information_schema.tables WHERE table_schema='nacos_prod' AND table_type='BASE TABLE' ORDER BY table_name;").splitlines()
 if set(found)!=set(expected):raise Rejected('restored table set differs from snapshot')
 result={}
 for table,meta in expected.items():
  select=','.join("IFNULL(HEX(CAST(`"+c+"` AS BINARY)),'NULL')" for c in meta['columns'])
  raw=mysql(cid,'SELECT '+select+' FROM `nacos_prod`.`'+table+'`;');rows=[]
  for line in raw.splitlines() if raw else []:
   parts=line.split('\t')
   if len(parts)!=len(meta['columns']):raise Rejected('unexpected normalized row width')
   rows.append(tuple(None if p=='NULL' else bytes.fromhex(p) for p in parts))
  if len(rows)!=meta['rows'] or sql_snapshot.row_digest(rows)!=meta['digest']:raise Rejected('restored snapshot row content/hash mismatch; details suppressed')
  check=mysql(cid,'CHECK TABLE `nacos_prod`.`'+table+'`;')
  if not check.endswith('\tstatus\tOK'):raise Rejected('restored table check not OK')
  result[table]={'rows':len(rows),'all_columns_digest_match':True}
 if mysql(cid,'SELECT @@event_scheduler;')!='OFF':raise Rejected('event scheduler must remain OFF')
 return result

def nacos_restore(image,source,work,containers,report):
 with gzip.open(source,'rb') as f:raw=f.read(128*1024**2+1)
 if len(raw)>128*1024**2:raise Rejected('snapshot decompression budget exceeded')
 expected=sql_snapshot.parse(raw.decode('utf-8'));uid=image_uid(image,'mysql');pw=work/'mysql-password';private(pw,uuid.uuid4().hex.encode());os.chown(pw,*uid)
 data=work/'mysql-data';data.mkdir(mode=0o700)
 cid=temp_container('nacos',image,work,data,uid,['--innodb-buffer-pool-size=128M','--performance-schema=OFF','--max-connections=10','--skip-log-bin','--event-scheduler=OFF','--local-infile=0','--secure-file-priv=NULL','--skip-networking'],[(pw,'/run/secrets/restore-password')],{'MYSQL_ROOT_PASSWORD_FILE':'/run/secrets/restore-password'});containers.append(cid)
 report['isolation']=isolation(cid,work);mysql_ready(cid);mysql(cid,raw);tables=nacos_rows(cid,expected)
 docker('restart',cid,timeout=60);mysql_ready(cid);after=nacos_rows(cid,expected)
 if tables!=after:raise Rejected('restart Nacos metadata changed')
 return {'complete_nacos_metadata_restored':True,'tables':tables,'table_count':len(tables),'restored_row_count':sum(x['rows'] for x in tables.values()),'users_password_hash_roles_permissions_compared':True,'event_scheduler':'OFF','nacos_jvm_started':False,'restart_persistence_verified':True,'source_secrets_used':False}

def redis_call(cid,*args):
 # Temporary password remains in an own600 config, and only inside exec environment.
 shell='export REDISCLI_AUTH="$(sed -n \'s/^requirepass //p\' /etc/redis/restore.conf)"; exec redis-cli --no-auth-warning --json "$@"'
 if args[0]=='INFO':shell=shell.replace('--json','--raw')
 p=docker('exec',cid,'sh','-c',shell,'redis-cli',*args)
 if args[0]=='INFO':return p.stdout.decode()
 try:return json.loads(p.stdout)
 except Exception:raise Rejected('unexpected isolated Redis JSON reply') from None

def redis_ready(cid):
 for _ in range(40):
  try:
   if redis_call(cid,'PING')=='PONG':return
  except Rejected:pass
  time.sleep(1)
 raise Rejected('isolated Redis readiness timeout')

def redis_fingerprints(cid):
 info=redis_call(cid,'INFO','keyspace');dbs=[]
 for line in info.splitlines():
  m=re.match(r'db([0-9]+):keys=([0-9]+),expires=([0-9]+)',line)
  if m:dbs.append((int(m[1]),int(m[2]),int(m[3])))
 records={};expiry={}
 # --json escaped binary is Unicode byte-wise; encode latin1 to recover original Redis bytes.
 shell='export REDISCLI_AUTH="$(sed -n \'s/^requirepass //p\' /etc/redis/restore.conf)"; exec redis-cli --no-auth-warning --json -n "$1" EVAL_RO '+"'local r={} for _,k in ipairs(redis.call(\"KEYS\",\"*\")) do r[#r+1]={k,redis.call(\"TYPE\",k).ok,redis.call(\"DUMP\",k),redis.call(\"PTTL\",k)} end return r' 0"
 for db,keys,expires in dbs:
  rows=json.loads(docker('exec',cid,'sh','-c',shell,'redis-cli',str(db)).stdout)
  if len(rows)!=keys:raise Rejected('isolated Redis keyspace count race')
  for key,kind,value,ttl in rows:
   identity=hashlib.sha256(str(db).encode()+b':'+key.encode('latin1')).hexdigest();records[identity]=hashlib.sha256(kind.encode()+value.encode('latin1')).hexdigest();expiry[identity]=ttl
 return {'keys':sum(x[1] for x in dbs),'expires':sum(x[2] for x in dbs),'databases':len(dbs),'records':records,'expiry':expiry}

def redis_restore(image,source,work,containers,report):
 uid=image_uid(image,'redis')
 data=work/'redis-data';data.mkdir(mode=0o700);own=data/'dump.rdb';shutil.copyfile(source,own);os.chown(own,*uid);own.chmod(0o600)
 check=docker('run','--rm','--pull=never','--network=none','--read-only','--user',str(uid[0])+':'+str(uid[1]),'--cap-drop=ALL','--security-opt=no-new-privileges:true','--cpus=1','--memory=256m','--pids-limit=32','--mount','type=bind,src='+str(own)+',dst=/snapshot.rdb,readonly',image,'redis-check-rdb','/snapshot.rdb')
 checked=check.stdout.decode(errors='replace');m=re.search(r'(\d+) keys read',checked);expected_keys=int(m[1]) if m else None
 if expected_keys is None or 'Checksum OK' not in checked:raise Rejected('RDB checker summary unsupported')
 # Empty data directory starts from this own readonly seed; later restart preserves scratch SAVE.
 seed=work/'redis-seed.rdb';own.rename(seed);os.chown(data,*uid)
 conf=work/'redis.conf';private(conf,('bind 127.0.0.1\nport 6379\ndir /data\ndbfilename dump.rdb\nsave ""\nappendonly no\nrequirepass '+uuid.uuid4().hex+'\n').encode());os.chown(conf,*uid)
 # Use a wrapper which copies only the private own seed before launching redis-server.
 cid=temp_container('redis',image,work,data,uid,['sh','-c','if test ! -s /data/dump.rdb; then cp /run/restore-seed.rdb /data/dump.rdb; fi; exec redis-server /etc/redis/restore.conf'],[(conf,'/etc/redis/restore.conf'),(seed,'/run/restore-seed.rdb')]);containers.append(cid)
 report['isolation']=isolation(cid,work);redis_ready(cid);before=redis_fingerprints(cid);started=time.monotonic()
 if before['keys']>expected_keys:raise Rejected('RDB recovered more keys than snapshot')
 # Save only the recovered scratch; restart reloads that scratch file without overwriting it from the original seed.
 if redis_call(cid,'SAVE')!='OK':raise Rejected('scratch SAVE failed')
 docker('restart',cid,timeout=60);redis_ready(cid);after=redis_fingerprints(cid);elapsed=(time.monotonic()-started)*1000
 for key,value in before['records'].items():
  ttl=before['expiry'][key]
  if ttl<0 or ttl>elapsed+2000:
   if after['records'].get(key)!=value:raise Rejected('Redis persistent key digest mismatch')
   new_ttl=after['expiry'][key]
   if (ttl==-1 and new_ttl!=-1) or (ttl>=0 and (new_ttl<0 or abs((ttl-new_ttl)-elapsed)>2000)):raise Rejected('Redis TTL elapsed-time semantics mismatch')
 for key,value in after['records'].items():
  if before['records'].get(key)!=value:raise Rejected('Redis unexpected postrestart key/value')
 if 'loading:0' not in redis_call(cid,'INFO','persistence'):raise Rejected('RDB load did not finish')
 return {'full_RDB_checksum_passed':True,'snapshot_keys_read':expected_keys,'nonempty_key_value_restore_exercised':before['keys']>0,'keys_restored':before['keys'],'keys_after_restart':after['keys'],'expired_or_elapsed_keys':expected_keys-before['keys'],'database_count':before['databases'],'all_persistent_key_type_value_digests_match':True,'restart_RDB_reload_verified':True,'ACL_password_config_restored':False,'source_snapshot_or_BGSAVE_requested':False}

def normalize_vhost(row):
 # HTTP export repeats description/tags beside metadata; CLI export adds empty limits.
 if set(row)-{'name','metadata','description','tags','limits'}:raise Rejected('unknown vhost fields require review')
 result=dict(row);metadata=result.get('metadata',{})
 if not isinstance(metadata,dict):raise Rejected('unsupported vhost metadata structure')
 for field,default in [('description',''),('tags',[])]:
  if field in result:
   if result[field]!=metadata.get(field,default):raise Rejected('non-equivalent duplicated vhost metadata')
   del result[field]
 if result.get('limits') in ({},[]):result.pop('limits')
 return result

def canonical_rows(rows):return sorted(json.dumps(x,sort_keys=True,separators=(',',':')) for x in rows)
def rabbit_export(cid,expected):
 docker('exec',cid,'rabbitmqctl','export_definitions','/tmp/restored-definitions.json',timeout=90)
 actual=json.loads(docker('exec',cid,'cat','/tmp/restored-definitions.json').stdout)
 # Official3.13.7 export intentionally filters internal* global parameters; query their read-only runtime representation separately.
 internal=[x for x in expected.get('global_parameters',[]) if x['name'].startswith('internal')]
 if any(x['name']!='internal_cluster_id' for x in internal):raise Rejected('unknown internal global parameter requires review')
 if internal:
  rows=json.loads(docker('exec',cid,'rabbitmqctl','list_global_parameters','--formatter','json').stdout)
  for source in internal:
   target=next((x for x in rows if x.get('name')==source['name']),None)
   if target is None:raise Rejected('internal cluster identity not found in restored runtime')
   try:value=json.loads(target['value'])
   except Exception:raise Rejected('internal parameter CLI JSON representation unsupported') from None
   left=hashlib.sha256(json.dumps(source['value'],sort_keys=True).encode()).digest();right=hashlib.sha256(json.dumps(value,sort_keys=True).encode()).digest()
   if left!=right:raise Rejected('internal cluster identity digest mismatch; no values emitted')
   actual.setdefault('global_parameters',[]).append({'name':source['name'],'value':value})
  if REPORT is not None:REPORT['internal_cluster_id_private_digest_match']=True;REPORT['CLI_export_internal_parameters_intentionally_filtered']=True
 return actual
def rabbit_compare(expected,actual):
 fields=['users','vhosts','permissions','topic_permissions','queues','exchanges','bindings','policies','parameters','global_parameters'];counts={}
 for key in fields:
  src=expected.get(key,[]);got=actual.get(key,[])
  if key=='users':got=[x for x in got if x['name'] in {u['name'] for u in src}]
  if key=='permissions':got=[x for x in got if x['user'] in {u['name'] for u in expected.get('users',[])}]
  # Empty default vhost can exist before import; it has no source secret or application messages.
  if key=='vhosts':
   got=[x for x in got if x['name'] in {v['name'] for v in src}];src=[normalize_vhost(x) for x in src];got=[normalize_vhost(x) for x in got]
  if canonical_rows(src)!=canonical_rows(got):
   if REPORT is not None:
    details=[]
    for left in src:
     right=next((x for x in got if x.get('name')==left.get('name')),None)
     if right is None:details.append({'matching_identity_found':False});continue
     changed=sorted(k for k in set(left)|set(right) if left.get(k)!=right.get(k))
     row={'matching_identity_found':True,'expected_field_names':sorted(left),'restored_field_names':sorted(right),'differing_field_names':changed}
     if key=='vhosts':
      allowed={'undefined','classic','quorum','stream',None}
      for field in changed:
       if field=='default_queue_type' and left.get(field) in allowed and right.get(field) in allowed:row['queue_type_categorical_difference']={'expected':left.get(field),'restored':right.get(field)}
       if field=='metadata' and isinstance(left.get(field),dict) and isinstance(right.get(field),dict):row['metadata_changed_field_names']=sorted(k for k in set(left[field])|set(right[field]) if left[field].get(k)!=right[field].get(k))
     details.append(row)
    REPORT['definition_comparison_difference']={'field':key,'expected_objects':len(src),'restored_objects':len(got),'objects':details}
   raise Rejected('Rabbit restored definitions differ in field '+key+'; values suppressed')
  counts[key]=len(src)
 return counts

def rabbit_restore(image,source,work,containers,report):
 definitions=json.loads(source.read_bytes())
 if definitions.get('parameters'):raise Rejected('runtime parameters present; external or unknown behavior requires review')
 known={'rabbit_version','rabbitmq_version','product_name','product_version','users','vhosts','permissions','topic_permissions','queues','exchanges','bindings','policies','parameters','global_parameters'}
 if set(definitions)-known:raise Rejected('unknown Rabbit definitions fields require review')
 uid=image_uid(image,'rabbitmq');data=work/'rabbit-data';data.mkdir(mode=0o700)
 plugins=work/'enabled_plugins';private(plugins,b'[rabbitmq_management].\n');os.chown(plugins,*uid)
 cid=temp_container('rabbit-topology',image,work,data,uid,[],[(plugins,'/etc/rabbitmq/enabled_plugins')],{'RABBITMQ_NODENAME':'rabbit@localhost','RABBITMQ_SERVER_ADDITIONAL_ERL_ARGS':'+S 2:2'});containers.append(cid)
 report['isolation']=isolation(cid,work)
 def ready():
  for _ in range(90):
   if docker('exec',cid,'rabbitmq-diagnostics','-q','check_running',check=False,timeout=20).returncode==0:return
   time.sleep(1)
  raise Rejected('isolated Rabbit readiness timeout')
 ready();docker('exec','-i',cid,'sh','-c','umask 077; cat >/tmp/snapshot-definitions.json; exec rabbitmqctl import_definitions /tmp/snapshot-definitions.json',data=source.read_bytes(),timeout=120)
 counts=rabbit_compare(definitions,rabbit_export(cid,definitions))
 for vhost in definitions.get('vhosts',[]):
  rows=json.loads(docker('exec',cid,'rabbitmqctl','list_queues','--vhost',vhost['name'],'name','messages','--formatter','json').stdout)
  if any(x.get('messages')!=0 for x in rows):raise Rejected('isolated queues must have zero messages')
 docker('restart',cid,timeout=60);ready();after=rabbit_compare(definitions,rabbit_export(cid,definitions))
 if counts!=after:raise Rejected('Rabbit definitions changed on restart')
 return {'complete_definitions_restored':True,'counts':counts,'user_password_hash_and_permissions_compared':True,'queue_messages':0,'messages_in_backup':False,'messages_published':0,'external_runtime_parameters':False,'restart_persistence_verified':True}

def main():
 global REPORT
 p=argparse.ArgumentParser();p.add_argument('component',choices=SPECS);p.add_argument('--check-only',action='store_true');p.add_argument('--execute-approved-local-restore',action='store_true');args=p.parse_args()
 if not args.check_only and not args.execute_approved_local_restore:raise Rejected('explicit approved intent required')
 os.umask(0o077);spec,source,manifest,before,pre=preflight(args.component)
 if args.check_only:
  if args.component=='nacos':
   with gzip.open(source,'rb') as f:raw=f.read(128*1024**2+1)
   if len(raw)>128*1024**2:raise Rejected('SQL limit exceeded')
   meta=sql_snapshot.parse(raw.decode());pre.update(table_count=len(meta),table_row_counts={k:v['rows'] for k,v in meta.items()},full_row_normalization_supported=True)
  elif args.component=='rabbit-topology':
   data=json.loads(source.read_bytes());pre.update(definition_fields=sorted(data),runtime_parameter_count=len(data.get('parameters',[])),object_counts={k:len(v) for k,v in data.items() if isinstance(v,list)})
  print(json.dumps({'status':'preflight-passed','metadata':pre,'snapshot_content_exported':False}));return
 parent=BASE/'_dell_full_snapshot_restore'
 if parent.resolve(strict=False)!=parent:raise Rejected('scratch parent symlink rejected')
 parent.mkdir(mode=0o700,exist_ok=True);work=parent/uuid.uuid4().hex;work.mkdir(mode=0o700)
 report={'status':'running','started_at':now(),'component':args.component,'preflight':pre,'source_snapshot_read_only':True,'CF_accessed':False,'cross_device_exported':False};containers=[];error=None;started=time.monotonic();REPORT=report
 try:
  report['verification']={'nacos':nacos_restore,'redis':redis_restore,'rabbit-topology':rabbit_restore}[args.component](spec[7],source,work,containers,report)
  report['status']='passed'
 except Exception as exc:
  error=type(exc).__name__;report['status']='failed';report['error_category']=error
  if isinstance(exc,(Rejected,sql_snapshot.Unsupported)):report['safe_reason']=str(exc)
 finally:
  failures=[]
  for cid in containers:
   try:
    c=json.loads(docker('inspect',cid).stdout)[0]
    if c['Config']['Labels'].get('dell.full.restore')!=work.name:raise Rejected('cleanup container label mismatch')
    if docker('rm','--force',cid,check=False,timeout=60).returncode:failures.append(cid)
   except Exception:failures.append(cid)
  report['temporary_containers_removed']=not failures
  report['source_snapshot_SHA_unchanged']=digest(source)==manifest['files'][source.name]
  report['live_container_identity_health_unchanged']=live_metadata()==before
  if failures or not report['source_snapshot_SHA_unchanged'] or not report['live_container_identity_health_unchanged']:report['status']='failed'
  report.update(finished_at=now(),elapsed_seconds=round(time.monotonic()-started,3),RPO_RTO_approved=False,disaster_recovery_claimed=False)
  # Keep only sanitized result in per-nonce directory; remove own restored data and temporary secrets after verified container cleanup.
  if not failures:
   for child in list(work.iterdir()):
    if child.is_dir() and not child.is_symlink():shutil.rmtree(child)
    else:child.unlink()
  private(work/'result.json',json.dumps(report,indent=2).encode());print(json.dumps(report))
 if report['status']!='passed':raise SystemExit(1)
if __name__=='__main__':
 try:main()
 except Exception as error:
  print(json.dumps({'status':'failed-before-restore','error_category':type(error).__name__,'safe_reason':str(error) if isinstance(error,(Rejected,sql_snapshot.Unsupported)) else 'unexpected error; values suppressed'}));sys.exit(1)
