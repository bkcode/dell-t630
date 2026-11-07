#!/usr/bin/python3
"""Root/QGA-only Ethernet networkd migration. NAS260 and router190 excluded; no app/host writes."""
import argparse,json,os,platform,socket,subprocess,uuid,hashlib,time,ipaddress
from pathlib import Path
ROOT=Path('/var/lib/dell-network19');NET=Path('/etc/systemd/network/00-dell-server19.network');CLOUD=Path('/etc/cloud/cloud.cfg.d/99-dell-server19-network.cfg');V6=Path('/etc/sysctl.d/95-dell-server19-interface.conf')
def run(a):
 p=subprocess.run(a,capture_output=True,text=True,timeout=30)
 if p.returncode:raise RuntimeError('fixed network action failed: '+a[0])
 return p.stdout
def put(p,data,mode=0o600):
 assert p.is_absolute() and not p.is_symlink() and p.parent.resolve()==p.parent
 p.parent.mkdir(parents=True,exist_ok=True);f=p.with_name(p.name+'.network19-new');assert not f.is_symlink();f.write_bytes(data);f.chmod(mode);os.replace(f,p)
def guard(c):
 assert os.geteuid()==0 and not Path('/etc/pve').exists() and c['vmid'] not in [190,260]
 assert socket.gethostname().split('.')[0]==c['hostname'] and platform.system()=='Linux'
 rows=json.loads(run(['ip','-j','addr']));found=[x for x in rows if x.get('address','').lower()==c['MAC'].lower()];assert len(found)==1
 i=found[0]['ifname'];assert i.isalnum() and len(i)<=15
 assert run(['systemctl','is-active','systemd-networkd.service']).strip()=='active'
 assert run(['systemctl','is-active','systemd-resolved.service']).strip()=='active'
 ips=[x['local'] for x in found[0].get('addr_info',[]) if x.get('family')=='inet'];return i,ips
def current():return json.loads((ROOT/'transaction.json').read_text())
def stage(c):
 i,ips=guard(c);assert c['old_ip'] in ips and c['new_ip'].startswith('192.168.19.') and c['gateway']=='192.168.19.1' and c['DNS']=='192.168.19.1'
 assert not (ROOT/'transaction.json').exists();ROOT.mkdir(mode=0o700,exist_ok=True);ROOT.chmod(0o700)
 old={}
 for p in [NET,CLOUD,V6]:
  assert not p.is_symlink();old[str(p)]={'hex':p.read_bytes().hex(),'mode':p.stat().st_mode&0o777} if p.exists() else None
 dns=[]
 try:
  for token in run(['resolvectl','dns',i]).partition(':')[2].split():dns.append(str(ipaddress.ip_address(token)))
 except Exception:raise RuntimeError('Cannot snapshot per-link DNS')
 v6={k:run(['sysctl','-n','net.ipv6.conf.'+i+'.'+k]).strip() for k in ['disable_ipv6','accept_ra','autoconf']}
 c.update(interface=i,old_files=old,old_DNS=dns,old_runtime_v6=v6,status='staged-old-network-active',nonce=uuid.uuid4().hex)
 put(ROOT/'transaction.json',(json.dumps(c)+'\n').encode());print(json.dumps({'status':c['status'],'interface':i,'nonce':c['nonce'],'network_changed':False}))
def apply(c):
 i,ips=guard(c);assert c['old_ip'] in ips or c['new_ip'] in ips
 body='[Match]\nMACAddress='+c['MAC']+'\n\n[Link]\nRequiredForOnline=yes\n\n[Network]\nDHCP=no\nAddress='+c['new_ip']+'/24\nGateway='+c['gateway']+'\nDNS='+c['DNS']+'\nIPv6AcceptRA=no\nLinkLocalAddressing=no\n'
 put(NET,body.encode(),0o644);put(CLOUD,b'network: {config: disabled}\n',0o644);put(V6,('net.ipv6.conf.'+i+'.disable_ipv6=1\nnet.ipv6.conf.'+i+'.accept_ra=0\nnet.ipv6.conf.'+i+'.autoconf=0\n').encode(),0o644)
 run(['networkctl','reload']);run(['networkctl','reconfigure',i]);run(['sysctl','-q','-p',str(V6)])
 end=time.monotonic()+50
 while True:
  _,after=guard(c);routes=json.loads(run(['ip','-j','route','show','default']))
  if c['new_ip'] in after and any(r.get('gateway')==c['gateway'] and r.get('dev')==i for r in routes):break
  if time.monotonic()>end:raise RuntimeError('New address/default route did not settle')
  time.sleep(.5)
 if c['old_ip']!=c['new_ip'] and c['old_ip'] in after:run(['ip','addr','del',c['old_ip']+'/24','dev',i])
 _,after=guard(c);assert after==[c['new_ip']]
 assert str(NET) in run(['networkctl','status','--no-pager','--lines=0',i]),'New00 NetworkFile not active'
 route=json.loads(run(['ip','-j','route','show','default']))
 for entry in route:
  if entry.get('gateway')==c['old_gateway'] and entry.get('dev')==i and c['old_gateway']!=c['gateway']:run(['ip','route','del','default','via',c['old_gateway'],'dev',i])
 route=json.loads(run(['ip','-j','route','show','default']));assert len(route)==1 and route[0].get('gateway')==c['gateway'] and route[0].get('dev')==i
 end=time.monotonic()+30
 while True:
  dns=[str(ipaddress.ip_address(v)) for v in run(['resolvectl','dns',i]).partition(':')[2].split()]
  if dns==[c['DNS']]:break
  if time.monotonic()>end:raise RuntimeError('New per-link DNS did not settle')
  time.sleep(.5)
 c['status']='new-network-committed';put(ROOT/'transaction.json',(json.dumps(c)+'\n').encode());print(json.dumps({'status':c['status'],'IP':c['new_ip'],'gateway':c['gateway'],'interface':i,'apps_started':False}))
def rollback(c):
 i,ips=guard(c)
 for text,value in c['old_files'].items():
  p=Path(text)
  if value is None:p.unlink(missing_ok=True)
  else:put(p,bytes.fromhex(value['hex']),value['mode'])
 run(['networkctl','reload']);run(['networkctl','reconfigure',i])
 end=time.monotonic()+40
 while True:
  _,after=guard(c)
  if c['old_ip'] in after:break
  if time.monotonic()>end:break
  time.sleep(.5)
 if c['old_ip'] not in after:run(['ip','addr','add',c['old_ip']+'/24','dev',i])
 if c['new_ip'] in after and c['new_ip']!=c['old_ip']:run(['ip','addr','del',c['new_ip']+'/24','dev',i])
 run(['ip','route','replace','default','via',c['old_gateway'],'dev',i])
 for key,value in c['old_runtime_v6'].items():run(['sysctl','-q','-w','net.ipv6.conf.'+i+'.'+key+'='+value])
 if c['old_DNS']:run(['resolvectl','dns',i,*c['old_DNS']])
 else:run(['resolvectl','revert',i])
 dns=[str(ipaddress.ip_address(v)) for v in run(['resolvectl','dns',i]).partition(':')[2].split()];assert dns==c['old_DNS']
 assert all(run(['sysctl','-n','net.ipv6.conf.'+i+'.'+k]).strip()==v for k,v in c['old_runtime_v6'].items())
 _,final_IPs=guard(c);assert final_IPs==[c['old_ip']] and c['new_ip'] not in final_IPs
 route=json.loads(run(['ip','-j','route','show','default']));assert len(route)==1 and route[0].get('gateway')==c['old_gateway'] and route[0].get('dev')==i
 assert str(NET) not in run(['networkctl','status','--no-pager','--lines=0',i]) or c['old_files'].get(str(NET)) is not None
 c['status']='old-network-restored';put(ROOT/'transaction.json',(json.dumps(c)+'\n').encode());print(json.dumps({'status':c['status'],'IP':c['old_ip'],'apps_started':False}))
p=argparse.ArgumentParser();p.add_argument('action',choices=['stage','apply','rollback','inspect']);a=p.parse_args()
try:
 if a.action=='stage':stage(json.load(__import__('sys').stdin))
 elif a.action=='apply':apply(current())
 elif a.action=='rollback':rollback(current())
 else:
  c=current();i,ips=guard(c);print(json.dumps({'status':c['status'],'interface':i,'IP':ips,'gateway':json.loads(run(['ip','-j','route','show','default']))}))
except Exception as e:print(json.dumps({'status':'failed','error_category':type(e).__name__,'details':'network-only transaction failed; use trusted QGA,do not blind retry'}));raise SystemExit(1)
