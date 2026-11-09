import importlib.util,json,unittest
from pathlib import Path
from unittest.mock import patch
BASE=Path(__file__).resolve().parent;SOURCE=BASE.parent/'guest-baseline'
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
new=load('newbaseline',SOURCE/'install-guest-baseline.py');old=load('oldbaseline',BASE/'install-guest-baseline.before.py');collector=load('collector',SOURCE/'collect-guest-health.py')
class CandidateTests(unittest.TestCase):
 def test_only_one_new_role_and_all_oldprofiles_unchanged(self):
  self.assertEqual(new.ROLES-old.ROLES,{'resource-service'});self.assertTrue(old.ROLES<=new.ROLES)
  rows=json.loads((BASE/'guest-targets.before.json').read_text())['roles']
  for row in rows:self.assertEqual(new.role_health_profile(row),old.role_health_profile(row));self.assertEqual(new.candidates(row),old.candidates(row))
 def test_resource_profile_exact_two_units_no_http_or_docker(self):
  row=new.target_for('resource-service','resource-service')
  self.assertEqual(row,{'role':'resource-service','hostname':'resource-service','vmid':280,'private_ip':'192.168.19.80','prefixlen':24})
  self.assertEqual(new.role_health_profile(row),{'services':['nfs-server.service','dell-resources-firewall.service'],'http_checks':[]})
  self.assertEqual(new.candidates(row)['candidate_service_units'],['nfs-server.service','dell-resources-firewall.service'])
 def test_new_catalog_preserves_oldentries_exact(self):
  before=json.loads((BASE/'guest-targets.before.json').read_text())['roles'];after=json.loads((SOURCE/'guest-targets.json').read_text())['roles'];self.assertEqual(after[:-1],before);self.assertEqual(len(after),11)
 def test_healthconfig_accepted_existing_collector_no_schemaextension(self):
  health=json.loads((BASE/'health.candidate.json').read_text());collector.validate(health,{'192.168.19.80'})
  self.assertEqual(health['http_checks'],[])
  with patch.object(collector,'unit_state',return_value=(1,1,True)):
   text,ok=collector.collect(health)
  self.assertTrue(ok);self.assertIn('service="nfs-server.service"',text);self.assertIn('service="dell-resources-firewall.service"',text)
 def test_otherIPs_no_unknown_role_and_wronghostname_rejected(self):
  with self.assertRaises(RuntimeError):new.target_for('resource-service','wrong-host')
  with self.assertRaises(RuntimeError):new.target_for('unknown','unknown')
  with self.assertRaises(ValueError):collector.validate(json.loads((BASE/'health.candidate.json').read_text()),{'192.168.19.20'})
 def test_Promtarget_append_only_current10_exact(self):
  live=json.loads((BASE/'prometheus-readonly-baseline.json').read_text())['public_target_files']['/opt/dell/ops/config/prometheus/targets/guest-node.json']['public_target_groups'];candidate=json.loads((BASE/'guest-node.candidate.json').read_text());self.assertEqual(candidate[:-1],live);self.assertEqual(candidate[-1],{'targets':['192.168.19.80:9100'],'labels':{'role':'resource-service','zone':'shared','vmid':'280'}})
 def test_exporter_private_bind_not_wildcard(self):
  row=new.target_for('resource-service','resource-service');drop,unit,timer=new.unit_text(row,'prometheus','prometheus');self.assertIn('--web.listen-address=192.168.19.80:9100',drop);self.assertNotIn('0.0.0.0',drop);self.assertIn('--role resource-service',drop)

# Tests below are also discovered by unittest module loading; CLI runner is at file end.

class LarkRoleTests(unittest.TestCase):
 def sources(self):
  return load('oldbridge',BASE/'lark-bridge.before.py'),load('newbridge',BASE.parent/'lark-notify/bridge.py')
 def data(self,role,name='GuestManagedUnitUnavailable'):
  return json.dumps({'version':'4','status':'firing','alerts':[{'status':'firing','startsAt':'2026-11-09T00:00:00Z','fingerprint':'1234567890abcdef','labels':{'alertname':name,'role':role,'severity':'warning','service':'nfs-server.service'}}]}).encode()
 def test_only_known_resource_role_added_preserve_every_other_byte(self):
  old,new=self.sources();raw=(BASE/'lark-bridge.before.py').read_text();line=next(x for x in raw.splitlines() if x.startswith('ROLES='));expected=raw.replace(line,line[:-1]+",'resource-service'}",1)
  self.assertEqual((BASE.parent/'lark-notify/bridge.py').read_text(),expected);self.assertEqual(new.ROLES-old.ROLES,{'resource-service'});self.assertEqual(new.ALERTS,old.ALERTS);self.assertEqual(new.LABELS,old.LABELS)
 def test_resource_positive_render_only_without_sender(self):
  old,new=self.sources()
  with self.assertRaises(old.Rejected):old.render(self.data('resource-service'),'active')
  body,receipt=new.render(self.data('resource-service'),'active');self.assertEqual(json.loads(body)['msg_type'],'text');self.assertIn('resource-service',json.loads(body)['content']['text'])
 def test_all_previous_known_roles_behave_identically_and_unknown_rejected(self):
  old,new=self.sources()
  for role in old.ROLES:self.assertEqual(new.render(self.data(role),'active'),old.render(self.data(role),'active'))
  with self.assertRaises(new.Rejected):new.render(self.data('unknown-resource'),'active')
  with self.assertRaises(new.Rejected):new.render(self.data('resource-service','UnapprovedAlert'),'active')

if __name__=='__main__':unittest.main()
