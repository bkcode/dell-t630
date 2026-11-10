#!/usr/bin/python3
"""Move only the existing HTTP navigation to a reviewed immutable source release."""
import base64,datetime,hashlib,json,os,pathlib,re,socket,subprocess,sys,time,urllib.request
from zoneinfo import ZoneInfo
C=pathlib.Path('/etc/dell-service-directory');B=pathlib.Path('/opt/dell/service-directory/releases');U=pathlib.Path('/etc/systemd/system/dell-service-directory.service');OLD='ddccc2b98bbb3dfdc9de649443dc3fcdc7b4860f';NEW='d56cae553bf95ce0e2c3fe8f258a2f99389aae7c';NAMES={'server.py','services.json','web/index.html','web/app.js','web/style.css'}
def run(a):return subprocess.check_output(a,stderr=subprocess.PIPE,timeout=30)
def sha(b):return hashlib.sha256(b).hexdigest()
def put(p,b):
 t=p.with_name(p.name+'.release-tmp');assert not t.exists();fd=os.open(t,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o644);os.fchmod(fd,0o644)
 with os.fdopen(fd,'wb')as f:f.write(b);f.flush();os.fsync(f.fileno())
 os.replace(t,p)
def frames(m):return{n:run(['systemctl','show',n,'--property=MainPID,ExecMainStartTimestampMonotonic,ActiveState,SubState']).decode().splitlines()for n in m['protected_services_before']}
def main():
 assert os.geteuid()==0 and socket.gethostname()=='publish-service';os.umask(0o077);x=json.load(sys.stdin);assert set(x)=={'files'}and set(x['files'])==NAMES;mp=C/'manifest.json';oldmp=mp.read_bytes();m=json.loads(oldmp);assert m['revision']==OLD and m['transport']=='HTTP';assert frames(m)==m['protected_services_before']
 for n,h in m['files'].items():assert sha((B/OLD/n).read_bytes())==h
 unit=U.read_text();assert '--http'in unit and'--cert'not in unit and'LoadCredential'not in unit and unit.count(str(B/OLD))==2;assert not(B/NEW).exists();release=B/NEW;release.mkdir(mode=0o755);release.chmod(0o755);(release/'web').mkdir(mode=0o755);(release/'web').chmod(0o755);files={n:base64.b64decode(b)for n,b in x['files'].items()};compile(files['server.py'],'server.py','exec')
 assert b'<header class="topbar">'not in files['web/index.html']and b'max-width:none'in files['web/style.css']
 for n,b in files.items():put(release/n,b)
 newunit=unit.replace(str(B/OLD),str(B/NEW));newmp=dict(m,revision=NEW,files={n:sha(b)for n,b in files.items()});assert not(C/'manifest.before-app-http-links.json').exists();put(C/'manifest.before-app-http-links.json',oldmp);put(C/'service.before-app-http-links.conf',unit.encode())
 try:
  run(['systemctl','stop','dell-service-directory.service']);put(U,newunit.encode());put(mp,(json.dumps(newmp,indent=2)+'\n').encode());run(['systemctl','daemon-reload']);run(['systemd-analyze','verify',str(U)]);run(['systemctl','start','dell-service-directory.service']);op=urllib.request.build_opener(urllib.request.ProxyHandler({}));ok=False
  for _ in range(25):
   try:
    with op.open('http://192.168.19.30:9080/api/services',timeout=2)as r:ok=r.status==200 and len(json.load(r)['services'])==14
    if ok:break
   except OSError:time.sleep(.3)
  assert ok and frames(m)==m['protected_services_before'];run(['systemctl','start','dell-guest-health.service'])
 except BaseException:
  run(['systemctl','stop','dell-service-directory.service']);put(U,unit.encode());put(mp,oldmp);run(['systemctl','daemon-reload']);run(['systemctl','start','dell-service-directory.service']);raise
 print(json.dumps({'captured_at':datetime.datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),'status':'internal-HTTP-service-links-verified','URL':'http://192.168.19.30:9080/','revision':NEW,'entry_count':14,'topbar_removed':True,'full_width_layout':True,'protected_services_unchanged':True,'TLS_or_login_credentials_loaded':False,'sourcefiles_sha256':newmp['files']}))
if __name__=='__main__':main()
