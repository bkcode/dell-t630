#!/usr/bin/env python3
"""Offline bridge-family ACL candidate renderer. Never connects to or writes PVE."""
import argparse,ipaddress,json,re
from pathlib import Path
HERE=Path(__file__).resolve().parent

def render(plan,inventory,old_ops=False):
 retired=set(plan.get('retired_vmids',[]));temporary=set(plan.get('temporary_bootstrap_vmids',[]))|{int(row['vmid']) for row in plan['guest_addresses'] if row.get('temporary_build_only') is True}
 assert temporary.issubset({9040,9041,9042,9043,9044,9045}) and not temporary.intersection(retired), 'Only approved Fish temporary identities in bootstrap list'
 active=[x for x in plan['guest_addresses'] if int(x['vmid']) not in retired]
 ipmap={int(x['vmid']):str(ipaddress.IPv4Address(x['new_ip'])) for x in active}
 assert len(ipmap)==len(active), 'Duplicate active VMID refuses candidate'
 aliasmap={int(x['vmid']):x.get('additional_ips',[]) for x in active};all_addresses=[]
 for v,primary in ipmap.items():
  aliases=aliasmap[v];assert isinstance(aliases,list) and all(isinstance(x,str) and str(ipaddress.IPv4Address(x))==x for x in aliases)
  assert not (v==190 and aliases), 'Gateway NIC topology cannot acquire service aliases'
  for x in [primary,*aliases]:assert ipaddress.IPv4Address(x) in ipaddress.IPv4Network('192.168.19.0/24');all_addresses.append(x)
 assert len(set(all_addresses))==len(all_addresses), 'One active physical owner per IPv4'
 endpoints=plan.get('service_endpoints',{})
 if 'artifact-service'in endpoints:
  endpoint=endpoints['artifact-service'];assert set(endpoint)=={'vmid','ip','tcp'} and type(endpoint['vmid']) is int and endpoint['vmid'] not in retired and endpoint['vmid'] in ipmap
  assert endpoint['ip']=='192.168.19.31' and endpoint['tcp']==[8081] and endpoint['ip'] in [ipmap[endpoint['vmid']],*aliasmap[endpoint['vmid']]], 'Nexus endpoint must belong to approved physical NIC'
 else:endpoint={'vmid':221,'ip':ipmap.get(221),'tcp':[8081]}
 assert ipmap[190]=='192.168.19.1' and all(ipaddress.ip_address(x) in ipaddress.ip_network('192.168.19.0/24') for x in ipmap.values())
 rows=[];gw=[];guests=[];macids=[];ipids=[];access={'vmbr19'};warnings=[]
 policy=plan['gateway_policy'];management=[str(ipaddress.IPv4Address(x)) for x in plan['gateway_management_sources']];wan_rules=[]
 for rule in policy['WAN_to_LAN']:
  src=rule['src'] if isinstance(rule['src'],list) else [rule['src']];src=[str(ipaddress.ip_network(x,strict=False)) if '/' in x else str(ipaddress.ip_address(x)) for x in src];dst=str(ipaddress.ip_network(rule['dst'],strict=False)) if '/' in rule['dst'] else str(ipaddress.ip_address(rule['dst']));ports=sorted(set(int(x) for x in rule['tcp']));assert ports and all(1<=x<=65535 for x in ports);wan_rules.append({'src':src,'dst':dst,'tcp':ports})
 for vm in inventory['guests']:
  v=int(vm['vmid'])
  if v in retired:continue
  for name,nic in sorted(vm['nics'].items()):
   assert re.fullmatch('net[0-9]+',name);index=int(name[3:])
   assert not nic.get('tag') and not nic.get('trunks'), 'VLAN/trunk NIC needs separate explicit design'
   if v==190 and index!=1:continue
   mac=next((nic[x] for x in ['virtio','e1000','e1000e','rtl8139','vmxnet3','hwaddr'] if x in nic),None);assert mac and re.fullmatch(r'(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}',mac);mac=mac.lower()
   # Direct QEMU tap / CT veth and legacy PVE-firewall peer are both known aliases.
   ports=[('veth' if vm['kind']=='lxc' else 'tap')+str(v)+'i'+str(index),'fwpr'+str(v)+'p'+str(index)]
   ip=ipmap.get(v) if (index==0 or v==190) and not vm.get('template') else None
   ips=([ip,*aliasmap.get(v,[])] if ip else [])
   row={'vmid':v,'nic':name,'mac':mac,'ip':ip,'ips':ips,'ports':ports,'current_bridge':nic.get('bridge'),'template':vm.get('template',False),'role':'gateway-LAN' if v==190 else 'temporary-bootstrap' if v in temporary else 'approved-role' if ip else 'quarantine-DHCP-only'};rows.append(row)
   if nic.get('firewall')=='1':warnings.append({'vmid':v,'nic':name,'warning':'Requires parent firewall=0/direct tap-veth at activation. This stage guards vmbr19 only, never prospective old fwbr.'})
   for port in ports:
    macids.append((port,mac))
    for address in ips:ipids.append((port,address))
    (gw if v==190 else guests).append(port)
 assert gw and len({x['mac'] for x in rows})==len(rows),'Duplicate MAC identity refuses candidate'
 peer=set()
 def add(src,dst,ports):
  if src in ipmap and dst in ipmap:
   for port in ports:peer.add((ipmap[src],ipmap[dst],int(port)))
 add(201,200,[3306])
 for v in [230,231,232]:add(v,200,[3306]);add(v,201,[6379,5672,8848,9848])
 add(240,210,[3306,6379,5672,8848,9848]);add(220,240,[22])
 shared=plan.get('shared_resource_service')
 if shared is not None:
  assert shared=={'vmid':280,'ip':'192.168.19.80','clients':{'230':'192.168.19.40','240':'192.168.19.45'},'tcp':[2049],'shared_directory':True}, 'Only explicit shared NFS contract allowed'
  assert ipmap.get(280)=='192.168.19.80' and ipmap.get(230)=='192.168.19.40' and ipmap.get(240)=='192.168.19.45', 'Resource identities must match fixed roles'
  add(230,280,[2049]);add(240,280,[2049])
 for v in [200,201,210,220,230,231,232,240,250,270]:
  if v in ipmap and endpoint['ip']:
   for port in endpoint['tcp']:peer.add((ipmap[v],endpoint['ip'],port))
 for v in ipmap:
  if v!=190 and v not in temporary:add(270,v,[9100])
 public=set()
 # WAN port matrix is rendered from the manager-owned policy, never re-created here.
 q=json.dumps
 def nft_set(name,types,values,fmt):
  values=sorted(set(values));s='  set '+name+' {\n    type '+types+';\n'
  if values:s+='    elements = { '+', '.join(fmt(x) for x in values)+' };\n'
  return s+'  }\n'
 out=['# OFFLINE CANDIDATE ONLY: parent must nft -c and atomically apply owned table.','# No host L3 routing/NAT or PVE firewall daemon dependency.','# Direct tap/veth required. Host INPUT/OUTPUT guard only vmbr19 in this stage.','table bridge dell19_acl {']
 out.append(nft_set('mac_ids','ifname . ether_addr',macids,lambda x:q(x[0])+' . '+x[1]))
 out.append(nft_set('ip_ids','ifname . ipv4_addr',ipids,lambda x:q(x[0])+' . '+x[1]))
 for name,values in [('gateway_ports',gw),('guest_ports',guests),('access_bridges',access)]:out.append(nft_set(name,'ifname',values,lambda x:q(x)))
 out.append(nft_set('peer_tcp','ipv4_addr . ipv4_addr . inet_service',peer,lambda x:x[0]+' . '+x[1]+' . '+str(x[2])))
 out.append(nft_set('lan_tcp','ipv4_addr . inet_service',public,lambda x:x[0]+' . '+str(x[1])))
 out+=['''  chain host_input {
    type filter hook input priority -200; policy accept;
    meta ibrname @access_bridges counter drop comment "no-host-service-on-server19-or-access-fwbr"
  }
  chain host_output {
    type filter hook output priority -200; policy accept;
    meta obrname @access_bridges counter drop comment "host-client-route-must-use-gateway-WAN"
  }
  chain forward {
    type filter hook forward priority -200; policy accept;
    meta ibrname "vmbr19" jump server19
    meta obrname "vmbr19" jump server19
  }
  chain server19 {
    ether type { 0x86dd, 0x8100, 0x88a8 } counter drop comment "no-ipv6-vlan-bypass"
    meta iifname . ether saddr != @mac_ids counter drop comment "unknown-port-or-source-MAC"
    ether type arp jump arp_guard
    ether type ip jump ip_guard
    counter drop comment "unapproved-ethertype"
  }
  chain arp_guard {
    meta iifname . arp saddr ether != @mac_ids counter drop comment "ARP-SHA-source-binding"
    arp operation request arp saddr ip 0.0.0.0 arp daddr ip 192.168.19.0/24 counter accept comment "address-probe"
    meta iifname . arp saddr ip @ip_ids counter accept comment "ARP-SPA-exact-port-IP"
    counter drop comment "ARP-source-IP-spoof"
  }
  chain ip_guard {
    meta iifname @guest_ports meta oifname @gateway_ports ip saddr { 0.0.0.0, 192.168.19.0/24 } udp sport 68 udp dport 67 counter accept comment "MAC-bound-DHCP-client-only"
    meta iifname @gateway_ports meta oifname @guest_ports ip saddr 192.168.19.1 udp sport 67 udp dport 68 counter accept comment "gateway-only-DHCP-server"
    meta oifname . ether daddr != @mac_ids counter drop comment "unicast-destination-MAC-binding"
    meta iifname @gateway_ports jump from_gateway
    meta iifname @guest_ports jump from_guest
    counter drop comment "unregistered-direction"
  }
  chain from_gateway {
    ip saddr 192.168.19.0/24 ip saddr != 192.168.19.1 counter drop comment "gateway-cannot-spoof-peer19"
    meta oifname . ip daddr != @ip_ids counter drop comment "approved-destination-IP-only"
    ct state invalid counter drop
    ct state { established, related } counter accept
    ip saddr 192.168.19.1 ip protocol icmp counter accept comment "gateway-diagnostics"''']
 nacos_lan=[]
 for index,rule in enumerate(wan_rules):
  # Preserve the already-applied dedicated Nacos line and its position after WG.
  if rule=={'src':['192.168.21.0/24'],'dst':'192.168.19.20','tcp':[8848,9848]}:
   nacos_lan.append(rule);continue
  src=rule['src'][0] if len(rule['src'])==1 else '{ '+', '.join(rule['src'])+' }';ports=str(rule['tcp'][0]) if len(rule['tcp'])==1 else '{ '+', '.join(map(str,rule['tcp']))+' }';out.append('    ip saddr '+src+' ip daddr '+rule['dst']+' tcp dport '+ports+' counter accept comment '+q('manager-WAN-to-LAN-'+str(index)))
 assert len(nacos_lan)<=1,'Duplicate dedicated LAN test-Nacos rule'
 vpn=policy.get('WireGuard_client_access')
 if vpn is not None:
  assert vpn['source']=='10.66.66.0/24' and vpn['no_NAT'] is True
  if set(vpn)=={'source','destination','tcp','reason','evidence','no_NAT'}:
   assert vpn['destination']=='192.168.19.50' and vpn['tcp']==[9001]
   out.append('    ip saddr 10.66.66.0/24 ip daddr 192.168.19.50 tcp dport 9001 counter accept comment "WireGuard-Penpot-only"')
  else:
   assert set(vpn)=={'source','destination','protocols','gateway_local_addresses','reason','evidence','no_NAT'}
   assert vpn['destination']=='192.168.19.0/24' and vpn['protocols']=='all' and vpn['gateway_local_addresses']==['192.168.21.23','192.168.19.1']
   # Explicitly authorized trusted VPN zone, only routed frames after all binding guards.
   out.append('    ip saddr 10.66.66.0/24 ip daddr 192.168.19.0/24 counter accept comment "trusted-WireGuard-to-server19"')
 if nacos_lan:
  out.append('    ip saddr 192.168.21.0/24 ip daddr 192.168.19.20 tcp dport { 8848, 9848 } counter accept comment "LAN-test-Nacos-only"')
 trusted_lan=policy.get('LAN_trusted_client_access')
 if trusted_lan is not None:
  assert set(trusted_lan)=={'source','destination','protocols','gateway_local_addresses','reason','evidence','no_NAT'}, 'Exact trusted LAN fields required'
  assert trusted_lan['source']=='192.168.21.0/24' and trusted_lan['destination']=='192.168.19.0/24' and trusted_lan['protocols']=='all' and trusted_lan['gateway_local_addresses']==['192.168.21.23','192.168.19.1'] and trusted_lan['no_NAT'] is True, 'Only confirmed LAN21/server19 noNAT contract allowed'
  assert isinstance(trusted_lan['reason'],str) and trusted_lan['reason'] and isinstance(trusted_lan['evidence'],str) and trusted_lan['evidence'], 'Trusted LAN authorization provenance required'
  out.append('    ip saddr 192.168.21.0/24 ip daddr 192.168.19.0/24 counter accept comment "trusted-LAN21-to-server19"')
 if old_ops:out.append('    ip saddr 10.63.30.40 tcp dport 9100 counter accept comment "TEMP-old-Ops-cutover-remove-final"')
 out+=['''    counter drop comment "gateway-ingress-denied"
  }
  chain from_guest {
    meta iifname . ip saddr != @ip_ids counter drop comment "guest-source-IP-binding"
    meta oifname @gateway_ports jump to_gateway
    meta oifname . ip daddr != @ip_ids counter drop comment "peer-destination-IP-binding"
    ct state invalid counter drop
    ct state { established, related } counter accept
    ip saddr . ip daddr . tcp dport @peer_tcp counter accept comment "explicit-role-TCP-matrix"
    counter drop comment "east-west-denied"
  }
  chain to_gateway {
    ip daddr 192.168.19.0/24 ip daddr != 192.168.19.1 counter drop comment "no-peer-hairpin-through-gateway"
    ct state invalid counter drop
    ct state { established, related } counter accept
    ip daddr 192.168.19.1 udp dport 53 counter accept
    ip daddr 192.168.19.1 tcp dport 53 counter accept
    ip daddr 192.168.19.1 ip protocol icmp counter accept''']
 if 270 in ipmap:out.append('    ip saddr '+ipmap[270]+' ip daddr 192.168.19.1 tcp dport 9100 counter accept comment "Ops-gateway-exporter-if-activated"')
 out+=['    ip daddr 192.168.21.0/24 counter drop comment "no-unapproved-server-to-management-LAN-session"','    ip daddr 192.168.19.1 counter drop comment "no-other-gateway-service"']
 egress=policy['LAN_to_public_internet']
 if egress.get('exclude_private_destinations'):out.append('    ip daddr { 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16 } counter drop comment "manager-exclude-private-destinations"')
 for proto in ['tcp','udp']:
  ports=sorted(set(int(x) for x in egress.get(proto,[])));assert all(1<=x<=65535 for x in ports)
  if ports:out.append('    '+proto+' dport { '+', '.join(map(str,ports))+' } counter accept comment "manager-public-egress"')
 if egress.get('icmp'):out.append('    ip protocol icmp counter accept')
 for key in ['CF_extra_public','publisher_optional_public_ssh']:
  rule=policy[key];src=str(ipaddress.ip_address(rule['src']))
  for proto in ['tcp','udp']:
   ports=sorted(set(int(x) for x in rule.get(proto,[])));assert all(1<=x<=65535 for x in ports)
   if ports:out.append('    ip saddr '+src+' '+proto+' dport { '+', '.join(map(str,ports))+' } counter accept comment '+q('manager-'+key))
 out+=['    counter drop comment "unapproved-egress"','  }','}']
 return '\n'.join(out)+'\n',{'status':'offline-candidate-not-applied','retired_vmids':sorted(retired),'temporary_bootstrap_vmids':sorted(temporary),'service_endpoints':endpoints,'inventory_timestamp':inventory.get('captured_at'),'rows':rows,'warnings':warnings,'peer_tcp_tuple_count':len(peer),'wan_to_lan_rules':wan_rules,'management_sources':management,'CF_legacy_LAN_origin_compatibility_enabled':False,'host_guard_bridges':['vmbr19'],'direct_attachment_required':True,'old_ops_transition_exception':old_ops,'required_before_apply':['Parent-owned nft -c with needed nf_tables_bridge/NFT_BRIDGE_META/NF_CONNTRACK_BRIDGE support; no such validation was run by read-only agent.','Atomic transaction delete/recreate only bridge dell19_acl; rollback table+startup mechanism preserved.','Confirm source/destination interface aliases and meta ibrname/obrname visibility using dedicated test before real data migration.','No blanket inet-forward ACCEPT workaround is needed while bridge-nf flags remain0; preserve/recheck them.','All target NICs must be firewall=0/direct tap-veth before activation; host guard onlyvmbr19. No prospective old-fwbr guard is applied in this stage.','MAC/IP registry refreshed before clone activation; unknown/template clone remains DHCP-only, never automatic prod role.','CF internal origin allowlist is unknown and intentionally not granted; parent must add exact approved origins.','New same-tools arbitrary SSH/other traffic is intentionally not preserved; review any required dependency before cutover.']}
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--plan',type=Path,default=HERE.parent/'migration-plan.json');p.add_argument('--inventory',type=Path,default=HERE/'nic-registry-current.json');p.add_argument('--output',type=Path,default=HERE/'bridge19-acl-candidate.nft');p.add_argument('--allow-old-ops-during-cutover',action='store_true');a=p.parse_args();rules,notes=render(json.loads(a.plan.read_text()),json.loads(a.inventory.read_text()),a.allow_old_ops_during_cutover);a.output.write_text(rules);a.output.with_suffix('.json').write_text(json.dumps(notes,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'candidate':str(a.output),'applied':False,'nic_identities':len(notes['rows']),'peer_tuple_count':notes['peer_tcp_tuple_count'],'warnings':len(notes['warnings'])}))
if __name__=='__main__':main()
