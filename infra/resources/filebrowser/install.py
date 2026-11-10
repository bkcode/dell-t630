#!/usr/bin/python3
"""Fresh VM280-only native management service; never formats or rewrites shared files."""
import argparse,datetime,fcntl,grp,hashlib,importlib.util,json,os,pathlib,pwd,re,socket,stat,subprocess,sys
HERE=pathlib.Path(__file__).resolve().parent
CONFIG=pathlib.Path('/etc/dell-filebrowser');STATE=pathlib.Path('/var/lib/dell-filebrowser');MANAGER=pathlib.Path('/var/lib/dell-filebrowser-manager');CODE=pathlib.Path('/opt/dell/filebrowser')
DIGEST='4af557de16603bdfba2ae87b7807b8654612c542b2deff826eedee72086a5da2';BINARY=CODE/'releases/v2.1.4-beta/filebrowser';UUID='57d8158e-5fcf-4dd2-8cb4-b47b1e54ed7b'
def need(ok,code):
 if not ok:raise RuntimeError(code)
def run(args,timeout=25,allowed=(0,)):
 p=subprocess.run(args,capture_output=True,timeout=timeout)
 need(p.returncode in allowed,'fixed-native-operation-failed');return p.stdout

def trusted(path,mode=None):
 for p in [path,*path.parents]:
  if p.exists()or p.is_symlink():
   s=p.lstat();need(not stat.S_ISLNK(s.st_mode)and s.st_uid==0 and not s.st_mode&0o022,'untrusted-root-path')
 if mode is not None:need(stat.S_IMODE(path.stat().st_mode)==mode,'unexpected-path-mode')

def fresh(path,data,mode):
 trusted(path.parent);need(not path.exists()and not path.is_symlink(),'existing-config-refused')
 path.parent.mkdir(parents=True,exist_ok=True,mode=0o755);trusted(path.parent)
 fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,mode);os.fchmod(fd,mode)
 with os.fdopen(fd,'wb')as f:f.write(data);f.flush();os.fsync(f.fileno())

def directory(path,mode,uid=0,gid=0):
 # mkdir's requested mode is reduced by umask; chmod only these fixed owned paths.
 trusted(path.parent)
 if path.exists()or path.is_symlink():
  st=path.lstat();need(stat.S_ISDIR(st.st_mode)and st.st_uid==uid and st.st_gid==gid and not stat.S_ISLNK(st.st_mode),'directory-identity-mismatch')
 else:path.mkdir(mode=mode)
 os.chown(path,uid,gid);path.chmod(mode)

def destinations():
 return {'config.yaml':(CONFIG/'config.yaml',0o644),'dell-filebrowser.service':(pathlib.Path('/etc/systemd/system/dell-filebrowser.service'),0o644),'dell-filebrowser-firewall.service':(pathlib.Path('/etc/systemd/system/dell-filebrowser-firewall.service'),0o644),'firewall.py':(CODE/'firewall.py',0o644),'launch.py':(CODE/'launch.py',0o644),'input.nft':(CONFIG/'input.nft',0o644)}

def public_hashes():
 result={}
 for name,(path,mode)in destinations().items():
  trusted(path,mode);st=path.stat();need(stat.S_ISREG(st.st_mode)and st.st_nlink==1 and st.st_size<=65536,'public-file-invalid')
  result[name]=hashlib.sha256(path.read_bytes()).hexdigest()
 return result

def credential_sources():
 return {name:CONFIG/'secrets'/name for name in ['jwt-key','admin-password']}

def private_preflight():
 trusted(CONFIG,0o755);trusted(CONFIG/'secrets',0o700);trusted(MANAGER,0o700)
 for name in ['admin-password','jwt-key','login.json']:
  path=CONFIG/'secrets'/name;trusted(path,0o600);st=path.stat()
  need(stat.S_ISREG(st.st_mode)and st.st_nlink==1 and 0<st.st_size<=65536,'private-file-invalid')
 for path in [STATE,STATE/'cache']:
  st=path.lstat();need(stat.S_ISDIR(st.st_mode)and not stat.S_ISLNK(st.st_mode)and st.st_uid==2000 and st.st_gid==2980 and stat.S_IMODE(st.st_mode)==0o700,'private-state-invalid')
 for path in [CODE,CODE/'releases',BINARY.parent]:trusted(path,0o755)
 for path in [CONFIG,CODE,*CODE.parents]:need(path.stat().st_mode&0o001,'public-parent-not-traversable')
 trusted(BINARY,0o755)

def metadata():
 names=['nfs-server.service','nfs-mountd.service','dell-resources-firewall.service','ssh.service','systemd-networkd.service','prometheus-node-exporter.service']
 return {n:run(['systemctl','show',n,'--property=MainPID,ExecMainStartTimestampMonotonic,ActiveState,SubState']).decode().splitlines()for n in names}

def identity():
 need(os.geteuid()==0 and socket.gethostname()=='resource-service'and not pathlib.Path('/etc/pve').exists(),'VM280-guest-root-only')
 ip=[a['local']for i in json.loads(run(['ip','-j','-4','addr','show','scope','global']))for a in i.get('addr_info',[])];need(ip==['192.168.19.80'],'resource-exact-IP')
 rows=json.loads(run(['findmnt','-J','--mountpoint','/srv/resources','-o','TARGET,UUID,FSTYPE,OPTIONS']))['filesystems'];need(len(rows)==1 and rows[0]['uuid']==UUID and rows[0]['fstype']=='ext4','existing-resource-UUID-required')
 root=pathlib.Path('/srv/resources');need(root.stat().st_uid==0 and root.stat().st_gid==2980 and stat.S_IMODE(root.stat().st_mode)==0o2770,'original-resource-permissions-required')
 need(grp.getgrgid(2980).gr_name=='resources','original-resource-group-required');trusted(BINARY);need(BINARY.is_file()and not BINARY.is_symlink()and BINARY.stat().st_nlink==1 and BINARY.stat().st_size==29064968 and hashlib.sha256(BINARY.read_bytes()).hexdigest()==DIGEST,'official-binary-digest-required')

def prepare():
 identity();trusted(HERE);before=metadata();need(not CONFIG.exists()and not STATE.exists()and not MANAGER.exists(),'fresh-management-install-only')
 for n in ['dell-filebrowser.service','dell-filebrowser-firewall.service']:need(not pathlib.Path('/etc/systemd/system',n).exists(),'management-unit-already-exists')
 for name in ['filebrowser']:
  try:pwd.getpwnam(name)
  except KeyError:pass
  else:raise RuntimeError('service-name-collision')
 try:pwd.getpwuid(2000)
 except KeyError:pass
 else:raise RuntimeError('service-UID-collision')
 sock=socket.socket()
 try:sock.bind(('192.168.19.80',8080))
 finally:sock.close()
 data=json.load(sys.stdin);need(set(data)=={'admin_password','operator_password','jwt_key'},'fixed-private-input-keys')
 for v in data.values():need(isinstance(v,str)and re.fullmatch('[A-Za-z0-9_-]{32,128}',v)is not None,'strong-private-input-required')
 spec=importlib.util.spec_from_file_location('management_renderer',HERE/'prepare.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);files=mod.render()
 mapping=destinations()
 need(set(files)==set(mapping),'fixed-rendered-files-required')
 directory(MANAGER,0o700);fresh(MANAGER/'before-services.json',(json.dumps(before,indent=2)+'\n').encode(),0o600)
 run(['useradd','--uid','2000','--gid','2980','--no-create-home','--home-dir',str(STATE),'--shell','/usr/sbin/nologin','--no-log-init','filebrowser'])
 directory(STATE,0o700,2000,2980)
 # STATE is intentionally app-owned; its cache is created without trusting it as root-owned.
 cache=STATE/'cache';cache.mkdir(mode=0o700);os.chown(cache,2000,2980);cache.chmod(0o700)
 directory(CONFIG,0o755);directory(CONFIG/'secrets',0o700)
 for public in [CODE,CODE/'releases',BINARY.parent]:directory(public,0o755)
 BINARY.chmod(0o755)
 credentials=credential_sources()
 fresh(credentials['admin-password'],(data['admin_password']+'\n').encode(),0o600);fresh(credentials['jwt-key'],(data['jwt_key']+'\n').encode(),0o600)
 login={'URL':'http://192.168.19.80:8080/','admin':{'username':'admin','password':data['admin_password']},'operator':{'username':'resources','password':data['operator_password']}}
 fresh(CONFIG/'secrets/login.json',(json.dumps(login,indent=2)+'\n').encode(),0o600)
 for name,(dest,mode)in mapping.items():fresh(dest,files[name].encode(),mode)
 private_preflight();hashes=public_hashes();need(hashes=={name:hashlib.sha256(value.encode()).hexdigest()for name,value in files.items()},'public-write-readback-mismatch')
 run(['systemctl','daemon-reload']);run(['systemd-analyze','verify','/etc/systemd/system/dell-filebrowser.service','/etc/systemd/system/dell-filebrowser-firewall.service'])
 run(['python3','-I','-B',str(CODE/'firewall.py'),'--check']);need(metadata()==before,'protected-services-changed')
 result={'at':datetime.datetime.now().astimezone().isoformat(),'status':'management-configuration-prepared-not-started','tag':'v2.1.4-beta','service_UID':2000,'shared_GID':2980,'native_no_Docker':True,'shared_files_or_permissions_rewritten':False,'protected_service_identities_unchanged':True,'public_files_sha256':hashes,'transport':'HTTP','HTTP_policy':'production-internal-management-HTTP-user-authorized'};fresh(MANAGER/'prepared.json',(json.dumps(result,indent=2)+'\n').encode(),0o600);print(json.dumps(result))

def activate():
 identity();private_preflight()
 for name in ['prepared.json','before-services.json']:trusted(MANAGER/name,0o600)
 need(not(MANAGER/'activated.json').exists()and not(MANAGER/'activated.json').is_symlink(),'management-already-activated')
 prepared=json.loads((MANAGER/'prepared.json').read_text());need(prepared.get('status')=='management-configuration-prepared-not-started'and public_hashes()==prepared.get('public_files_sha256'),'prepared-public-files-drifted')
 before=json.loads((MANAGER/'before-services.json').read_text());need(metadata()==before,'protected-services-drifted-before-start')
 try:
  run(['systemctl','enable','--now','dell-filebrowser-firewall.service','dell-filebrowser.service'],timeout=60)
  need(metadata()==before,'protected-services-changed-on-start');need(run(['systemctl','is-active','dell-filebrowser.service']).decode().strip()=='active','management-not-active')
  result={'at':datetime.datetime.now().astimezone().isoformat(),'status':'management-service-started-authentication-and-upload-acceptance-pending','protected_service_identities_unchanged':True,'port':8080,'transport':'HTTP','HTTPS':False,'NFS_or_client_restarts':False,'Java_or_business_HTTP_started':False}
  fresh(MANAGER/'activated.json',(json.dumps(result,indent=2)+'\n').encode(),0o600)
 except Exception:
  # Leave the protective firewall in place. Never touch existing NFS or other services.
  run(['systemctl','disable','--now','dell-filebrowser.service'],timeout=30)
  raise
 print(json.dumps(result))

def main():
 os.umask(0o077);a=argparse.ArgumentParser();a.add_argument('action',choices=['prepare','activate']);x=a.parse_args()
 need(os.geteuid()==0,'guest-root-required');identity()
 fd=os.open('/run/dell-filebrowser-install.lock',os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW,0o600)
 with os.fdopen(fd,'r+b')as lock:
  st=os.fstat(lock.fileno());need(stat.S_ISREG(st.st_mode)and st.st_uid==0 and st.st_nlink==1 and stat.S_IMODE(st.st_mode)==0o600,'untrusted-install-lock')
  fcntl.flock(lock.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
  prepare()if x.action=='prepare'else activate()
if __name__=='__main__':
 try:main()
 except Exception as e:
  message=str(e);print(json.dumps({'status':'management-install-not-confirmed','error_type':type(e).__name__,'failure_code':message if re.fullmatch('[A-Za-z0-9-]{1,100}',message)else'private-native-details-withheld'}));raise SystemExit(1)
