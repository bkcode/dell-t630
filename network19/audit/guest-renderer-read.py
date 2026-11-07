#!/usr/bin/env python3
"""Fixed-scope read-only renderer/network-file inventory; no guest transactions."""
import json,sys,datetime
from pathlib import Path
from zoneinfo import ZoneInfo
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts'));import control
T={x['target']['vmid']:x['target'] for x in json.loads((ROOT/'evidence/implementation/private-guest-access.json').read_text())['roles']}
NIC=json.loads((ROOT/'network19/audit/nic-registry-stage.json').read_text());MAC={x['vmid']:next((x['nics']['net0'][m] for m in ['virtio','e1000','hwaddr'] if m in x['nics']['net0']),None) for x in NIC['guests'] if x['vmid'] in T}
CODE=r'''
import json,sys,pathlib,subprocess,re,socket,stat
p=json.load(sys.stdin);assert socket.gethostname()==p['hostname'] and not pathlib.Path('/etc/pve').exists()
def run(a):
 try:r=subprocess.run(a,capture_output=True,text=True,timeout=15);return r.returncode,r.stdout
 except (FileNotFoundError,subprocess.TimeoutExpired):return -1,''
_,raw=run(['ip','-j','addr']);links=json.loads(raw);link=[x for x in links if x.get('address','').lower()==p['mac'].lower()];assert len(link)==1;i=link[0]['ifname']
out={'vmid':p['vmid'],'hostname':socket.gethostname(),'interface':i,'mac':p['mac'],'interface_addresses':[{'family':x['family'],'address':x['local'],'prefix':x['prefixlen'],'dynamic':x.get('dynamic',False)} for x in link[0].get('addr_info',[])],'default_routes':{},'network_services':{}}
for family in ['-4','-6']:
 code,data=run(['ip','-j',family,'route','show','default']);out['default_routes'][family]={'exit':code,'routes':json.loads(data) if code==0 else []}
for unit in ['systemd-networkd.service','systemd-resolved.service','NetworkManager.service','networking.service']:
 code,data=run(['systemctl','show',unit,'-p','LoadState','-p','ActiveState','-p','SubState']);out['network_services'][unit]=dict(x.split('=',1) for x in data.splitlines() if '=' in x)
code,data=run(['networkctl','status',i,'--no-pager','--full']);out['networkctl_status']={'exit':code,'selected_lines':[l.strip().lstrip('●').strip() for l in data.splitlines() if re.match(r'^\s*(?:Link File|Network File|State|Online state|OnlineState|Type|Driver|Address|Gateway|DNS|DNS Domain|DHCP4 Client ID|DHCP6 Client DUID):',l)]}
code,data=run(['resolvectl','status',i,'--no-pager']);out['resolved_link']={'exit':code,'selected_lines':[l.strip() for l in data.splitlines() if re.match(r'^\s*(?:Current Scopes|Protocols|Current DNS Server|DNS Servers|DNS Domain|DefaultRoute setting):',l)]}
rp=pathlib.Path('/etc/resolv.conf');out['resolv_conf']={'symlink':rp.is_symlink(),'resolved_path':str(rp.resolve()),'settings':[l.strip() for l in rp.read_text().splitlines() if l.strip().split(' ',1)[0] in ['nameserver','search','domain','options']]}
allow={'Match':{'Name','MACAddress','PermanentMACAddress','Driver','Type','Kind','Virtualization','Host','Path'},'Link':{'RequiredForOnline','ActivationPolicy','MTUBytes','MACAddress'},'Network':{'Address','Gateway','DNS','Domains','DHCP','IPv6AcceptRA','LinkLocalAddressing','KeepConfiguration','ConfigureWithoutCarrier','DefaultRouteOnDevice','IPForward','LLMNR','MulticastDNS','IPv6PrivacyExtensions'},'DHCP':{'UseDNS','UseNTP','UseRoutes','UseGateway','RouteMetric','ClientIdentifier','UseDomains','UseHostname'},'DHCPv4':{'UseDNS','UseNTP','UseRoutes','UseGateway','RouteMetric','ClientIdentifier','UseDomains','UseHostname'},'DHCPv6':{'UseDNS','UseNTP','UseDomains'},'Address':{'Address','Peer','Scope','PreferredLifetime','AddPrefixRoute'},'Route':{'Gateway','Destination','PreferredSource','Scope','Metric','Table','Protocol','GatewayOnLink'},'RoutingPolicyRule':{'From','To','Table','Priority'}}
def parse(path):
 section='';rows=[]
 for l in path.read_text().splitlines():
  l=l.strip()
  if l.startswith('[') and l.endswith(']'):section=l[1:-1]
  elif '=' in l and not l.startswith(('#',';')):
   k,v=l.split('=',1)
   if k.strip() in allow.get(section,set()):rows.append({'section':section,'key':k.strip(),'value':v.strip()})
 return rows
files=[]
for priority,folder in enumerate(['/etc/systemd/network','/run/systemd/network','/usr/local/lib/systemd/network','/usr/lib/systemd/network']):
 d=pathlib.Path(folder)
 for f in sorted(d.glob('*.network')):
  files.append({'path':str(f),'basename':f.name,'directory_priority':priority,'symlink':f.is_symlink(),'masked':f.is_symlink() and str(f.resolve())=='/dev/null','selected_settings':parse(f) if f.is_file() else []})
  for drop in sorted(f.with_name(f.name+'.d').glob('*.conf')):files.append({'path':str(drop),'basename':drop.name,'dropin_for':f.name,'directory_priority':priority,'selected_settings':parse(drop)})
out['network_files']=files
out['ifupdown_files']=[]
for f in [pathlib.Path('/etc/network/interfaces'),*sorted(pathlib.Path('/etc/network/interfaces.d').glob('*'))]:
 if f.is_file():out['ifupdown_files'].append({'path':str(f),'selected_lines':[l.strip() for l in f.read_text().splitlines() if l.strip().split(' ',1)[0] in ['auto','allow-hotplug','iface','address','netmask','gateway','dns-nameservers','dns-search','source','source-directory']],'custom_up_down_commands_present':any(re.match(r'^\s*(?:pre-up|up|post-up|pre-down|down|post-down)\s',l) for l in f.read_text().splitlines())})
out['netplan_files']=[]
for f in sorted(pathlib.Path('/etc/netplan').glob('*.yaml')):
 safe=[]
 for l in f.read_text().splitlines():
  s=l.strip()
  if re.match(r'^(?:renderer|ethernets|match|macaddress|set-name|dhcp4|dhcp6|gateway4|gateway6|addresses|nameservers|routes|to|via|metric|optional|link-local|accept-ra|network|version):',s) or re.fullmatch(r'-\s*[0-9a-fA-F.:]+(?:/\d+)?',s):safe.append(l)
 out['netplan_files'].append({'path':str(f),'network_only_selected_lines':safe})
out['cloud_init_network_disable_files']=[]
for f in sorted(pathlib.Path('/etc/cloud/cloud.cfg.d').glob('*.cfg')):
 lines=f.read_text().splitlines();hit=[l.strip() for l in lines if re.match(r'^\s*network\s*:',l) or re.match(r'^\s*config\s*:\s*disabled\s*$',l) or re.match(r'^\s*disable_network_activation\s*:',l)]
 if hit:out['cloud_init_network_disable_files'].append({'path':str(f),'network_settings':hit})
for base in ['/run/cloud-init/network-config.json','/var/lib/cloud/instance/network-config.json']:
 f=pathlib.Path(base)
 if f.exists():out.setdefault('cloud_init_network_config_files_present',[]).append(base)
code,data=run(['cloud-id']);out['cloud_id']=data.strip() if code==0 else 'unavailable'
out['ipv6_interface_sysctl']={k:(pathlib.Path('/proc/sys/net/ipv6/conf')/i/k).read_text().strip() for k in ['disable_ipv6','accept_ra','autoconf'] if (pathlib.Path('/proc/sys/net/ipv6/conf')/i/k).exists()};out['secret_or_userdata_or_environment_read']=False
print(json.dumps(out))
'''
def main():
 roles={x['target']['vmid']:x['name'] for x in json.loads((ROOT/'evidence/implementation/private-guest-access.json').read_text())['roles']};D={'captured_at':datetime.datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),'mode':'read-only-renderer-audit','excluded':[190,260,100],'guests':[]}
 for v in [230,200,201,210,220,221,231,232,240,250,270]:
  import shlex
  r=control.guest(v,'sudo -n python3 -c '+shlex.quote(CODE),data=json.dumps({'vmid':v,'hostname':roles[v],'mac':MAC[v]}).encode(),timeout=95,info=T[v]);assert r['exit_code']==0,('readonly guest transport failed',v,r['exit_code']);out=json.loads(r['stdout']);D['guests'].append(out);p=ROOT/'network19/audit/guest-renderer-state.json';p.write_text(json.dumps(D,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'vmid':v,'interface':out['interface'],'networkctl':out['networkctl_status'],'default':out['default_routes']['-4'],'network_files':[(f['path'],f['selected_settings']) for f in out['network_files'] if f['path'].startswith(('/run/','/etc/'))]}),flush=True)
if __name__=='__main__':main()
