#!/usr/bin/env python3
"""Delete only two official, unreferenced historical installer ISOs; no guest/data cleanup."""
import os,json,hashlib,subprocess,socket,stat,datetime
from pathlib import Path
assert os.geteuid()==0 and socket.gethostname()=='pve' and Path('/etc/pve').is_dir()
items=[{'volid':'store:iso/debian-12.10.0-amd64-netinst.iso','path':'/mnt/pve/store/template/iso/debian-12.10.0-amd64-netinst.iso','size':663748608,'sha256':'ee8d8579128977d7dc39d48f43aec5ab06b7f09e1f40a9d98f2a9d149221704a'}, {'volid':'store:iso/ubuntu-24.04.2-live-server-amd64.iso','path':'/mnt/pve/store/template/iso/ubuntu-24.04.2-live-server-amd64.iso','size':3213064192,'sha256':'d6dab0c3a657988501b4bd76f1297c053df710e06e0c3aece60dead24f270b4d'}]
protected=Path('/mnt/pve/store/template/iso/dell-artifacts-20261106.iso');protected_stat=protected.stat();backup_dir=Path('/mnt/pve/store/dell-artifacts/cleanup-backups-20261107');backup_names=sorted(p.name for p in backup_dir.glob('*.vma.zst'));assert len(backup_names)==21
before_resources=json.loads(subprocess.check_output(['pvesh','get','/cluster/resources','--type','vm','--output-format','json']));identity=lambda rows:sorted((r['vmid'],r['name'],r.get('template',0),r['status']) for r in rows)
assert sorted(r['vmid'] for r in before_resources if r.get('template'))==[9001,9010,9011]
assert len(before_resources)==15 and sorted(r['vmid'] for r in before_resources if r['status']=='running')==[100,190,200,201,210,220,221,230,240,250,260,270]
base=Path('/root/dell-bootstrap/recovery-20261108/unused-official-installers');base.mkdir(parents=True,exist_ok=False);base.chmod(0o700)
def save(name,x):
 p=base/name;p.write_text(json.dumps(x,indent=2)+'\n');p.chmod(0o600)
def refs_for(item):
 refs=[]
 for pattern in ['nodes/*/qemu-server/*.conf','nodes/*/lxc/*.conf']:
  for p in Path('/etc/pve').glob(pattern):
   for line in p.read_text().splitlines():
    if (item['volid'] in line or item['path'] in line or Path(item['path']).name in line):refs.append(str(p))
 return sorted(set(refs))
def open_users(path):
 found=[]
 for proc in Path('/proc').iterdir():
  if not proc.name.isdigit():continue
  try:fds=list((proc/'fd').iterdir())
  except OSError:continue
  for fd in fds:
   try:dest=os.readlink(fd)
   except OSError:continue
   if dest==path or dest==path+' (deleted)':found.append(int(proc.name))
 return sorted(set(found))
checks=[]
for item in items:
 p=Path(item['path']);s=p.lstat();assert stat.S_ISREG(s.st_mode) and not p.is_symlink() and p.resolve()==p and s.st_uid==0 and s.st_size==item['size']
 assert subprocess.check_output(['pvesm','path',item['volid']],text=True).strip()==item['path']
 assert not refs_for(item) and not open_users(item['path'])
 h=hashlib.sha256()
 with p.open('rb') as f:
  for data in iter(lambda:f.read(4*1024*1024),b''):h.update(data)
 assert h.hexdigest()==item['sha256'],'Official bytes mismatch'
 checks.append({**item,'inode':s.st_ino,'mtime_ns':s.st_mtime_ns,'device':s.st_dev,'no_config_or_snapshot_ref':True,'no_open_FD':True,'official_SHA_match':True})
save('preflight.json',{'at':datetime.datetime.now().astimezone().isoformat(),'scope':'two exact official installer ISOs only','checks':checks,'protected_shared_ISO_bytes':protected_stat.st_size,'protected_archives':21})
deleted=[]
for item in checks:
 p=Path(item['path']);s=p.lstat();assert (s.st_ino,s.st_mtime_ns,s.st_dev,s.st_size)==(item['inode'],item['mtime_ns'],item['device'],item['size']);assert not refs_for(item) and not open_users(item['path'])
 subprocess.run(['pvesm','free',item['volid']],check=True,capture_output=True);assert not p.exists();deleted.append(item)
 save('progress.json',{'deleted':deleted})
after_resources=json.loads(subprocess.check_output(['pvesh','get','/cluster/resources','--type','vm','--output-format','json']));assert identity(before_resources)==identity(after_resources)
assert protected.exists() and (protected.stat().st_ino,protected.stat().st_size)==(protected_stat.st_ino,protected_stat.st_size)
assert sorted(p.name for p in backup_dir.glob('*.vma.zst'))==backup_names
result={'at':datetime.datetime.now().astimezone().isoformat(),'status':'two-unused-official-installers-cleaned','deleted':deleted,'logical_bytes_reclaimed':sum(i['size'] for i in deleted),'shared_artifacts_ISO_unchanged':True,'protected21_archives_unchanged':True,'guest_identity_states_unchanged':True,'VMs_or_disks_deleted':False,'LXC_template_cache_deleted':False,'migration_performed':False}
save('receipt.json',result);print(json.dumps(result))
