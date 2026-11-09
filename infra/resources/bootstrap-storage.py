#!/usr/bin/python3
"""Initialize only the newly allocated, blank100GiB scsi1 disk inside VM280."""
import datetime,json,os,pathlib,socket,stat,subprocess,uuid as uuid_module
M=pathlib.Path('/srv/resources');D=pathlib.Path('/dev/disk/by-id/scsi-0QEMU_QEMU_HARDDISK_drive-scsi1')
def run(args):return subprocess.check_output(args,stderr=subprocess.PIPE,text=True,timeout=30).strip()
def require(value,code):
 if not value:raise ValueError(code)
def blank_disk(row):
 require(row.get('type')=='disk'and type(row.get('size'))in(int,str)and int(row['size'])==100*1024**3 and not row.get('children')and not row.get('fstype')and all(x is None for x in row.get('mountpoints',[])),'new-empty100GiB-whole-disk-required')
def fstab_available(text,device):
 rows=[line.split()for line in text.splitlines()if line.strip()and not line.lstrip().startswith('#')]
 require(all(len(row)>=2 for row in rows),'existing-fstab-invalid')
 require(not any(row[1]==str(M)or row[0]in(device,str(D))for row in rows),'resource-fstab-conflict')
def main():
 require(os.geteuid()==0 and socket.gethostname()=='resource-service'and not pathlib.Path('/etc/pve').exists(),'resource280-guest-only')
 ips=[a['local']for i in json.loads(run(['ip','-j','-4','address','show','scope','global']))for a in i.get('addr_info',[])if a.get('family')=='inet'];require(ips==['192.168.19.80'],'resource-exact-IP')
 require(D.exists(),'assigned-scsi1-missing');disk=D.resolve(strict=True);d=str(disk);require(stat.S_ISBLK(disk.stat().st_mode),'assigned-device-not-block')
 disk_rdev=disk.stat().st_rdev
 rows=json.loads(run(['lsblk','-J','-b','-o','NAME,TYPE,SIZE,FSTYPE,MOUNTPOINTS',d]))['blockdevices'];require(len(rows)==1,'one-assigned-block-device');blank_disk(rows[0])
 require(not run(['wipefs','--no-act',d]),'assigned-disk-has-signatures')
 require(subprocess.run(['findmnt','--source',d],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=10).returncode!=0,'assigned-disk-already-mounted')
 # Every target/config conflict is checked BEFORE mkfs; never format then discover
 # that another filesystem or persistent unit already owns /srv/resources.
 for path in [M,*M.parents]:
  if path.exists()or path.is_symlink():
   item=path.lstat();require(not stat.S_ISLNK(item.st_mode)and item.st_uid==0 and not item.st_mode&0o022,'untrusted-resource-mount-path')
 require(subprocess.run(['findmnt','--mountpoint',str(M)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=10).returncode!=0,'resource-target-already-mounted')
 require(not M.exists()or(M.is_dir()and not any(M.iterdir())),'resource-target-not-empty')
 unit=pathlib.Path('/etc/systemd/system/srv-resources.mount');require(not unit.exists()and not unit.is_symlink(),'existing-native-mount-unit')
 fstab=pathlib.Path('/etc/fstab');item=fstab.lstat();require(stat.S_ISREG(item.st_mode)and item.st_uid==0 and item.st_nlink==1 and not item.st_mode&0o022,'trusted-fstab-required');old=fstab.read_text();fstab_available(old,d)
 require(D.resolve(strict=True)==disk and disk.stat().st_rdev==disk_rdev,'assigned-disk-identity-drift')
 M.mkdir(mode=0o555,exist_ok=True);M.chmod(0o555)
 subprocess.run(['mkfs.ext4','-q','-m','0','-L','dell-resources','-E','lazy_itable_init=1,lazy_journal_init=1',d],check=True,capture_output=True,timeout=120)
 data_uuid=run(['blkid','-s','UUID','-o','value',d]);require(str(uuid_module.UUID(data_uuid))==data_uuid,'fresh-canonical-filesystem-uuid')
 require(fstab.read_text()==old,'fstab-concurrent-change')
 text=old.rstrip()+'\nUUID='+data_uuid+' /srv/resources ext4 defaults,nofail,nodev,nosuid,noexec,x-systemd.device-timeout=15s 0 2\n'
 temp=fstab.with_name('.fstab-dell-resources-'+uuid_module.uuid4().hex)
 try:
  fd=os.open(temp,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,stat.S_IMODE(item.st_mode))
  os.fchmod(fd,stat.S_IMODE(item.st_mode));os.fchown(fd,item.st_uid,item.st_gid)
  with os.fdopen(fd,'w')as stream:stream.write(text);stream.flush();os.fsync(stream.fileno())
  os.replace(temp,fstab)
  fd=os.open(fstab.parent,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
  try:os.fsync(fd)
  finally:os.close(fd)
 finally:
  if temp.exists():temp.unlink()
 subprocess.run(['systemctl','daemon-reload'],check=True,capture_output=True,timeout=30);subprocess.run(['mount',str(M)],check=True,capture_output=True,timeout=45)
 actual=json.loads(run(['findmnt','-J','--mountpoint',str(M),'-o','TARGET,UUID,FSTYPE']))['filesystems'];require(len(actual)==1 and actual[0]['target']==str(M)and actual[0]['uuid']==data_uuid and actual[0]['fstype']=='ext4','fresh-filesystem-mount-mismatch')
 print(json.dumps({'at':datetime.datetime.now().astimezone().isoformat(),'status':'new-blank-resource-data-disk-initialized-mounted','vmid':280,'device':d,'uuid':data_uuid,'data_GiB':100,'mountpoint':str(M),'root_disk_or_existing_volume_formatted':False,'unmounted_underlay_mode':'0555 root:root','exports_or_Java_started':False}))
if __name__=='__main__':main()
