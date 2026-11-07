#!/usr/bin/env python3
"""Run via trusted SSH inside a newly provisioned guest; only its empty extra disk."""
from pathlib import Path
import subprocess,json,os,argparse,ipaddress
p=argparse.ArgumentParser();p.add_argument('--role',required=True);p.add_argument('--size-gib',type=int,default=0);p.add_argument('--mountpoint');p.add_argument('--format-empty',action='store_true');args=p.parse_args()
assert os.geteuid()==0 and not Path('/etc/pve').exists()
assert subprocess.check_output(['hostname'],text=True).strip()==args.role
assert args.role in {'data-prod-db','data-prod-infra','data-test','publish-service','artifact-service','java-prod-01','java-prod-02','java-prod-03','java-test-01','penpot-service','nas-media','ops-service'}
# During the staging LAN phase, accept only IPv4 management; no global IPv6 auto-addresses.
route=json.loads(subprocess.check_output(['ip','-j','route','show','default'],text=True))
iface=next(x['dev'] for x in route if x.get('gateway'))
config='net.ipv6.conf.'+iface+'.disable_ipv6=1\nnet.ipv6.conf.all.accept_ra=0\nnet.ipv6.conf.default.accept_ra=0\nnet.ipv6.conf.default.autoconf=0\nnet.ipv6.conf.'+iface+'.accept_ra=0\nnet.ipv6.conf.'+iface+'.autoconf=0\n'
Path('/etc/sysctl.d/90-dell-guest-addressing.conf').write_text(config)
subprocess.run(['sysctl','-p','/etc/sysctl.d/90-dell-guest-addressing.conf'],check=True,capture_output=True)
ipv6=json.loads(subprocess.check_output(['ip','-j','-6','addr','show','dev',iface],text=True))
assert not any(x.get('scope')=='global' for n in ipv6 for x in n.get('addr_info',[])), 'Global IPv6 remains on staging interface'
result={'role':args.role,'hostname':args.role,'staging_interface_ipv6_disabled':True,'ipv6_kernel_loopback_preserved':True,'business_services_started':False,'storage':None}
if args.size_gib:
 assert args.mountpoint in ['/srv/dell-data','/srv/dell-build','/srv/nexus','/srv/penpot']
 data=Path('/dev/disk/by-id/scsi-0QEMU_QEMU_HARDDISK_drive-scsi1')
 if not data.exists():raise RuntimeError('Expected named extra guest disk not found')
 device=str(data.resolve())
 assert int(subprocess.check_output(['blockdev','--getsize64',device],text=True))==args.size_gib*1024**3
 block=json.loads(subprocess.check_output(['lsblk','-J','-b','-o','NAME,TYPE,SIZE,FSTYPE,MOUNTPOINTS',device],text=True))['blockdevices'][0]
 assert block['type']=='disk' and not block.get('children'), 'Unexpected partitions; inspect manually'
 filesystem=subprocess.run(['blkid','-s','TYPE','-o','value',device],capture_output=True,text=True).stdout.strip()
 if not filesystem:
  if not args.format_empty:raise RuntimeError('Empty disk requires explicit format-empty')
  assert not subprocess.check_output(['wipefs','--no-act',device],text=True).strip()
  assert subprocess.run(['findmnt','--source',device],stdout=subprocess.DEVNULL).returncode!=0
  subprocess.run(['mkfs.ext4','-q','-m','0','-L','dell-data','-E','lazy_itable_init=1,lazy_journal_init=1',device],check=True,capture_output=True)
 elif filesystem!='ext4':raise RuntimeError('Unexpected filesystem; never overwrite')
 uuid=subprocess.check_output(['blkid','-s','UUID','-o','value',device],text=True).strip()
 mountpoint=Path(args.mountpoint);mountpoint.mkdir(parents=True,exist_ok=True)
 assert not mountpoint.is_symlink()
 mounts=subprocess.run(['findmnt','-J','-M',str(mountpoint),'-o','TARGET,UUID'],capture_output=True,text=True)
 if mounts.returncode==0:
  assert json.loads(mounts.stdout)['filesystems'][0]['uuid']==uuid
 else:
  assert not any(mountpoint.iterdir()),'Refusing to mount over existing guest files'
  fstab=Path('/etc/fstab');text=fstab.read_text()
  if uuid not in text:
   assert not any(str(mountpoint) in line.split() for line in text.splitlines() if line and not line.startswith('#'))
   fstab.write_text(text.rstrip()+'\nUUID='+uuid+' '+str(mountpoint)+' ext4 defaults,nofail,x-systemd.device-timeout=10s 0 2\n')
  subprocess.run(['systemctl','daemon-reload'],check=True,capture_output=True)
  subprocess.run(['mount',str(mountpoint)],check=True,capture_output=True)
 result['storage']={'device':device,'size_gib':args.size_gib,'uuid':uuid,'mountpoint':str(mountpoint),'guest_mount_verified':True}
print(json.dumps(result))
