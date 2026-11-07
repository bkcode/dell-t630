#!/usr/bin/env python3
"""PVE-owned LXC network-only transaction; no token/config export."""
from pathlib import Path
import json,sys,datetime
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'scripts'));import control
P=r'''import json,subprocess,os,time
from pathlib import Path
def run(a):
 p=subprocess.run(a,capture_output=True,text=True,timeout=60)
 if p.returncode:raise RuntimeError('fixed-CF-network-action-failed:'+a[0])
 return p.stdout
conf=Path('/etc/pve/lxc/100.conf');old=conf.read_bytes();rows={x.split(': ',1)[0]:x.split(': ',1)[1] for x in old.decode().splitlines() if ': ' in x};assert rows['hostname']=='cf-tunnel' and rows['net0']=='name=eth0,bridge=vmbr0,firewall=1,hwaddr=BC:24:11:42:04:C1,ip=dhcp,type=veth'
root=Path('/root/dell-bootstrap/network19/cf');root.mkdir(mode=0o700,exist_ok=False)
p=root/'100-before.conf';p.write_bytes(old);p.chmod(0o600)
def ct(args):return run(['pct','exec','100','--',*args])
pid=ct(['systemctl','show','cloudflared','--value','-p','MainPID']).strip();assert pid.isdigit() and int(pid)>0
p=root/'resolv-before';p.write_text(ct(['cat','/etc/resolv.conf']));p.chmod(0o600)
p=root/'interfaces-before';p.write_text(ct(['cat','/etc/network/interfaces']));p.chmod(0o600)
old_v6={key:ct(['sysctl','-n','net.ipv6.conf.eth0.'+key]).strip() for key in ['disable_ipv6','accept_ra']}
assert ct(['sh','-c','test ! -e /etc/sysctl.d/95-dell-cf-network19.conf && echo absent']).strip()=='absent'
new='name=eth0,bridge=vmbr19,firewall=0,hwaddr=BC:24:11:42:04:C1,ip=192.168.19.5/24,gw=192.168.19.1,ip6=manual,type=veth'
record={'container':100,'old_IP':'192.168.21.150','new_IP':'192.168.19.5','token_read_or_exported':False,'protected_backup_location':'PVE-only','cloudflared_PID_before':pid}
try:
 run(['pct','set','100','--net0',new,'--nameserver','192.168.19.1'])
 end=time.monotonic()+35
 while True:
  ips=json.loads(ct(['ip','-4','-j','addr','show','dev','eth0']));v=[a['local'] for x in ips for a in x.get('addr_info',[]) if a.get('family')=='inet']
  routes=json.loads(ct(['ip','-4','-j','route','show','default']))
  if v==['192.168.19.5'] and len(routes)==1 and routes[0].get('gateway')=='192.168.19.1':break
  if time.monotonic()>end:raise RuntimeError('CF-new-network-not-settled')
  time.sleep(.5)
 # Interface-only IPv6 policy, applied inside the unprivileged container namespace.
 ct(['sh','-c',"install -m 644 /dev/null /etc/sysctl.d/95-dell-cf-network19.conf; printf '%s\\n' 'net.ipv6.conf.eth0.disable_ipv6=1' 'net.ipv6.conf.eth0.accept_ra=0' > /etc/sysctl.d/95-dell-cf-network19.conf; sysctl -q -p /etc/sysctl.d/95-dell-cf-network19.conf"])
 assert ct(['systemctl','is-active','cloudflared']).strip()=='active'
 after=ct(['systemctl','show','cloudflared','--value','-p','MainPID']).strip();assert after==pid
 assert 'nameserver 192.168.19.1' in ct(['cat','/etc/resolv.conf'])
 sockets=ct(['ss','-H','-tunp']);record['active_7844_connections']=sum('7844' in line and 'cloudflared' in line for line in sockets.splitlines())
 record.update(status='CF-network19-committed-token-and-process-preserved',cloudflared_PID_after=after,network={'IP':v,'default':routes},IPv6=ct(['sysctl','-n','net.ipv6.conf.eth0.disable_ipv6']).strip())
except Exception as e:
 errors=[]
 try:
  ct(['rm','-f','/etc/sysctl.d/95-dell-cf-network19.conf'])
  for key,value in old_v6.items():ct(['sysctl','-q','-w','net.ipv6.conf.eth0.'+key+'='+value])
 except Exception:errors.append('interface-IPv6-rollback')
 for args in [['pct','set','100','--net0',rows['net0']],(['pct','set','100','--nameserver',rows['nameserver']] if 'nameserver' in rows else ['pct','set','100','--delete','nameserver'])]:
  try:run(args)
  except Exception:errors.append('PVE-config-rollback')
 record.update(status='failed-network-rollback-attempted',reason=type(e).__name__,rollback_errors=errors)
 print(json.dumps(record));raise SystemExit(1)
print(json.dumps(record))
'''
result=json.loads(control.pve('python3 -',data=P.encode(),timeout=150));result['at']=datetime.datetime.now().isoformat();(R/'network19/evidence/CF-network-move.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
