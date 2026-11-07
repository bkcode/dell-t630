#!/usr/bin/env python3
"""Read-only190 network metadata and short own-DNS queries, not cross-LAN proof."""
import datetime,importlib.util,json,shlex
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('mgr',HERE/'manager.py');mgr=importlib.util.module_from_spec(s);s.loader.exec_module(mgr)
CODE=r'''import json,os,socket,struct,subprocess,time
from pathlib import Path
if os.geteuid()!=0 or Path('/etc/pve').exists() or socket.gethostname().split('.')[0]!='network-gateway':raise SystemExit('190 only')
name='ops-service.dell.home.arpa';query=struct.pack('!HHHHHH',0x1901,0x100,1,0,0,0)+b''.join(bytes([len(p)])+p.encode() for p in name.split('.'))+b'\0'+struct.pack('!HH',1,1)
def skip(data,pos):
 for _ in range(128):
  v=data[pos]
  if v&0xc0==0xc0:return pos+2
  pos+=1
  if not v:return pos
  pos+=v
 raise ValueError('bounded DNS name')
def answers(data):
 ident,flags,questions,count,_,_=struct.unpack('!HHHHHH',data[:12])
 if ident!=0x1901 or flags&15:raise ValueError('DNS response rejected')
 pos=12
 for _ in range(questions):pos=skip(data,pos)+4
 out=[]
 for _ in range(count):
  pos=skip(data,pos);kind,cls,ttl,size=struct.unpack('!HHIH',data[pos:pos+10]);pos+=10
  if kind==1 and cls==1 and size==4:out.append(socket.inet_ntoa(data[pos:pos+size]))
  pos+=size
 return out
probe={}
for proto in ['udp','tcp']:
 try:
  sock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM if proto=='udp' else socket.SOCK_STREAM);sock.settimeout(3)
  if proto=='udp':sock.sendto(query,('192.168.19.1',53));data=sock.recv(4096)
  else:
   sock.connect(('192.168.19.1',53));sock.sendall(struct.pack('!H',len(query))+query);size=struct.unpack('!H',sock.recv(2))[0];data=b''
   while len(data)<size:data+=sock.recv(size-len(data))
  result=answers(data);probe[proto]={'A':result,'matches_migration_plan':result==['192.168.19.70']};sock.close()
 except Exception as error:probe[proto]={'passed':False,'error_category':type(error).__name__}
fields=subprocess.run(['systemctl','show','dell-gateway19-dnsmasq.service','-p','User','-p','Group','-p','AmbientCapabilities','-p','CapabilityBoundingSet','-p','NoNewPrivileges','-p','ProtectSystem','-p','ReadWritePaths','-p','MainPID','-p','ActiveState'],capture_output=True,text=True,check=True).stdout.splitlines();unit=dict(x.split('=',1) for x in fields if '='in x);pid=int(unit['MainPID']);process={}
for line in Path('/proc',str(pid),'status').read_text().splitlines():
 key,_,value=line.partition(':')
 if key in ['Uid','Gid','CapEff','CapAmb','NoNewPrivs']:process[key]=value.strip()
nf=json.loads(subprocess.run(['nft','-j','list','ruleset'],capture_output=True,text=True,check=True).stdout);chains=[{k:x['chain'].get(k) for k in ['family','table','name','type','hook','policy']} for x in nf['nftables'] if 'chain'in x]
lease=Path('/var/lib/misc/dnsmasq.leases').stat();out={'at':time.time(),'status':'read-only-gateway-metadata-and-ownDNS','DNS_short_queries':probe,'DNS_query_scope':'gateway-local socket only, not external-LAN-client proof','dnsmasq_unit':unit,'dnsmasq_process_metadata':process,'lease_owner_mode':{'uid':lease.st_uid,'gid':lease.st_gid,'mode':oct(lease.st_mode&0o777)},'chains':chains,'no_NAT':all(x['type']!='nat' for x in chains),'routes':json.loads(subprocess.run(['ip','-j','route'],capture_output=True,text=True,check=True).stdout),'IPv6_addresses':json.loads(subprocess.run(['ip','-j','-6','addr'],capture_output=True,text=True,check=True).stdout),'pending_transaction':Path('/var/lib/dell-gateway19/pending.json').exists(),'rollback_timer_active':subprocess.run(['systemctl','is-active','--quiet','dell-gateway19-rollback.timer']).returncode==0,'failed_units':subprocess.run(['systemctl','--failed','--no-legend','--plain'],capture_output=True,text=True).stdout.splitlines(),'forwarding':{key:subprocess.run(['sysctl','-n',key],capture_output=True,text=True,check=True).stdout.strip() for key in ['net.ipv4.ip_forward','net.ipv4.conf.all.forwarding','net.ipv4.conf.eth0.forwarding','net.ipv4.conf.eth1.forwarding']}}
print(json.dumps(out))'''
def main():
 target=json.loads((HERE.parent/'evidence/gateway-initial-access.json').read_text())['target'];result=mgr.ssh(target,'sudo -n python3 -c '+shlex.quote(CODE),timeout=60)
 if result['exit_code']:raise RuntimeError('read-only gateway audit failed; raw withheld')
 value={'at':datetime.datetime.now().astimezone().isoformat(),'result':json.loads(result['stdout'])};(HERE/'active-audit.json').write_text(json.dumps(value,indent=2)+'\n');print(json.dumps(value))
if __name__=='__main__':main()
