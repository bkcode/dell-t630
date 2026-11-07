#!/usr/bin/env python3
"""Coordinator-only final retirement. Refuses any guest using old uplink/bridges."""
from pathlib import Path
import sys,json,shlex,datetime
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'scripts'));import control
P=r'''from pathlib import Path
import subprocess,json,os,hashlib,datetime,shutil
assert os.geteuid()==0 and Path('/etc/pve').exists()
def run(a,check=True):
 p=subprocess.run(a,capture_output=True,text=True,timeout=45)
 if check and p.returncode:raise RuntimeError('fixed management-only action failed:'+a[0])
 return p.stdout
oldbridges=['vmbr10','vmbr20','vmbr30','vmbr40'];rows=[]
for kind,folder in [('vm',Path('/etc/pve/qemu-server')),('lxc',Path('/etc/pve/lxc'))]:
 for p in folder.glob('*.conf'):
  if not p.stem.isdigit():continue
  c={l.split(': ',1)[0]:l.split(': ',1)[1] for l in p.read_text().split('\n[',1)[0].splitlines() if ': ' in l}
  for key,value in c.items():
   if key.startswith('net') and key[3:].isdigit():
    bridge=next((x.split('=',1)[1] for x in value.split(',') if x.startswith('bridge=')),None)
    assert bridge==('vmbr0' if p.stem=='190' and key=='net0' else 'vmbr19'), 'guest not wholly migrated'
   if key.startswith('ipconfig') and p.stem!='190':assert '192.168.21.' not in value and '10.63.' not in value
  rows.append({'vmid':int(p.stem),'kind':kind})
for bridge in oldbridges:assert not list((Path('/sys/class/net')/bridge/'brif').iterdir()),'old bridge still has port'
assert not json.loads(run(['ip','-j','addr','show','vmbr19']))[0].get('addr_info')
prior=Path('/etc/sysctl.d/90-dell-forward.conf')
if prior.exists():assert prior.read_text().strip()=='net.ipv4.ip_forward=1'
assert not Path('/etc/sysctl.d/99-z-dell-management-only.conf').exists()
interfaces=Path('/etc/network/interfaces').read_bytes();assert b'192.168.21.22/24' in interfaces and b'gateway 192.168.21.1' in interfaces
assert 'via 192.168.21.23 dev vmbr0' in run(['ip','route','get','192.168.19.10'])
run(['nft','list','table','bridge','dell19_acl'])
root=Path('/root/dell-bootstrap/network19/old-host-retirement');root.mkdir(mode=0o700,exist_ok=False)
paths=['/etc/network/interfaces.d/dell-internal','/etc/nftables.d/dell.nft','/usr/local/sbin/dell-apply-firewall','/etc/systemd/system/dell-network.service','/etc/sysctl.d/90-dell-forward.conf']
for name in paths:
 p=Path(name)
 if p.is_file():
  f=root/p.name;f.write_bytes(p.read_bytes());f.chmod(0o600)
for family,name in [('inet','dell_filter'),('ip','dell_nat'),('bridge','dell19_acl')]:
 f=root/(family+'-'+name+'.nft');f.write_text(run(['nft','list','table',family,name]));f.chmod(0o600)
record={'at':datetime.datetime.now().isoformat(),'phase':'backed-up','PVE_management_before_SHA':hashlib.sha256(interfaces).hexdigest(),'guests_checked':len(rows)}
def save():
 f=root/'result.json';f.write_text(json.dumps(record,indent=2));f.chmod(0o600)
save()
run(['systemctl','disable','--now','dell-network.service'])
# Quiesce host L3 before removing any filtering: bridge forwarding is independent.
run(['sysctl','-q','-w','net.ipv4.ip_forward=0','net.ipv6.conf.all.forwarding=0','net.ipv6.conf.default.forwarding=0'])
for family in ['ipv4','ipv6']:
 for folder in Path('/proc/sys/net',family,'conf').iterdir():
  f=folder/'forwarding'
  if f.is_file():f.write_text('0\n')
assert Path('/proc/sys/net/ipv4/ip_forward').read_text().strip()=='0'
# Remove only our old persistent loader/configuration, leaving protected backups.
for name in ['/etc/nftables.d/dell.nft','/usr/local/sbin/dell-apply-firewall','/etc/systemd/system/dell-network.service']:
 p=Path(name);assert not p.is_symlink();p.unlink()
Path('/etc/systemd/system/dell-network.service').symlink_to('/dev/null')
for bridge in oldbridges:
 run(['ifdown',bridge],False)
 link=Path('/sys/class/net')/bridge
 if link.exists():
  assert (link/'bridge').exists() and not list((link/'brif').iterdir())
  run(['ip','link','set','dev',bridge,'down']);run(['ip','link','delete','dev',bridge,'type','bridge'])
 assert not link.exists()
Path('/etc/network/interfaces.d/dell-internal').unlink()
# No global flush: keep the new bridge table and every unrelated table.
transaction='delete table inet dell_filter\ndelete table ip dell_nat\n';runcheck=subprocess.run(['nft','-c','-f','-'],input=transaction,capture_output=True,text=True);assert runcheck.returncode==0
subprocess.run(['nft','-f','-'],input=transaction,capture_output=True,text=True,check=True)
prior=Path('/etc/sysctl.d/90-dell-forward.conf')
if prior.exists():
 assert prior.read_text().strip()=='net.ipv4.ip_forward=1';prior.unlink()
policy=Path('/etc/sysctl.d/99-z-dell-management-only.conf');assert not policy.exists()
policy.write_text('net.ipv4.ip_forward=0\nnet.ipv4.conf.all.forwarding=0\nnet.ipv4.conf.default.forwarding=0\nnet.ipv6.conf.all.forwarding=0\nnet.ipv6.conf.default.forwarding=0\n');policy.chmod(0o644)
run(['sysctl','-q','-p',str(policy)])
for family in ['ipv4','ipv6']:
 for folder in Path('/proc/sys/net',family,'conf').iterdir():
  f=folder/'forwarding'
  if f.is_file():f.write_text('0\n')
run(['systemctl','daemon-reload'])
assert Path('/etc/network/interfaces').read_bytes()==interfaces
assert all(not (Path('/sys/class/net')/x).exists() for x in oldbridges)
assert not any(a.get('local','').startswith('10.63.') or a.get('local','').startswith('192.168.19.') for r in json.loads(run(['ip','-j','addr'])) for a in r.get('addr_info',[]))
assert 'via 192.168.21.23 dev vmbr0' in run(['ip','route','get','192.168.19.10'])
assert Path('/proc/sys/net/ipv4/ip_forward').read_text().strip()=='0'
forward={family:{p.parent.name:p.read_text().strip() for p in Path('/proc/sys/net',family,'conf').glob('*/forwarding')} for family in ['ipv4','ipv6']};assert all(value=='0' for values in forward.values() for value in values.values())
tables=run(['nft','list','tables']).splitlines();assert 'table inet dell_filter' not in tables and 'table ip dell_nat' not in tables and 'table bridge dell19_acl' in tables
assert run(['systemctl','is-enabled','dell-network.service'],False).strip()=='masked'
marker=Path('/root/dell-bootstrap/network19/management-only-active');marker.write_text('PVE management/L2 only. Router190 owns L3. Legacy host NAT provisioning retired.\n');marker.chmod(0o600)
record.update(status='PVE-management-and-L2-only-old-NAT-bridges-retired',phase='complete',old_four_bridges_absent=True,old_NAT_filter_tables_absent=True,PVE_main_management_config_unchanged=True,server19_host_addresses_absent=True,host19_client_route='via192.168.21.23 devvmbr0',IPv4_forward='0',all_interface_forwarding_zero=True,forwarding=forward,remaining_tables=tables,old_loader_masked=True,backup_PVE_only=True,host_reboot_executed=False)
save();print(json.dumps(record))'''
try:
 x=json.loads(control.pve('python3 -',data=P.encode(),timeout=250));(R/'network19/evidence/host-management-only-retirement.json').write_text(json.dumps(x,indent=2)+'\n');print(json.dumps(x))
except Exception:
 print('Host cleanup refused or unconfirmed; inspect exact PVE-only stage result; do not re-enable NAT blindly.');raise
