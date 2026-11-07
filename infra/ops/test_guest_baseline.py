#!/usr/bin/env python3
"""Offline guest baseline regressions. No APT, SSH, service, timer or network calls."""
import contextlib,importlib.util,json,os,stat,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent

def load(name,file):
    spec=importlib.util.spec_from_file_location(name,HERE/'guest-baseline'/file)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
installer=load('guest_install','install-guest-baseline.py')
collector=load('guest_collect','collect-guest-health.py')
ROW={'role':'data-prod-db','hostname':'data-prod-db','vmid':200,'private_ip':'10.63.10.10','prefixlen':24}

class GuestGates(unittest.TestCase):
    def test_twelve_roles_exclude_pve_and_cf(self):
        self.assertEqual(len(installer.ROLES),12);self.assertNotIn('pve',installer.ROLES);self.assertNotIn('cf-tunnel',installer.ROLES)
    def test_hostname_mismatch_rejected(self):
        with self.assertRaises(RuntimeError):installer.target_for('data-prod-db','source-mac')
    def test_pve_role_rejected(self):
        with self.assertRaises(RuntimeError):installer.target_for('pve','pve')
    def test_cf_role_rejected(self):
        with self.assertRaises(RuntimeError):installer.target_for('cf-tunnel','cf-tunnel')
    def test_pve_filesystem_gate_rejects_before_commands(self):
        with patch.object(installer.os,'geteuid',return_value=0),patch.object(installer.Path,'exists',return_value=True),patch.object(installer,'command') as cmd:
            with self.assertRaisesRegex(RuntimeError,'PVE host'):installer.guest_gate('data-prod-db')
            cmd.assert_not_called()
    def test_debian12_rejected_before_service_commands(self):
        with patch.object(installer.os,'geteuid',return_value=0),patch.object(installer.Path,'exists',return_value=False),patch.object(installer.platform,'system',return_value='Linux'),patch.object(installer.platform,'machine',return_value='x86_64'),patch.object(installer.Path,'read_text',return_value='ID=debian\nVERSION_ID=12\n'),patch.object(installer,'command') as cmd:
            with self.assertRaisesRegex(RuntimeError,'Debian 13'):installer.guest_gate('data-prod-db')
            cmd.assert_not_called()
    def test_baremetal_or_container_rejected(self):
        with patch.object(installer.os,'geteuid',return_value=0),patch.object(installer.Path,'exists',return_value=False),patch.object(installer.platform,'system',return_value='Linux'),patch.object(installer.platform,'machine',return_value='x86_64'),patch.object(installer.Path,'read_text',return_value='ID=debian\nVERSION_ID=13\n'),patch.object(installer,'target_for',return_value=ROW),patch.object(installer,'command',return_value=SimpleNamespace(returncode=1,stdout='none')):
            with self.assertRaisesRegex(RuntimeError,'KVM/QEMU'):installer.guest_gate('data-prod-db')
    def test_catalog_exact_plan_guest_addresses(self):
        doc=json.loads((HERE/'guest-baseline/guest-targets.json').read_text());plan=json.loads((HERE.parents[1]/'plan.json').read_text())
        expected={r['name']:r.get('ip') or r.get('planned_ip') for r in plan['roles'] if r['kind']=='vm'}
        self.assertEqual({r['role']:r['private_ip'] for r in doc['roles']},expected)
    def test_temporary_lan_is_not_private_activation(self):
        data=[{'ifname':'ens18','flags':['UP'],'addr_info':[{'family':'inet','local':'192.168.21.199','prefixlen':24,'scope':'global'}]}]
        self.assertFalse(installer.private_address_present(ROW,data))
    def test_exact_private_up_address_passes(self):
        data=[{'ifname':'ens18','flags':['UP'],'addr_info':[{'family':'inet','local':ROW['private_ip'],'prefixlen':24,'scope':'global'}]}]
        self.assertTrue(installer.private_address_present(ROW,data))
    def test_wrong_prefix_or_loopback_rejected(self):
        for name,prefix in [('lo',24),('ens18',32)]:
            data=[{'ifname':name,'flags':['UP'],'addr_info':[{'family':'inet','local':ROW['private_ip'],'prefixlen':prefix,'scope':'global'}]}]
            self.assertFalse(installer.private_address_present(ROW,data))
    def test_all_listener_forms_detected(self):
        rows='tcp LISTEN 0 4096 0.0.0.0:9100 0.0.0.0:*\ntcp LISTEN 0 4096 [::]:9100 [::]:*\nudp UNCONN 0 0 10.63.10.10:9100 0.0.0.0:*\n'
        self.assertEqual(installer.listeners(rows),['0.0.0.0:9100','10.63.10.10:9100','[::]:9100'])
    def test_private_gate_precedes_unmask(self):
        with patch.object(sys,'argv',['x','--activate','--role','data-prod-db']),patch.object(installer,'guest_gate',return_value=ROW),patch.object(installer,'management_lock',side_effect=lambda:contextlib.nullcontext()),patch.object(installer,'require_private_ip',side_effect=RuntimeError('private absent')),patch.object(installer,'command') as cmd:
            with self.assertRaisesRegex(RuntimeError,'private absent'):installer.main()
            cmd.assert_not_called()
    def test_install_policy_order_and_post_mask(self):
        events=[]
        @contextlib.contextmanager
        def policy():
            events.append('deny-policy')
            try:yield
            finally:events.append('restore-policy')
        def apt(args,**kwargs):events.append('apt-'+args[-1]);return SimpleNamespace(returncode=0)
        with patch.object(installer.shutil,'which',return_value='/usr/bin/ss'),patch.object(installer,'mask_exporter',side_effect=lambda:events.append('mask')),patch.object(installer,'wait_apt_idle',side_effect=lambda:events.append('apt-idle')),patch.object(installer,'deny_daemon_starts',side_effect=policy),patch.object(installer.subprocess,'run',side_effect=apt),patch.object(installer,'command',side_effect=lambda *a,**kw:events.append('post-stop')),patch.object(installer,'install_files',side_effect=lambda r:events.append('files')),patch.object(installer,'receipt',side_effect=lambda *a:events.append('receipt')):
            installer.run_action(SimpleNamespace(install_only=True),ROW)
        self.assertLess(events.index('mask'),events.index('deny-policy'));self.assertLess(events.index('deny-policy'),events.index('apt-update'))
        self.assertEqual(events.count('mask'),2);self.assertLess(events.index('post-stop'),events.index('restore-policy'));self.assertLess(events.index('restore-policy'),events.index('files'))
    def test_failed_apt_still_stops_masks_and_restores(self):
        events=[]
        @contextlib.contextmanager
        def policy():
            try:yield
            finally:events.append('policy-restored')
        with patch.object(installer.shutil,'which',return_value='/usr/bin/ss'),patch.object(installer,'mask_exporter',side_effect=lambda:events.append('mask')),patch.object(installer,'wait_apt_idle'),patch.object(installer,'deny_daemon_starts',side_effect=policy),patch.object(installer.subprocess,'run',return_value=SimpleNamespace(returncode=1)),patch.object(installer,'command',side_effect=lambda *a,**kw:events.append('stop')),patch.object(installer,'install_files') as install:
            with self.assertRaises(RuntimeError):installer.run_action(SimpleNamespace(install_only=True),ROW)
            install.assert_not_called()
        self.assertEqual(events,['mask','stop','mask','policy-restored'])
    def test_dropin_is_private_bound_with_exec_condition(self):
        drop,service,timer=installer.unit_text(ROW,'prometheus','prometheus')
        self.assertIn('--web.listen-address=10.63.10.10:9100',drop);self.assertNotIn('0.0.0.0',drop);self.assertIn('--check-private-ip --role data-prod-db',drop)
        self.assertIn('ProtectSystem=strict',service);self.assertNotIn('EnvironmentFile',service);self.assertNotIn('/var/log',service);self.assertIn('OnUnitActiveSec=60s',timer)

class PolicyRecovery(unittest.TestCase):
    def setUp(self):
        private=HERE.parents[1]/'private'/'ops';private.mkdir(parents=True,exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(prefix='guest-policy-tests-',dir=private);self.base=Path(self.temp.name).resolve();self.policy=self.base/'policy-rc.d'
        self.mock=patch.object(installer,'POLICY',self.policy);self.mock.start()
    def tearDown(self):self.mock.stop();self.temp.cleanup()
    def test_absent_policy_removed_after_use(self):
        with installer.deny_daemon_starts():self.assertIn('exit 101',self.policy.read_text())
        self.assertFalse(self.policy.exists())
    def test_existing_bytes_mode_inode_restored(self):
        self.policy.write_text('original custom policy\n');self.policy.chmod(0o640);before=self.policy.stat()
        with installer.deny_daemon_starts():self.assertNotEqual(self.policy.stat().st_ino,before.st_ino)
        after=self.policy.stat();self.assertEqual(self.policy.read_text(),'original custom policy\n');self.assertEqual(stat.S_IMODE(after.st_mode),0o640);self.assertEqual(after.st_ino,before.st_ino)
    def test_exception_restores_original(self):
        self.policy.write_text('original')
        with self.assertRaisesRegex(RuntimeError,'apt failed'):
            with installer.deny_daemon_starts():raise RuntimeError('apt failed')
        self.assertEqual(self.policy.read_text(),'original')
    def test_existing_symlink_restored_without_touching_target(self):
        target=self.base/'original';target.write_text('original');self.policy.symlink_to('original')
        with installer.deny_daemon_starts():self.assertFalse(self.policy.is_symlink())
        self.assertTrue(self.policy.is_symlink());self.assertEqual(os.readlink(self.policy),'original');self.assertEqual(target.read_text(),'original')
    def test_concurrent_policy_not_overwritten(self):
        self.policy.write_text('original');other=self.base/'other';other.write_text('external-change')
        with self.assertRaisesRegex(RuntimeError,'changed concurrently'):
            with installer.deny_daemon_starts():os.replace(other,self.policy)
        self.assertEqual(self.policy.read_text(),'external-change');backups=list(self.base.glob('.policy-rc.d.dell-backup-*'));self.assertEqual(len(backups),1);self.assertEqual(backups[0].read_text(),'original')
    def test_incomplete_policy_record_blocks_retry(self):
        marker=self.base/'.policy-rc.d.dell-active.json';marker.write_text('{}')
        with self.assertRaisesRegex(RuntimeError,'unfinished'):
            with installer.deny_daemon_starts():pass
        self.assertEqual(marker.read_text(),'{}');self.assertFalse(self.policy.exists())
    def test_busy_apt_lock_not_deleted_or_killed(self):
        lock=self.base/'dpkg.lock';lock.write_text('keep')
        with patch.object(installer,'APT_LOCKS',[lock]),patch.object(installer.fcntl,'lockf',side_effect=BlockingIOError),patch.object(installer.time,'monotonic',side_effect=[0,121]):
            with self.assertRaisesRegex(RuntimeError,'no locks deleted'):installer.wait_apt_idle()
        self.assertEqual(lock.read_text(),'keep')

class CollectorSafety(unittest.TestCase):
    def c(self):return installer.candidates(ROW)
    def test_default_http_checks_disabled(self):self.assertEqual(self.c()['http_checks'],[])
    def test_own_actuator_url_allowed(self):
        c=self.c();c['http_checks']=[{'name':'java','url':'http://127.0.0.1:9999/actuator/health/readiness'}]
        collector.validate(c,{ROW['private_ip'],'127.0.0.1'})
    def test_other_guest_http_rejected(self):
        c=self.c();c['http_checks']=[{'name':'other','url':'http://10.63.10.11:8848/health'}]
        with self.assertRaisesRegex(ValueError,'this guest'):collector.validate(c,{ROW['private_ip'],'127.0.0.1'})
    def test_credentials_query_and_headers_rejected(self):
        for check in [{'name':'bad','url':'http://user:pass@127.0.0.1/health'},{'name':'bad','url':'http://127.0.0.1/health?token=value'},{'name':'bad','url':'http://127.0.0.1/health','headers':{'Authorization':'example'}}]:
            c=self.c();c['http_checks']=[check]
            with self.assertRaises(ValueError):collector.validate(c,{ROW['private_ip'],'127.0.0.1'})
    def test_business_path_rejected(self):
        c=self.c();c['http_checks']=[{'name':'trade','url':'http://127.0.0.1/orders/create'}]
        with self.assertRaisesRegex(ValueError,'health/root'):collector.validate(c,{ROW['private_ip'],'127.0.0.1'})
    def test_env_config_fields_rejected(self):
        c=self.c();c['environment']={'PASSWORD':'example'}
        with self.assertRaisesRegex(ValueError,'unknown config fields'):collector.validate(c,{ROW['private_ip']})
    def test_only_allowlisted_systemd_properties_requested(self):
        p=SimpleNamespace(returncode=0,stdout='LoadState=loaded\nActiveState=active\n',stderr='')
        with patch.object(collector.subprocess,'run',return_value=p) as run:
            self.assertEqual(collector.unit_state('ssh.service'),(1,1,True))
        args=run.call_args.args[0];self.assertIn('--property=LoadState',args);self.assertIn('--property=ActiveState',args);self.assertNotIn('Environment',str(args));self.assertNotIn('journalctl',str(args))
    def test_metrics_never_include_env_logs_body_or_url(self):
        c=self.c();c['http_checks']=[{'name':'local','url':'http://127.0.0.1:9999/health'}]
        with patch.object(collector,'unit_state',return_value=(1,1,True)),patch.object(collector,'http_state',return_value=(1,200)):
            body,ok=collector.collect(c)
        self.assertTrue(ok);self.assertIn('dell_guest_http_up',body);self.assertNotIn('http://',body);self.assertNotIn('PASSWORD',body);self.assertNotIn('stdout',body)
    def test_http_error_is_status_only(self):
        import urllib.error
        with patch.object(collector.urllib.request,'build_opener') as make:
            make.return_value.open.side_effect=urllib.error.HTTPError('http://127.0.0.1/health',401,'unauthorized',{},None)
            self.assertEqual(collector.http_state('http://127.0.0.1/health'),(0,401))
    def test_redirects_refused(self):self.assertIsNone(collector.NoRedirect().redirect_request(None,None,None,None,None,None))

if __name__=='__main__':unittest.main()
