#!/usr/bin/env python3
"""Manager-only stage: no-IP vmbr19, move stopped104 off21, full-clone router190. No old routing removal."""
from pathlib import Path
import sys,json,shlex,datetime
BASE=Path(__file__).resolve().parents[1];sys.path.insert(0,str(BASE/'scripts'));import control
WAN='02:63:19:01:90:00';LAN='02:63:19:01:90:01'
code=r'''import os,json,subprocess,hashlib,socket,struct,time,datetime
from pathlib import Path
assert os.geteuid()==0 and Path('/etc/pve').exists() and socket.gethostname()=='pve'
def run(a,timeout=60):
 p=subprocess.run(a,capture_output=True,text=True,timeout=timeout)
 if p.returncode:raise RuntimeError('Stage command failed: '+a[0]+' '+a[1])
 return p.stdout
assert not Path('/etc/pve/qemu-server/190.conf').exists()
assert run(['qm','status','104']).strip()=='status: stopped'
original=Path('/etc/pve/qemu-server/104.conf').read_bytes();assert b'ip=192.168.21.23/24' in original
for path in Path('/etc/pve/qemu-server').glob('*.conf'):
 text=path.read_text();assert '02:63:19:01:90:00' not in text and '02:63:19:01:90:01' not in text
# Three narrowly scoped ARP queries, not ping-as-proof.
mac=bytes.fromhex(Path('/sys/class/net/vmbr0/address').read_text().strip().replace(':',''));target=socket.inet_aton('192.168.21.23');src=socket.inet_aton('192.168.21.22');responses=set()
with socket.socket(socket.AF_PACKET,socket.SOCK_RAW,socket.htons(0x0806)) as raw:
 raw.bind(('vmbr0',0));raw.settimeout(.25)
 packet=b'\xff'*6+mac+b'\x08\x06'+struct.pack('!HHBBH',1,0x0800,6,4,1)+mac+src+b'\0'*6+target
 # Construct from real byte constants (raw source escaping normalization below).
 packet=bytes([255])*6+mac+bytes.fromhex('0806')+struct.pack('!HHBBH',1,0x0800,6,4,1)+mac+src+bytes(6)+target
 for _ in range(3):
  raw.send(packet);end=time.monotonic()+1
  while time.monotonic()<end:
   try:data=raw.recv(2048)
   except socket.timeout:continue
   if len(data)>=42 and data[12:14]==bytes.fromhex('0806') and data[20:22]==bytes.fromhex('0002') and data[28:32]==target:responses.add(':'.join(format(x,'02x') for x in data[22:28]))
assert not responses,'21.23 ARP responder detected; stop before reusing address'
root=Path('/root/dell-bootstrap/network19');root.mkdir(parents=True,exist_ok=True,mode=0o700);root.chmod(0o700)
before=root/'before';before.mkdir(mode=0o700,exist_ok=False)
for name,data in [('vm104.conf',original),('interfaces',Path('/etc/network/interfaces').read_bytes())]:
 p=before/name;p.write_bytes(data);p.chmod(0o600)
bridge=Path('/etc/network/interfaces.d/dell-network19.conf');assert not bridge.exists()
bridge.write_text('auto vmbr19\niface vmbr19 inet manual\n    bridge-ports none\n    bridge-stp off\n    bridge-fd 0\n    post-up /usr/sbin/sysctl -q -w net.ipv6.conf.vmbr19.disable_ipv6=1\n');bridge.chmod(0o644)
run(['ifup','vmbr19']);address=json.loads(run(['ip','-j','addr','show','vmbr19']))[0];assert not address.get('addr_info')
config={k:v.strip() for k,v in (l.split(':',1) for l in original.decode().splitlines() if ':' in l)}
network=config['net0'].replace('bridge=vmbr0','bridge=vmbr19');assert 'bridge=vmbr19' in network
run(['qm','set','104','--net0',network,'--ipconfig0','ip=192.168.19.104/24,gw=192.168.19.1'])
profile=Path('/mnt/pve/store/snippets/dell-linux-default-user.yaml').read_text();assert 'preserve_hostname: false' in profile
profile=profile.replace('preserve_hostname: false','preserve_hostname: false\nhostname: network-gateway',1)
snippet=Path('/mnt/pve/store/snippets/dell-network-gateway-user.yaml');assert not snippet.exists();snippet.write_text(profile);snippet.chmod(0o600)
run(['qm','clone','9010','190','--name','network-gateway','--full','1','--storage','store','--format','qcow2'],timeout=300)
run(['qm','set','190','--memory','512','--balloon','0','--cores','2','--onboot','0','--startup','order=5,up=20,down=120','--net0','virtio=02:63:19:01:90:00,bridge=vmbr0','--net1','virtio=02:63:19:01:90:01,bridge=vmbr19','--ipconfig0','ip=192.168.21.23/24,gw=192.168.21.1','--ipconfig1','ip=192.168.19.1/24','--nameserver','192.168.21.1','--cicustom','user=store:snippets/'+snippet.name,'--description','network19 gateway; user-authorized WAN21.23 LAN19.1; oldhost routing retained until migration validated'])
run(['qm','start','190'])
r={'at':datetime.datetime.now().isoformat(),'status':'bridge19-nohostIP-and-router190-started-initial-forwarding-unconfigured','old104':'stopped net0 vmbr19,CloudInit19.104;OS still requires validation','old104_config_backup_PVE_only':str(before/'vm104.conf'),'old104_config_sha256':hashlib.sha256(original).hexdigest(),'gateway':{'vmid':190,'hostname':'network-gateway','WAN':'192.168.21.23/24','LAN':'192.168.19.1/24','WAN_MAC':'02:63:19:01:90:00','LAN_MAC':'02:63:19:01:90:01','vcpu':2,'memory_mib':512,'disk_gib':32},'ARP23_responders_before':list(responses),'PVE_management_unchanged':True,'old_bridges_NAT_forwarding_not_removed':True,'other_apps_not_stopped':True}
(root/'host-stage-receipt.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
'''
r=control.pve('python3 -c '+shlex.quote(code),timeout=420)
(BASE/'network19/evidence/host-stage-receipt.json').write_bytes(r);text=r.decode();print(text)
