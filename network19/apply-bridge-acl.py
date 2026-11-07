#!/usr/bin/env python3
"""Parent-only apply one owned bridge-family table; host management/IP/NAT unchanged."""
from pathlib import Path
import sys,json,shlex,ast
BASE=Path(__file__).resolve().parents[1];sys.path.insert(0,str(BASE/'scripts'));import control
rules=(BASE/'network19/audit/bridge19-acl-candidate.nft').read_text();assert rules.count('table bridge dell19_acl {')==1 and 'table inet' not in rules
helper=r'''#!/usr/bin/python3
import subprocess
from pathlib import Path
assert Path('/etc/pve').exists()
p=Path('/etc/dell-network19/bridge19.nft');assert not p.is_symlink() and p.stat().st_uid==0 and not p.stat().st_mode&0o077
exists=subprocess.run(['nft','list','table','bridge','dell19_acl'],capture_output=True).returncode==0
body=(b'delete table bridge dell19_acl\n' if exists else b'')+p.read_bytes()
subprocess.run(['nft','-c','-f','-'],input=body,check=True,capture_output=True)
subprocess.run(['nft','-f','-'],input=body,check=True,capture_output=True)
'''
ast.parse(helper)
unit='''[Unit]
Description=Dell server19 L2 identity and role ACL
Requires=pve-cluster.service
After=pve-cluster.service network.target
Before=pve-guests.service
[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/usr/local/sbin/dell-apply-network19-bridge
[Install]
WantedBy=multi-user.target
'''
drop='[Unit]\nRequires=dell-network19-bridge.service\nAfter=dell-network19-bridge.service\n'
remote='''import sys,subprocess,json,os,hashlib,datetime,ast
from pathlib import Path
assert os.geteuid()==0 and Path('/etc/pve').exists()
payload=json.load(sys.stdin);assert set(payload)=={'rules','helper','unit','drop'}
body=payload['rules'].encode();assert len(body)<100000 and body.count(b'table bridge dell19_acl {')==1 and b'table inet' not in body
ast.parse(payload['helper'])
folder=Path('/root/dell-bootstrap/network19/acl');folder.mkdir(mode=0o700,exist_ok=True)
p=subprocess.run(['nft','list','table','bridge','dell19_acl'],capture_output=True)
backup=folder/('before-'+datetime.datetime.now().strftime('%Y%m%dT%H%M%S')+'.nft');backup.write_bytes(p.stdout if p.returncode==0 else b'');backup.chmod(0o600)
# Precheck before changing persistent service metadata.
transaction=(b'delete table bridge dell19_acl\\n' if p.returncode==0 else b'')+body
subprocess.run(['nft','-c','-f','-'],input=transaction,check=True,capture_output=True)
files=[('/etc/dell-network19/bridge19.nft',body,0o600),('/usr/local/sbin/dell-apply-network19-bridge',payload['helper'].encode(),0o750),('/etc/systemd/system/dell-network19-bridge.service',payload['unit'].encode(),0o644),('/etc/systemd/system/pve-guests.service.d/40-network19-bridge.conf',payload['drop'].encode(),0o644)]
for name,data,mode in files:
 path=Path(name);assert not path.exists() and not path.is_symlink();path.parent.mkdir(exist_ok=True,parents=True);path.write_bytes(data);path.chmod(mode)
subprocess.run(['systemctl','daemon-reload'],check=True,capture_output=True)
subprocess.run(['systemctl','enable','--now','dell-network19-bridge.service'],check=True,capture_output=True,timeout=30)
q=subprocess.run(['nft','-j','list','table','bridge','dell19_acl'],capture_output=True,text=True,check=True)
chains=[x['chain'] for x in json.loads(q.stdout)['nftables'] if 'chain'in x]
print(json.dumps({'at':datetime.datetime.now().isoformat(),'status':'dedicated-bridge19-ACL-applied','rules_sha256':hashlib.sha256(body).hexdigest(),'chains':[{'name':x['name'],'hook':x.get('hook')} for x in chains],'old_table_backup_PVE_only':str(backup),'PVE_management_IP_or_inet_NAT_not_changed':True,'bridge_nf_not_enabled':True,'startup_before_pve_guests':True,'actual_packet_acceptance':'pending-canary-migration'}))
'''
ast.parse(remote)
payload=json.dumps({'rules':rules,'helper':helper,'unit':unit,'drop':drop}).encode()
result=control.pve('python3 -c '+shlex.quote(remote),data=payload,timeout=90);(BASE/'network19/evidence/bridge-ACL-applied.json').write_bytes(result);print(result.decode())
