import copy,importlib.util,json,unittest
from pathlib import Path
from unittest.mock import patch
H=Path(__file__).resolve().parent

def load(name,file):
 s=importlib.util.spec_from_file_location(name,H/file);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
stage=load('network19_java_stage','stage-java240.py');pub=load('network19_public_contract','contract-tool.py');mysql=load('network19_mysql_hosts','mysql-hosts.py');monitor=load('network19_monitoring','migrate-monitoring.py')
class RuntimeConfigTests(unittest.TestCase):
 def test_explicit_addresses_imports_and_secrets_preserved(self):
  model={'server':{'address':'10.63.20.20'},'spring':{'config':{'import':['nacos:finger-common.yaml?group=DELL_TEST&refreshEnabled=false','nacos:finger-auth.yaml?group=DELL_TEST&refreshEnabled=false']},'datasource':{'url':'jdbc:mysql://10.63.20.10:3306/finger_auth_test?useSSL=false','password':'fixture-only-secret'},'cloud':{'nacos':{'password':'fixture-only-token'}}},'finger':{'auth':{'bootstrap':{'issuer':'http://192.168.21.22:19999','clients':{'finger-admin':{'secret':'fixture-only','redirect-uris':['http://192.168.21.22:19999/dell-test/callback']}}}}}}
  new,_=stage.transform(model,pub.DATAIDS);self.assertEqual(new['server']['address'],'192.168.19.45');self.assertIn('192.168.19.20',new['spring']['datasource']['url']);self.assertIn('network19-v1',new['spring']['config']['import'][0]);self.assertEqual(stage.secret_leaves(model),stage.secret_leaves(new))
 def test_unknown_address_key_rejected(self):
  with self.assertRaises(stage.Refused):stage.transform({'unknown':'http://10.63.20.20:1234'},pub.DATAIDS)
 def test_internal_names_bridge_and_namespace_not_rewritten(self):
  model={'spring':{'rabbitmq':{'virtual-host':'/finger-test'},'cloud':{'nacos':{'config':{'namespace':'fixture-namespace'}}}},'test':'mysql','bridge':'172.18.0.1'}
  self.assertEqual(stage.transform(model,pub.DATAIDS)[0],model)
 def test_only_active_mandatory_Nacos_IDs_allowed(self):
  with self.assertRaises(stage.Refused):stage.transform({'spring':{'config':{'import':['nacos:unknown.yaml','nacos:finger-common.yaml']}}},pub.DATAIDS)
class PublicCanonicalTests(unittest.TestCase):
 def test_only_literals_changed_algorithm_preserved(self):
  text="# history10.63.20.20\nvalue='10.63.20.20'\nassert value!='10.63.20.10'\n"
  new,edits=pub.patch_python(text);self.assertIn('# history10.63.20.20',new);self.assertIn('192.168.19.45',new);self.assertEqual(len(edits),2)
 def test_capture_prepared_matches_installed_not_pending(self):
  x=json.loads((H/'prepared-public-contract.json').read_text());self.assertTrue(x['no_pending_quiescence_code_used']);self.assertEqual(len(x['publisher_files']),5)
 def test_exact18_table_grants_migrate_suffix_only(self):
  for user,record in mysql.CONTRACT['accounts'].items():
   rows=[v+' TO `'+user+'`@`'+mysql.OLD+'`' for v in record['grant_prefixes']];new=mysql.migrate_grants(rows,user,mysql.OLD,mysql.NEW)
   self.assertEqual([x.split(' TO ')[0] for x in rows],[x.split(' TO ')[0] for x in new]);self.assertTrue(all(x.endswith('@`192.168.19.45`') for x in new))
 def test_whole_statement_unexpected_suffix_refused(self):
  with self.assertRaises(mysql.Refused):mysql.migrate_grants(['GRANT ALL ON *.* TO `someone`@`%`'],'finger_auth_test',mysql.OLD,mysql.NEW)
 def test_monitoring_only_own_url_host(self):
  self.assertEqual(monitor.local_url('http://10.63.20.20:9999/actuator/health','10.63.20.20','192.168.19.45'),'http://192.168.19.45:9999/actuator/health');self.assertEqual(monitor.local_url('http://127.0.0.1:9999/readyz','10.63.20.20','192.168.19.45'),'http://127.0.0.1:9999/readyz')
 def test_health_URL_credentials_or_query_refused(self):
  for url in ['http://user:secret@10.63.20.20/health','http://10.63.20.20/health?token=fixture']:
   with self.assertRaises(monitor.Refused):monitor.local_url(url,'10.63.20.20','192.168.19.45')
if __name__=='__main__':unittest.main()
