#!/usr/bin/env python3
"""Offline fixtures only. No SSH/Docker/nft calls, no current files are changed."""
import base64,copy,importlib.util,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
control=load('cleanup_control',HERE/'candidates/control.py');bridge=load('cleanup_bridge',HERE/'candidates/render-bridge-acl.py');gw=load('cleanup_gw',HERE/'candidates/gateway-policy.py');old_bridge=load('current_bridge',ROOT/'network19/audit/render-bridge-acl.py');old_gw=load('current_gw',ROOT/'network19/gateway/policy.py')
PLAN=json.loads((HERE/'fixtures/baseline-plan.json').read_text());INVENTORY=json.loads((HERE/'fixtures/baseline-inventory.json').read_text());MODEL=json.loads((HERE/'proposed-model.json').read_text());MACS=('02:63:19:01:90:00','02:63:19:01:90:01')
def proposed():
 p=copy.deepcopy(PLAN);p['retired_vmids']=copy.deepcopy(MODEL['retired_vmids']);p['service_endpoints']=copy.deepcopy(MODEL['service_endpoints'])
 p['temporary_bootstrap_vmids']=copy.deepcopy(MODEL['temporary_bootstrap_vmids'])
 next(x for x in p['guest_addresses'] if x['vmid']==220)['additional_ips']=['192.168.19.31']
 return p
class SSHSelection(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(dir=HERE);self.root=Path(self.tmp.name).resolve();self.plan={'roles':[{'name':'publish-service','vmid':220,'ip':'192.168.19.30','additional_ips':['192.168.19.31']}],'retired_vmids':[]};self.key='ssh-ed25519 '+base64.b64encode(b'SYNTHETIC_ONLY_NOT_A_REAL_KEY').decode()
 def tearDown(self):self.tmp.cleanup()
 def invoke(self,addresses,expected=None,plan=None):
  (self.root/'plan.json').write_text(json.dumps(plan or self.plan));interfaces=[]
  for name,ips in addresses:interfaces.append({'name':name,'ip-addresses':[{'ip-address-type':'ipv4','ip-address':ip} for ip in ips]})
  with patch.object(control,'ROOT',self.root),patch.object(control,'KNOWN',self.root/'known'),patch.object(control,'pve',return_value=json.dumps(interfaces).encode()),patch.object(control,'qga',return_value=self.key):return control.trust_guest(220,expected_ip=expected)
 def test_declared_aliases_choose_primary_not_QGA_order(self):
  result=self.invoke([('ens9',['192.168.19.31','192.168.19.30'])]);self.assertEqual(result['ip'],'192.168.19.30');self.assertEqual(result['host_key_alias'],'dell-vm220')
 def test_missing_primary_or_unknown_uplink_IP_reject(self):
  for values in [['192.168.19.31'],['192.168.19.30','192.168.19.32']]:
   with self.assertRaises(RuntimeError):self.invoke([('ens9',values)])
 def test_no_declaration_retains_single_IP_boundary(self):
  plan=copy.deepcopy(self.plan);plan['roles'][0].pop('additional_ips')
  with self.assertRaises(RuntimeError):self.invoke([('ens9',['192.168.19.30','192.168.19.31'])],plan=plan)
  self.assertEqual(self.invoke([('ens9',['192.168.19.30'])],plan=plan)['ip'],'192.168.19.30')
 def test_alias_on_second_NIC_or_expect_alias_reject(self):
  with self.assertRaises(RuntimeError):self.invoke([('ens9',['192.168.19.30']),('ens10',['192.168.19.31'])])
  with self.assertRaises(RuntimeError):self.invoke([('ens9',['192.168.19.30','192.168.19.31'])],expected='192.168.19.31')
 def test_declared_but_not_yet_assigned_alias_allows_primary_only(self):self.assertEqual(self.invoke([('ens9',['192.168.19.30'])])['ip'],'192.168.19.30')
 def test_legacy_Docker_interface_exclusion_preserved(self):self.assertEqual(self.invoke([('ens9',['192.168.19.30','192.168.19.31']),('docker0',['172.17.0.1']),('br-abc',['172.18.0.1'])])['ip'],'192.168.19.30')
 def test_duplicate_active_owner_or_retired_owner_cannot_gain_trust(self):
  plan=copy.deepcopy(self.plan);plan['roles'].append({'name':'artifact-service','vmid':221,'ip':'192.168.19.31'})
  with self.assertRaises(RuntimeError):self.invoke([('ens9',['192.168.19.30'])],plan=plan)
  plan['retired_vmids']=[221];self.assertEqual(self.invoke([('ens9',['192.168.19.30'])],plan=plan)['ip'],'192.168.19.30')
  plan=copy.deepcopy(self.plan);plan['retired_vmids']=[220]
  with self.assertRaises(RuntimeError):self.invoke([('ens9',['192.168.19.30'])],plan=plan)
 def test_alias_does_not_weaken_hostkey_change_rejection(self):
  self.invoke([('ens9',['192.168.19.30'])]);self.key='ssh-ed25519 '+base64.b64encode(b'DIFFERENT_SYNTHETIC_KEY').decode()
  with self.assertRaisesRegex(RuntimeError,'host key changed'):self.invoke([('ens9',['192.168.19.30','192.168.19.31'])])
class BridgeAndDNS(unittest.TestCase):
 def test_no_new_model_keeps_old_bridge_rules_exactly(self):self.assertEqual(bridge.render(PLAN,INVENTORY)[0],old_bridge.render(PLAN,INVENTORY)[0])
 def test_alias_uses_one_MAC_row_and_two_IP_bindings_same_port(self):
  text,meta=bridge.render(proposed(),INVENTORY);rows=[r for r in meta['rows'] if r['vmid']==220];self.assertEqual(len(rows),1);self.assertEqual(rows[0]['ips'],['192.168.19.30','192.168.19.31'])
  for port in ['tap220i0','fwpr220p0']:
   for ip in ['192.168.19.30','192.168.19.31']:self.assertIn('"'+port+'" . '+ip,text)
  self.assertFalse(any(r['vmid'] in [221,231,232] for r in meta['rows']))
 def test_endpoint_keeps_existing_Nexus_peers_without_retired_VM_identity(self):
  text,meta=bridge.render(proposed(),INVENTORY);self.assertIn('192.168.19.40 . 192.168.19.10 . 3306',text);self.assertIn('192.168.19.45 . 192.168.19.20 . 3306',text);self.assertIn('192.168.19.40 . 192.168.19.31 . 8081',text);self.assertIn('192.168.19.70 . 192.168.19.30 . 9100',text);self.assertNotIn('192.168.19.70 . 192.168.19.31 . 9100',text)
  for ip in ['192.168.19.41','192.168.19.42']:self.assertNotIn(ip,text)
 def test_alias_duplicate_active_IP_unowned_endpoint_or_extra_port_reject(self):
  p=proposed();p['retired_vmids'].remove(221)
  with self.assertRaises(AssertionError):bridge.render(p,INVENTORY)
  p=proposed();next(x for x in p['guest_addresses'] if x['vmid']==220)['additional_ips']=[]
  with self.assertRaises(AssertionError):bridge.render(p,INVENTORY)
  p=proposed();p['service_endpoints']['artifact-service']['tcp']=[8081,22]
  with self.assertRaises(AssertionError):bridge.render(p,INVENTORY)
 def test_WG_full_clause_binding_order_and_no_host_L3_NAT_unchanged(self):
  old=bridge.render(PLAN,INVENTORY)[0];new=bridge.render(proposed(),INVENTORY)[0];extract=lambda t:t.split('  chain from_gateway {')[1].split('  chain from_guest {')[0]
  self.assertEqual(extract(old),extract(new));self.assertIn('trusted-WireGuard-to-server19',new);self.assertLess(new.index('unicast-destination-MAC-binding'),new.index('trusted-WireGuard-to-server19'));self.assertNotIn('masquerade',new);self.assertNotIn('table inet',new)
 def test_DNS_preserves_artifact_alias_and_only_retires_old_host_records(self):
  old=old_gw.load(PLAN,*MACS);new=gw.load(proposed(),*MACS);self.assertIn({'role':'artifact-service','address':'192.168.19.31'},new['hosts']);self.assertIn({'role':'publish-service','address':'192.168.19.30'},new['hosts']);self.assertFalse(any(r['address'] in ['192.168.19.41','192.168.19.42'] for r in new['hosts']));self.assertEqual(gw.nft(new,{'WAN':'eth0','LAN':'eth1'}),old_gw.nft(old,{'WAN':'eth0','LAN':'eth1'}));self.assertEqual(new['WireGuard_client_access'],old['WireGuard_client_access'])
 def test_gateway_compiler_without_cleanup_model_is_backward_compatible(self):self.assertEqual(gw.load(PLAN,*MACS),old_gw.load(PLAN,*MACS))
 def test_DNS_only_gate_keeps_logical31_and_refuses_WG_or_extra_record_changes(self):
  module=load('dns_delta',HERE/'dns_delta.py');old=old_gw.load(PLAN,*MACS);new=gw.load(proposed(),*MACS);self.assertFalse(module.validate_dns_only_delta(old,new)['nft_or_network_change_permitted'])
  bad=copy.deepcopy(new);bad['WireGuard_client_access']['source']='0.0.0.0/0'
  with self.assertRaises(ValueError):module.validate_dns_only_delta(old,bad)
  bad=copy.deepcopy(new);bad['hosts']=[x for x in bad['hosts'] if x['role']!='artifact-service']
  with self.assertRaises(ValueError):module.validate_dns_only_delta(old,bad)
  bad=copy.deepcopy(new);bad['hosts'].append({'role':'new-unapproved','address':'192.168.19.199'})
  with self.assertRaises(ValueError):module.validate_dns_only_delta(old,bad)
 def test_Fish_builders_get_only_temporary_L2_binding_no_DNS_or_auto_monitor(self):
  p=proposed();inventory=copy.deepcopy(INVENTORY)
  for index,vmid in enumerate([9040,9041,9042]):
   ip='192.168.19.'+str(197+index);p['guest_addresses'].append({'vmid':vmid,'name':'fish-builder-'+str(vmid),'new_ip':ip});inventory['guests'].append({'vmid':vmid,'kind':'vm','template':False,'nics':{'net0':{'virtio':'02:90:40:00:00:0'+str(index),'bridge':'vmbr19','firewall':'0'}}})
  text,meta=bridge.render(p,inventory);rows=[x for x in meta['rows'] if x['vmid'] in [9040,9041,9042]];self.assertEqual(len(rows),3);self.assertTrue(all(x['role']=='temporary-bootstrap' for x in rows))
  for ip in ['192.168.19.197','192.168.19.198','192.168.19.199']:self.assertNotIn('192.168.19.70 . '+ip+' . 9100',text)
  c=gw.load(p,*MACS);self.assertFalse(any(x['address'] in ['192.168.19.197','192.168.19.198','192.168.19.199'] for x in c['hosts']))
 def test_QA9043_to_9045_are_temporary_and_do_not_gain_DNS_or_OS_monitor_peers(self):
  p=proposed();inventory=copy.deepcopy(INVENTORY)
  for index,vmid in enumerate([9043,9044,9045]):
   address='192.168.19.'+str(197+index);p['guest_addresses'].append({'vmid':vmid,'name':['fish-qa-linux','fish-qa-docker','fish-qa-java'][index],'new_ip':address});inventory['guests'].append({'vmid':vmid,'kind':'vm','template':False,'nics':{'net0':{'virtio':'02:90:43:00:00:0'+str(index),'bridge':'vmbr19','firewall':'0'}}})
  text,meta=bridge.render(p,inventory);rows=[x for x in meta['rows'] if x['vmid'] in [9043,9044,9045]];self.assertEqual(len(rows),3);self.assertTrue(all(x['role']=='temporary-bootstrap' for x in rows));cfg=gw.load(p,*MACS)
  for address in ['192.168.19.197','192.168.19.198','192.168.19.199']:
   self.assertFalse(any(x['address']==address for x in cfg['hosts']));self.assertNotIn('192.168.19.70 . '+address+' . 9100',text)
 def test_root_temporary_build_only_raw_flags_are_equivalent_and_range_limited(self):
  p=proposed();p.pop('temporary_bootstrap_vmids');inventory=copy.deepcopy(INVENTORY);p['guest_addresses'].append({'vmid':9043,'name':'fish-qa-linux','new_ip':'192.168.19.197','temporary_build_only':True});inventory['guests'].append({'vmid':9043,'kind':'vm','template':False,'nics':{'net0':{'virtio':'02:90:43:00:00:09','bridge':'vmbr19','firewall':'0'}}});text,meta=bridge.render(p,inventory);self.assertEqual(next(r for r in meta['rows'] if r['vmid']==9043)['role'],'temporary-bootstrap');self.assertNotIn('192.168.19.70 . 192.168.19.197 . 9100',text);self.assertFalse(any(x['address']=='192.168.19.197' for x in gw.load(p,*MACS)['hosts']))
  bad=copy.deepcopy(p);bad['guest_addresses'][-1]['vmid']=9046
  with self.assertRaises(AssertionError):bridge.render(bad,inventory)
  with self.assertRaises(gw.Rejected):gw.load(bad,*MACS)
 def test_outside_temporary_range_and_simultaneous_reused_IP_owners_reject(self):
  p=proposed();p['temporary_bootstrap_vmids'].append(9046)
  with self.assertRaises(AssertionError):bridge.render(p,INVENTORY)
  with self.assertRaises(gw.Rejected):gw.load(p,*MACS)
  p=proposed();inventory=copy.deepcopy(INVENTORY)
  for index,vmid in enumerate([9040,9043]):
   p['guest_addresses'].append({'vmid':vmid,'name':'same-IP-temp-'+str(vmid),'new_ip':'192.168.19.197'});inventory['guests'].append({'vmid':vmid,'kind':'vm','template':False,'nics':{'net0':{'virtio':'02:90:44:00:00:0'+str(index),'bridge':'vmbr19','firewall':'0'}}})
  with self.assertRaises(AssertionError):bridge.render(p,inventory)
 def test_DNS_removes_only_retired_records_that_still_exist_not_Nexus31(self):
  module=load('dns_delta',HERE/'dns_delta.py');old=old_gw.load(PLAN,*MACS);new=gw.load(proposed(),*MACS);review=module.validate_dns_only_delta(old,new);self.assertEqual(set(map(tuple,review['removed'])),{(x['role'],x['address']) for x in old['hosts']}.intersection(module.REMOVALS));old=copy.deepcopy(old);old['hosts']=[x for x in old['hosts'] if x['role']!='publish-legacy'];self.assertTrue(module.validate_dns_only_delta(old,new))
 def test_DNS_rejects_alias_without_owner_declaration(self):
  p=proposed();next(x for x in p['guest_addresses'] if x['vmid']==220)['additional_ips']=[]
  with self.assertRaises(gw.Rejected):gw.load(p,*MACS)
if __name__=='__main__':unittest.main()
