import importlib.util,unittest
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace
s=importlib.util.spec_from_file_location('NAS_QA_worker',Path(__file__).with_name('worker.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class ScopeTests(unittest.TestCase):
 def test_invalid_nonce_cannot_target_existing_unit_or_path(self):
  for value in ['../dell-nas','', 'real-unit','A'*32,'0'*31]:
   with self.assertRaises(m.Failure):m.paths(value)
 def test_positive_scope_is_nonce_only(self):
  p=m.paths('a'*32);self.assertEqual(p['unit'],'dell-nas-sys001-'+'a'*32+'.service');self.assertNotEqual(p['unit'],'dell-nas-jellyfin.service');self.assertTrue(p['file'].endswith('/'+'a'*32+'/scratch.ext4'))
 def test_real_disk_partition_and_by_id_rejected(self):
  for device in ['/dev/sda','/dev/sdb1','/dev/disk/by-id/scsi-0QEMU_QEMU_HARDDISK_drive-scsi1','/dev/mapper/root']:
   with self.assertRaises(m.Failure):m.validate_loop(device,'/QA/new','/QA/new')
 def test_only_exact_loop_back_file_accepted(self):
  m.validate_loop('/dev/loop7','/QA/new','/QA/new')
  with self.assertRaises(m.Failure):m.validate_loop('/dev/loop7','/real/media','/QA/new')
 def test_QA_unit_is_not_production_unit_or_boot_enabled(self):
  source=Path(__file__).parents[0]/'preflight.json';import json
  template=json.loads(source.read_text())['real_unit_content'];contract=m.paths('a'*32);contract['uuid']='11111111-2222-3333-4444-555555555555'
  def run(args,**kw):return SimpleNamespace(stdout='real.mount\n' if args[-1]==str(m.REAL) else 'qa.mount\n')
  # Derive original mount name exactly from the observed template, keeping its structure.
  real_mnt=next(l.split('=',1)[1] for l in template.splitlines() if l.startswith('BindsTo='))
  with patch.object(m,'run',side_effect=lambda args,**kw:SimpleNamespace(stdout=(real_mnt if args[-1]==str(m.REAL) else 'qa.mount')+'\n')):
   rendered=m.render_unit(template,contract)
  self.assertIn(str(m.GUARD)+' --mountpoint '+contract['mount'],rendered);self.assertIn('--minimum-gib 1',rendered);self.assertNotIn(m.REAL_UUID,rendered);self.assertNotIn('[Install]',rendered);self.assertIn('Restart=no',rendered);self.assertIn('JobTimeoutSec=20s',rendered);self.assertIn('--project-name '+contract['project'],rendered);self.assertIn(str(m.PROD_COMPOSE),rendered)
class PrecheckRegression(unittest.TestCase):
 def test_failed_precheck_never_invokes_phase(self):
  spec=importlib.util.spec_from_file_location('QA_manager_gate',Path(__file__).with_name('run.py'));runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)
  for code,bad in [(0,True),(1,False)]:
   record={'nonce':'a'*32,'status':'passed','native_command_exit_code':code,'checks':{k:True for k in runner.REQUIRED_PRECHECKS}}
   if bad:record['checks']['memory512']=False
   from unittest.mock import Mock
   callback=Mock()
   with self.assertRaises(RuntimeError):runner.guarded_phase_call('b1','a'*32,callback,record)
   callback.assert_not_called()
class StartupRaceBounds(unittest.TestCase):
 def test_old_exited_within15_only(self):
  old={'id':'fixture','status':'exited','started_at':'old','OOM':False}
  self.assertTrue(m.waiting_old_exited(old,old,1))
  with self.assertRaises(m.Failure):m.waiting_old_exited(old,old,16)
 def test_new_started_then_exited_rejected(self):
  old={'id':'fixture','status':'exited','started_at':'old','OOM':False};new=dict(old,started_at='new')
  with self.assertRaises(m.Failure):m.waiting_old_exited(new,old,1)
 def test_OOM_never_gets_old_state_grace(self):
  old={'id':'fixture','status':'exited','started_at':'old','OOM':False}
  with self.assertRaises(m.Failure):m.waiting_old_exited(dict(old,OOM=True),old,1)
if __name__=='__main__':unittest.main()
