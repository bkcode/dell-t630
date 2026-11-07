#!/usr/bin/env python3
from pathlib import Path
import subprocess,json,socket,os,argparse
p=argparse.ArgumentParser();p.add_argument('--role',required=True);a=p.parse_args()
assert os.geteuid()==0 and not Path('/etc/pve').exists() and socket.gethostname()==a.role
assert a.role in ['data-prod-db','data-prod-infra','data-test','artifact-service','penpot-service','ops-service','nas-media']
docker=['docker','--host','unix:///var/run/docker.sock']
info=json.loads(subprocess.check_output(docker+['info','--format','{{json .}}'],text=True));assert info['Name']==a.role and info['Containers']==0
p=Path('/etc/docker/daemon.json');old=p.read_text();settings=json.loads(old)
changed=settings.get('features',{}).get('containerd-snapshotter') is not False or settings.get('live-restore') is not False
if changed:
 backup=Path('/root/dell-docker-daemon-before-runtime-profile.json')
 if not backup.exists():backup.write_text(old);backup.chmod(0o600)
 settings.setdefault('features',{})['containerd-snapshotter']=False;settings['live-restore']=False
 p.write_text(json.dumps(settings,indent=2)+'\n')
 try:subprocess.run(['systemctl','restart','docker'],check=True,capture_output=True)
 except Exception:
  p.write_text(old);subprocess.run(['systemctl','restart','docker'],check=True,capture_output=True);raise
info=json.loads(subprocess.check_output(docker+['info','--format','{{json .}}'],text=True));assert info['Driver']=='overlay2' and info['Containers']==0
print(json.dumps({'role':a.role,'driver':info['Driver'],'docker_root':info['DockerRootDir'],'live_restore':info['LiveRestoreEnabled'],'containers':info['Containers'],'changed':changed,'old_backend_data_preserved':True}))
