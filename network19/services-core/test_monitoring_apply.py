import copy,importlib.util,json,unittest
from pathlib import Path
from unittest.mock import patch
H=Path(__file__).resolve().parent;s=importlib.util.spec_from_file_location('monitor_apply',H/'apply-monitoring.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class CanaryFixtures(unittest.TestCase):
 def fixture(self):
  c=json.loads((H.parents[1]/'network19/contracts/230.json').read_text());addresses=[{'ifname':'ens18','address':c['MAC'],'flags':['UP'],'addr_info':[{'local':c['new_ip'],'prefixlen':24,'scope':'global'}]}];return c,addresses
 def test_committed_MAC_IP24_passes(self):
  c,a=self.fixture();self.assertEqual(m.os_committed(c,a),'ens18')
 def test_wrong_MAC_or_old_address_rejected(self):
  c,a=self.fixture();bad=copy.deepcopy(a);bad[0]['address']='00:00:00:00:00:00'
  with self.assertRaises(m.Refused):m.os_committed(c,bad)
  a[0]['addr_info'].append({'local':c['old_ip'],'prefixlen':24,'scope':'global'})
  with self.assertRaises(m.Refused):m.os_committed(c,a)
 def test_delayed_exact_listener_passes_without_widening(self):
  values=iter(['','LISTEN 0 4096 192.168.19.40:9100 0.0.0.0:*'])
  self.assertEqual(m.wait_listener('192.168.19.40',query=lambda:next(values),clock=lambda:0,sleeper=lambda _:None),['192.168.19.40:9100'])
 def test_other_listener_never_passes_and_deadline_is_bounded(self):
  times=iter([0,16])
  with self.assertRaises(m.Refused):m.wait_listener('192.168.19.40',query=lambda:'LISTEN 0 4096 0.0.0.0:9100 0.0.0.0:*',clock=lambda:next(times),sleeper=lambda _:None)
 def test_230_paired_stage_keeps_no_business_or_candidate_activation(self):
  model=json.loads((H/'prepared/monitoring/vm230/role-contract.json').read_text());bundle=H/'prepared/monitoring/vm230'
  with patch.object(m,'owned',return_value=None):rows,health=m.candidate_contract(bundle,model)
  self.assertEqual(len(rows),6);self.assertEqual(health['services'],['ssh.service','qemu-guest-agent.service','prometheus-node-exporter.service']);self.assertEqual(health['http_checks'],[]);self.assertEqual(health['private_ip'],'192.168.19.40')
if __name__=='__main__':unittest.main()
