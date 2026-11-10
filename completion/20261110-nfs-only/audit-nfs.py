#!/usr/bin/env python3
"""Bounded VM280 and NFS-client metadata; no secret or resource body reads."""
import concurrent.futures,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts'));import control
known=json.loads((ROOT/'evidence/implementation/private-guest-access.json').read_text())['roles']
targets={x['target']['vmid']:x['target'] for x in known if x.get('target',{}).get('vmid') in [230,240,280]}
targets[280]=json.loads((ROOT/'completion/20261109-resources/guest-access.json').read_text())['target']
SCRIPT=r'''
import datetime,hashlib,json,os,socket,stat,subprocess
from pathlib import Path
from zoneinfo import ZoneInfo
ROLE=ROLE_ID
assert os.geteuid()==0 and socket.gethostname()=={230:'java-prod-01',240:'java-test-01',280:'resource-service'}[ROLE] and not Path('/etc/pve').exists()
def run(args,allowed=(0,)):
 p=subprocess.run(args,capture_output=True,text=True,timeout=12)
 assert p.returncode in allowed,'readonly-command-failed'
 return p.stdout.strip()
def units(names):
 return {name:dict(x.split('=',1)for x in run(['systemctl','show',name,'--property=ActiveState,SubState,MainPID,UnitFileState,FragmentPath,ActiveEnterTimestampMonotonic']).splitlines()if'='in x)for name in names}
def public(path):
 p=Path(path);assert p.is_file()and not p.is_symlink()and p.stat().st_uid==0
 b=p.read_bytes();assert len(b)<100000
 return {'sha256':hashlib.sha256(b).hexdigest(),'mode':oct(stat.S_IMODE(p.stat().st_mode))}
def metadata(path):
 p=Path(path);s=p.stat();return {'uid':s.st_uid,'gid':s.st_gid,'mode':oct(stat.S_IMODE(s.st_mode)),'device':s.st_dev,'inode':s.st_ino,'size':s.st_size}
mount='/srv/resources'if ROLE==280 else'/mnt/resources'
guard=run(['python3','-I','-B','/opt/dell/resources/guard.py','--role','server'if ROLE==280 else'client-'+str(ROLE)])
out={'at':datetime.datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),'vmid':ROLE,'hostname':socket.gethostname(),'guard':json.loads(guard),'mount':json.loads(run(['findmnt','-J','--mountpoint',mount,'-o','TARGET,SOURCE,FSTYPE,OPTIONS,UUID'])),'mutations':False,'credentials_or_file_contents_read':False}
if ROLE==280:
 out['units']=units(['dell-filebrowser.service','dell-filebrowser-firewall.service','nfs-server.service','nfs-mountd.service','srv-resources.mount','dell-resources-firewall.service','ssh.service','prometheus-node-exporter.service','dell-guest-health.service'])
 out['health']=json.loads(Path('/etc/dell-guest-monitoring/health.json').read_text())
 out['exports']=run(['exportfs','-v']);out['NFS_versions']=Path('/proc/fs/nfsd/versions').read_text().strip()
 out['public_files']={p:public(p)for p in ['/etc/systemd/system/dell-filebrowser.service','/etc/systemd/system/dell-filebrowser-firewall.service','/etc/dell-filebrowser/config.yaml','/etc/dell-filebrowser/input.nft','/opt/dell/filebrowser/launch.py','/opt/dell/filebrowser/firewall.py','/etc/exports.d/dell-resources.exports','/etc/nfs.conf.d/90-dell-resources.conf','/etc/dell-resources/input.nft']}
 out['filebrowser_units_source']={p:Path(p).read_text()for p in ['/etc/systemd/system/dell-filebrowser.service','/etc/systemd/system/dell-filebrowser-firewall.service']}
 out['web_table']=run(['nft','list','table','inet','dell_filebrowser_input'])
 out['NFS_input_table']=run(['nft','list','table','inet','dell_resources_input'])
 out['state_metadata']=metadata('/var/lib/dell-filebrowser');out['resource_root_metadata']=metadata('/srv/resources')
 out['listener_8080']=run(['ss','-H','-lnt','sport = :8080'])
else:
 out['units']=units(['mnt-resources.mount','mnt-resources.automount']);out['runtime_identity']=run(['id','finger']);out['mount_units']={p:public(p)for p in ['/etc/systemd/system/mnt-resources.mount','/etc/systemd/system/mnt-resources.automount']}
print(json.dumps(out))
'''
def one(role):
 result=control.guest(role,'sudo -n python3 -',data=SCRIPT.replace('ROLE_ID',str(role)).encode(),timeout=90,info=targets[role])
 if result['exit_code']:return {'vmid':role,'status':'unconfirmed','exit_code':result['exit_code']}
 return json.loads(result['stdout'])
with concurrent.futures.ThreadPoolExecutor(max_workers=3)as pool:result=list(pool.map(one,[280,230,240]))
assert all('guard'in x for x in result),result
Path(__file__).with_name('before-resume.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps([{'vmid':x['vmid'],'guard':x['guard'],'hostname':x['hostname']}for x in result]))
