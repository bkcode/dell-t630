#!/usr/bin/env python3
"""Online Grafana SQLite backup plus network-none app restore of an owned synthetic dashboard."""
import os,socket,json,subprocess,sqlite3,uuid,hashlib,time,urllib.request,urllib.error,base64,shutil,tarfile,datetime
from pathlib import Path
assert os.geteuid()==0 and socket.gethostname()=='ops-service' and not Path('/etc/pve').exists()
fs=json.loads(subprocess.check_output(['findmnt','-J','-T','/srv/dell-data','-o','TARGET,UUID'],text=True))['filesystems'];assert len(fs)==1 and fs[0]['target']=='/srv/dell-data' and fs[0]['uuid']=='01b1f302-27be-4fbd-b4af-b8e782d85dea'
bundle=Path('/opt/dell/ops');password=(bundle/'secrets/grafana-admin-password').read_text().strip();uid='dell-backup-'+uuid.uuid4().hex[:12]
headers={'Authorization':'Basic '+base64.b64encode(('dell_admin:'+password).encode()).decode()}
base='http://10.63.30.40:3000'
def api(method,path,body=None):
 h=dict(headers);data=None
 if body is not None:data=json.dumps(body).encode();h['Content-Type']='application/json'
 with urllib.request.urlopen(urllib.request.Request(base+path,data=data,method=method,headers=h),timeout=15) as r:return json.load(r)
api('POST','/api/dashboards/db',{'dashboard':{'id':None,'uid':uid,'title':'Dell backup acceptance '+uid,'schemaVersion':41,'panels':[]},'overwrite':False})
root=Path('/root/dell-app-backups');root.mkdir(exist_ok=True,mode=0o700);root.chmod(0o700)
folder=root/uid;folder.mkdir(mode=0o700);restored=folder/'restore';restored.mkdir(mode=0o700)
source=Path('/srv/dell-data/ops/grafana/grafana.db');assert source.is_file() and not source.is_symlink()
backup=folder/'grafana.db'
with sqlite3.connect('file:'+str(source)+'?mode=ro',uri=True) as src,sqlite3.connect(backup) as dst:src.backup(dst)
backup.chmod(0o600)
with sqlite3.connect('file:'+str(backup)+'?mode=ro',uri=True) as db:
 assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
 # Grafana13 stores dashboards in unified resource tables; use actual restored API below.
shutil.copyfile(backup,restored/'grafana.db');os.chown(restored,472,472);restored.chmod(0o700);os.chown(restored/'grafana.db',472,472);(restored/'grafana.db').chmod(0o600)
image=json.loads((bundle/'images.lock.json').read_text())['images']['grafana']['reference'];name='dell-grafana-restore-'+uuid.uuid4().hex[:12]
started=time.monotonic();passed=False
try:
 subprocess.run(['docker','--host','unix:///var/run/docker.sock','run','--detach','--name',name,'--network','none','--restart','no','--read-only','--user','472:472','--cpus','0.5','--memory','512m','--memory-swap','512m','--pids-limit','128','--cap-drop','ALL','--security-opt','no-new-privileges:true','--tmpfs','/tmp:size=64m,mode=1777','--mount','type=bind,src='+str(restored)+',dst=/var/lib/grafana','--env','GF_LOG_MODE=console','--env','GF_LOG_LEVEL=warn','--env','GF_PATHS_LOGS=/tmp/logs','--env','GF_PATHS_PLUGINS=/tmp/plugins','--env','GF_PLUGINS_PREINSTALL_DISABLED=true',image],check=True,capture_output=True,timeout=30)
 request_config='silent\nshow-error\nfail\nmax-time = 5\nuser = "dell_admin:'+password+'"\nurl = "http://127.0.0.1:3000/api/dashboards/uid/'+uid+'"\n'
 deadline=time.monotonic()+120
 while time.monotonic()<deadline:
  p=subprocess.run(['docker','exec','-i',name,'curl','--config','-'],input=request_config,capture_output=True,text=True,timeout=10)
  if p.returncode==0:
   result=json.loads(p.stdout)
   if result.get('dashboard',{}).get('uid')==uid:passed=True;break
  time.sleep(2)
 assert passed,'Isolated Grafana application restore did not validate'
finally:
 subprocess.run(['docker','rm','--force',name],capture_output=True,timeout=30)
 api('DELETE','/api/dashboards/uid/'+uid)
assert passed
manifest={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'online-sqlite-backup-and-isolated-grafana-app-restore-passed','dashboard_uid':uid,'backup_sha256':hashlib.sha256(backup.read_bytes()).hexdigest(),'backup_bytes':backup.stat().st_size,'restore_seconds':round(time.monotonic()-started,3),'existing_target_admin_login_retained':True,'network_none':True,'host_port_published':False,'source_sqlite_replaced':False,'source_fixture_deleted':True,'coverage':['Grafana SQLite users/dashboards/settings','Ops declarative configuration'],'excluded':['Prometheus TSDB','Alertmanager notification log','approved full-business RPO/RTO','CF data']}
(folder/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');(folder/'manifest.json').chmod(0o600)
archive=root/(uid+'.tar.gz')
with tarfile.open(archive,'w:gz') as t:
 t.add(backup,arcname='grafana.db');t.add(folder/'manifest.json',arcname='manifest.json');t.add(bundle/'config',arcname='ops-config')
archive.chmod(0o600);manifest['archive_path']=str(archive);manifest['archive_sha256']=hashlib.sha256(archive.read_bytes()).hexdigest();manifest['archive_bytes']=archive.stat().st_size
shutil.rmtree(restored)
print(json.dumps(manifest))
