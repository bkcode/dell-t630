#!/usr/bin/python3
"""VM220 fresh service-directory installation. No publisher/Java/Nexus operations."""
import argparse,base64,datetime,grp,hashlib,json,os,pathlib,pwd,re,socket,stat,subprocess,sys,urllib.request,ssl
from zoneinfo import ZoneInfo
BASE=pathlib.Path('/opt/dell/service-directory');CONFIG=pathlib.Path('/etc/dell-service-directory');EXPECTED_FILES={'server.py','web/index.html','web/app.js','web/style.css','services.json'}
def require(v,c):
 if not v:raise RuntimeError(c)
def run(a,t=25):
 p=subprocess.run(a,capture_output=True,timeout=t);require(p.returncode==0,'fixed-native-operation-failed');return p.stdout

def safe(p):
 for x in [p,*p.parents]:
  if x.exists()or x.is_symlink():
   s=x.lstat();require(not stat.S_ISLNK(s.st_mode)and s.st_uid==0 and not s.st_mode&0o022,'untrusted-config-path')

def mkdir(p,mode,uid=0,gid=0):
 safe(p.parent);require(not p.exists()and not p.is_symlink(),'existing-directory-refused');p.mkdir(mode=mode);os.chown(p,uid,gid);p.chmod(mode)
def put(p,b,mode):
 safe(p.parent);require(not p.exists()and not p.is_symlink(),'existing-file-refused');fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,mode);os.fchmod(fd,mode)
 with os.fdopen(fd,'wb')as f:f.write(b);f.flush();os.fsync(f.fileno())

def identity():
 require(os.geteuid()==0 and socket.gethostname()=='publish-service'and not pathlib.Path('/etc/pve').exists(),'VM220-root-only')
 ips=[a['local']for i in json.loads(run(['ip','-j','-4','addr','show','scope','global']))if i['ifname']=='eth0'for a in i.get('addr_info',[])];require(ips==['192.168.19.30'],'fixed-publisher-IP')

def frame():
 units=['ssh.service','docker.service','prometheus-node-exporter.service','dell-guest-health.timer','systemd-networkd.service']
 return {n:run(['systemctl','show',n,'--property=MainPID,ExecMainStartTimestampMonotonic,ActiveState,SubState']).decode().splitlines()for n in units}

def main():
 identity();os.umask(0o077);x=json.load(sys.stdin);require(set(x)=={'files','revision'},'fixed-input-shape');require(set(x['files'])==EXPECTED_FILES,'exact-release-files');require(re.fullmatch('[a-f0-9]{40}',x['revision'])is not None,'committed-source-revision-required')
 for p in [BASE,CONFIG]:safe(p.parent);require(not p.exists()and not p.is_symlink(),'new-service-path-collision')
 for n in ['servicedirectory',2001]:
  try:pwd.getpwnam(n)if isinstance(n,str)else pwd.getpwuid(n)
  except KeyError:pass
  else:raise RuntimeError('service-user-collision')
 try:grp.getgrgid(2001)
 except KeyError:pass
 else:raise RuntimeError('service-group-collision')
 for n in ['dell-service-directory.service','dell-service-directory-firewall.service']:require(not pathlib.Path('/etc/systemd/system',n).exists(),'new-unit-collision')
 with socket.socket()as s:s.bind(('192.168.19.30',9080))
 files={n:base64.b64decode(raw)for n,raw in x['files'].items()};require(all(len(b)<256*1024 for b in files.values()),'release-file-size');compile(files['server.py'],'server.py','exec');catalog=json.loads(files['services.json']);require(set(catalog)=={'services'}and len(catalog['services'])==14,'reviewed-initial14addresses-required');before=frame()
 run(['groupadd','--gid','2001','servicedirectory']);run(['useradd','--uid','2001','--gid','2001','--no-create-home','--no-log-init','--home-dir',str(BASE),'--shell','/usr/sbin/nologin','servicedirectory'])
 mkdir(BASE,0o755);mkdir(BASE/'releases',0o755);release=BASE/'releases'/x['revision'];mkdir(release,0o755);mkdir(release/'web',0o755)
 for name,b in files.items():put(release/name,b,0o644)
 mkdir(CONFIG,0o755);mkdir(CONFIG/'secrets',0o700)
 run(['openssl','req','-x509','-newkey','rsa:3072','-nodes','-sha256','-days','365','-keyout',str(CONFIG/'secrets/tls-key'),'-out',str(CONFIG/'tls.crt'),'-subj','/CN=publish-service.dell.home.arpa','-addext','subjectAltName=IP:192.168.19.30,DNS:publish-service.dell.home.arpa','-addext','basicConstraints=critical,CA:FALSE','-addext','extendedKeyUsage=serverAuth'],40);(CONFIG/'secrets/tls-key').chmod(0o600);(CONFIG/'tls.crt').chmod(0o644)
 nft='''table inet dell_service_directory_input {
 chain input {
  type filter hook input priority -6; policy accept;
  tcp dport 9080 ct state invalid counter drop
  iifname "lo" tcp dport 9080 accept
  ip saddr { 192.168.21.0/24, 10.66.66.0/24, 192.168.19.30 } tcp dport 9080 counter accept
  tcp dport 9080 counter drop
  udp dport 9080 counter drop
 }
}
''';put(CONFIG/'input.nft',nft.encode(),0o644)
 firewall='''#!/usr/bin/python3
import os,json,pathlib,subprocess,socket,stat
assert os.geteuid()==0 and socket.gethostname()=='publish-service'
p=pathlib.Path('/etc/dell-service-directory/input.nft');assert not p.is_symlink()and p.stat().st_uid==0 and not p.stat().st_mode&0o022
expected='''+repr(nft)+'''
assert p.read_text()==expected
r=subprocess.run(['nft','-j','list','tables'],capture_output=True,check=True,timeout=10);tables=json.loads(r.stdout)['nftables'];own=any(v.get('table',{}).get('family')=='inet'and v.get('table',{}).get('name')=='dell_service_directory_input'for v in tables)
body=((('delete table inet dell_service_directory_input'+chr(10))if own else'')+expected).encode()
subprocess.run(['nft','-c','-f','-'],input=body,capture_output=True,check=True,timeout=10)
subprocess.run(['nft','-f','-'],input=body,capture_output=True,check=True,timeout=10)
''';put(BASE/'firewall.py',firewall.encode(),0o644)
 fw='''[Unit]
Description=Dell service-directory input policy
Before=dell-service-directory.service
[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/usr/bin/python3 -I -B /opt/dell/service-directory/firewall.py
[Install]
WantedBy=multi-user.target
'''
 unit='''[Unit]
Description=Service address directory
After=network-online.target dell-service-directory-firewall.service
Wants=network-online.target
Requires=dell-service-directory-firewall.service
StartLimitIntervalSec=120
StartLimitBurst=3
[Service]
Type=simple
User=servicedirectory
Group=servicedirectory
WorkingDirectory=/opt/dell/service-directory
UMask=0077
LoadCredential=tls-key:/etc/dell-service-directory/secrets/tls-key
ExecStart=/usr/bin/python3 -I -B '''+str(release/'server.py')+''' --bind 192.168.19.30 --port 9080 --catalog '''+str(release/'services.json')+''' --cert /etc/dell-service-directory/tls.crt --key %d/tls-key
Restart=on-failure
RestartSec=5
NoNewPrivileges=yes
ProtectSystem=strict
ProtectHome=yes
PrivateTmp=yes
MemoryMax=128M
CPUQuota=30%
TasksMax=32
LimitNOFILE=256
[Install]
WantedBy=multi-user.target
'''
 put(pathlib.Path('/etc/systemd/system/dell-service-directory-firewall.service'),fw.encode(),0o644);put(pathlib.Path('/etc/systemd/system/dell-service-directory.service'),unit.encode(),0o644);run(['systemctl','daemon-reload']);run(['systemd-analyze','verify','/etc/systemd/system/dell-service-directory-firewall.service','/etc/systemd/system/dell-service-directory.service'])
 manifest={'revision':x['revision'],'repository':'bkcode/deploy','files':{n:hashlib.sha256(b).hexdigest()for n,b in files.items()},'protected_services_before':before};put(CONFIG/'manifest.json',(json.dumps(manifest,indent=2)+'\n').encode(),0o644)
 try:
  run(['systemctl','enable','--now','dell-service-directory-firewall.service','dell-service-directory.service'],50);require(before==frame(),'protected-publisher-services-changed')
 except Exception:run(['systemctl','disable','--now','dell-service-directory.service']);raise
 out={'at':datetime.datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),'status':'service-directory-started-native-acceptance-pending','URL':'https://192.168.19.30:9080/','repository':'bkcode/deploy','revision':x['revision'],'service_UID_GID':2001,'initial_web_addresses':14,'anonymous_read_only':True,'application_accounts_or_passwords_created':False,'protected_services_unchanged':True,'Java_or_Nexus_or_Penpot_updated':False,'source_keys_or_secrets_copied_to_release':False,'certificate_fingerprint':run(['openssl','x509','-in',str(CONFIG/'tls.crt'),'-noout','-fingerprint','-sha256']).decode().strip()};print(json.dumps(out))
if __name__=='__main__':
 try:main()
 except Exception as e:print(json.dumps({'status':'service-directory-installation-not-confirmed','error_type':type(e).__name__,'failure_code':str(e)if re.fullmatch('[a-zA-Z0-9-]{1,100}',str(e))else'withheld'}));raise SystemExit(1)
