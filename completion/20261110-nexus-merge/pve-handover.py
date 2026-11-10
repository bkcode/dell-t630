#!/usr/bin/env python3
"""PVE-only fixed221->220 cold handover, preserving separate publisher build disk."""
import hashlib,json,os,subprocess,sys
from pathlib import Path
assert os.geteuid()==0 and Path('/etc/pve').exists()
os.umask(0o077);payload=json.load(sys.stdin)
def run(args,timeout=60):return subprocess.check_output(args,stderr=subprocess.PIPE,timeout=timeout).decode().strip()
def config(v):return dict(line.split(': ',1)for line in run(['qm','config',str(v)]).splitlines()if ': 'in line)
def stopped(v):assert run(['qm','status',str(v)])=='status: stopped'
state=json.loads(Path('/root/dell-bootstrap/nexus-merge-20261110/backup-current.json').read_text());assert state['status']=='verified' and state['source_still_stopped']
archive=Path(state['archive']);assert archive.stat().st_size==state['bytes'] and archive.stat().st_mode&0o777==0o600
with archive.open('rb')as stream:assert hashlib.file_digest(stream,'sha256').hexdigest()==state['sha256']
stopped(221);c221=config(221);assert c221['scsi1'].startswith('store:221/vm-221-disk-1.qcow2,')
c220=config(220);assert c220['scsi1'].startswith('store:220/vm-220-disk-1.qcow2,') and c220['scsi2']=='store:iso/dell-artifacts-20261106.iso,media=cdrom,size=13183532K'
p=Path('/etc/dell-network19/bridge19.nft');before=p.read_bytes();assert hashlib.sha256(before).hexdigest()==payload['old_sha'];after=payload['rules'].encode()
assert after.count(b'table bridge dell19_acl {')==1 and b'table inet'not in after and b'tap221i0'not in after
transaction=b'delete table bridge dell19_acl\n'+after
subprocess.run(['nft','-c','-f','-'],input=transaction,check=True,capture_output=True)
run(['qm','set','221','--onboot','0'])
run(['qm','shutdown','220','--timeout','180'],timeout=200);stopped(220);stopped(221)
folder=Path('/root/dell-bootstrap/nexus-merge-20261110');(folder/'bridge-before.nft').write_bytes(before);(folder/'bridge-before.nft').chmod(0o600)
(folder/'vm220-before.conf').write_text(run(['qm','config','220']));(folder/'vm220-before.conf').chmod(0o600)
run(['qm','set','220','--delete','scsi2'])
run(['qm','set','220','--cores','6','--memory','8192','--startup','order=30,up=90,down=180'])
run(['qm','move-disk','221','scsi1','--target-vmid','220','--target-disk','scsi2'],timeout=180)
a,b=config(220),config(221);assert a['scsi1']==c220['scsi1'] and 'scsi1'not in b and a['scsi2'].startswith('store:220/')and 'media=cdrom'not in a['scsi2']
p.write_bytes(after);p.chmod(0o600)
subprocess.run(['nft','-f','-'],input=transaction,check=True,capture_output=True)
run(['qm','start','220'],timeout=90)
result={'status':'original-Nexus-disk-owned-only-by220-and-220-boot-requested','VM221_status':run(['qm','status','221']),'VM220_status':run(['qm','status','220']),'VM220_cores':a['cores'],'VM220_memory_MiB':a['memory'],'VM220_build_disk_unchanged':a['scsi1']==c220['scsi1'],'VM220_Nexus_disk':a['scsi2'],'installer_ISO_detached_not_deleted':True,'source_OS_disk_and_cold_backup_retained':True,'bridge31_source_ownership':'220MAC','PVE_L3_or_NAT_changed':False,'VM220_backup_performed':False}
(folder/'handover-result.json').write_text(json.dumps(result));(folder/'handover-result.json').chmod(0o600);print(json.dumps(result))
