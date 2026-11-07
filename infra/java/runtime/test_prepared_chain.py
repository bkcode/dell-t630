#!/usr/bin/env python3
"""Local preparation checks only; no target/source SQL, SSH, HTTP write or application start."""
import ast,hashlib,importlib.util,json,re,stat,sys,unittest,zipfile
from pathlib import Path
import yaml
sys.dont_write_bytecode=True
BASE=Path(__file__).resolve().parents[3];PRIVATE=BASE/'private/java';CHAIN=PRIVATE/'test-chain'

class PreparedChainTests(unittest.TestCase):
 def test_explicit_test_target_and_no_prod_issuer(self):
  meta=json.loads((CHAIN/'metadata.json').read_text())
  self.assertEqual(meta['issuer'],'http://192.168.21.22:19999')
  self.assertFalse(meta['runtime_started']);self.assertEqual(meta['sql_execution'],'not-executed')
  workers=[]
  for row in meta['services']:
   cfg=yaml.safe_load(Path(row['runtime_config']).read_text())
   self.assertEqual(cfg['spring']['application']['name'],row['name'])
   self.assertEqual(cfg['server']['address'],'10.63.20.20')
   self.assertEqual(cfg['spring']['profiles']['active'],'dell-test')
   self.assertTrue(all(not v.startswith('optional:') for v in cfg['spring']['config']['import']))
   self.assertEqual(cfg['spring']['cloud']['nacos']['server-addr'],'10.63.20.10:8848')
   self.assertNotIn('http://192.168.21.22:9999',Path(row['runtime_config']).read_text())
   workers.append((cfg['snowflake']['data-center-id'],cfg['snowflake']['worker-id']))
  self.assertEqual(len(workers),len(set(workers)))

 def test_accounts_are_distinct_dml_only_and_host_bound(self):
  meta=json.loads((CHAIN/'metadata.json').read_text());accounts=meta['accounts']
  self.assertEqual(len({a['user'] for a in accounts}),3)
  self.assertTrue(all(a['user'].endswith('_test') and a['schema'].endswith('_test') and a['client_host']=='10.63.20.20' for a in accounts))
  sql=(CHAIN/'sql/accounts-admin.sql').read_text()
  grants=[l for l in sql.splitlines() if l.startswith('GRANT ')]
  self.assertEqual(len(grants),18)
  self.assertTrue(all('`.*' not in l for l in grants))
  self.assertTrue(all(l.startswith('GRANT SELECT, INSERT, UPDATE, DELETE ON ') and "@'10.63.20.20'" in l for l in grants))

 def test_structure_contains_no_source_rows(self):
  meta=json.loads((CHAIN/'metadata.json').read_text())
  self.assertEqual(sum(v['target_tables'] for v in meta['structures'].values()),18)
  for name in ['auth','system','coms']:
   text=(CHAIN/'sql'/(name+'-structure.sql')).read_text()
   self.assertFalse(bool(re.search(r'^\s*(INSERT|UPDATE|DELETE|REPLACE|DROP|TRUNCATE)\b',text,re.M|re.I)))
   self.assertIn('USE `finger_'+name+'_test`;',text)
   self.assertEqual(hashlib.sha256(text.encode()).hexdigest(),meta['structures'][name]['ddl_sha256'])
  seed=(CHAIN/'sql/synthetic-admin.sql').read_text()
  self.assertIn('FNTEST0001',seed)
  self.assertTrue(bool(re.search(r'\{bcrypt\}\$2[aby]\$\d\d\$[./A-Za-z0-9]{53}',seed)))

 def test_secret_and_runtime_file_permissions(self):
  for path in list((PRIVATE/'secrets').glob('*'))+list((CHAIN/'runtime').rglob('*.yaml')):
   self.assertFalse(path.is_symlink())
   self.assertEqual(stat.S_IMODE(path.stat().st_mode),0o600)
  self.assertEqual(stat.S_IMODE(PRIVATE.stat().st_mode),0o700)

 def test_fresh_secrets_absent_from_application_jars(self):
  values=[p.read_bytes().strip() for p in (PRIVATE/'secrets').glob('*') if p.is_file()]
  build=json.loads((BASE/'infra/java/build-status.json').read_text())
  for row in build['services']:
   jar=Path(row['artifact']['path'])
   self.assertEqual(hashlib.sha256(jar.read_bytes()).hexdigest(),row['artifact']['sha256'])
   with zipfile.ZipFile(jar) as z:
    for name in z.namelist():
     if not name.startswith('BOOT-INF/classes/') or name.endswith('/'):continue
     payload=z.read(name)
     self.assertTrue(all(value not in payload for value in values),'Fresh runtime secret found in application artifact')

 def test_release_manifest_and_units_without_target_effects(self):
  releases=sorted((PRIVATE/'releases').iterdir());self.assertTrue(releases)
  path=Path(__file__).with_name('deploy-test-chain.py');spec=importlib.util.spec_from_file_location('guest_deployer',path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
  meta=module.check_manifest(releases[-1]);self.assertEqual(len(meta['services']),5)
  for row in meta['services']:
   unit=module.unit(row)
   self.assertIn('User=finger',unit);self.assertIn('Group=finger',unit)
   self.assertIn('--spring.config.location=file:',unit)
   self.assertNotIn('/root/.local',unit)
   self.assertIn('-Djava.awt.headless=true',unit)
  for source in Path(__file__).parent.glob('*.py'):ast.parse(source.read_text())

if __name__=='__main__':unittest.main()
