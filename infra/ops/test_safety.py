#!/usr/bin/env python3
"""Offline safety regression checks. No Docker service, mount or source mutation."""
import importlib.util, sys, tempfile, unittest
sys.dont_write_bytecode=True
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('dell_ops_manage',HERE/'scripts'/'manage.py')
manage=importlib.util.module_from_spec(spec);spec.loader.exec_module(manage)
UUID='12345678-1234-4234-8234-123456789abc'

class Safety(unittest.TestCase):
    def setUp(self):
        private=HERE.parents[1]/'private'/'ops'
        private.mkdir(parents=True,exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(prefix='safety-test-',dir=private)
        self.base=Path(self.temp.name).resolve()
        self.mount=self.base/'disk';self.mount.mkdir()
        self.root=self.mount/'test-data'
        self.c={'ROLE':'ops-service','DATA_MOUNTPOINT':str(self.mount),'DATA_ROOT':str(self.root),'DATA_FS_UUID':UUID}
        self.meta={'target':str(self.mount),'source':'/dev/vdb1','uuid':UUID,'fstype':'ext4','options':'rw,relatime'}
    def tearDown(self):self.temp.cleanup()
    def good(self,name):return {'service':name,'state':'running','health':'healthy'}
    def test_missing_service_cannot_pass_health(self):
        with patch.object(manage,'states',return_value=[self.good('mysql')]), patch.object(manage,'compose',return_value='mysql\nredis\n'):
            with self.assertRaisesRegex(RuntimeError,'service sets differ'):manage.health({'ROLE':'ops-service'})
    def test_unexpected_service_cannot_pass(self):
        with self.assertRaisesRegex(RuntimeError,'service sets differ'):
            manage.require_complete_health({'mysql'},[self.good('mysql'),self.good('redis')])
    def test_duplicate_service_cannot_pass(self):
        with self.assertRaisesRegex(RuntimeError,'service sets differ'):
            manage.require_complete_health({'mysql'},[self.good('mysql'),self.good('mysql')])
    def test_exact_healthy_set_passes(self):
        manage.require_complete_health({'mysql','redis'},[self.good('redis'),self.good('mysql')])
    def test_missing_mount_rejects_before_writes(self):
        before=list(self.mount.iterdir())
        with patch.object(manage.subprocess,'run',return_value=SimpleNamespace(returncode=1)),patch.object(manage,'filesystem') as finder:
            with self.assertRaisesRegex(RuntimeError,'not mounted'):manage.verify_data_mount(self.c)
            finder.assert_not_called()
        self.assertEqual(before,list(self.mount.iterdir()))
        self.assertFalse(self.root.exists())
    def test_uuid_required(self):
        self.c['DATA_FS_UUID']=''
        with self.assertRaisesRegex(RuntimeError,'DATA_FS_UUID'):manage.verify_data_mount(self.c)
    def test_wrong_uuid_rejected(self):
        bad=dict(self.meta,uuid='ffffffff-ffff-4fff-8fff-ffffffffffff')
        with patch.object(manage.subprocess,'run',return_value=SimpleNamespace(returncode=0)),patch.object(manage,'filesystem',return_value=bad):
            with self.assertRaisesRegex(RuntimeError,'UUID mismatch'):manage.verify_data_mount(self.c)
    def test_readonly_mount_rejected(self):
        bad=dict(self.meta,options='ro,relatime')
        with patch.object(manage.subprocess,'run',return_value=SimpleNamespace(returncode=0)),patch.object(manage,'filesystem',return_value=bad):
            with self.assertRaisesRegex(RuntimeError,'writable'):manage.verify_data_mount(self.c)
    def test_dotdot_escape_rejected(self):
        self.c['DATA_ROOT']=str(self.mount)+'/../../outside'
        with self.assertRaisesRegex(RuntimeError,'traversal'):manage.verify_data_mount(self.c)
    def test_symlink_escape_rejected(self):
        outside=self.base/'outside';outside.mkdir()
        self.root.symlink_to(outside,target_is_directory=True)
        with self.assertRaisesRegex(RuntimeError,'symlink'):manage.verify_data_mount(self.c)
    def test_nested_or_wrong_filesystem_rejected(self):
        self.root.mkdir()
        def lookup(path,exact_mount=False):
            return self.meta if path==self.mount else dict(self.meta,target=str(self.root),source='/dev/vdc1')
        with patch.object(manage.subprocess,'run',return_value=SimpleNamespace(returncode=0)),patch.object(manage,'filesystem',side_effect=lookup):
            with self.assertRaisesRegex(RuntimeError,'another or nested'):manage.verify_data_mount(self.c)
    def test_exact_uuid_and_mount_pass_without_creating_paths(self):
        with patch.object(manage.subprocess,'run',return_value=SimpleNamespace(returncode=0)),patch.object(manage,'filesystem',return_value=self.meta):
            self.assertEqual(manage.verify_data_mount(self.c),self.meta)
        self.assertFalse(self.root.exists())
    def test_systemd_owns_mount_and_recovery(self):
        unit=manage.systemd_unit(self.c,'example.mount')
        for value in ['RequiresMountsFor='+str(self.mount),'BindsTo=docker.service example.mount','ExecStartPre=',' supervise\n',' stop\n','Restart=on-failure','StartLimitBurst=5']:
            self.assertIn(value,unit)

if __name__=='__main__':unittest.main()
