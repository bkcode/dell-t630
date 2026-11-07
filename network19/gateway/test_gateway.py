#!/usr/bin/env python3
"""Offline parser and fake-kernel transaction regressions. No host network access."""
import copy,importlib.util,json,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
sys.dont_write_bytecode=True;HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE));import policy as p
spec=importlib.util.spec_from_file_location('gateway_runtime',HERE/'manage.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
PLAN=json.loads((HERE.parent/'migration-plan.json').read_text());MAC=('02:63:19:01:90:00','02:63:19:01:90:01');IF={'WAN':'ens9','LAN':'enp7s0'}
def config():
 plan=copy.deepcopy(PLAN);plan['gateway_policy'].pop('CF_fake_IP_proxy_compatibility',None);plan['gateway_policy'].pop('WireGuard_client_access',None);return p.load(plan,*MAC)
class Parser(unittest.TestCase):
 def test_parent_plan_compiles_fixed_topology(self):
  c=config();p.validate_config(c);self.assertEqual(c['vmid'],190);self.assertEqual(c['management_hosts'],['192.168.21.22','192.168.21.116'])
 def test_wrong_router_NAT_default_allow_rejected(self):
  for section,key,value in [('router','vmid',191),('gateway_policy','NAT','masquerade'),('gateway_policy','default_forward','accept')]:
   plan=copy.deepcopy(PLAN);plan[section][key]=value
   with self.assertRaises(p.Rejected):p.load(plan,*MAC)
 def test_IPv6_or_wrong_subnet_or_hostbits_rejected(self):
  for ip in ['::1','192.168.21.0/23','192.168.21.3/24','0.0.0.0/0','192.168.19.5; accept']:
   with self.assertRaises(p.Rejected):p.ip(ip,p.WAN)
 def test_explicit_management_hosts_required_not_entire_subnet(self):
  plan=copy.deepcopy(PLAN);plan['gateway_management_sources']=['192.168.21.0/24']
  with self.assertRaises(p.Rejected):p.load(plan,*MAC)
 def test_MAC_multicast_same_or_injected_rejected(self):
  for bad in ['ff:ff:ff:ff:ff:ff','01:00:00:00:00:01','02:63:19:01:90:00\naccept']:
   with self.assertRaises(p.Rejected):p.load(PLAN,bad,MAC[1])
  with self.assertRaises(p.Rejected):p.load(PLAN,MAC[0],MAC[0])
 def test_boolean_and_duplicate_ports_rejected(self):
  for values in [[True],[0],[65536],[22,22],['22; accept']]:
   with self.assertRaises(p.Rejected):p.ports(values)
 def test_DHCP_static_collision_or_duplicate_rejected(self):
  plan=copy.deepcopy(PLAN);plan['guest_addresses'][0]['new_ip']='192.168.19.200'
  with self.assertRaises(p.Rejected):p.load(plan,*MAC)
  plan=copy.deepcopy(PLAN);plan['guest_addresses'][1]['new_ip']=plan['guest_addresses'][0]['new_ip']
  with self.assertRaises(p.Rejected):p.load(plan,*MAC)
 def test_DNS_record_injection_rejected(self):
  plan=copy.deepcopy(PLAN);plan['guest_addresses'][0]['name']='cf-tunnel\nserver=attacker'
  with self.assertRaises(p.Rejected):p.load(plan,*MAC)
 def test_CF_transport_must_keep_QUIC_and_HTTP2(self):
  plan=copy.deepcopy(PLAN);plan['gateway_policy']['CF_extra_public']['udp']=[]
  with self.assertRaises(p.Rejected):p.load(plan,*MAC)
 def test_runtime_schema_rejects_extra_fields_and_unsafe_interface(self):
  c=config();c['shell']='id'
  with self.assertRaises(p.Rejected):p.validate_config(c)
  with self.assertRaises(p.Rejected):p.nft(config(),{'WAN':'eth0";accept','LAN':'eth1'})
class Rendering(unittest.TestCase):
 def test_denies_ipv6_default_and_same_LAN_hairpin_no_NAT(self):
  text=p.nft(config(),IF);self.assertIn('policy drop',text);self.assertIn('iifname "enp7s0" oifname "enp7s0" counter drop',text);self.assertIn('ct state established,related ct mark',text)
  for token in ['masquerade','snat','dnat','flush ruleset']:self.assertNotIn(token,text.lower())
 def test_DHCP_DNS_LAN_only_pool_separate_from_statics(self):
  text=p.dnsmasq(config(),IF);self.assertIn('interface=enp7s0\n',text);self.assertIn('except-interface=ens9\n',text);self.assertIn('no-dhcp-interface=ens9\n',text);self.assertIn('listen-address=192.168.19.1',text);self.assertIn('192.168.19.200,192.168.19.239',text)
 def test_network_matches_MAC_and_never_enables_forwarding(self):
  for role,mac in zip(['WAN','LAN'],MAC):
   text=p.network(config(),role);self.assertIn('MACAddress='+mac,text);self.assertNotIn('Name=',text);self.assertNotIn('IPv4Forwarding=',text);self.assertIn('IPMasquerade=no',text)
 def test_dnsmasq_uses_own_UID_and_exact_lease_file_not_DAC_override(self):
  text=m.units('2026-11-06 09:00:00 UTC')[m.DNS];self.assertIn('User=dnsmasq',text);self.assertIn('Group=nogroup',text);self.assertIn('AmbientCapabilities=CAP_NET_ADMIN CAP_NET_RAW CAP_NET_BIND_SERVICE',text);self.assertIn('ReadWritePaths=/var/lib/misc/dnsmasq.leases\n',text);self.assertNotIn('CAP_DAC_OVERRIDE',text);self.assertNotIn('CAP_SETUID',text);self.assertIn('dhcp-leasefile=/var/lib/misc/dnsmasq.leases',p.dnsmasq(config(),IF));self.assertIn('group=nogroup',p.dnsmasq(config(),IF));self.assertNotIn('group=dnsmasq',p.dnsmasq(config(),IF))
 def test_timer_independent_calendar_and_monotonic(self):
  units=m.units('2026-11-06 09:00:00 UTC');text=units[m.TIMER];self.assertIn('OnActiveSec=180s',text);self.assertIn('Persistent=true',text);self.assertIn('OnCalendar=2026-11-06 09:00:00 UTC',text);self.assertIn('rollback',units['dell-gateway19-rollback.service'])
class FakeIPCompatibility(unittest.TestCase):
 def test_exact_fake_IP_addition_does_not_remove_general_nonpublic_exclusion(self):
  c=config();text=p.nft(c,IF);self.assertIn('198.18.0.0/15',p.NONPUBLIC);self.assertEqual(sum('ip daddr 198.18.0.0/15' in line for line in text.splitlines()),3);self.assertIn('ct mark set '+p.FAKE_MARK,text);self.assertIn('ct mark { '+p.FLOW_MARK+', '+p.FAKE_MARK+' } accept',text)
  legacy=copy.deepcopy(c);legacy.pop('OW_fake_IP_proxy');old=p.nft(legacy,IF);self.assertNotIn(p.FAKE_MARK,old);self.assertIn('ct mark '+p.FLOW_MARK+' accept',old)
 def test_wrong_fake_range_extra_port_or_other_contract_changes_refused(self):
  c=config()
  for key,value in [('destination','192.168.0.0/16'),('source','0.0.0.0/0'),('tcp',[22,53,80,443]),('udp',[53,123,7844])]:
   bad=copy.deepcopy(c);bad['OW_fake_IP_proxy'][key]=value
   with self.assertRaises(p.Rejected):p.validate_config(bad)
  old=copy.deepcopy(c);old.pop('OW_fake_IP_proxy')
  with patch.object(m,'load_policy',return_value=p):
   m.validate_hot_delta(old,c);bad=copy.deepcopy(c);bad['WAN_to_LAN'][0]['tcp'].append(9002)
   with self.assertRaises(RuntimeError):m.validate_hot_delta(old,bad)
 def test_hot_dispatch_is_nonblocking_while_parent_holds_transaction_lock(self):
  with patch.object(m,'run',return_value=SimpleNamespace(returncode=0,stdout=b'')) as run:m.queue_hot_apply()
  args=run.call_args.args[0];self.assertEqual(args[0],'systemd-run');self.assertIn('--no-block',args);self.assertIn('--property=Type=oneshot',args);self.assertNotIn('--wait',args)
 def test_hot_rollback_only_restores_owned_policy_and_config_no_service_restart(self):
  import base64
  legacy=config();legacy.pop('OW_fake_IP_proxy');old=json.dumps(legacy).encode();before={'mock-unit':['MainPID=10']};pending={'kind':'hot-policy-only','service_fingerprints':before};snapshot={'old_own_nft':p.nft(legacy,IF),'files':{str(m.CONFIG):{'data':base64.b64encode(old).decode(),'mode':0o600},'/etc/systemd/system/'+m.TIMER:{'data':base64.b64encode(b'[Timer]\n').decode(),'mode':0o644}}};commands=[]
  with tempfile.TemporaryDirectory() as tmp:
   with patch.object(m,'STATE',Path(tmp)),patch.object(m,'PENDING',Path(tmp)/'pending'),patch.object(m,'put') as writer,patch.object(m,'run',side_effect=lambda args,*a,**kw:(commands.append(args) or SimpleNamespace(returncode=0,stdout=b''))),patch.object(m,'service_fingerprints',return_value=before):
    result=m.hot_rollback(pending,snapshot);self.assertTrue(result['persistent_service_PIDs_unchanged']);self.assertTrue(any(call.args[0]==m.CONFIG and call.args[1]==old for call in writer.call_args_list))
  self.assertFalse(any(args[0] in ('ip','sysctl') or args[:2] in (['systemctl','stop'],['systemctl','restart']) for args in commands))

class CFFakeIPCompatibility(unittest.TestCase):
 def test_only_CF_source_gets_fake_7844_and_distinct_rollback_mark(self):
  new=p.load(copy.deepcopy(PLAN),*MAC);text=p.nft(new,IF);lines=[x for x in text.splitlines() if 'ip daddr 198.18.0.0/15' in x and 'dport 7844'in x];self.assertEqual(len(lines),2);self.assertTrue(all('ip saddr 192.168.19.5 ' in x and 'ct mark set '+p.CF_FAKE_MARK in x for x in lines));self.assertIn(p.CF_FAKE_MARK,text)
  old=copy.deepcopy(new);old.pop('CF_fake_IP_proxy');self.assertNotIn(p.CF_FAKE_MARK,p.nft(old,IF))
  with patch.object(m,'load_policy',return_value=p):m.validate_hot_delta(old,new)
 def test_CF_scope_drift_or_modifying_existing_OW_compatibility_rejected(self):
  new=p.load(copy.deepcopy(PLAN),*MAC);old=copy.deepcopy(new);old.pop('CF_fake_IP_proxy')
  for key,value in [('source','192.168.19.0/24'),('destination','192.168.0.0/16'),('tcp',[22,7844])]:
   bad=copy.deepcopy(new);bad['CF_fake_IP_proxy'][key]=value
   with self.assertRaises(p.Rejected):p.validate_config(bad)
  bad=copy.deepcopy(new);bad['OW_fake_IP_proxy']['icmp']=False
  with patch.object(m,'load_policy',return_value=p):
   with self.assertRaises(p.Rejected):m.validate_hot_delta(old,bad)

class WireGuardPenpotAccess(unittest.TestCase):
 def full(self):
  plan=copy.deepcopy(PLAN);plan['gateway_policy']['WireGuard_client_access']={'source':'10.66.66.0/24','destination':'192.168.19.50','tcp':[9001],'reason':'historical narrow fixture','evidence':'fixture','no_NAT':True};return p.load(plan,*MAC)
 def test_whole_VPN_source_only_Penpot9001_forward_no_INPUT(self):
  c=self.full();self.assertEqual(c['WireGuard_client_access'],{'source':'10.66.66.0/24','destination':'192.168.19.50','tcp':[9001],'no_NAT':True});text=p.nft(c,IF);input_part=text.split(' chain forward')[0];self.assertNotIn('10.66.66.',input_part);lines=[x for x in text.splitlines() if 'ip saddr 10.66.66.0/24'in x];self.assertEqual(len(lines),1);self.assertIn('ip daddr 192.168.19.50 tcp dport 9001 ct state new',lines[0]);self.assertIn('ct mark set '+p.WG_MARK,lines[0]);self.assertIn('counter accept comment "WG-Penpot-TCP9001"',lines[0]);self.assertIn('iifname "'+IF['WAN']+'" oifname "'+IF['LAN']+'"',lines[0])
 def test_old_config_keeps_exact_INPUT_and_return_state_does_not_accept_mark4(self):
  new=self.full();old=copy.deepcopy(new);old.pop('WireGuard_client_access');before=p.nft(old,IF);after=p.nft(new,IF);self.assertEqual(before.split(' chain forward')[0],after.split(' chain forward')[0]);self.assertNotIn(p.WG_MARK,before);self.assertIn(p.WG_MARK,after)
 def test_source_0_0_broad_destination_other_host_ports_protocols_rejected(self):
  for key,value in [('source','0.0.0.0/0'),('source','10.66.0.0/16'),('source','10.66.66.3'),('destination','192.168.19.0/24'),('destination','192.168.19.60'),('tcp',[9001,22]),('tcp',[True]),('no_NAT',False)]:
   bad=self.full();bad['WireGuard_client_access'][key]=value
   with self.assertRaises(p.Rejected):p.validate_config(bad)
  bad=self.full();bad['WireGuard_client_access']['protocols']='all'
  with self.assertRaises(p.Rejected):p.validate_config(bad)
 def test_raw_master_unknown_icmp_or_protocol_fields_rejected(self):
  for key,value in [('icmp',True),('protocols','all'),('udp',[9001])]:
   plan=copy.deepcopy(PLAN);plan['gateway_policy']['WireGuard_client_access']={'source':'10.66.66.0/24','destination':'192.168.19.50','tcp':[9001],'reason':'historical narrow fixture','evidence':'fixture','no_NAT':True};plan['gateway_policy']['WireGuard_client_access'][key]=value
   with self.assertRaises(p.Rejected):p.load(plan,*MAC)
 def test_hot_delta_only_optional_WG_plus_plan_provenance(self):
  new=self.full();old=copy.deepcopy(new);old.pop('WireGuard_client_access')
  with patch.object(m,'load_policy',return_value=p):
   m.validate_hot_delta(old,new)
   bad=copy.deepcopy(new);bad['management_hosts'].append('192.168.21.117')
   with self.assertRaises(RuntimeError):m.validate_hot_delta(old,bad)
 def test_no_broad_input_or_special_rollback_renderer_remains(self):
  import inspect
  text=p.nft(self.full(),IF);self.assertNotIn('ip daddr { 192.168.21.23, 192.168.19.1 } ct mark set',text);self.assertNotIn('counter accept comment "WG-TrustedVPN',text)

class TrustedVPNFullUpgrade(unittest.TestCase):
 def test_runtime_check_reaches_identity_guard_before_any_readiness_work(self):
  class GuardReached(Exception):pass
  with patch.object(m,'read_config',return_value=config()),patch.object(m,'guard',side_effect=GuardReached('real guard reached')) as identity:
   with self.assertRaises(GuardReached):m.check()
   identity.assert_called_once()
 def test_full_exact_scope_all_IPv4_only_exact_local_addresses(self):
  full=p.load(copy.deepcopy(PLAN),*MAC);self.assertEqual(full['WireGuard_client_access'],p.WG_FULL);text=p.nft(full,IF);rows=[x for x in text.splitlines() if 'ip saddr 10.66.66.0/24'in x];self.assertEqual(len(rows),2);self.assertTrue(all('ct mark set '+p.WG_FULL_MARK in x and 'dport'not in x and 'ct state new'not in x for x in rows));self.assertIn('ip daddr { 192.168.21.23, 192.168.19.1 }',rows[0]);self.assertIn('ip daddr 192.168.19.0/24',rows[1]);self.assertIn('ct mark != '+p.WG_FULL_MARK+' accept',text)
 def test_full_upgrade_preserves_old_mark4_but_rollback_excludes_mark5(self):
  full=p.load(copy.deepcopy(PLAN),*MAC);old=copy.deepcopy(full);old['WireGuard_client_access']=copy.deepcopy(p.WG_NARROW);live=p.nft(full,IF);back=p.nft(old,IF)
  self.assertIn(p.WG_MARK,live);self.assertIn(p.WG_FULL_MARK,live);self.assertIn('ct mark != '+p.WG_FULL_MARK+' accept',back);self.assertNotIn('ct mark set '+p.WG_FULL_MARK,back);self.assertNotIn('WG-TrustedVPN',back);self.assertIn('WG-Penpot-TCP9001',back)
 def test_full_only_from_confirmed_narrow_and_other_contract_unchanged(self):
  full=p.load(copy.deepcopy(PLAN),*MAC);old=copy.deepcopy(full);old['WireGuard_client_access']=copy.deepcopy(p.WG_NARROW)
  with patch.object(m,'load_policy',return_value=p):
   m.validate_hot_delta(old,full);missing=copy.deepcopy(old);missing.pop('WireGuard_client_access')
   with self.assertRaises(RuntimeError):m.validate_hot_delta(missing,full)
   bad=copy.deepcopy(full);bad['management_hosts'].append('192.168.21.117')
   with self.assertRaises(RuntimeError):m.validate_hot_delta(old,bad)
 def test_full_no_other_source_destination_gateway_address_or_NAT(self):
  full=p.load(copy.deepcopy(PLAN),*MAC)
  for key,value in [('source','0.0.0.0/0'),('source','10.66.0.0/16'),('destination','192.168.0.0/16'),('protocols','tcp'),('gateway_local_addresses',['192.168.21.1','192.168.19.1']),('no_NAT',False)]:
   bad=copy.deepcopy(full);bad['WireGuard_client_access'][key]=value
   with self.assertRaises(p.Rejected):p.validate_config(bad)
 def test_rollback_override_is_exact_guarded_old_policy_without_restarts(self):
  import base64
  full=p.load(copy.deepcopy(PLAN),*MAC);old=copy.deepcopy(full);old['WireGuard_client_access']=copy.deepcopy(p.WG_NARROW);guarded=p.nft(old,IF);raw='old literal nft retained';before={'unit':['MainPID=1']};pending={'kind':'hot-policy-only','service_fingerprints':before};original={'old_own_nft':raw,'hot_rollback_nft':guarded,'files':{str(m.CONFIG):{'data':base64.b64encode(json.dumps(old).encode()).decode(),'mode':0o600},'/etc/systemd/system/'+m.TIMER:None}};commands=[]
  with tempfile.TemporaryDirectory() as tmp:
   with patch.object(m,'STATE',Path(tmp)),patch.object(m,'PENDING',Path(tmp)/'pending'),patch.object(m,'put') as writer,patch.object(m,'run',side_effect=lambda args,*a,**kw:(commands.append(args) or SimpleNamespace(returncode=0,stdout=b''))),patch.object(m,'service_fingerprints',return_value=before):
    result=m.hot_rollback(pending,original);self.assertTrue(result['persistent_service_PIDs_unchanged']);content=next(x.args[1] for x in writer.call_args_list if x.args[0]==Path(tmp)/'hot-rollback.nft').decode();self.assertIn(guarded,content);self.assertNotIn(raw,content)
  self.assertFalse(any(args[0] in ('ip','sysctl') or args[:2] in (['systemctl','stop'],['systemctl','restart']) for args in commands))

class FakeKernel:
 def __init__(self):self.values={};self.writes=[];self.filtered=False
 def read(self,key):
  if key not in self.values:self.values[key]='0' if 'forward' in key else '1'
  return self.values[key]
 def sysctl(self,key,value):
  self.writes.append((key,str(value)));self.values[key]=str(value)
  # Model the documented reset of IPv4 router defaults when global forwarding changes.
  if key=='net.ipv4.ip_forward':
   for scope in ['all','default']:
    for name in ['accept_redirects','send_redirects','accept_source_route']:self.values['net.ipv4.conf.'+scope+'.'+name]='1'
 def run(self,args,*a,**kw):
  if args[:2]==['sysctl','-n']:return SimpleNamespace(returncode=0,stdout=(self.read(args[2])+'\n').encode())
  if args[0]=='systemctl':return SimpleNamespace(returncode=1,stdout=b'disabled\n')
  if args[:2]==['nft','--file']:self.filtered=True
  return SimpleNamespace(returncode=0,stdout=b'')
class ForwardingAndRollback(unittest.TestCase):
 def test_boot_security_never_sets_any_v4_forward_to_one(self):
  k=FakeKernel()
  with patch.object(m,'sysctl',side_effect=k.sysctl),patch.object(m,'run',side_effect=k.run):result=m.harden(IF,False)
  self.assertEqual(result,{'all':'0','WAN':'0','LAN':'0'});self.assertFalse(any(value=='1' and ('net.ipv4.ip_forward'==key or 'net/ipv4/conf/' in key and key.endswith('/forwarding') or key=='net.ipv4.conf.all.forwarding') for key,value in k.writes))
 def test_filter_and_zero_forwarding_precede_ready_enable(self):
  k=FakeKernel();original=k.run
  def run(args,*a,**kw):
   if args[:3]==['ip','-j','route']:return SimpleNamespace(returncode=0,stdout=json.dumps([{'gateway':'192.168.21.1','dev':IF['WAN']}]).encode())
   if args[:5]==['nft','-j','list','table','inet']:return SimpleNamespace(returncode=0,stdout=json.dumps({'nftables':[{'chain':{'name':n,'policy':v}} for n,v in [('input','drop'),('forward','drop'),('output','accept')]]}).encode())
   return original(args,*a,**kw)
  def write(key,value):
   if str(value)=='1' and ('ipv4' in key and (key.endswith('forwarding') or key.endswith('ip_forward'))):self.assertTrue(k.filtered,'must never enable before the filter load')
   k.sysctl(key,value)
  def read(path,*args,**kw):
   relative=str(path).replace('/proc/sys/','')
   key=relative.replace('/','.') if '/lo/' in relative else relative
   return k.values.get(key,'0')
  with patch.object(m,'load_policy',return_value=p),patch.object(m,'read_config',return_value=config()),patch.object(m,'guard',return_value=IF),patch.object(m,'native_checks',return_value='mock-native-rules'),patch.object(m,'put'),patch.object(m,'sysctl',side_effect=write),patch.object(m,'run',side_effect=run),patch.object(m,'nft_state',return_value=True),patch.object(m.Path,'read_text',autospec=True,side_effect=read):
   m.boot_firewall();self.assertTrue(k.filtered);self.assertEqual(m.forwarding_values(IF),{'all':'0','WAN':'0','LAN':'0'});result=m.ready();self.assertEqual(result['forwarding_all_WAN_LAN'],{'all':'1','WAN':'1','LAN':'1'})
 def test_stop_units_quiesce_all_interfaces_not_only_global(self):
  units=m.units('2026-11-06 09:00:00 UTC')
  for unit in [m.FIREWALL,m.READY]:self.assertIn('manage.py quiesce',units[unit]);self.assertNotIn('ExecStop=/usr/sbin/sysctl',units[unit])
 def test_enable_phase_reapplies_security_after_kernel_reset(self):
  k=FakeKernel()
  with patch.object(m,'sysctl',side_effect=k.sysctl),patch.object(m,'run',side_effect=k.run):self.assertEqual(m.harden(IF,True),{'all':'1','WAN':'1','LAN':'1'})
  for scope in ['all','default']:
   for key in ['accept_redirects','send_redirects','accept_source_route']:self.assertEqual(k.values['net.ipv4.conf.'+scope+'.'+key],'0')
 def test_failed_enable_reverts_all_three_forwarding_values_to_zero(self):
  k=FakeKernel();count=0
  def security(interfaces):
   nonlocal count;count+=1
   if count==2:raise RuntimeError('injected after enabling')
  with patch.object(m,'sysctl',side_effect=k.sysctl),patch.object(m,'run',side_effect=k.run),patch.object(m,'security_flags',side_effect=security):
   with self.assertRaises(RuntimeError):m.harden(IF,True)
   self.assertEqual(m.forwarding_values(IF),{'all':'0','WAN':'0','LAN':'0'})
 def test_snapshot_covers_every_hardening_key_and_restores_each_value(self):
  k=FakeKernel()
  with patch.object(m,'FILES',[]),patch.object(m,'SERVICES',[]),patch.object(m,'guard',return_value=IF),patch.object(m,'nft_state',return_value=False),patch.object(m,'sysctl',side_effect=k.sysctl),patch.object(m,'run',side_effect=k.run):
   snapshot=m.snapshot(config());initial=dict(snapshot['sysctls']);m.harden(IF,True);self.assertTrue(set(key for key,value in k.writes).issubset(initial));m.restore_sysctls(initial)
   self.assertEqual({key:k.values[key] for key in initial},initial)
 def test_foreign_tables_refused_not_flushed(self):
  value={'nftables':[{'table':{'family':'inet','name':'some_other_owner'}}]}
  with patch.object(m,'run',return_value=SimpleNamespace(returncode=0,stdout=json.dumps(value).encode())):
   with self.assertRaisesRegex(RuntimeError,'foreign'):m.nft_state()
if __name__=='__main__':unittest.main()
