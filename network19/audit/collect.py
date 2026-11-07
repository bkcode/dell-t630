#!/usr/bin/env python3
"""Read-only PVE migration inventory. Whitelist VM/CT metadata; never dumps secrets."""
import json,datetime,sys
from pathlib import Path
from zoneinfo import ZoneInfo
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts'));import control
CODE=r'''
import json,subprocess,pathlib,re,datetime,socket
assert pathlib.Path('/etc/pve').exists() and socket.gethostname()=='pve'
def run(args,timeout=30):
 r=subprocess.run(args,capture_output=True,text=True,timeout=timeout);return {'exit_code':r.returncode,'stdout':r.stdout}
def parsed_config(path,kind):
 fields={};allowed={'name','hostname','memory','balloon','cores','sockets','onboot','startup','template','ciuser','citype','nameserver','searchdomain','ostype','agent','unprivileged'};interfaces={};cloud={}
 for line in path.read_text().splitlines():
  key,sep,value=line.partition(':')
  if not sep:continue
  value=value.strip()
  if key in allowed:fields[key]=value
  elif re.fullmatch(r'ipconfig\d+',key):cloud[key]=value
  elif re.fullmatch(r'net\d+',key):
   params={};allowed_net={'bridge','firewall','tag','trunks','link_down','mtu','queues','rate','name','hwaddr','ip','ip6','gw','gw6','type','model','macaddr','virtio','e1000','e1000e','rtl8139','vmxnet3'}
   for part in value.split(','):
    k,e,v=part.partition('=')
    if e and k in allowed_net:params[k]=v
   interfaces[key]=params
 return {'vmid':int(path.stem),'kind':kind,'fields':fields,'nics':interfaces,'cloudinit_network':cloud,'secret_fields_emitted':False}
resources=run(['pvesh','get','/cluster/resources','--type','vm','--output-format','json']);assert resources['exit_code']==0;resources=json.loads(resources['stdout']);index={x['vmid']:x for x in resources};rows=[]
for kind,folder in [('qemu','qemu-server'),('lxc','lxc')]:
 for path in sorted((pathlib.Path('/etc/pve')/folder).glob('*.conf'),key=lambda p:int(p.stem)):
  row=parsed_config(path,kind);res=index.get(row['vmid'],{});row['runtime']={k:res.get(k) for k in ['status','template','cpus','maxmem','mem','maxdisk','uptime']};row['qga_network']={'attempted':False}
  if kind=='qemu' and res.get('status')=='running':
   r=run(['qm','agent',str(row['vmid']),'network-get-interfaces'],12);row['qga_network']={'attempted':True,'exit_code':r['exit_code']}
   if r['exit_code']==0:
    try:
     nets=json.loads(r['stdout']);row['qga_network']['interfaces']=[{'name':n.get('name'),'hardware_address':n.get('hardware-address'),'ip_addresses':[{'address':a.get('ip-address'),'prefix':a.get('prefix'),'type':a.get('ip-address-type')} for a in n.get('ip-addresses',[])]} for n in nets]
    except ValueError:row['qga_network']['parse_failed']=True
  rows.append(row)
network={}
for key,args in {'ipv4_addresses':['ip','-j','-4','addr'],'ipv4_routes':['ip','-j','-4','route','show','table','all'],'ipv6_addresses':['ip','-j','-6','addr'],'ipv6_routes':['ip','-j','-6','route','show','table','all'],'bridge_links':['bridge','-j','link'],'ipv4_neighbors':['ip','-j','-4','neigh'],'nft_ruleset':['nft','-j','list','ruleset']}.items():
 r=run(args);network[key]={'exit_code':r['exit_code']}
 if r['exit_code']==0:
  try:network[key]['data']=json.loads(r['stdout'])
  except ValueError:network[key]['parse_failed']=True
network['forwarding']={k:pathlib.Path('/proc/sys')/k.replace('.','/') for k in ['net.ipv4.ip_forward','net.ipv6.conf.all.forwarding']};network['forwarding']={k:p.read_text().strip() for k,p in network['forwarding'].items()}
# Network files are restricted to interface/address/route-related directives; never read credentials.
configs=[]
for path in [pathlib.Path('/etc/network/interfaces'),*sorted(pathlib.Path('/etc/network/interfaces.d').glob('*'))]:
 if not path.is_file():continue
 lines=[]
 for line in path.read_text().splitlines():
  s=line.strip();first=s.split()[0] if s else ''
  if first in ['auto','allow-hotplug','iface','address','gateway','bridge-ports','bridge-stp','bridge-fd','bridge-vlan-aware','bridge-vids','source','source-directory','mtu']:lines.append(s)
 configs.append({'path':str(path),'allowed_directives':lines})
network['interface_files']=configs
mem={l.split(':',1)[0]:int(l.split()[1])*1024 for l in pathlib.Path('/proc/meminfo').read_text().splitlines() if l.startswith(('MemTotal:','MemAvailable:','SwapTotal:','SwapFree:'))}
print(json.dumps({'captured_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'mode':'read-only','commands':['pvesh get /cluster/resources --type vm --output-format json','whitelist /etc/pve/qemu-server/*.conf and /etc/pve/lxc/*.conf','qm agent RUNNING_VM network-get-interfaces','ip -j addr/route/neigh','bridge -j link','nft -j list ruleset','read forwarding sysctls and whitelisted interfaces directives'],'guests':rows,'vmid190_available':190 not in {x['vmid'] for x in rows} and 190 not in index,'all_resource_vmids':sorted(index),'host_memory_bytes':mem,'host_network':network,'config_secret_fields_emitted':False,'pve_or_guest_mutations':False}))
'''
def main():
 raw=control.pve('python3 -',data=CODE.encode(),timeout=200);j=json.loads(raw);p=ROOT/'network19/audit/current-inventory.json';p.write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'captured_at':j['captured_at_utc'],'guest_count':len(j['guests']),'vmid190_available':j['vmid190_available'],'guests':[{'vmid':x['vmid'],'kind':x['kind'],'name':x['fields'].get('name',x['fields'].get('hostname')),'status':x['runtime'].get('status'),'template':x['fields'].get('template'),'nics':x['nics'],'cloudinit':x['cloudinit_network']} for x in j['guests']]}))
if __name__=='__main__':main()
