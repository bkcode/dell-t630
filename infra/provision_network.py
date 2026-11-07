from pathlib import Path
if Path('/root/dell-bootstrap/network19/management-only-active').exists():
 raise SystemExit('Legacy PVE host routing/NAT retired; use network19 gateway workflow')
import subprocess,json,datetime
base=Path('/root/dell-bootstrap');base.mkdir(mode=0o700,exist_ok=True)
source=base/'network'
management=Path('/etc/network/interfaces')
if '192.168.21.22/24' not in management.read_text():raise SystemExit('Unexpected management network')
files=['/etc/network/interfaces','/etc/network/interfaces.d/dell-internal','/etc/sysctl.d/90-dell-forward.conf','/etc/nftables.d/dell.nft','/etc/systemd/system/dell-network.service','/usr/local/sbin/dell-apply-firewall']
backup=base/('network-before-'+datetime.datetime.now().strftime('%Y%m%dT%H%M%S')+'.json')
state={'files':{p:Path(p).read_text() if Path(p).is_file() else None for p in files},'forward':Path('/proc/sys/net/ipv4/ip_forward').read_text(),'tables':{}}
for family,name in [('inet','dell_filter'),('ip','dell_nat')]:
 p=subprocess.run(['nft','list','table',family,name],capture_output=True,text=True);state['tables'][family+' '+name]=p.stdout if p.returncode==0 else None
backup.write_text(json.dumps(state,indent=2));backup.chmod(0o600)
rulefile=Path('/etc/nftables.d/dell.nft');rulefile.parent.mkdir(exist_ok=True)
config=(source/'dell-network.nft').read_text()
deletes=''.join('delete table '+k+'\n' for k,v in state['tables'].items() if v)
p=subprocess.run(['nft','-c','-f','-'],input=deletes+config,capture_output=True,text=True)
if p.returncode:raise SystemExit(p.stderr)
bridgefile=Path('/etc/network/interfaces.d/dell-internal');bridgeconfig=(source/'internal-bridges.conf').read_text()
if bridgefile.exists() and bridgefile.read_text()!=bridgeconfig:raise SystemExit('Existing bridge configuration differs')
unit='''[Unit]
Description=Dell isolated guest routing and firewall
DefaultDependencies=no
After=local-fs.target systemd-sysctl.service
Before=network-pre.target
Wants=network-pre.target
[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/usr/local/sbin/dell-apply-firewall
[Install]
WantedBy=multi-user.target
'''
try:
 rulefile.write_text(config)
 helper=Path('/usr/local/sbin/dell-apply-firewall');helper.write_text((source/'apply_guest_firewall.py').read_text());helper.chmod(0o755)
 # No persistent forward=1 sysctl: the early service installs filtering before enabling routing.
 prior=Path('/etc/sysctl.d/90-dell-forward.conf')
 if prior.exists() and prior.read_text().strip()=='net.ipv4.ip_forward=1':prior.unlink()
 Path('/etc/systemd/system/dell-network.service').write_text(unit)
 subprocess.run(['systemctl','daemon-reload'],check=True)
 subprocess.run(['systemctl','restart','dell-network.service'],check=True)
 bridgefile.write_text(bridgeconfig)
 for zone in [10,20,30,40]:
  name=f'vmbr{zone}'
  if subprocess.run(['ip','link','show',name],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode:subprocess.run(['ifup',name],check=True)
 subprocess.run(['systemctl','enable','dell-network.service'],check=True,capture_output=True)
except Exception:
 current=[]
 for family,name in [('inet','dell_filter'),('ip','dell_nat')]:
  if subprocess.run(['nft','list','table',family,name],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0:current.append('delete table '+family+' '+name+'\n')
 restore=''.join(current)+''.join(v or '' for v in state['tables'].values())
 try:
  if state['forward'].strip()=='0':subprocess.run(['sysctl','-w','net.ipv4.ip_forward=0'],check=True,capture_output=True)
  if restore:subprocess.run(['nft','-f','-'],input=restore,text=True,check=True)
 finally:
  subprocess.run(['sysctl','-w','net.ipv4.ip_forward='+state['forward'].strip()],check=True,capture_output=True)
 for p,content in state['files'].items():
  f=Path(p)
  if content is None:
   if f.exists():f.unlink()
  else:f.parent.mkdir(exist_ok=True,parents=True);f.write_text(content)
 subprocess.run(['systemctl','daemon-reload'],check=True)
 raise
print('Internal bridges and atomic dedicated filtering active; management unchanged; backup '+str(backup))
