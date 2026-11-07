import importlib.util,unittest
from pathlib import Path
s=importlib.util.spec_from_file_location('network19_mysql_parser',Path(__file__).with_name('mysql-hosts.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class ParserFixtures(unittest.TestCase):
 def test_single_column_body_TAB_preserved_opaque(self):
  body="IDENTIFIED WITH 'caching_sha2_password' AS 'SYNTHETIC\tOPAQUE' REQUIRE NONE ACCOUNT UNLOCK"
  self.assertEqual(m.parse_create_rest('CREATE USER `finger_system_test`@`10.63.20.20` '+body,'finger_system_test',m.OLD),body)
 def test_explicit_account_column_accepted_without_splitting_auth(self):
  body="IDENTIFIED WITH 'caching_sha2_password' AS 'FAKE\tONLY' REQUIRE NONE"
  self.assertEqual(m.parse_create_rest('finger_auth_test@'+m.OLD+"\tCREATE USER 'finger_auth_test'@'"+m.OLD+"' "+body,'finger_auth_test',m.OLD),body)
 def test_wrong_account_or_unknown_leading_column_refused(self):
  for raw in ["CREATE USER `other`@`10.63.20.20` IDENTIFIED WITH 'x' AS 'fixture'", "arbitrary\tCREATE USER `finger_auth_test`@`10.63.20.20` IDENTIFIED WITH 'x' AS 'fixture'"]:
   with self.assertRaises(m.Refused):m.parse_create_rest(raw,'finger_auth_test',m.OLD)
if __name__=='__main__':unittest.main()
