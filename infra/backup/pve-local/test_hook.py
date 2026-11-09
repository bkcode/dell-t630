#!/usr/bin/env python3
"""Offline negative tests; no PVE, SSH, Docker, archive payload or real credentials."""
import ast,collections,importlib.util,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
HERE=Path(__file__).resolve().parent
TEMP_BASE='/private/tmp' if Path('/private/tmp').is_dir() else '/tmp'
spec=importlib.util.spec_from_file_location('pve_backup_hook',HERE/'hook.py');h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)

class HookSafety(unittest.TestCase):
 def test_policy_exact_scope_and_exclusions(self):
  p=json.loads((HERE/'policy.json').read_text());self.assertEqual(p['allowed_vmids'],[100,190,200,201,210,221,230,240,250,260,270]);self.assertEqual(p['excluded_vmids'],[220]);self.assertEqual(p['mode'],'snapshot');self.assertEqual(p['mailto'],'')
 def test_relative_and_parent_traversal(self):
  for value in ['relative','/tmp/../etc/shadow']:
   with self.assertRaises(RuntimeError):h.safe_path(value)
 def test_symlink_parent_refused_before_content_read(self):
  with tempfile.TemporaryDirectory(dir=TEMP_BASE,prefix='backup-hook-') as t:
   root=Path(t);(root/'real').mkdir();(root/'link').symlink_to(root/'real',target_is_directory=True);(root/'real/file').write_text('synthetic')
   with self.assertRaises(RuntimeError):h.safe_path(root/'link/file')
 def test_atomic_private_manifest_and_no_symlink_overwrite(self):
  with tempfile.TemporaryDirectory(dir=TEMP_BASE,prefix='backup-hook-') as t:
   p=Path(t)/'state.json';h.atom(p,{'synthetic':True});self.assertEqual(p.stat().st_mode&0o777,0o600);self.assertEqual(json.loads(p.read_text()),{'synthetic':True})
   other=Path(t)/'other';other.write_text('keep');link=Path(t)/'link.json';link.symlink_to(other)
   with self.assertRaises(RuntimeError):h.atom(link,{})
   self.assertEqual(other.read_text(),'keep')
 def test_archive_namespace_and_vmid(self):
  with tempfile.TemporaryDirectory(dir=TEMP_BASE,prefix='backup-hook-') as t:
   root=Path(t);dump=root/'dump';dump.mkdir();outside=root/'vzdump-qemu-190-2026_11_09-01_00_00.vma.zst';outside.write_bytes(b'fixture')
   with self.assertRaises(RuntimeError):h.owned_archive({'dumpdir':str(dump)},outside,190)
   wrong=dump/'vzdump-qemu-220-2026_11_09-01_00_00.vma.zst';wrong.write_bytes(b'fixture')
   with self.assertRaises(RuntimeError):h.owned_archive({'dumpdir':str(dump)},wrong,190)
 def test_archive_formats_cannot_swap_CF_and_VM(self):
  with tempfile.TemporaryDirectory(dir=TEMP_BASE,prefix='backup-hook-') as t:
   root=Path(t)
   for name,vmid in [('vzdump-lxc-190-2026_11_09-01_00_00.tar.zst',190),('vzdump-qemu-100-2026_11_09-01_00_00.vma.zst',100)]:
    p=root/name;p.write_bytes(b'fixture')
    with self.assertRaises(RuntimeError):h.owned_archive({'dumpdir':str(root)},p,vmid)
 def test_job_end_true_only_for_complete_verified_run(self):
  tree=ast.parse((HERE/'hook.py').read_text());assign=next(n for n in ast.walk(tree) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='success' for t in n.targets));code=compile(ast.Expression(assign.value),'<actual-hook-job-end>','eval');ids=[100,190,200,201,210,221,230,240,250,260,270]
  def check(ledger,phase='job-end'):return eval(code,{'__builtins__':{'set':set,'map':map,'str':str,'all':all}},{'p':{'allowed_vmids':ids},'ledger':ledger,'phase':phase})
  good={'results':{str(v):{'status':'verified'} for v in ids}}
  self.assertTrue(check(good))
  for status in ['running','backup-failed','verification-failed']:
   bad=json.loads(json.dumps(good));bad['results']['100']['status']=status;self.assertFalse(check(bad))
  missing=json.loads(json.dumps(good));missing['results'].pop('100');self.assertFalse(check(missing))
  extra=json.loads(json.dumps(good));extra['results']['220']={'status':'verified'};self.assertFalse(check(extra))
  logerr={**good,'log_permission_error':True};self.assertFalse(check(logerr));self.assertFalse(check(good,'job-abort'))

if __name__=='__main__':unittest.main()
