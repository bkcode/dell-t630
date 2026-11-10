#!/usr/bin/python3
"""VM250 runtime-only password prefill; never prints credentials or edits source Git."""
import argparse,copy,datetime,hashlib,http.cookiejar,json,os,pathlib,re,shlex,socket,subprocess,sys,time,urllib.request,urllib.error,uuid
from zoneinfo import ZoneInfo
B=pathlib.Path('/opt/dell/penpot');H=B/'runtime/health-supervision';T=pathlib.Path('/root/dell-penpot-prefill-approved-20261110');R=B/'runtime/login-prefill-approved';SECRET=pathlib.Path('/etc/penpot/browser-login-defaults.json');LOCATION=R/'selfhost-login.conf';LOCK=H/'deployment-lock.json';D=['docker','--host','unix:///var/run/docker.sock'];OLD_SOURCE='/opt/dell/penpot/source/frontend/selfhost/login-defaults.example.json';TARGET='/etc/nginx/overrides/server.d/selfhost-login.conf';SHA={str(B/'compose.fresh.yaml'):'0e7c4c2106f720ea0e8035c85b645140b582540a127e05085ca4a41003c05aa6',str(H/'compose.health-supervision.yaml'):'806177bae84d81af31fc42e9f6e4cb06b331e01640e78e975c8d00d9cd90dc18',str(LOCK):'2c6f252611504778810604d89092f4238dd243b633ac1a22cb8b9191e81cb6dc'}
NGINX_SHA256='d88c86636b95a875cee5fd1f5f65df77de4f67be61b94effcdd04dea69510aef'
def need(v,c):
 if not v:raise RuntimeError(c)
def run(a,data=None,timeout=35):
 p=subprocess.run(a,input=data,capture_output=True,timeout=timeout);need(p.returncode==0,'fixed-native-operation-failed');return p.stdout

def sha(b):return hashlib.sha256(b).hexdigest()
def put(p,b,mode=0o644):
 t=p.with_name(p.name+'.prefill-tmp');need(not t.exists(),'unfinished-owned-write');fd=os.open(t,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,mode);os.fchmod(fd,mode)
 with os.fdopen(fd,'wb')as f:f.write(b);f.flush();os.fsync(f.fileno())
 os.replace(t,p)

def compose(files):return D+['compose','--project-directory',str(B),'--project-name','penpot','--env-file','/etc/penpot/.env','-f',str(files[0]),'-f',str(files[1])]
def identity():
 need(os.geteuid()==0 and socket.gethostname()=='penpot-service'and not pathlib.Path('/etc/pve').exists(),'VM250-root-only');need(run(['git','--no-optional-locks','-C',str(B/'source'),'rev-parse','HEAD']).decode().strip()=='ff1783e7865af7aae571c985f03e057631b7af63','existing-custom-Git-required');need(not run(['git','--no-optional-locks','-C',str(B/'source'),'status','--porcelain']).strip(),'source-must-stay-clean')
def owner():return json.loads(pathlib.Path('/etc/penpot/new-identities.json').read_text())['owner']
def owner_login():
 d=owner();jar=http.cookiejar.CookieJar();op=urllib.request.build_opener(urllib.request.ProxyHandler({}),urllib.request.HTTPCookieProcessor(jar));req=urllib.request.Request('http://192.168.19.50:9001/api/main/methods/login-with-password',data=json.dumps({k:d[k]for k in ['email','password']}).encode(),method='POST',headers={'Content-Type':'application/json','Accept':'application/json'})
 with op.open(req,timeout=15)as response:response.read(65536);need(response.status==200 and len(list(jar))>0,'original-owner-login-not-confirmed')
def frontend():return run(D+['ps','-q','--filter','label=com.docker.compose.project=penpot','--filter','label=com.docker.compose.service=penpot-frontend']).decode().strip()
def original_files():
 out={}
 for path,h in SHA.items():
  p=pathlib.Path(path);need(p.resolve()==p and p.stat().st_uid==0 and not p.stat().st_mode&0o022,'trusted-owned-public-file');raw=p.read_bytes();need(sha(raw)==h,'existing-public-contract-drift');out[path]=raw
 return out

def prepare(location):
 import yaml
 identity();old=original_files();private=pathlib.Path('/etc/penpot');st=private.lstat();need(private.resolve()==private and st.st_uid==0 and st.st_gid==0 and st.st_mode&0o777==0o700,'trusted-root-private-directory-required');need(sha(location.encode())==NGINX_SHA256,'exact-reviewed-location-required');need(not T.exists()and not R.exists()and not SECRET.exists(),'fresh-prefill-preparation-required');run(['systemctl','is-active','--quiet','dell-penpot.service']);run(['python3','-I','-B',str(H/'supervisor.py'),'check']);owner_login();d=owner();need(set(['email','password'])<=set(d)and d['email']=='owner@dell.local'and bool(d['password']),'original-owner-required');need('allow 192.168.21.0/24;'in location and'allow 10.66.66.0/24;'in location and'deny all;'in location and'no-store'in location,'fixed-trusted-client-policy');T.mkdir(mode=0o700);(T/'before').mkdir(mode=0o700);(T/'candidate').mkdir(mode=0o700);R.mkdir(mode=0o755);R.chmod(0o755)
 for path,b in old.items():put(T/'before'/pathlib.Path(path).name,b,0o600)
 put(LOCATION,location.encode());put(SECRET,(json.dumps({k:d[k]for k in ['email','password']})+'\n').encode(),0o600);os.chown(SECRET,1001,1001)
 base=old[str(B/'compose.fresh.yaml')];need(base.count(OLD_SOURCE.encode())==1,'one-old-secret-source-required');newbase=base.replace(OLD_SOURCE.encode(),str(SECRET).encode(),1);oldparsed=yaml.safe_load(base);expected=copy.deepcopy(oldparsed);expected['secrets']['login-defaults']['file']=str(SECRET);need(yaml.safe_load(newbase)==expected,'only-prefill-secret-source-change-allowed')
 overlay=old[str(H/'compose.health-supervision.yaml')];anchor=b'    volumes:\n    - type: bind\n      source: ./runtime/health-supervision/frontend-health.sh';need(overlay.count(anchor)==1,'one-reviewed-frontend-mount-anchor');addition=('    volumes:\n    - type: bind\n      source: '+str(LOCATION)+'\n      target: '+TARGET+'\n      read_only: true\n      bind:\n        create_host_path: false\n    - type: bind\n      source: ./runtime/health-supervision/frontend-health.sh').encode();newoverlay=overlay.replace(anchor,addition,1);expected=yaml.safe_load(overlay);expected['services']['penpot-frontend']['volumes'].insert(0,{'type':'bind','source':str(LOCATION),'target':TARGET,'read_only':True,'bind':{'create_host_path':False}});need(yaml.safe_load(newoverlay)==expected,'only-readonly-prefill-location-mount-change-allowed')
 lock=json.loads(old[str(LOCK)]);newlock=copy.deepcopy(lock);mounts=newlock['services']['penpot-frontend']['expected_mounts'];found=[m for m in mounts if m['destination']=='/run/secrets/login-defaults'];need(len(found)==1 and found[0]['source']==OLD_SOURCE and found[0]['rw']is False,'one-reviewed-old-secret-mount-required');found[0]['source']=str(SECRET);need(not any(m['destination']==TARGET for m in mounts),'location-not-previously-overridden');mounts.append({'source':str(LOCATION),'destination':TARGET,'rw':False});newlock['package_file_sha256']['compose.fresh.yaml']=sha(newbase);newlock['package_file_sha256']['runtime/login-prefill-approved/selfhost-login.conf']=sha(location.encode());newlock['supervision_file_sha256']['compose.health-supervision.yaml']=sha(newoverlay);put(T/'candidate/compose.fresh.yaml',newbase,0o600);put(T/'candidate/compose.health-supervision.yaml',newoverlay,0o600);put(T/'candidate/deployment-lock.json',(json.dumps(newlock,indent=2)+'\n').encode(),0o600)
 finish_prepare()

def finish_prepare():
 import yaml
 identity();old=original_files();need(T.exists()and not(T/'prepared.json').exists(),'partial-owned-preparation-required');need(sha(LOCATION.read_bytes())==NGINX_SHA256,'reviewed-location-must-stay-fixed');location=LOCATION.read_text();d=owner();st=SECRET.stat();need(st.st_uid==1001 and st.st_gid==1001 and st.st_mode&0o777==0o600 and not SECRET.is_symlink()and json.loads(SECRET.read_text())=={k:d[k]for k in ['email','password']},'private-owner-defaults-contract')
 newbase=(T/'candidate/compose.fresh.yaml').read_bytes();newoverlay=(T/'candidate/compose.health-supervision.yaml').read_bytes();need(newbase==old[str(B/'compose.fresh.yaml')].replace(OLD_SOURCE.encode(),str(SECRET).encode(),1),'exact-secret-source-candidate-required');expected=yaml.safe_load(old[str(H/'compose.health-supervision.yaml')]);expected['services']['penpot-frontend']['volumes'].insert(0,{'type':'bind','source':str(LOCATION),'target':TARGET,'read_only':True,'bind':{'create_host_path':False}});need(yaml.safe_load(newoverlay)==expected,'exact-readonly-overlay-candidate-required');expected=json.loads(old[str(LOCK)]);found=[m for m in expected['services']['penpot-frontend']['expected_mounts']if m['destination']=='/run/secrets/login-defaults'];need(len(found)==1 and found[0]['source']==OLD_SOURCE,'one-old-secret-lock-required');found[0]['source']=str(SECRET);expected['services']['penpot-frontend']['expected_mounts'].append({'source':str(LOCATION),'destination':TARGET,'rw':False});expected['package_file_sha256']['compose.fresh.yaml']=sha(newbase);expected['package_file_sha256']['runtime/login-prefill-approved/selfhost-login.conf']=sha(location.encode());expected['supervision_file_sha256']['compose.health-supervision.yaml']=sha(newoverlay);need(json.loads((T/'candidate/deployment-lock.json').read_text())==expected,'exact-reviewed-lock-candidate-required')
 cfg=json.loads(run(compose([T/'candidate/compose.fresh.yaml',T/'candidate/compose.health-supervision.yaml'])+['config','--format','json']));need(len(cfg['services'])==11 and cfg['secrets']['login-defaults']['file']==str(SECRET),'exact11-new-config');need({n:s['image']for n,s in cfg['services'].items()}=={n:s['image']for n,s in json.loads(run(compose([B/'compose.fresh.yaml',H/'compose.health-supervision.yaml'])+['config','--format','json']))['services'].items()},'all-image-references-must-stay-fixed')
 f=frontend();need(bool(f),'frontend-required-for-native-parser-check');token=uuid.uuid4().hex;tmp='/tmp/dell-prefill-'+token;test='error_log stderr warn;\npid '+tmp+'/nginx.pid;\nevents {}\nhttp { access_log off; server { listen 127.0.0.1:18089;\n'+location+'\n} }\n';shell='umask 077; mkdir '+shlex.quote(tmp)+'; trap '+shlex.quote('rm -f '+tmp+'/nginx.conf '+tmp+'/nginx.pid; for n in client_body_temp proxy_temp fastcgi_temp uwsgi_temp scgi_temp; do if [ -d '+tmp+'/$n ]; then rmdir '+tmp+'/$n; fi; done; rmdir '+tmp)+' EXIT; cat > '+shlex.quote(tmp+'/nginx.conf')+'; nginx -t -p '+shlex.quote(tmp+'/')+' -c '+shlex.quote(tmp+'/nginx.conf');run(D+['exec','-i',f,'sh','-ec',shell],test.encode());s={'status':'prepared-native-parser-and-exact11-config-passed','candidate_public_SHA256':{n:sha((T/'candidate'/n).read_bytes())for n in ['compose.fresh.yaml','compose.health-supervision.yaml','deployment-lock.json']},'Git_code_or_images_changed':False,'original_owner_login_verified':True,'real_password_output':False};put(T/'prepared.json',(json.dumps(s,indent=2)+'\n').encode(),0o600);print(json.dumps(s))

def health_ready():
 p=subprocess.run(['systemctl','is-active','--quiet','dell-penpot.service']);
 if p.returncode:return False
 names=run(D+['ps','-q','--filter','label=com.docker.compose.project=penpot']).decode().split()
 if len(names)!=11:return False
 for cid in names:
  d=json.loads(run(D+['inspect','--format','{"image":{{json .Image}},"health":{{json .State.Health.Status}}}',cid]));
  if d['health']!='healthy':return False
 return True

def apply():
 identity();old=original_files();need((T/'prepared.json').exists(),'prepared-transaction-required');prepared=json.loads((T/'prepared.json').read_text());names={'compose.fresh.yaml':B/'compose.fresh.yaml','compose.health-supervision.yaml':H/'compose.health-supervision.yaml','deployment-lock.json':LOCK}
 for n,p in names.items():need(sha((T/'candidate'/n).read_bytes())==prepared['candidate_public_SHA256'][n]and p.read_bytes()==old[str(p)],'public-CAS-before-maintenance')
 initial_identity=pathlib.Path('/etc/penpot/new-identities.json').read_bytes()
 # stop is bounded separately, and a stopped supervisor cannot race a lock update.
 p=subprocess.run(['systemctl','stop','dell-penpot.service'],capture_output=True,timeout=180);need(p.returncode==0,'controlled-stop-failed');need(subprocess.run(['systemctl','is-active','--quiet','dell-penpot.service']).returncode!=0,'supervisor-still-active')
 try:
  for n,p in names.items():put(p,(T/'candidate'/n).read_bytes())
  run(['python3','-I','-B',str(H/'supervisor.py'),'check']);run(['systemctl','start','--no-block','dell-penpot.service']);deadline=time.monotonic()+240
  while time.monotonic()<deadline:
   if health_ready():break
   time.sleep(2)
  else:raise RuntimeError('controlled-start-not11healthy')
  run(['python3','-I','-B',str(H/'supervisor.py'),'check']);f=frontend();request="exec 3<>/dev/tcp/127.0.0.1/8080; printf 'GET /js/selfhost-login.json HTTP/1.0\\r\\nHost: localhost\\r\\nConnection: close\\r\\n\\r\\n' >&3; cat <&3";raw=run(D+['exec',f,'/usr/bin/timeout','6','/bin/bash','-ec',request]);headers,body=raw.split(b'\r\n\r\n',1);need(re.match(rb'HTTP/1\.[01] 200',headers)is not None and b'no-store'in headers.lower(),'local-prefill-response-must-be-uncached200');d=owner();need(json.loads(body)=={k:d[k]for k in ['email','password']},'prefill-must-match-existing-owner');backend=run(D+['ps','-q','--filter','label=com.docker.compose.project=penpot','--filter','label=com.docker.compose.service=penpot-backend']).decode().strip();negative=run(D+['exec',backend,'/usr/bin/curl','--max-time','6','--noproxy','*','-sS','-o','/dev/null','-w','%{http_code}','-H','X-Real-IP: 192.168.21.230','-H','X-Forwarded-For: 192.168.21.230','http://penpot-frontend:8080/js/selfhost-login.json']).decode().strip();need(negative=='403','unapproved-Docker-peer-must-not-read-prefill');owner_login();need(pathlib.Path('/etc/penpot/new-identities.json').read_bytes()==initial_identity,'original-identity-file-changed');identity()
 except BaseException:
  p=subprocess.run(['systemctl','stop','dell-penpot.service'],capture_output=True,timeout=180);need(p.returncode==0,'recovery-stop-unconfirmed')
  for n,p in names.items():put(p,(T/'before'/n).read_bytes())
  run(['python3','-I','-B',str(H/'supervisor.py'),'check']);run(['systemctl','start','--no-block','dell-penpot.service']);deadline=time.monotonic()+240
  while time.monotonic()<deadline:
   if health_ready():break
   time.sleep(2)
  else:raise RuntimeError('old-config-recovery-not11healthy')
  raise
 out={'captured_at':datetime.datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),'status':'prefill-enabled-existing-owner-and-source-ACL-verified','owner_email':owner()['email'],'original_password_and_identity_file_unchanged':True,'prefill_JSON_matches_existing_owner':True,'unapproved_Docker_peer_with_spoofed_headers_status':negative,'containers_healthy':11,'Git_HEAD':'ff1783e7865af7aae571c985f03e057631b7af63','Git_clean':True,'image_references_unchanged':True,'native_supervisor_contract_passed':True,'password_values_or_hashes_output':False,'real_client_LAN_browser_verification_pending':True};put(T/'applied.json',(json.dumps(out,indent=2)+'\n').encode(),0o600);print(json.dumps(out))

def main():
 os.umask(0o077);a=argparse.ArgumentParser();a.add_argument('action',choices=['prepare','finish-prepare','apply']);x=a.parse_args();prepare(sys.stdin.read())if x.action=='prepare'else finish_prepare()if x.action=='finish-prepare'else apply()
if __name__=='__main__':
 try:main()
 except Exception as e:print(json.dumps({'status':'prefill-not-confirmed','error_type':type(e).__name__,'fixed_code':str(e)if re.fullmatch('[a-zA-Z0-9-]{1,90}',str(e))else'private-details-withheld'}));raise SystemExit(1)
