#!/usr/bin/env python3
"""Meaningful pure regressions; no package, mount, network or guest operations."""
import copy
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent

def module(name, file):
    spec = importlib.util.spec_from_file_location(name, HERE / file)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value

p = module('resource_prepare_test', 'prepare.py')
g = module('resource_guard_test', 'guard.py')

def policy():
    value = copy.deepcopy(p.EXAMPLE)
    value['server']['data_uuid'] = 'ea24ad76-517b-43df-a1d0-7c879506bc77'  # synthetic only
    return value


def server_row():
    return {'target': '/srv/resources', 'source': '/dev/vdb', 'fstype': 'ext4',
            'uuid': policy()['server']['data_uuid'], 'options': 'rw,nodev,nosuid,noexec'}


def client_row():
    return {'target': '/mnt/resources', 'source': '192.168.19.80:/', 'fstype': 'nfs4',
            'options': 'rw,vers=4.1,proto=tcp,hard,sec=sys,nodev,nosuid,noexec'}


class ResourceContract(unittest.TestCase):
    def test_pending_uuid_validates_but_cannot_render_installable_units(self):
        p.validate(p.EXAMPLE, allow_pending=True)
        with self.assertRaises(ValueError): p.render(p.EXAMPLE)

    def test_wrong_resource_identity_clients_paths_and_environment_split_rejected(self):
        for edit in [lambda x: x['server'].update(ip='192.168.19.11'),
                     lambda x: x['clients'].append({'vmid': 221, 'hostname': 'other', 'ip': '192.168.19.31'}),
                     lambda x: x.update(client_mount='/mnt/dell-artifacts'),
                     lambda x: x.update(shared_environment_directory=False),
                     lambda x: x.update(resource_gid=989),
                     lambda x: x.update(optional_http_enabled=True),
                     lambda x: x['server'].update(system_disk_gib=20)]:
            bad = policy(); edit(bad)
            with self.assertRaises(ValueError): p.render(bad)

    def test_uuid_injection_and_noncanonical_nil_rejected(self):
        for value in [None, 'not-a-uuid', 'ea24ad76-517b-43df-a1d0-7c879506bc77\nExecStart=id', '00000000-0000-0000-0000-000000000000']:
            bad = policy(); bad['server']['data_uuid'] = value
            with self.assertRaises(ValueError): p.render(bad)

    def test_export_single_filesystem_two_exact_clients_and_root_squash(self):
        export = p.render(policy())['server/dell-resources.exports']
        self.assertEqual(len(export.splitlines()), 1)
        self.assertEqual(export.count('root_squash,'), 2)
        self.assertEqual(export.count('fsid=0,mountpoint,'), 2)
        for forbidden in ['*(', '/24(', 'no_root_squash', 'all_squash', 'async', 'crossmnt']:
            self.assertNotIn(forbidden, export)

    def test_v41_only_no_udp_and_no_fallback_version(self):
        conf = p.render(policy())['server/90-dell-resources.conf']
        for setting in ['vers3=n', 'vers4.0=n', 'vers4.1=y', 'vers4.2=n', 'udp=n', 'rdma=n', 'host=192.168.19.80']:
            self.assertIn(setting, conf)

    def test_client_automount_no_network_cycle_hard_and_noexec(self):
        files = p.render(policy())
        for vmid in [230, 240]:
            mount = files[f'client-{vmid}/mnt-resources.mount']
            auto = files[f'client-{vmid}/mnt-resources.automount']
            for word in ['vers=4.1', 'hard', 'noexec', 'What=192.168.19.80:/', 'Where=/mnt/resources']:
                self.assertIn(word, mount)
            self.assertNotIn('soft,', mount)
            self.assertNotIn('network-online.target', auto)
            self.assertNotIn('/mnt/dell-artifacts', mount)

    def test_future_java_dependency_has_mount_gate_not_business_start(self):
        for vmid in [230, 240]:
            text = p.render(policy())[f'client-{vmid}/future-java-resource-dependency.conf']
            self.assertIn('BindsTo=mnt-resources.mount', text)
            self.assertIn('ExecStartPre=+/usr/bin/python3', text)
            self.assertNotIn('ExecStart=', text)
            self.assertNotIn('WantedBy=', text)

    def test_server_guard_accepts_exact_uuid_and_mount_flags(self):
        g.check_mount(policy(), 'server', server_row(), 'resource-service', ('resources', 2980))

    def test_server_guard_rejects_rootdisk_missing_uuid_or_wrong_filesystem(self):
        for delta in [{'uuid': None}, {'uuid': 'wrong'}, {'target': '/'}, {'fstype': 'overlay'}, {'options': 'rw'}]:
            row = server_row(); row.update(delta)
            with self.assertRaises(ValueError): g.check_mount(policy(), 'server', row, 'resource-service', ('resources', 2980))

    def test_client_guard_preserves_finger_primary_and_requires_supplementary(self):
        g.check_mount(policy(), 'client-230', client_row(), 'java-prod-01', ('resources', 2980), (999, 989), [989, 2980])
        for identity, groups in [((999, 2980), [2980]), ((1000, 989), [2980]), ((999, 989), [989])]:
            with self.assertRaises(ValueError): g.check_mount(policy(), 'client-230', client_row(), 'java-prod-01', ('resources', 2980), identity, groups)

    def test_client_guard_rejects_wrong_host_server_protocol_soft_or_local_fallback(self):
        for delta in [{'source': '192.168.19.11:/'}, {'target': '/mnt/dell-artifacts'}, {'fstype': 'ext4'},
                      {'options': client_row()['options'].replace('vers=4.1', 'vers=4.2')},
                      {'options': client_row()['options'].replace('hard', 'soft')}]:
            row = client_row(); row.update(delta)
            with self.assertRaises(ValueError): g.check_mount(policy(), 'client-240', row, 'java-test-01', ('resources', 2980), (999, 989), [2980])
        with self.assertRaises(ValueError): g.check_mount(policy(), 'client-230', client_row(), 'java-test-01', ('resources', 2980), (999, 989), [2980])

    def test_gid_collision_rejected(self):
        with self.assertRaises(ValueError): g.check_mount(policy(), 'server', server_row(), 'resource-service', ('unrelated', 2980))

    def test_firewall_blocks_other_nfs_sources_rpc_udp_and_keeps_protective_rules_on_stop(self):
        files = p.render(policy()); nft = files['server/dell-resources-input.nft']
        self.assertIn('tcp dport 2049 ip saddr { 192.168.19.40, 192.168.19.45 } accept', nft)
        self.assertIn('tcp dport 2049 drop', nft)
        self.assertIn('udp dport 2049 drop', nft)
        self.assertNotIn('flush ruleset', nft)
        unit = files['server/dell-resources-firewall.service']
        self.assertNotIn('\nExecStop=', unit)

    def firewall_namespace(self):
        files = p.render(policy())
        namespace = {'__name__': 'owned_firewall_test_only'}
        exec(compile(files['server/apply-firewall.py'], 'rendered-firewall-helper', 'exec'), namespace)
        return files, namespace

    def test_firewall_repeat_is_atomic_owned_replace_preserves_foreign_tables(self):
        files, helper = self.firewall_namespace()
        rules = files['server/dell-resources-input.nft']
        initial = helper['transaction'](rules, {'nftables': [{'table': {'family': 'inet', 'name': 'foreign'}}]})
        self.assertEqual(initial, rules)
        repeated = helper['transaction'](rules, {'nftables': [{'table': {'family': 'inet', 'name': 'foreign'}}, {'table': {'family': 'inet', 'name': 'dell_resources_input'}}]})
        self.assertEqual(repeated, 'delete table inet dell_resources_input\n'+rules)
        self.assertNotIn('delete table inet foreign', repeated)
        self.assertNotIn('flush ruleset', repeated)
        self.assertIn('/opt/dell/resources/apply-firewall.py --check', files['server/dell-resources-firewall.service'])
        self.assertNotIn('ExecStart=/usr/sbin/nft --file', files['server/dell-resources-firewall.service'])

    def test_firewall_wrong_rules_or_ambiguous_listing_rejected(self):
        files, helper = self.firewall_namespace()
        rules = files['server/dell-resources-input.nft']
        for changed in [rules+'flush ruleset\n', rules.replace('192.168.19.40', '192.168.19.0/24'), rules.replace('dell_resources_input', 'another')]:
            with self.assertRaises(ValueError): helper['transaction'](changed, {'nftables': []})
        duplicate = {'table': {'family': 'inet', 'name': 'dell_resources_input'}}
        with self.assertRaises(ValueError): helper['transaction'](rules, {'nftables': [duplicate, duplicate]})

    def test_loopback_RPC_not_dropped_and_all_legacy_external_ports_still_denied(self):
        files = p.render(policy())
        nft = files['server/dell-resources-input.nft']
        self.assertLess(nft.index('iifname "lo" accept'), nft.index('th dport { 111, 20048 } drop'))
        self.assertIn('vers2=n', files['server/90-dell-resources.conf'])
        self.assertIn('vers3=n', files['server/90-dell-resources.conf'])

    def test_bootstrap_rejects_nonempty_wrongsize_or_mounted_data_device(self):
        bootstrap = module('resource_bootstrap_test', 'bootstrap-storage.py')
        original = {'type': 'disk', 'size': 100*1024**3, 'fstype': None, 'children': [], 'mountpoints': [None]}
        bootstrap.blank_disk(original)
        for change in [{'size': 32*1024**3}, {'fstype': 'ext4'}, {'children': [{'name': 'sdb1'}]}, {'mountpoints': ['/']}, {'type': 'part'}]:
            with self.assertRaises(ValueError): bootstrap.blank_disk({**original, **change})

    def test_bootstrap_fstab_target_or_device_conflict_refused(self):
        bootstrap = module('resource_bootstrap_fstab_test', 'bootstrap-storage.py')
        bootstrap.fstab_available('UUID=root / ext4 defaults 0 1\n', '/dev/sdb')
        for text in ['UUID=old /srv/resources ext4 defaults 0 2\n', '/dev/sdb /old ext4 defaults 0 2\n', str(bootstrap.D)+' /old ext4 defaults 0 2\n']:
            with self.assertRaises(ValueError): bootstrap.fstab_available(text, '/dev/sdb')

    def test_mountd_preserves_client_supplementary_groups(self):
        text = p.render(policy())['server/90-dell-resources.conf']
        mountd = text.split('[mountd]\n', 1)[1]
        self.assertIn('manage-gids=n\n', mountd)
        self.assertNotIn('manage-gids=y', text)
        self.assertNotIn('no_root_squash', p.render(policy())['server/dell-resources.exports'])

    def test_effective_mountd_manage_gids_readback_must_be_n(self):
        from types import SimpleNamespace
        installer = module('resource_install_mountd_test', 'install.py')
        command = ['/usr/sbin/nfsconf', '--get', 'mountd', 'manage-gids']
        with patch.object(installer, 'run', return_value=SimpleNamespace(stdout=b'n\n')) as run:
            installer.verify_mountd_groups()
            run.assert_called_once_with(command)
        for actual in [b'y\n', b'', b'yes\n', b'true\n']:
            with self.subTest(actual=actual), patch.object(installer, 'run', return_value=SimpleNamespace(stdout=actual)):
                with self.assertRaisesRegex(ValueError, '^effective-mountd-manage-gids-mismatch$'):
                    installer.verify_mountd_groups()

    def native_automount_row(self):
        return {'target': '/mnt/resources', 'source': 'systemd-1', 'fstype': 'autofs',
                'uuid': None, 'options': 'rw,relatime,fd=52,pgrp=1,timeout=0,minproto=5,maxproto=5,direct,pipe_ino=1234'}

    def test_native_stacked_autofs_and_NFS_selects_only_real_mount(self):
        nfs = client_row()
        nfs['options'] += ',relatime,timeo=600,retrans=2,clientaddr=192.168.19.40'
        for rows in [[self.native_automount_row(), nfs], [nfs, self.native_automount_row()]]:
            chosen = g.select_mount(rows, '/mnt/resources')
            self.assertIs(chosen, nfs)
            g.check_mount(policy(), 'client-230', chosen, 'java-prod-01', ('resources', 2980), (999, 989), [989, 2980])

    def test_autofs_only_runtime_guard_rejects_installer_can_select_owned(self):
        auto = self.native_automount_row()
        with self.assertRaisesRegex(ValueError, '^real-NFS-mount-required$'):
            g.select_mount([auto], '/mnt/resources')
        self.assertIs(g.select_mount([auto], '/mnt/resources', allow_autofs_only=True), auto)

    def test_foreign_duplicate_or_nonresource_stacks_rejected(self):
        auto = self.native_automount_row(); nfs = client_row()
        wrong_source = {**auto, 'source': 'foreign-automounter'}
        indirect = {**auto, 'options': 'rw,indirect'}
        for rows in [[wrong_source, nfs], [indirect, nfs], [auto, auto], [nfs, nfs],
                     [auto, nfs, nfs], [auto, {**nfs, 'fstype': 'ext4'}],
                     [auto, {**nfs, 'target': '/mnt/elsewhere'}],
                     [{**auto, 'children': [nfs]}, nfs]]:
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                g.select_mount(rows, '/mnt/resources', allow_autofs_only=True)
        with self.assertRaises(ValueError):
            g.select_mount([{**auto, 'target': '/srv/resources'}, server_row()], '/srv/resources')

    def test_stacked_selection_does_not_weaken_NFS_source_or_options(self):
        for change in [{'source': '192.168.19.11:/'}, {'options': 'rw,vers=4.1,proto=tcp,soft,sec=sys,nodev,nosuid,noexec'}, {'options': 'rw,vers=4.2,proto=tcp,hard,sec=sys,nodev,nosuid,noexec'}]:
            selected = g.select_mount([self.native_automount_row(), {**client_row(), **change}], '/mnt/resources')
            with self.assertRaises(ValueError):
                g.check_mount(policy(), 'client-230', selected, 'java-prod-01', ('resources', 2980), (999, 989), [989, 2980])

    def test_installer_autofs_only_requires_previous_owned_mount_and_automount(self):
        from types import SimpleNamespace
        import json
        installer = module('resource_install_stack_test', 'install.py')
        auto = self.native_automount_row()
        result = SimpleNamespace(returncode=0, stdout=json.dumps({'filesystems': [auto]}).encode())
        owned = {'files': {'/etc/systemd/system/mnt-resources.mount': 'known', '/etc/systemd/system/mnt-resources.automount': 'known'}}
        with patch.object(installer, 'run', return_value=result), patch.object(installer, 'safe_path'):
            self.assertFalse(installer.client_directory(owned))
            for previous in [{'files': {}}, {'files': {'unrelated': 'known'}}, {'files': {'/etc/systemd/system/mnt-resources.automount': 'known'}}]:
                with self.subTest(previous=previous), self.assertRaises(ValueError):
                    installer.client_directory(previous)

    def test_reinstall_accepts_only_expected_group_writable_mounted_data_root(self):
        from types import SimpleNamespace
        import json
        installer = module('resource_install_mounted_root_test', 'install.py')
        result = SimpleNamespace(returncode=0, stdout=json.dumps({'filesystems': [self.native_automount_row(), client_row()]}).encode())
        owned = {'files': {'/etc/systemd/system/mnt-resources.mount': 'known', '/etc/systemd/system/mnt-resources.automount': 'known'}}
        path = Path('/mnt/resources')
        real_stat = Path.stat
        def metadata(value, *args, **kwargs):
            if value == path:
                return SimpleNamespace(st_mode=0o42770, st_uid=0, st_gid=2980)
            return real_stat(value, *args, **kwargs)
        with patch.object(installer, 'run', return_value=result), patch.object(installer, 'safe_path') as trust, patch.object(Path, 'stat', metadata), patch.object(Path, 'is_symlink', return_value=False), patch.object(Path, 'resolve', lambda p, **kwargs: p):
            self.assertFalse(installer.client_directory(owned))
            trust.assert_called_once_with(path.parent)
        for delta in [{'st_mode': 0o42777}, {'st_uid': 999}, {'st_gid': 989}]:
            bad = SimpleNamespace(**{**{'st_mode': 0o42770, 'st_uid': 0, 'st_gid': 2980}, **delta})
            with self.subTest(delta=delta), patch.object(installer, 'run', return_value=result), patch.object(installer, 'safe_path'), patch.object(Path, 'stat', return_value=bad), patch.object(Path, 'is_symlink', return_value=False), patch.object(Path, 'resolve', lambda p, **kwargs: p):
                with self.assertRaises(ValueError): installer.client_directory(owned)

    def test_http_is_optional_read_only_image_prefix(self):
        files = p.render(policy()); conf = files['optional-http/NOT-ENABLED-nginx.conf']
        self.assertIn('limit_except GET HEAD { deny all; }', conf)
        self.assertIn('autoindex off;', conf)
        self.assertIn('disable_symlinks on;', conf)
        self.assertNotIn('proxy_pass', conf)
        self.assertFalse(any('nginx.service' in key for key in files))


if __name__ == '__main__':
    unittest.main()
