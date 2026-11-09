#!/usr/bin/python3
"""Apply user-supplied test-only credentials; never prints values or touches production."""
import argparse,base64,datetime,fcntl,hashlib,importlib.util,json,os,pathlib,re,socket,stat,subprocess,urllib.request,urllib.parse,urllib.error
B=pathlib.Path('/opt/dell/data/test-data');STATE=pathlib.Path('/root/dell-test-credentials');TARGET='192.168.19.20';D=['/usr/bin/docker','--host','unix:///var/run/docker.sock']

def need(v,code):
 if not v:raise RuntimeError(code)
def run(a,data=None,timeout=25):
 p=subprocess.run(a,input=data,capture_output=True,timeout=timeout)
 need(p.returncode==0,'fixed-native-operation-failed');return p.stdout

def put_private(p,d):
 need(not p.exists(),'private-result-exists');fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
 with os.fdopen(fd,'w')as f:json.dump(d,f);f.write('\n');f.flush();os.fsync(f.fileno())

def original_file(p):
 s=p.lstat();need(not p.is_symlink()and p.resolve()==p and stat.S_ISREG(s.st_mode)and s.st_nlink==1 and stat.S_IMODE(s.st_mode)==0o600,'file-identity')
 return p.read_bytes(),(s.st_dev,s.st_ino,s.st_uid,s.st_gid,stat.S_IMODE(s.st_mode))

def inplace(p,data,identity):
 fd=os.open(p,os.O_WRONLY|os.O_NOFOLLOW)
 try:
  s=os.fstat(fd);need((s.st_dev,s.st_ino,s.st_uid,s.st_gid,stat.S_IMODE(s.st_mode))==identity and s.st_nlink==1,'bound-file-identity-drift')
  os.ftruncate(fd,0);pos=0
  while pos<len(data):pos+=os.write(fd,data[pos:])
  os.fsync(fd)
 finally:os.close(fd)

def sql(query,password,tcp=False):
 shell='IFS= read -r MYSQL_PWD; export MYSQL_PWD; exec mysql --no-defaults --binary-mode --user=root --batch --raw --skip-column-names --default-character-set=utf8mb4 '
 shell+=('--protocol=TCP --host='+TARGET+' --port=3306 --ssl-mode=DISABLED --get-server-public-key 'if tcp else'--protocol=socket ')
 return run(D+['exec','-i','dell-data-test-data-mysql-1','sh','-ec',shell],password.encode()+b'\n'+query.encode()).decode().strip()

def esc(s):
 need(re.fullmatch(r'[A-Za-z0-9_@.:%+=,/-]{1,256}',s)is not None,'unsupported-password-literal')
 return "'"+s+"'"

class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,*a,**kw):return None
class Rabbit:
 def __init__(self,user,password):self.user=user;self.password=password;self.op=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
 def api(self,method,path,data=None,missing=False):
  need(path.startswith(('/api/users','/api/vhosts','/api/permissions','/api/whoami')),'fixed-rabbit-path')
  body=json.dumps(data).encode()if data is not None else None
  h={'Authorization':'Basic '+base64.b64encode((self.user+':'+self.password).encode()).decode()}
  if body is not None:h['Content-Type']='application/json'
  try:
   with self.op.open(urllib.request.Request('http://'+TARGET+':15672'+path,data=body,method=method,headers=h),timeout=10)as r:raw=r.read(1048576);return json.loads(raw)if raw else None
  except urllib.error.HTTPError as e:
   code=e.code;e.close()
   if missing and code==404:return None
   raise RuntimeError('fixed-rabbit-request-failed')from None

def frames():
 ids=run(D+['ps','--filter','label=com.docker.compose.project=dell-data-test-data','--quiet','--no-trunc']).decode().split();need(len(ids)==4,'expected4containers')
 fmt='{"ID":{{json .Id}},"Image":{{json .Image}},"PID":{{json .State.Pid}},"Start":{{json .State.StartedAt}},"Running":{{json .State.Running}},"Health":{{json (index (index .State "Health") "Status")}},"FailingStreak":{{json (index (index .State "Health") "FailingStreak")}},"Restarts":{{json .RestartCount}},"OOM":{{json .State.OOMKilled}}}'
 r=sorted([json.loads(run(D+['inspect','--format',fmt,c]))for c in ids],key=lambda x:x['ID']);need(all(x['Running']and x['Health']=='healthy'and type(x.get('FailingStreak'))is int and x['FailingStreak']==0 and not x['OOM']for x in r),'healthy-base-required');return r

def supervisor_frame():
 raw=run(['systemctl','show','dell-data-test-data.service','--property=LoadState,ActiveState,SubState,MainPID,ExecMainStartTimestampMonotonic']).decode()
 row=dict(line.split('=',1)for line in raw.splitlines()if '='in line)
 need(row.get('LoadState')=='loaded'and row.get('ActiveState')=='active'and row.get('SubState')=='running'and row.get('MainPID','').isdigit()and int(row['MainPID'])>0 and row.get('ExecMainStartTimestampMonotonic','').isdigit()and int(row['ExecMainStartTimestampMonotonic'])>0,'healthy-supervisor-required')
 return row

def mysql_change(desired,old,ident,work):
 oldpwd=old.decode().strip();new=desired['mysql_password'];p=B/'secrets/mysql-root-password'
 rows=[json.loads(l)for l in sql("SELECT JSON_ARRAY(User,Host,plugin,ssl_type,account_locked,COALESCE(JSON_CONTAINS_PATH(User_attributes,'one','$.additional_password'),0)) FROM mysql.user WHERE User='root' ORDER BY Host;",oldpwd).splitlines()]
 need({r[1]for r in rows}=={'localhost','%'}and all(r[2]=='caching_sha2_password'and r[5]==0 for r in rows),'original-root-contract')
 tls=sql('SELECT @@require_secure_transport,@@tls_version;',oldpwd);need(tls.split('\t')[0]=='0'and all(r[3]==''for r in rows),'original-nonrequired-TLS-contract');changed_hosts=[]
 try:
  for r in rows:
   changed_hosts.append(r[1]);sql("ALTER USER 'root'@"+esc(r[1])+" IDENTIFIED WITH "+r[2]+' BY '+esc(new)+' RETAIN CURRENT PASSWORD;',oldpwd)
  inplace(p,(new+'\n').encode(),ident)
  need(sql('SELECT CURRENT_USER();',new)=='root@localhost'and sql('SELECT CURRENT_USER();',new,True)=='root@%','new-root-auth-required')
  for r in rows:sql("ALTER USER 'root'@"+esc(r[1])+' DISCARD OLD PASSWORD;',new)
  after=[json.loads(l)for l in sql("SELECT JSON_ARRAY(User,Host,plugin,ssl_type,account_locked,COALESCE(JSON_CONTAINS_PATH(User_attributes,'one','$.additional_password'),0)) FROM mysql.user WHERE User='root' ORDER BY Host;",new).splitlines()]
  need(rows==after and sql('SELECT @@require_secure_transport,@@tls_version;',new)==tls,'original-root-plugin-TLS-contract')
 except Exception:
  restored=False
  if changed_hosts:
   rollback=''.join("ALTER USER 'root'@"+esc(r[1])+" IDENTIFIED WITH "+r[2]+' BY '+esc(oldpwd)+"; ALTER USER 'root'@"+esc(r[1])+" DISCARD OLD PASSWORD;" for r in rows if r[1]in changed_hosts)
   for candidate in [oldpwd,new]:
    try:sql(rollback,candidate);restored=True;break
    except Exception:pass
   need(restored,'mysql-rollback-SQL-unconfirmed')
  inplace(p,old,ident)
  need(sql('SELECT CURRENT_USER();',oldpwd)=='root@localhost'and sql('SELECT CURRENT_USER();',oldpwd,True)=='root@%','mysql-rollback-auth-unconfirmed')
  rollback_rows=[json.loads(l)for l in sql("SELECT JSON_ARRAY(User,Host,plugin,ssl_type,account_locked,COALESCE(JSON_CONTAINS_PATH(User_attributes,'one','$.additional_password'),0)) FROM mysql.user WHERE User='root' ORDER BY Host;",oldpwd).splitlines()]
  need(rollback_rows==rows,'mysql-rollback-contract-unconfirmed')
  raise
 put_private(work/'mysql-result.json',{'status':'desired-test-root-credential-applied','plugin_Host_TLS_and_lock_flags_unchanged':True,'socket_and_TLSdisabled_TCP_auth_verified':True,'old_secondary_password_removed':True,'secret_original_inode_preserved':True})

def redis_acl():
 shell='export REDISCLI_AUTH="$(cat /run/secrets/redis-password)"; exec redis-cli --no-auth-warning --json ACL GETUSER default'
 raw=json.loads(run(D+['exec','--user=0','dell-data-test-data-redis-1','sh','-ec',shell]))
 if isinstance(raw,list):raw=dict(zip(raw[::2],raw[1::2]))
 need(isinstance(raw,dict)and isinstance(raw.get('passwords'),list),'redis-ACL-shape');return raw

def redis_change(desired,old,ident,work):
 sp=importlib.util.spec_from_file_location('test_redis_client',B/'scripts/acceptance.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
 acl_before=redis_acl();need(len(acl_before['passwords'])==1 and 'nopass'not in acl_before.get('flags',[]),'redis-original-single-password');put_private(work/'redis-ACL.before.json',acl_before)
 c=m.Redis({'SERVICE_IP':TARGET});new=desired['redis_password'];p=B/'secrets/redis-password';path='/run/dell-redis/redis.conf';raw=run(D+['exec','--user=0','dell-data-test-data-redis-1','cat',path]);put_private(work/'redis-runtime.before.json',{'bytes_base64':base64.b64encode(raw).decode()})
 need(sum(l.startswith(b'requirepass ')for l in raw.splitlines())==1,'fixed-runtime-pass-line')
 after=b'\n'.join((b'requirepass '+new.encode())if l.startswith(b'requirepass ')else l for l in raw.split(b'\n'))
 try:
  need(c.call('ACL','SETUSER','default','>'+new)=='OK','redis-add-password-transition')
  inplace(p,(new+'\n').encode(),ident);need(c.call('CONFIG','SET','requirepass',new)=='OK','redis-set-runtime')
  run(D+['exec','--user=0','-i','dell-data-test-data-redis-1','sh','-ec','cat > /run/dell-redis/redis.conf'],after)
  fresh=m.Redis({'SERVICE_IP':TARGET})
  try:need(fresh.call('PING')=='PONG','new-redis-auth')
  finally:fresh.close()
  acl_after=redis_acl();need(len(acl_after['passwords'])==1 and {k:v for k,v in acl_after.items()if k!='passwords'}=={k:v for k,v in acl_before.items()if k!='passwords'},'redis-nonpassword-ACL-changed')
 except Exception:
  steps=[];runtime=False
  try:c.call('CONFIG','SET','requirepass',old.decode().strip());runtime=True
  except Exception:
   for value in [new,old.decode().strip()]:
    attempt=None
    try:
     attempt=m.Redis({'SERVICE_IP':TARGET},auth=False);attempt.call('AUTH',value);attempt.call('CONFIG','SET','requirepass',old.decode().strip());runtime=True;break
    except Exception:pass
    finally:
     if attempt:attempt.close()
  steps.append(runtime)
  try:inplace(p,old,ident);steps.append(True)
  except Exception:steps.append(False)
  try:run(D+['exec','--user=0','-i','dell-data-test-data-redis-1','sh','-ec','cat > /run/dell-redis/redis.conf'],raw);steps.append(True)
  except Exception:steps.append(False)
  try:
   check=m.Redis({'SERVICE_IP':TARGET})
   try:steps.append(check.call('PING')=='PONG')
   finally:check.close()
  except Exception:steps.append(False)
  c.close();need(all(steps),'redis-rollback-unconfirmed');raise
 c.close();put_private(work/'redis-result.json',{'status':'desired-test-Redis-credential-applied','AUTH_PING_verified':True,'secret_original_inode_preserved':True,'runtime_config_requirepass_only_synced':True,'CONFIG_REWRITE_or_parent_permission_change':False,'data_ACL_categories_and_other_settings_changed':False})

def rabbit_change(desired,old,ident,env,env_ident,defs,defs_ident,work):
 original_env=env.decode();cfg=dict(l.split('=',1)for l in original_env.splitlines()if '='in l and not l.startswith('#'));olduser=cfg['RABBIT_ADMIN_USER'];client=Rabbit(olduser,old.decode().strip());newuser=desired['rabbit_user'];newpass=desired['rabbit_password']
 definition=json.loads(defs);need(set(['users','vhosts','permissions']).issubset(definition)and all(isinstance(definition[k],list)for k in ['users','vhosts','permissions']),'old-definitions-shape');need(newuser not in {x['name']for x in definition['users']},'definition-user-collision');need(sum(l.startswith('RABBIT_ADMIN_USER=')for l in original_env.splitlines())==1,'one-admin-env-key')
 users=client.api('GET','/api/users');need(newuser not in {x['name']for x in users},'new-admin-user-collision')
 before_vhosts={x['name']for x in client.api('GET','/api/vhosts')};wanted=before_vhosts|{'/'}
 client.api('PUT','/api/users/'+urllib.parse.quote(newuser,safe=''),{'password':newpass,'tags':'administrator'})
 for vhost in sorted(wanted):
  v=urllib.parse.quote(vhost,safe='')
  if vhost not in before_vhosts:client.api('PUT','/api/vhosts/'+v,{})
  client.api('PUT','/api/permissions/'+v+'/'+urllib.parse.quote(newuser,safe=''),{'configure':'.*','write':'.*','read':'.*'})
 fresh=Rabbit(newuser,newpass);need(fresh.api('GET','/api/whoami')['name']==newuser,'new-rabbit-admin-auth')
 salt=os.urandom(4);hashed=base64.b64encode(salt+hashlib.sha256(salt+newpass.encode()).digest()).decode()
 definition['users'].append({'name':newuser,'password_hash':hashed,'hashing_algorithm':'rabbit_password_hashing_sha256','tags':['administrator']})
 for v in sorted(wanted):
  if v not in {x['name']for x in definition['vhosts']}:definition['vhosts'].append({'name':v})
  definition['permissions'].append({'user':newuser,'vhost':v,'configure':'.*','write':'.*','read':'.*'})
 inplace(B/'secrets/rabbit-definitions.json',(json.dumps(definition,indent=2)+'\n').encode(),defs_ident)
 inplace(B/'secrets/rabbit-admin-password',(newpass+'\n').encode(),ident)
 lines=original_env.splitlines();need(sum(l.startswith('RABBIT_ADMIN_USER=')for l in lines)==1,'one-admin-env-key');newenv='\n'.join('RABBIT_ADMIN_USER='+newuser if l.startswith('RABBIT_ADMIN_USER=')else l for l in lines)+'\n';inplace(B/'.env',newenv.encode(),env_ident)
 need(fresh.api('GET','/api/whoami')['name']==newuser and client.api('GET','/api/whoami')['name']==olduser,'old-new-admin-preserved')
 put_private(work/'rabbit-result.json',{'status':'desired-test-Rabbit-admin-ready','old_admin_and_app_accounts_preserved':True,'new_admin_authenticated':True,'default_and_existing_vhost_permissions_ready':True,'persistent_definitions_and_helper_config_synced':True,'definitions_secret_original_inode_preserved':True,'queues_bindings_or_messages_deleted_or_published':False})

def main():
 a=argparse.ArgumentParser();a.add_argument('--run-id',required=True);x=a.parse_args();need(re.fullmatch('[0-9a-f]{32}',x.run_id)is not None,'run-id');os.umask(0o077)
 need(os.geteuid()==0 and socket.gethostname()=='data-test'and not pathlib.Path('/etc/pve').exists(),'test210-only');fs=json.loads(run(['findmnt','-J','--mountpoint','/srv/dell-data','-o','TARGET,UUID']))['filesystems'];need(len(fs)==1 and fs[0]['uuid']=='dd1773f9-aa48-4401-a9c8-caf0f66845f3','dedicated-test-volume')
 need(STATE.resolve()==STATE and STATE.is_dir()and STATE.stat().st_uid==0 and stat.S_IMODE(STATE.stat().st_mode)==0o700,'private-state-directory')
 lockfd=os.open(STATE/'.transaction.lock',os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW|os.O_NONBLOCK,0o600)
 try:
  item=os.fstat(lockfd);need(stat.S_ISREG(item.st_mode)and item.st_uid==0 and item.st_nlink==1 and stat.S_IMODE(item.st_mode)==0o600,'private-transaction-lock');fcntl.flock(lockfd,fcntl.LOCK_EX|fcntl.LOCK_NB)
  work=STATE/x.run_id;need(work.resolve()==work and stat.S_IMODE(work.stat().st_mode)==0o700,'private-run');need({f.name for f in work.iterdir()}=={'desired.json'},'fresh-desired-only');desired=json.loads((work/'desired.json').read_text());need(set(desired)=={'mysql_password','redis_password','rabbit_user','rabbit_password'}and desired['rabbit_user']=='admin','fixed-request-shape');[esc(desired[k])for k in desired]
  ips=[v['local']for i in json.loads(run(['ip','-j','-4','address','show','scope','global']))if i['ifname']not in ['lo','docker0']and not i['ifname'].startswith(('br-','veth'))for v in i.get('addr_info',[])];need(ips==[TARGET],'target-exact-IP')
  before_supervisor=supervisor_frame();before=frames();paths={'mysql':B/'secrets/mysql-root-password','redis':B/'secrets/redis-password','rabbit':B/'secrets/rabbit-admin-password','env':B/'.env','definitions':B/'secrets/rabbit-definitions.json'};snap={k:original_file(p)for k,p in paths.items()}
  put_private(work/'before-files.json',{k:{'bytes_base64':base64.b64encode(v[0]).decode(),'identity':v[1]}for k,v in snap.items()});stage='rabbit'
  try:
   rabbit_change(desired,*snap['rabbit'],*snap['env'],*snap['definitions'],work);stage='mysql';mysql_change(desired,*snap['mysql'],work);stage='redis';redis_change(desired,*snap['redis'],work);need(frames()==before,'source-container-frames-changed');need(supervisor_frame()==before_supervisor,'source-supervisor-frame-changed')
  except Exception as e:
   result={'status':'test-credential-change-not-fully-confirmed','stage':stage,'error_type':type(e).__name__,'failure_code':str(e)if re.fullmatch('[a-zA-Z0-9-]{1,80}',str(e))else'withheld','private_backup_preserved':True};put_private(work/'failure.json',result);print(json.dumps(result));raise SystemExit(1)
  result={'at':datetime.datetime.now().astimezone().isoformat(),'status':'user-specified-test-credentials-applied','run_id':x.run_id,'mysql_root_hosts':['localhost','%'],'redis_default_authenticated':True,'rabbit_admin_user':desired['rabbit_user'],'original4_container_frames_unchanged':True,'supervisor_PID_and_starttime_unchanged':True,'source_or_production_or_Nacos_credentials_changed':False,'TLS_or_authplugin_or_other_user_passwords_changed':False,'password_values_or_authhashes_output':False,'service_restart':False};put_private(work/'result.json',result);print(json.dumps(result))
 finally:os.close(lockfd)
if __name__=='__main__':
 try:main()
 except Exception as e:print(json.dumps({'status':'test-credentials-not-confirmed','error_type':type(e).__name__}));raise SystemExit(1)
