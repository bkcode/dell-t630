from pathlib import Path
import json,sys,datetime
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'scripts'));import control
P=r'''import json,subprocess,time,hashlib
from pathlib import Path
def run(a,timeout=90,check=True):
 p=subprocess.run(a,capture_output=True,text=True,timeout=timeout)
 if check and p.returncode:raise RuntimeError('fixed CF action failed '+a[0]+':'+p.stderr[-180:])
 return p

def ct(a):return run(['pct','exec','100','--',*a]).stdout
backup=Path('/root/dell-bootstrap/network19/cf');assert (backup/'100-before.conf').is_file()
record={'status':'starting-cold-recovery','token_exported':False,'protected_backup':'PVE-only','old_hot_attempt':'PVE restored oldNIC/IP but default route missing; preserving service with controlled container restart'}
result=backup/'cold-result.json'
def save():result.write_text(json.dumps(record,indent=2));result.chmod(0o600)
try:
 # Restore old functional default before controlled stop; old DHCP already reacquired original IP.
 ct(['ip','route','replace','default','via','192.168.21.1','dev','eth0'])
 unitpath=ct(['systemctl','show','cloudflared','--value','-p','FragmentPath']).strip();assert unitpath.startswith(('/etc/systemd/','/usr/lib/systemd/','/lib/systemd/'))
 before=ct(['sha256sum',unitpath]).split()[0]
 record['phase']='old-functional-restored';save()
 run(['pct','shutdown','100','--timeout','60']);assert 'stopped' in run(['pct','status','100']).stdout
 record['phase']='stopped';save()
 net='name=eth0,bridge=vmbr19,firewall=0,hwaddr=BC:24:11:42:04:C1,ip=192.168.19.5/24,gw=192.168.19.1,ip6=manual,type=veth'
 run(['pct','set','100','--net0',net,'--nameserver','192.168.19.1'])
 record['phase']='new-config-stopped';save();run(['pct','start','100']);record['phase']='new-container-started';save()
 end=time.monotonic()+60
 while True:
  p=run(['pct','exec','100','--','systemctl','is-active','cloudflared'],check=False)
  if p.returncode==0 and p.stdout.strip()=='active':break
  if time.monotonic()>end:raise RuntimeError('cloudflared-not-active')
  time.sleep(1)
 ips=json.loads(ct(['ip','-4','-j','addr','show','dev','eth0']));values=[a['local'] for x in ips for a in x.get('addr_info',[]) if a.get('family')=='inet'];assert values==['192.168.19.5']
 routes=json.loads(ct(['ip','-4','-j','route','show','default']));assert len(routes)==1 and routes[0].get('gateway')=='192.168.19.1'
 assert 'nameserver 192.168.19.1' in ct(['cat','/etc/resolv.conf'])
 assert before==ct(['sha256sum',unitpath]).split()[0]
 ct(['sh','-c',"printf '%s\\n' 'net.ipv6.conf.eth0.disable_ipv6=1' 'net.ipv6.conf.eth0.accept_ra=0' > /etc/sysctl.d/95-dell-cf-network19.conf; chmod 644 /etc/sysctl.d/95-dell-cf-network19.conf; sysctl -q -p /etc/sysctl.d/95-dell-cf-network19.conf"])
 record.update(status='CF-network19-committed-controlled-restart',IP=values,default=routes,service_unit_including_token_bytes_unchanged=True,cloudflared_active=True,IPv6disabled=ct(['sysctl','-n','net.ipv6.conf.eth0.disable_ipv6']).strip()=='1')
 save()
except Exception as e:
 record.update(status='failed-explicit-recovery-required',reason=type(e).__name__+':'+str(e)[:200]);save()
print(json.dumps(record))
'''
x=json.loads(control.pve('python3 -',data=P.encode(),timeout=240));x['at']=datetime.datetime.now().isoformat();(R/'network19/evidence/CF-network-move.json').write_text(json.dumps(x,indent=2)+'\n');print(json.dumps(x));assert x['status']=='CF-network19-committed-controlled-restart'
