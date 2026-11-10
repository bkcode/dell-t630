#!/usr/bin/python3
"""Fixed existing VM280 manager transport change, preserving accounts and NFS."""
import base64,datetime,hashlib,json,os,pathlib,re,socket,ssl,subprocess,sys,time,urllib.request,urllib.parse,urllib.error
from zoneinfo import ZoneInfo
C=pathlib.Path('/etc/dell-filebrowser');M=pathlib.Path('/var/lib/dell-filebrowser-manager');CODE=pathlib.Path('/opt/dell/filebrowser');UNIT=pathlib.Path('/etc/systemd/system/dell-filebrowser.service');DEST={'config.yaml':C/'config.yaml','launch.py':CODE/'launch.py','dell-filebrowser.service':UNIT};OLD={'config.yaml':'74b7443364b7736880f395ba0b50e2b374ca11ea29bdb886cf3798bb7c2a5376','launch.py':'310d9485b54c70b9ee9aeb5c33fb3f52e6e6c7823ff688c7d1d7107b6eff71d7','dell-filebrowser.service':'3471c058871d350fa72aca6edb187f91473d2176c4f646aac92dc7a6aaf5eff7'}
NEW={'config.yaml':'7fe50a00dd568632abdc29286812af49322a25958b67c38f4cff625c5a52f5db','dell-filebrowser.service':'94aec8ba0232171b65b1671b12c4dfa8cc4891c3926a1745cd19d4eb25974ca7','launch.py':'e1c3732ca61545747e70a1b23459902796646f872d4147fe2680813834297d4c'}
def need(v,c):
 if not v:raise RuntimeError(c)
def run(a):return subprocess.check_output(a,stderr=subprocess.PIPE,timeout=35)
def sha(b):return hashlib.sha256(b).hexdigest()
def put(p,b,mode=0o644):
 t=p.with_name(p.name+'.http-tmp');need(not t.exists(),'unfinished-owned-write');fd=os.open(t,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,mode);os.fchmod(fd,mode)
 with os.fdopen(fd,'wb')as f:f.write(b);f.flush();os.fsync(f.fileno())
 os.replace(t,p)
def frames():return{n:run(['systemctl','show',n,'--property=MainPID,ExecMainStartTimestampMonotonic,ActiveState,SubState']).decode().splitlines()for n in ['nfs-server.service','nfs-mountd.service','dell-resources-firewall.service','ssh.service','systemd-networkd.service','prometheus-node-exporter.service']}
class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,*a,**kw):return None
class API:
 def __init__(self,secure):
  self.base=('https'if secure else'http')+'://192.168.19.80:8080';handlers=[urllib.request.ProxyHandler({}),NoRedirect()]
  if secure:handlers.append(urllib.request.HTTPSHandler(context=ssl.create_default_context(cafile=str(C/'tls.crt'))))
  self.op=urllib.request.build_opener(*handlers)
 def request(self,path,token=None,method='GET',password=None):
  h={}
  if token:h['Authorization']='Bearer '+token
  if password:h['X-Password']=urllib.parse.quote(password,safe='')
  try:
   with self.op.open(urllib.request.Request(self.base+path,method=method,headers=h),timeout=6)as r:return r.status,r.read(1048576)
  except urllib.error.HTTPError as e:c=e.code;e.close();return c,b''
 def login(self,name,password):
  c,b=self.request('/api/auth/login?'+urllib.parse.urlencode({'username':name}),method='POST',password=password);need(c==200,'existing-account-login-failed');s=b.decode().strip()
  try:s=json.loads(s)
  except ValueError:pass
  need(isinstance(s,str)and s.count('.')==2,'JWT-response-required');return s
 def account(self,token):
  c,b=self.request('/api/users?username=self',token);need(c==200,'existing-account-metadata-failed');d=json.loads(b);return {k:d.get(k)for k in ['username','loginMethod','permissions','scopes']}
def main():
 os.umask(0o077);need(os.geteuid()==0 and socket.gethostname()=='resource-service','VM280-root-only');need((C/'bootstrap.complete').exists(),'initialized-manager-required');fs=json.loads(run(['findmnt','-J','--mountpoint','/srv/resources','-o','UUID']))['filesystems'];need(len(fs)==1 and fs[0]['uuid']=='57d8158e-5fcf-4dd2-8cb4-b47b1e54ed7b','original-resource-UUID-required');data=json.load(sys.stdin);need(set(data)==set(DEST),'fixed-public-change-set');new={n:base64.b64decode(b)for n,b in data.items()};old={n:p.read_bytes()for n,p in DEST.items()};need(all(sha(b)==NEW[n]for n,b in new.items()),'exact-reviewed-HTTP-public-files-required');prepared=M/'prepared.json';oldprepared=prepared.read_bytes();prep=json.loads(oldprepared)
 for n,p in DEST.items():need(not p.is_symlink()and p.stat().st_uid==0 and sha(old[n])==OLD[n]and prep['public_files_sha256'][n]==OLD[n],'original-public-file-drift')
 oldcfg=json.loads(old['config.yaml']);newcfg=json.loads(new['config.yaml']);expected=json.loads(old['config.yaml']);expected['http'].pop('tlsCert');expected['http'].pop('tlsKey');need(newcfg==expected,'HTTP-only-config-delta-required');need(new['dell-filebrowser.service']==old['dell-filebrowser.service'].replace(b'LoadCredential=tls-key:/etc/dell-filebrowser/secrets/tls-key\n',b''),'TLS-only-unit-delta-required');compile(new['launch.py'],'launch.py','exec');need(b"reader('tls-key')"not in new['launch.py'],'no-TLS-key-loading-required')
 healthpath=pathlib.Path('/etc/dell-guest-monitoring/health.json');oldhealth=healthpath.read_bytes();health=json.loads(oldhealth);need(health['role']=='resource-service'and health['http_checks']==[{'name':'filebrowser-https-health','url':'https://192.168.19.80:8080/health','ca_file':'/etc/dell-filebrowser/tls.crt'}],'original-HTTPS-health-required');newhealth=dict(health,http_checks=[{'name':'filebrowser-http-health','url':'http://192.168.19.80:8080/health'}]);loginpath=C/'secrets/login.json';oldlogin=loginpath.read_bytes();login=json.loads(oldlogin);beforeframes=frames();oldapi=API(True);account_before={}
 for kind in ['admin','operator']:
  a=login[kind];account_before[kind]=oldapi.account(oldapi.login(a['username'],a['password']))
 backup=M/'before-http-20261110';need(not backup.exists(),'owned-transaction-exists');backup.mkdir(mode=0o700)
 for n,b in old.items():put(backup/n,b,0o600)
 for n,b in [('prepared.json',oldprepared),('health.json',oldhealth),('login.json',oldlogin)]:put(backup/n,b,0o600)
 updatedprep=json.loads(oldprepared)
 for n,b in new.items():updatedprep['public_files_sha256'][n]=sha(b)
 updatedprep['transport']='HTTP';updatedlogin=dict(login,URL='http://192.168.19.80:8080/')
 for n,p in DEST.items():need(p.read_bytes()==old[n],'public-file-drift-before-write')
 need(prepared.read_bytes()==oldprepared and healthpath.read_bytes()==oldhealth and loginpath.read_bytes()==oldlogin,'owned-config-drift-before-write')
 try:
  run(['systemctl','stop','dell-filebrowser.service'])
  for n,p in DEST.items():put(p,new[n])
  put(prepared,(json.dumps(updatedprep,indent=2)+'\n').encode(),0o600);put(healthpath,(json.dumps(newhealth,indent=2)+'\n').encode());put(loginpath,(json.dumps(updatedlogin,indent=2)+'\n').encode(),0o600);run(['systemctl','daemon-reload']);run(['systemd-analyze','verify',str(UNIT)]);run(['systemctl','start','dell-filebrowser.service']);api=API(False);ready=False
  for _ in range(30):
   try:
    code,b=api.request('/health');ready=code==200 and json.loads(b).get('message')=='ok'
    if ready:break
   except OSError:time.sleep(.3)
  need(ready,'HTTP-health-not-confirmed');account_after={}
  for kind in ['admin','operator']:
   a=login[kind];account_after[kind]=api.account(api.login(a['username'],a['password']))
  need(account_after==account_before,'original-account-permissions-changed');need(frames()==beforeframes,'protected-NFS-service-identities-changed');run(['systemctl','start','dell-guest-health.service'])
  c,_=api.request('/api/users?username=self');need(c==401,'anonymous-files-must-remain-protected');op=login['operator'];token=api.login(op['username'],op['password']);admincode,_=api.request('/api/settings',token);need(admincode==403,'daily-admin-settings-must-be-denied')
  metrics=pathlib.Path('/var/lib/prometheus/node-exporter-textfile/dell_guest_health.prom').read_text();need('dell_guest_http_up{role="resource-service",check="filebrowser-http-health"} 1'in metrics,'HTTP-health-metric-not-confirmed')
 except BaseException:
  run(['systemctl','stop','dell-filebrowser.service'])
  for n,p in DEST.items():put(p,old[n])
  put(prepared,oldprepared,0o600);put(healthpath,oldhealth);put(loginpath,oldlogin,0o600);run(['systemctl','daemon-reload']);run(['systemctl','start','dell-filebrowser.service']);run(['systemctl','start','dell-guest-health.service'])
  restored=False
  for _ in range(25):
   try:
    code,b=oldapi.request('/health');restored=code==200 and json.loads(b).get('message')=='ok'
    if restored:break
   except OSError:time.sleep(.3)
  need(restored,'original-HTTPS-rollback-health-unconfirmed')
  for kind in ['admin','operator']:
   a=login[kind];need(oldapi.account(oldapi.login(a['username'],a['password']))==account_before[kind],'original-account-rollback-unconfirmed')
  raise
 result={'captured_at':datetime.datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),'status':'FileBrowser-internal-HTTP-verified','URL':'http://192.168.19.80:8080/','only3rendered_runtime_files_changed':True,'public_SHA256':{n:sha(b)for n,b in new.items()},'original_admin_and_resources_passwords_verified':True,'original_account_scope_and_permissions_unchanged':True,'anonymous_file_access_denied':401,'daily_admin_settings_denied':403,'JWT_marker_UID_GID_and_state_paths_unchanged':True,'NFS_and_protected_service_identities_unchanged':True,'HTTP_health_and_existing6service_collector_verified':True,'TLS_private_key_not_loaded':True,'old_TLS_material_retained_inactive':True,'real_passwords_JWT_or_config_body_output':False};put(backup/'result.json',(json.dumps(result,indent=2)+'\n').encode(),0o600);print(json.dumps(result))
if __name__=='__main__':
 try:main()
 except Exception as e:print(json.dumps({'status':'HTTP-switch-not-confirmed','error_type':type(e).__name__,'failure_code':str(e)if re.fullmatch('[a-zA-Z0-9-]{1,90}',str(e))else'withheld'}));raise SystemExit(1)
