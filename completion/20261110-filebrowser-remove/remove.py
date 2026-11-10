#!/usr/bin/env python3
"""Remove only retired FileBrowser installation from live paths; preserve NFS and private rollback."""
import datetime,grp,hashlib,json,os,pwd,socket,stat,subprocess
from pathlib import Path
from zoneinfo import ZoneInfo
assert os.geteuid()==0 and socket.gethostname()=='resource-service' and not Path('/etc/pve').exists()
os.umask(0o077)
ARCHIVE=Path('/root/dell-filebrowser-removed-20261110');assert not ARCHIVE.exists()
paths={'code':Path('/opt/dell/filebrowser'),'configuration':Path('/etc/dell-filebrowser'),'application-state':Path('/var/lib/dell-filebrowser'),'manager-state':Path('/var/lib/dell-filebrowser-manager'),'prior-retirement':Path('/root/dell-filebrowser-retired-20261110')}
units=['dell-filebrowser.service','dell-filebrowser-firewall.service']
protected=['nfs-server.service','nfs-mountd.service','srv-resources.mount','dell-resources-firewall.service','ssh.service','systemd-networkd.service','prometheus-node-exporter.service']
nfsfiles=['/etc/exports.d/dell-resources.exports','/etc/nfs.conf.d/90-dell-resources.conf','/etc/dell-resources/input.nft','/etc/systemd/system/srv-resources.mount','/etc/systemd/system/nfs-server.service.d/50-dell-resources.conf','/etc/systemd/system/dell-resources-firewall.service','/etc/dell-guest-monitoring/health.json']
def run(args,allowed=(0,),timeout=30):
 r=subprocess.run(args,capture_output=True,text=True,timeout=timeout);assert r.returncode in allowed,'fixed-command-failed:'+args[0];return r.stdout.strip()
def frames():return {u:run(['systemctl','show',u,'-p','ActiveState','-p','SubState','-p','MainPID','-p','ExecMainStartTimestampMonotonic'])for u in protected}
def save(value):
 p=ARCHIVE/'removal.json';p.write_text(json.dumps(value,indent=2)+'\n');p.chmod(0o600)
assert json.loads(run(['python3','-I','-B','/opt/dell/resources/guard.py','--role','server']))['mount_guard']
account=pwd.getpwnam('filebrowser');assert (account.pw_uid,account.pw_gid,account.pw_dir,account.pw_shell)==(2000,2980,'/var/lib/dell-filebrowser','/usr/sbin/nologin')
assert grp.getgrgid(2980).gr_name=='resources'
assert not any((Path(base)/n).lstat().st_uid==2000 for base,dirs,files in os.walk('/srv/resources',followlinks=False)for n in dirs+files),'shared-files-own-service-account'
assert subprocess.run(['pgrep','-u','2000'],capture_output=True).returncode==1,'service-account-process-running'
for u in units:
 p=Path('/etc/systemd/system')/u;assert p.is_symlink()and os.readlink(p)=='/dev/null'
 assert run(['systemctl','show',u,'-p','ActiveState','--value'])=='inactive'
assert not run(['ss','-H','-lnt','sport = :8080'])
assert subprocess.run(['nft','list','table','inet','dell_filebrowser_input'],capture_output=True).returncode!=0
mounts=json.loads(run(['findmnt','--json','--list','--output','TARGET']))['filesystems']
for p in paths.values():
 assert p.is_dir()and not p.is_symlink()and p.resolve()==p and p.stat().st_dev==os.stat('/').st_dev
 assert all(Path(m['target'])!=p and p not in Path(m['target']).parents for m in mounts)
binary=paths['code']/'releases/v2.1.4-beta/filebrowser'
with binary.open('rb')as f:assert hashlib.file_digest(f,'sha256').hexdigest()=='4af557de16603bdfba2ae87b7807b8654612c542b2deff826eedee72086a5da2'
original_frames=frames();original_files={p:Path(p).read_bytes()for p in nfsfiles};exports=run(['exportfs','-v']);versions=Path('/proc/fs/nfsd/versions').read_bytes();policy=run(['nft','-s','list','table','inet','dell_resources_input'])
ARCHIVE.mkdir(mode=0o700);ARCHIVE.chmod(0o700);moved=[];removed_user=False
journal={'phase':'prepared','scope':'retired-FileBrowser-only','original_paths':{k:str(p)for k,p in paths.items()},'resource_files_removed':False,'credentials_exported':False};save(journal)
try:
 for key,p in paths.items():
  os.rename(p,ARCHIVE/key);moved.append(key);journal['moved']=moved;save(journal)
 for u in units:(Path('/etc/systemd/system')/u).unlink()
 run(['systemctl','daemon-reload'])
 run(['userdel','filebrowser']);removed_user=True
 try:pwd.getpwnam('filebrowser');raise RuntimeError('account-still-present')
 except KeyError:pass
 assert grp.getgrgid(2980).gr_name=='resources'
 assert all(not p.exists()and not p.is_symlink()for p in paths.values())
 for u in units:
  r=subprocess.run(['systemctl','show',u,'-p','LoadState','-p','ActiveState'],capture_output=True,text=True);v=dict(line.split('=',1)for line in r.stdout.splitlines()if'='in line);assert v=={'LoadState':'not-found','ActiveState':'inactive'}
 assert frames()==original_frames and all(Path(p).read_bytes()==raw for p,raw in original_files.items())
 assert run(['exportfs','-v'])==exports and Path('/proc/fs/nfsd/versions').read_bytes()==versions and run(['nft','-s','list','table','inet','dell_resources_input'])==policy
 assert json.loads(run(['python3','-I','-B','/opt/dell/resources/guard.py','--role','server']))['mount_guard']
except Exception:
 if removed_user:run(['useradd','--uid','2000','--gid','2980','--no-create-home','--home-dir','/var/lib/dell-filebrowser','--shell','/usr/sbin/nologin','--no-log-init','filebrowser'])
 for key in reversed(moved):os.rename(ARCHIVE/key,paths[key])
 for u in units:
  p=Path('/etc/systemd/system')/u
  if not p.is_symlink():os.symlink('/dev/null',p)
 run(['systemctl','daemon-reload']);journal['phase']='failed-original-retired-layout-restored';save(journal);raise
journal['phase']='FileBrowser-removed-from-live-installation-NFS-preserved';save(journal)
result={'at':datetime.datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),'status':journal['phase'],'live_installation_paths_absent':list(map(str,paths.values())),'FileBrowser_units':'not-found/inactive','unused_UID2000_account_removed':True,'shared_resources_GID2980_preserved':True,'TCP8080_closed':not run(['ss','-H','-lnt','sport = :8080']),'protected_archive_VM280_only':str(ARCHIVE),'archive_mode':'0700','archive_manifest_mode':'0600','NFS_config_exports_versions_input_and_health_bytes_unchanged':True,'NFS_and_other_protected_services_not_restarted':True,'resource_files_removed_or_migrated':False,'secret_contents_read_or_exported':False,'Nexus_operation_performed':False}
print(json.dumps(result))
