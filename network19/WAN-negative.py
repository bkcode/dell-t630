from pathlib import Path
import sys,json,shlex,datetime
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'scripts'));import control
info=json.loads((R/'network19/evidence/gateway-initial-access.json').read_text())
if 'target' in info:info=info['target']
# Stored gateway receipt has public transport identity; normalize without accepting keys.
info={'vmid':190,'ip':'192.168.21.23','host_key_alias':'dell-gw190'}
def counter():
 r=control.guest(190,'sudo nft -j list chain inet dell_gateway19 forward',info=info);assert r['exit_code']==0
 rules=[v['rule'] for v in json.loads(r['stdout'])['nftables'] if 'rule' in v]
 drops=[r for r in rules if len(r['expr'])==2 and 'counter' in r['expr'][0] and 'drop' in r['expr'][1]];assert len(drops)==1
 return drops[0]['expr'][0]['counter']['packets']
before=counter()
P=r'''import socket,struct,json
from pathlib import Path
# Real host client positive control: listener is healthy and approved21.22 is allowed.
with socket.create_connection(('192.168.19.10',3306),timeout=3):pass
src=socket.inet_aton('192.0.2.19');dst=socket.inet_aton('192.168.19.10')
def csum(data):
 if len(data)%2:data+=b'\0'
 n=sum(struct.unpack('!'+str(len(data)//2)+'H',data));n=(n&65535)+(n>>16);n=(n&65535)+(n>>16);return (~n)&65535
tcp=struct.pack('!HHLLBBHHH',65019,3306,0x19630001,0,5<<4,2,1024,0,0);pseudo=src+dst+struct.pack('!BBH',0,6,len(tcp));tcp=tcp[:16]+struct.pack('!H',csum(pseudo+tcp))+tcp[18:]
ip=struct.pack('!BBHHHBBH4s4s',0x45,0,40,0x1963,0,64,6,0,src,dst);ip=ip[:10]+struct.pack('!H',csum(ip))+ip[12:]
mac=bytes.fromhex(Path('/sys/class/net/vmbr0/address').read_text().strip().replace(':',''));frame=bytes.fromhex('026319019000')+mac+bytes.fromhex('0800')+ip+tcp
with socket.socket(socket.AF_PACKET,socket.SOCK_RAW,socket.htons(0x0800)) as s:s.bind(('vmbr0',0));sent=s.send(frame)
print(json.dumps({'real_PVE_client_to_data200_TCP3306':True,'diagnostic_untrusted_source':'192.0.2.19 TEST-NET documentation address, no real LAN client impersonated','destination':'192.168.19.10:3306 existing healthy MySQL listener','source_MAC':'real PVE vmbr0 MAC','ether_destination':'existing GW190 WAN MAC','raw_unicast_SYN_sent':1,'bytes':sent,'ARP_broadcast_credentials_or_SQL_sent':False,'network_configuration_changed':False}))'''
x=json.loads(control.pve('python3 -',data=P.encode()));after=counter();x.update(at=datetime.datetime.now().isoformat(),GW_forward_final_drop_before=before,GW_forward_final_drop_after=after,GW_forward_final_drop_delta=after-before,passed=after-before>=1,scope='one deliberately untrusted WAN source to real healthy internal listener; other WAN ports remain configuration-only validation');(R/'network19/evidence/WAN-untrusted-source-negative.json').write_text(json.dumps(x,indent=2)+'\n');print(json.dumps(x));assert x['passed']
