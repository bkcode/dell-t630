#!/usr/bin/env python3
"""Offline guards only; no SSH, data server or Docker call."""
import importlib.util,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('fixture_worker',HERE/'fixture-worker.py');w=importlib.util.module_from_spec(spec);spec.loader.exec_module(w)

class Safety(unittest.TestCase):
 def setUp(self):
  parent=HERE.parents[1]/'private/backups/app';parent.mkdir(parents=True,exist_ok=True)
  self.temp=tempfile.TemporaryDirectory(prefix='offline-guard-',dir=parent);self.path=Path(self.temp.name).resolve()
  self.cfg=patch.object(w,'config',{'ROLE':'prod-db','DATA_MOUNTPOINT':str(self.path)});self.cfg.start()
 def tearDown(self):self.cfg.stop();self.temp.cleanup()
 def test_only_formal_data_hosts_are_eligible(self):self.assertEqual(set(w.ROLE_BY_HOST),{'data-prod-db','data-prod-infra'})
 def test_malformed_work_identifier_rejected(self):
  with self.assertRaises(RuntimeError):w.workspace('../../private')
 def test_nonempty_restore_directory_rejected_before_docker(self):
  self.path.joinpath('existing').write_text('keep')
  with patch.object(w,'docker') as docker:
   with self.assertRaisesRegex(RuntimeError,'must be empty'):w.temp_container('fixed@sha256:abc','name',self.path,(1,1),[])
   docker.assert_not_called()
 def test_restore_container_is_closed_and_never_mounts_source(self):
  empty=self.path/'empty';empty.mkdir()
  result=type('Result',(),{'stdout':('a'*64).encode()})()
  with patch.object(w.os,'chown'),patch.object(w,'docker',return_value=result) as docker:
   w.temp_container('mysql@sha256:abc','name',empty,(1,1),[],socket_dir=True)
  args=docker.call_args.args
  for flag in ['--pull=never','--platform=linux/amd64','--network=none','--read-only','--cap-drop=ALL']:self.assertIn(flag,args)
  self.assertNotIn('-p',args);self.assertFalse(any(x.startswith('--publish') for x in args));self.assertTrue(any('src='+str(empty) in x for x in args))
 def test_symlink_workspace_rejected(self):
  parent=self.path/'_dell_app_backup_fixture';outside=self.path/'outside';outside.mkdir();parent.symlink_to(outside,target_is_directory=True)
  with self.assertRaisesRegex(RuntimeError,'symlink'):w.workspace('a'*32,True)
 def test_state_cannot_select_a_business_database(self):
  nonce='a'*32;work=w.workspace(nonce,True)
  state={'nonce':nonce,'role':'prod-db','kind':'synthetic-backup-fixtures-only','database':'finger_business','payload':'backup-fixture:'+nonce}
  work.joinpath('state.json').write_text(json.dumps(state))
  with self.assertRaisesRegex(RuntimeError,'scope mismatch'):w.state_for(nonce)
 def test_export_requires_verified_pure_fixture(self):
  nonce='b'*32;work=w.workspace(nonce,True)
  state={'nonce':nonce,'role':'prod-db','kind':'synthetic-backup-fixtures-only','payload':'backup-fixture:'+nonce,'database':'dell_backup_fixture_'+nonce[:12],'nacos_data_id':'dell_backup_fixture_'+nonce,'nacos_group':'DELL_BACKUP_VERIFY','redis_key':'dell:backup-fixture:'+nonce,'rabbit_vhost':'/dell-backup-fixture-'+nonce[:12],'rabbit_queue':'dell.backup.fixture','contains_credentials':False,'contains_business_data':False}
  work.joinpath('state.json').write_text(json.dumps(state));artifact=work/'artifact';artifact.mkdir()
  artifact.joinpath('manifest.json').write_text(json.dumps({**state,'isolated_restore_verified':False}))
  with self.assertRaisesRegex(RuntimeError,'only verified pure'):w.export(nonce)

if __name__=='__main__':unittest.main()
