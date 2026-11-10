#!/usr/bin/python3
"""Fixed VM220 navigation transport change; preserves old release for rollback."""
import base64,datetime,hashlib,json,os,pathlib,re,socket,subprocess,sys,time,urllib.request
from zoneinfo import ZoneInfo
B=pathlib.Path('/opt/dell/service-directory/releases');C=pathlib.Path('/etc/dell-service-directory');U=pathlib.Path('/etc/systemd/system/dell-service-directory.service');OLD='63b8c0873936e94f8483c4f1f8747aedb0180d43';NEW='c141506ec6a59dd7f123cabc00f099f1cf87d4e1';NAMES={'server.py','services.json','web/index.html','web/app.js','web/style.css'}
def run(a):return subprocess.check_output(a,stderr=subprocess.PIPE,timeout=30)
def sha(b):return hashlib.sha256(b).hexdigest()
def put(p,raw,mode=0o644):
 t=p.with_name(p.name+'.http-tmp');assert not t.exists();fd=os.open(t,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,mode);os.fchmod(fd,mode)
 with os.fdopen(fd,'wb')as f:f.write(raw);f.flush();os.fsync(f.fileno())
 os.replace(t,p)
def frames(m):return {n:run(['systemctl','show',n,'--property=MainPID,ExecMainStartTimestampMonotonic,ActiveState,SubState']).decode().splitlines()for n in m['protected_services_before']}
def main():
 assert os.geteuid()==0 and socket.gethostname()=='publish-service';os.umask(0o077);x=json.load(sys.stdin);assert set(x)=={'files'}and set(x['files'])==NAMES;mfile=C/'manifest.json';oldmanifest=mfile.read_bytes();m=json.loads(oldmanifest);assert m['revision']==OLD;assert frames(m)==m['protected_services_before']
 for n,h in m['files'].items():assert sha((B/OLD/n).read_bytes())==h
 oldunit=U.read_text();expected='ExecStart=/usr/bin/python3 -I -B '+str(B/OLD/'server.py')+' --bind 192.168.19.30 --port 9080 --catalog '+str(B/OLD/'services.json')+' --cert /etc/dell-service-directory/tls.crt --key %d/tls-key';assert oldunit.count(expected)==1 and oldunit.count('LoadCredential=tls-key:/etc/dell-service-directory/secrets/tls-key\n')==1
 assert not(B/NEW).exists()and not(C/'manifest.before-http.json').exists();release=B/NEW;release.mkdir(mode=0o755);release.chmod(0o755);(release/'web').mkdir(mode=0o755);(release/'web').chmod(0o755);files={n:base64.b64decode(raw)for n,raw in x['files'].items()};compile(files['server.py'],'server.py','exec')
 for n,raw in files.items():put(release/n,raw)
 newunit=oldunit.replace(expected,'ExecStart=/usr/bin/python3 -I -B '+str(release/'server.py')+' --bind 192.168.19.30 --port 9080 --catalog '+str(release/'services.json')+' --http').replace('LoadCredential=tls-key:/etc/dell-service-directory/secrets/tls-key\n','');assert 'LoadCredential='not in newunit and '--cert'not in newunit and '--key'not in newunit
 put(C/'manifest.before-http.json',oldmanifest,0o600);put(C/'service.before-http.conf',oldunit.encode(),0o600)
 updated=dict(m,revision=NEW,files={n:sha(raw)for n,raw in files.items()},transport='HTTP',URL='http://192.168.19.30:9080/')
 try:
  run(['systemctl','stop','dell-service-directory.service']);put(U,newunit.encode());put(mfile,(json.dumps(updated,indent=2)+'\n').encode());run(['systemctl','daemon-reload']);run(['systemd-analyze','verify',str(U)]);run(['systemctl','start','dell-service-directory.service']);op=urllib.request.build_opener(urllib.request.ProxyHandler({}));ok=False
  for _ in range(25):
   try:
    with op.open('http://192.168.19.30:9080/api/services',timeout=2)as r:rows=json.load(r)['services'];ok=r.status==200 and len(rows)==14 and any(z['url']=='http://192.168.19.30:9080/'for z in rows)
    if ok:break
   except OSError:time.sleep(.3)
  assert ok and frames(m)==m['protected_services_before']
 except BaseException:
  run(['systemctl','stop','dell-service-directory.service']);put(U,oldunit.encode());put(mfile,oldmanifest);run(['systemctl','daemon-reload']);run(['systemctl','start','dell-service-directory.service']);raise
 result={'captured_at':datetime.datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),'status':'plain-HTTP-navigation-verified','URL':'http://192.168.19.30:9080/','revision':NEW,'entry_count':14,'no_TLS_credentials_loaded':True,'sourcefiles_sha256':updated['files'],'protected_services_unchanged':True,'firewall_or_other_service_changes':False,'old_HTTPS_material_retained_as_inactive_history':True};print(json.dumps(result))
if __name__=='__main__':main()
