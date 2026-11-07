#!/usr/bin/env python3
from pathlib import Path
import subprocess,json,os,argparse,socket
p=argparse.ArgumentParser();p.add_argument('--uuid',required=True);a=p.parse_args()
assert os.geteuid()==0 and not Path('/etc/pve').exists() and socket.gethostname()=='penpot-service'
mount=Path('/srv/penpot');assert mount.resolve()==mount
fs=json.loads(subprocess.check_output(['findmnt','-J','-M',str(mount),'-o','TARGET,SOURCE,FSTYPE,UUID,OPTIONS'],text=True))['filesystems'][0]
assert fs['uuid']==a.uuid and fs['target']==str(mount) and 'rw' in fs['options'].split(',')
info=json.loads(subprocess.check_output(['docker','info','--format','{{json .}}'],text=True));assert info['Name']==socket.gethostname() and info['Containers']==0 and info['Images']==0
subprocess.run(['systemctl','stop','docker.service','docker.socket'],check=True,capture_output=True)
root=mount/'docker';root.mkdir(mode=0o711,exist_ok=True)
configuration=Path('/etc/docker/daemon.json');data=json.loads(configuration.read_text())
data.update({'data-root':str(root),'live-restore':False});configuration.write_text(json.dumps(data,indent=2)+'\n')
check=Path('/usr/local/libexec/dell-penpot-data-check');check.parent.mkdir(parents=True,exist_ok=True)
check.write_text('''#!/usr/bin/python3
import json,subprocess
x=json.loads(subprocess.check_output(['findmnt','-J','-M','/srv/penpot','-o','TARGET,UUID,OPTIONS'],text=True))['filesystems'][0]
assert x['target']=='/srv/penpot' and x['uuid']=='''+repr(a.uuid)+''' and 'rw' in x['options'].split(',')
''');check.chmod(0o755)
unit=subprocess.check_output(['systemd-escape','--path','--suffix=mount',str(mount)],text=True).strip()
folder=Path('/etc/systemd/system/docker.service.d');folder.mkdir(exist_ok=True,parents=True)
(folder/'20-dell-penpot-data.conf').write_text('[Unit]\nRequiresMountsFor=/srv/penpot\nBindsTo='+unit+'\nAfter='+unit+'\n[Service]\nExecStartPre=/usr/local/libexec/dell-penpot-data-check\n')
subprocess.run(['systemctl','daemon-reload'],check=True,capture_output=True);subprocess.run(['systemctl','start','docker.service'],check=True,capture_output=True)
info=json.loads(subprocess.check_output(['docker','info','--format','{{json .}}'],text=True));assert info['DockerRootDir']==str(root)
print(json.dumps({'status':'base-storage-ready-no-application','uuid':a.uuid,'mountpoint':str(mount),'docker_root_dir':info['DockerRootDir'],'containerd_image_cache_reconstructible_on_os_disk':True,'live_restore':False,'application_containers':info['Containers']}))
