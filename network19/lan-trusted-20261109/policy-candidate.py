#!/usr/bin/env python3
"""Strict server19 gateway contract and deterministic, shell-free config rendering."""
import copy,hashlib,ipaddress,json,re
WAN=ipaddress.IPv4Network('192.168.21.0/24');LAN=ipaddress.IPv4Network('192.168.19.0/24');TABLE='dell_gateway19';FLOW_MARK='0x19000001';FAKE_MARK='0x19000002';CF_FAKE_MARK='0x19000003';WG_MARK='0x19000004';WG_FULL_MARK='0x19000005';LAN_FULL_MARK='0x19000006'
WG_NARROW={'source':'10.66.66.0/24','destination':'192.168.19.50','tcp':[9001],'no_NAT':True}
WG_FULL={'source':'10.66.66.0/24','destination':'192.168.19.0/24','protocols':'all','gateway_local_addresses':['192.168.21.23','192.168.19.1'],'no_NAT':True}
LAN_FULL={'source': '192.168.21.0/24', 'destination': '192.168.19.0/24', 'protocols': 'all', 'gateway_local_addresses': ['192.168.21.23', '192.168.19.1'], 'no_NAT': True}
NONPUBLIC=['0.0.0.0/8','10.0.0.0/8','100.64.0.0/10','127.0.0.0/8','169.254.0.0/16','172.16.0.0/12','192.0.0.0/24','192.0.2.0/24','192.168.0.0/16','198.18.0.0/15','198.51.100.0/24','203.0.113.0/24','224.0.0.0/4','240.0.0.0/4']
class Rejected(ValueError):pass

def ip(value,net):
 if not isinstance(value,str):raise Rejected('IPv4 text required')
 try:item=ipaddress.IPv4Network(value,strict=True)
 except ValueError:raise Rejected('canonical IPv4 network/address required') from None
 if not item.subnet_of(net):raise Rejected('address outside approved subnet')
 return str(item.network_address) if item.prefixlen==32 else str(item)

def mac(value):
 if not isinstance(value,str) or not re.fullmatch('[0-9a-f]{2}(:[0-9a-f]{2}){5}',value) or int(value[:2],16)&1 or value in ('00:00:00:00:00:00','ff:ff:ff:ff:ff:ff'):raise Rejected('canonical unicast MAC required')
 return value

def ports(values):
 if not isinstance(values,list) or not values or len(values)>32 or any(type(p) is not int or not 1<=p<=65535 for p in values) or len(set(values))!=len(values):raise Rejected('distinct bounded integer ports required')
 return sorted(values)

def endpoints(value,net):
 values=value if isinstance(value,list) else [value]
 if not values or len(values)>32:raise Rejected('bounded endpoint list required')
 result=[ip(v,net) for v in values]
 if len(set(result))!=len(result):raise Rejected('duplicate endpoint')
 return result

def load(plan,wan_mac,lan_mac):
 router=plan['router'];policy=plan['gateway_policy']
 if router['vmid']!=190 or router['hostname']!='network-gateway' or router['WAN']['ip']!='192.168.21.23/24' or router['WAN']['gateway']!='192.168.21.1' or router['LAN']['ip']!='192.168.19.1/24' or router.get('no_NAT_between_LAN_subnets') is not True:raise Rejected('fixed reviewed190 topology required')
 wm,lm=mac(wan_mac),mac(lan_mac)
 if wm==lm:raise Rejected('two distinct MACs required')
 mgmt=endpoints(plan['gateway_management_sources'],WAN)
 if '192.168.21.22' not in mgmt or any('/' in x for x in mgmt):raise Rejected('explicit management hosts including PVE required')
 required={'WAN_to_LAN','LAN_to_public_internet','CF_extra_public','publisher_optional_public_ssh','CF_legacy_LAN_origin_compatibility','default_forward','established_related','invalid','NAT','LAN_DNS_DHCP','gateway_ssh','IPv6','same_subnet_routed_attempts'}
 if (not required.issubset(policy) or set(policy)-required-{'OW_fake_IP_proxy_compatibility','CF_fake_IP_proxy_compatibility','WireGuard_client_access','LAN_trusted_client_access'}) or policy['NAT']!='none' or policy['default_forward']!='drop' or policy['invalid']!='drop' or policy['established_related'] is not True:raise Rejected('approved deny/return-state/noNAT policy required')
 records=[];seen=set()
 for row in plan['guest_addresses']:
  if row['vmid']==190:continue
  address=ip(row['new_ip'],LAN);role=row['name']
  if '/' in address or int(ipaddress.IPv4Address(address))&255 not in range(2,200) or address in seen or not re.fullmatch('[a-z0-9][a-z0-9-]{0,62}',role):raise Rejected('unique static role below DHCP pool required')
  seen.add(address);records.append({'role':role,'address':address})
 if not any(x=={'role':'cf-tunnel','address':'192.168.19.5'} for x in records):raise Rejected('existing CF fixed identity required')
 matrix=[]
 for row in policy['WAN_to_LAN']:
  if set(row)!={'src','dst','tcp'}:raise Rejected('unknown WAN matrix field')
  matrix.append({'src':endpoints(row['src'],WAN),'dst':endpoints(row['dst'],LAN),'tcp':ports(row['tcp'])})
 public=policy['LAN_to_public_internet']
 if set(public)!={'src','tcp','udp','icmp','exclude_private_destinations'} or public['src']!=str(LAN) or public['exclude_private_destinations'] is not True or public['icmp'] is not True:raise Rejected('explicit public-only egress required')
 tcp,udp=ports(public['tcp']),ports(public['udp'])
 if not {53,80,443}.issubset(tcp) or not {53,123}.issubset(udp):raise Rejected('approved DNS/web/NTP egress required')
 cf=policy['CF_extra_public'];pub=policy['publisher_optional_public_ssh'];compat=policy['CF_legacy_LAN_origin_compatibility']
 if cf!={'src':'192.168.19.5','tcp':[7844],'udp':[7844]} or pub!={'src':'192.168.19.30','tcp':[22]}:raise Rejected('exact CF QUIC/HTTP2 and publisher compatibility required')
 if set(compat)!={'src','dst','tcp','comment'} or compat['src']!='192.168.19.5' or compat['dst']!=str(WAN):raise Rejected('scoped legacy CF origin compatibility required')
 compat_ports=ports(compat['tcp'])
 if compat_ports!=[80,443,8081,8096,9001,9999]:raise Rejected('only approved CF origin ports')
 result={'schema_version':1,'vmid':190,'hostname':'network-gateway','WAN_MAC':wm,'LAN_MAC':lm,'management_hosts':mgmt,'hosts':records,'WAN_to_LAN':matrix,'public_tcp':tcp,'public_udp':udp,'CF_compat_tcp':compat_ports,'migration_plan_sha256':hashlib.sha256(json.dumps(plan,sort_keys=True,separators=(',',':')).encode()).hexdigest()}
 if 'OW_fake_IP_proxy_compatibility'in policy:
  raw=policy['OW_fake_IP_proxy_compatibility']
  if set(raw)!={'source','destination','tcp','udp','icmp','reason','evidence','no_NAT_or_private_subnet_expansion'} or raw['no_NAT_or_private_subnet_expansion'] is not True:raise Rejected('exact OW fake-IP plan fields required')
  result['OW_fake_IP_proxy']={k:raw[k] for k in ['source','destination','tcp','udp','icmp']}
 if 'CF_fake_IP_proxy_compatibility'in policy:
  raw=policy['CF_fake_IP_proxy_compatibility']
  if set(raw)!={'source','destination','tcp','udp','reason','evidence','no_NAT_or_other_role_scope_expansion'} or raw['no_NAT_or_other_role_scope_expansion'] is not True:raise Rejected('exact CF fake-IP plan fields required')
  result['CF_fake_IP_proxy']={k:raw[k] for k in ['source','destination','tcp','udp']}
 if 'WireGuard_client_access'in policy:
  raw=policy['WireGuard_client_access']
  narrow={'source','destination','tcp','reason','evidence','no_NAT'};full={'source','destination','protocols','gateway_local_addresses','reason','evidence','no_NAT'}
  if set(raw) not in (narrow,full) or raw['no_NAT'] is not True or not isinstance(raw['reason'],str) or not isinstance(raw['evidence'],str) or not raw['reason'] or not raw['evidence']:raise Rejected('exact explicit WireGuard authorization contract required')
  keys=['source','destination','tcp','no_NAT'] if set(raw)==narrow else ['source','destination','protocols','gateway_local_addresses','no_NAT']
  result['WireGuard_client_access']={k:raw[k] for k in keys}
 if 'LAN_trusted_client_access'in policy:
  raw=policy['LAN_trusted_client_access']
  if set(raw)!={'source','destination','protocols','gateway_local_addresses','reason','evidence','no_NAT'} or not raw['reason']or not raw['evidence']:raise Rejected('exact approved LAN trust contract required')
  result['LAN_trusted_client_access']={k:raw[k]for k in LAN_FULL}
 return validate_config(result)

def validate_config(config):
 # Runtime only accepts canonical output of the public master plan compiler, bound by its hash.
 required={'schema_version','vmid','hostname','WAN_MAC','LAN_MAC','management_hosts','hosts','WAN_to_LAN','public_tcp','public_udp','CF_compat_tcp','migration_plan_sha256'}
 if not isinstance(config,dict) or (not required.issubset(config) or set(config)-required-{'OW_fake_IP_proxy','CF_fake_IP_proxy','WireGuard_client_access','LAN_trusted_client_access'}) or config['schema_version']!=1 or config['vmid']!=190 or config['hostname']!='network-gateway' or not re.fullmatch('[a-f0-9]{64}',str(config['migration_plan_sha256'])):raise Rejected('canonical compiled config required')
 if mac(config['WAN_MAC'])==mac(config['LAN_MAC']):raise Rejected('distinct MACs required')
 mgmt=endpoints(config['management_hosts'],WAN)
 if '192.168.21.22' not in mgmt or any('/'in x for x in mgmt):raise Rejected('explicit management hosts required')
 for key in ('public_tcp','public_udp','CF_compat_tcp'):ports(config[key])
 if config['public_tcp']!=[53,80,443] or config['public_udp']!=[53,123] or config['CF_compat_tcp']!=[80,443,8081,8096,9001,9999]:raise Rejected('compiled fixed egress ports drift')
 for row in config['WAN_to_LAN']:
  if set(row)!={'src','dst','tcp'}:raise Rejected('matrix shape rejected')
  endpoints(row['src'],WAN);endpoints(row['dst'],LAN);ports(row['tcp'])
 if not 1<=len(config['WAN_to_LAN'])<=32 or not 1<=len(config['hosts'])<=64:raise Rejected('bounded static policy required')
 seen=set()
 for row in config['hosts']:
  if set(row)!={'role','address'} or not re.fullmatch('[a-z0-9][a-z0-9-]{0,62}',row['role']):raise Rejected('static host record rejected')
  address=ip(row['address'],LAN)
  if '/'in address or int(ipaddress.IPv4Address(address))&255 not in range(2,200) or address in seen:raise Rejected('invalid static host')
  seen.add(address)
 if 'OW_fake_IP_proxy'in config:
  if config['OW_fake_IP_proxy']!={'source':'192.168.19.0/24','destination':'198.18.0.0/15','tcp':[53,80,443],'udp':[53,123],'icmp':True} or type(config['OW_fake_IP_proxy'].get('icmp')) is not bool:raise Rejected('only exact OW managed fake-IP compatibility permitted')
 if 'CF_fake_IP_proxy'in config:
  if config['CF_fake_IP_proxy']!={'source':'192.168.19.5','destination':'198.18.0.0/15','tcp':[7844],'udp':[7844]}:raise Rejected('only CF19.5 exact fake-IP7844 permitted')
 if 'WireGuard_client_access'in config:
  if config['WireGuard_client_access'] not in (WG_NARROW,WG_FULL) or config['WireGuard_client_access'].get('no_NAT') is not True:raise Rejected('only exact narrow or explicitly risk-authorized full VPN contract permitted')
 if 'LAN_trusted_client_access'in config:
  if config['LAN_trusted_client_access']!=LAN_FULL or config['LAN_trusted_client_access'].get('no_NAT')is not True:raise Rejected('only exact explicit trustedLAN contract permitted')
 return config

def iface(value):
 if not isinstance(value,str) or not re.fullmatch('[A-Za-z0-9_.-]{1,15}',value) or value=='lo':raise Rejected('safe actual NIC name required')
 return value

def lit(values):return '{ '+', '.join(values)+' }'
def nft(config,interfaces):
 validate_config(config);wan,lan=iface(interfaces['WAN']),iface(interfaces['LAN'])
 return_marks=[FLOW_MARK]+([FAKE_MARK] if config.get('OW_fake_IP_proxy') else [])+([CF_FAKE_MARK] if config.get('CF_fake_IP_proxy') else [])+([WG_MARK] if config.get('WireGuard_client_access') else [])+([WG_FULL_MARK] if config.get('WireGuard_client_access')==WG_FULL else [])+([LAN_FULL_MARK]if config.get('LAN_trusted_client_access')==LAN_FULL else [])
 if wan==lan:raise Rejected('distinct interfaces required')
 lines=[f'table inet {TABLE} {{',f' set nonpublic {{ type ipv4_addr; flags interval; elements = {lit(NONPUBLIC)}; }}',f' set management {{ type ipv4_addr; elements = {lit(config["management_hosts"])}; }}',' chain input { type filter hook input priority 0; policy drop;','  iifname "lo" accept','  meta nfproto ipv6 drop','  ct state invalid drop',f'  iifname "{wan}" ip saddr 192.168.19.0/24 drop',f'  iifname "{lan}" ip saddr {{ 0.0.0.0, 192.168.19.0/24 }} udp sport 68 udp dport 67 ip daddr {{ 255.255.255.255, 192.168.19.255, 192.168.19.1 }} accept',f'  iifname "{lan}" ip saddr != 192.168.19.0/24 drop',f'  ct state established,related ct mark != {WG_FULL_MARK} ct mark != {LAN_FULL_MARK} accept',f'  iifname "{wan}" ip saddr @management ip daddr {{ 192.168.21.23, 192.168.19.1 }} tcp dport 22 accept',f'  iifname "{wan}" ip saddr @management ip daddr {{ 192.168.21.23, 192.168.19.1 }} icmp type echo-request limit rate 10/second burst 20 packets accept',f'  iifname "{lan}" ip saddr 192.168.19.0/24 ip daddr 192.168.19.1 udp dport 53 accept',f'  iifname "{lan}" ip saddr 192.168.19.0/24 ip daddr 192.168.19.1 tcp dport 53 accept','  counter drop',' }',' chain forward { type filter hook forward priority 0; policy drop;','  meta nfproto ipv6 drop','  ct state invalid drop',f'  iifname "{wan}" ip saddr 192.168.19.0/24 drop',f'  iifname "{lan}" ip saddr != 192.168.19.0/24 drop',f'  iifname "{lan}" oifname "{lan}" counter drop',f'  ct state established,related ct mark {lit(return_marks) if len(return_marks)>1 else FLOW_MARK} accept']
 if config.get('WireGuard_client_access')==WG_FULL:
  index=lines.index(f'  ct state established,related ct mark != {WG_FULL_MARK} ct mark != {LAN_FULL_MARK} accept')
  lines.insert(index,f'  iifname "{wan}" ip saddr 10.66.66.0/24 ip daddr {{ 192.168.21.23, 192.168.19.1 }} ct mark set {WG_FULL_MARK} counter accept comment "WG-TrustedVPN-Gateway-IPv4"')
  lines.append(f'  iifname "{wan}" oifname "{lan}" ip saddr 10.66.66.0/24 ip daddr 192.168.19.0/24 ct mark set {WG_FULL_MARK} counter accept comment "WG-TrustedVPN-Server19-IPv4"')
 elif config.get('WireGuard_client_access')==WG_NARROW:
  lines.append(f'  iifname "{wan}" oifname "{lan}" ip saddr 10.66.66.0/24 ip daddr 192.168.19.50 tcp dport 9001 ct state new ct mark set {WG_MARK} counter accept comment "WG-Penpot-TCP9001"')
 for row in config['WAN_to_LAN']:
  lines.append(f'  iifname "{wan}" oifname "{lan}" ip saddr {lit(row["src"])} ip daddr {lit(row["dst"])} tcp dport {lit([str(p) for p in row["tcp"]])} ct state new ct mark set {FLOW_MARK} accept')
 if config.get('LAN_trusted_client_access')==LAN_FULL:
  index=lines.index('  counter drop')
  lines.insert(index,f'  iifname "{wan}" ip saddr 192.168.21.0/24 ip daddr {{ 192.168.21.23, 192.168.19.1 }} ct mark set {LAN_FULL_MARK} counter accept comment "LAN-Trusted-Gateway-IPv4"')
  lines.append(f'  iifname "{wan}" oifname "{lan}" ip saddr 192.168.21.0/24 ip daddr 192.168.19.0/24 ct mark set {LAN_FULL_MARK} counter accept comment "LAN-Trusted-Server19-IPv4"')
 lines.append(f'  iifname "{lan}" oifname "{wan}" ip saddr 192.168.19.5 ip daddr 192.168.21.0/24 tcp dport {lit([str(p) for p in config["CF_compat_tcp"]])} ct state new ct mark set {FLOW_MARK} accept')
 if config.get('OW_fake_IP_proxy'):
  for proto,ports_key in [('tcp','tcp'),('udp','udp')]:
   lines.append(f'  iifname "{lan}" oifname "{wan}" ip saddr 192.168.19.0/24 ip daddr 198.18.0.0/15 {proto} dport {lit([str(x) for x in config["OW_fake_IP_proxy"][ports_key]])} ct state new ct mark set {FAKE_MARK} accept')
  lines.append(f'  iifname "{lan}" oifname "{wan}" ip saddr 192.168.19.0/24 ip daddr 198.18.0.0/15 ip protocol icmp ct state new ct mark set {FAKE_MARK} accept')
 if config.get('CF_fake_IP_proxy'):
  for proto in ['tcp','udp']:
   lines.append(f'  iifname "{lan}" oifname "{wan}" ip saddr 192.168.19.5 ip daddr 198.18.0.0/15 {proto} dport 7844 ct state new ct mark set {CF_FAKE_MARK} accept')
 for proto,key in [('tcp','public_tcp'),('udp','public_udp')]:
  lines.append(f'  iifname "{lan}" oifname "{wan}" ip saddr 192.168.19.0/24 ip daddr != @nonpublic {proto} dport {lit([str(p) for p in config[key]])} ct state new ct mark set {FLOW_MARK} accept')
  lines.append(f'  iifname "{lan}" oifname "{wan}" ip saddr 192.168.19.5 ip daddr != @nonpublic {proto} dport 7844 ct state new ct mark set {FLOW_MARK} accept')
 lines += [f'  iifname "{lan}" oifname "{wan}" ip saddr 192.168.19.30 ip daddr != @nonpublic tcp dport 22 ct state new ct mark set {FLOW_MARK} accept',f'  iifname "{lan}" oifname "{wan}" ip saddr 192.168.19.0/24 ip daddr != @nonpublic ip protocol icmp ct state new ct mark set {FLOW_MARK} accept','  counter drop',' }',' chain output { type filter hook output priority 0; policy accept; }','}']
 return '\n'.join(lines)+'\n'

def dnsmasq(config,interfaces):
 validate_config(config);wan,lan=iface(interfaces['WAN']),iface(interfaces['LAN'])
 lines=['port=53',f'interface={lan}',f'except-interface={wan}','except-interface=lo','listen-address=192.168.19.1','bind-interfaces',f'no-dhcp-interface={wan}','no-dhcp-interface=lo','no-resolv','server=192.168.21.1','domain-needed','bogus-priv','no-hosts','domain=dell.home.arpa','local=/dell.home.arpa/','dhcp-authoritative','dhcp-range=set:lan19,192.168.19.200,192.168.19.239,255.255.255.0,1h','dhcp-option=tag:lan19,option:router,192.168.19.1','dhcp-option=tag:lan19,option:dns-server,192.168.19.1','dhcp-lease-max=40','dhcp-leasefile=/var/lib/misc/dnsmasq.leases','dhcp-ignore-names','user=dnsmasq','group=nogroup']
 lines += ['host-record='+row['role']+','+row['role']+'.dell.home.arpa,'+row['address'] for row in config['hosts']]
 return '\n'.join(lines)+'\n'

def network(config,role):
 validate_config(config)
 if role not in ('WAN','LAN'):raise Rejected('fixed interface role required')
 address='192.168.21.23/24' if role=='WAN' else '192.168.19.1/24'
 lines=['[Match]','MACAddress='+config[role+'_MAC'],'','[Network]','Address='+address,'DHCP=no','LinkLocalAddressing=no','IPv6AcceptRA=no','IPv6Forwarding=no','IPMasquerade=no','LLMNR=no','MulticastDNS=no']
 if role=='WAN':lines+=['DNS=192.168.21.1','NTP=192.168.21.1','','[Route]','Destination=0.0.0.0/0','Gateway=192.168.21.1','Metric=100']
 return '\n'.join(lines)+'\n'
