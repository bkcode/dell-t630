#!/usr/bin/env python3
"""Pure fixed-renderer tests. No sockets, subprocesses, installs or real credentials."""
import copy
import importlib.util
import json
from pathlib import Path
import types
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('filebrowser_renderer', HERE / 'prepare.py')
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)


def generated(name):
    module = types.ModuleType('generated_' + name.replace('.', '_'))
    exec(compile(p.render()[name], name, 'exec'), module.__dict__)
    return module


class FixedConfiguration(unittest.TestCase):
    def test_exact_six_public_outputs_and_source_compilation(self):
        files = p.render()
        self.assertEqual(set(files), {'config.yaml', 'dell-filebrowser.service', 'dell-filebrowser-firewall.service', 'firewall.py', 'launch.py', 'input.nft'})
        for name in ['launch.py', 'firewall.py']:
            compile(files[name], name, 'exec')
        p.validate_config(json.loads(files['config.yaml']))

    def test_no_secret_literals_or_admin_password_in_public_config(self):
        value = p.config()
        self.assertEqual(value['auth']['key'], '${DELL_FB_JWT_KEY}')
        self.assertEqual(value['http']['tlsKey'], '${CREDENTIALS_DIRECTORY}/tls-key')
        self.assertNotIn('adminPassword', p.render()['config.yaml'])
        self.assertEqual(value['auth']['methods']['password']['adminUsername'], 'admin')
        self.assertTrue(p.manifest()['includes_secrets'] is False)

    def test_mandatory_auth_and_single_private_resource_scope(self):
        cfg = p.config(); auth = cfg['auth']['methods']; source = cfg['server']['sources']
        self.assertIs(auth['noauth'], False)
        self.assertEqual(auth['password'], {'enabled': True, 'signup': False, 'minLength': 16, 'adminUsername': 'admin'})
        self.assertTrue(all(auth[key]['enabled'] is False for key in ['proxy', 'jwt', 'ldap', 'oidc', 'passkey']))
        self.assertEqual(len(source), 1)
        self.assertEqual(source[0]['path'], '/srv/resources')
        self.assertIs(source[0]['config']['private'], True)
        self.assertIs(source[0]['config']['createUserDir'], False)
        self.assertNotIn('share', source[0]['config']['defaultPermissions'])
        self.assertIs(cfg['userDefaults']['account']['permissions']['share'], False)

    def test_dangerous_config_mutations_rejected(self):
        mutations = [lambda c: c['http'].update(listen='0.0.0.0'),
                     lambda c: c['http'].update(port=80),
                     lambda c: c['http'].update(trustProxyHeaders=True),
                     lambda c: c['http'].update(disableWebDAV=False),
                     lambda c: c['server']['database'].update(path='/srv/resources/app.db'),
                     lambda c: c['server'].update(cacheDir='/srv/resources/cache'),
                     lambda c: c['server']['sources'].append({'path': '/'}),
                     lambda c: c['server']['sources'][0]['config'].update(private=False),
                     lambda c: c['server']['sources'][0]['config']['defaultPermissions'].update(modify=True),
                     lambda c: c['server']['sources'][0]['config']['defaultPermissions'].update(delete=True),
                     lambda c: c['auth']['methods'].update(noauth=True),
                     lambda c: c['auth']['methods']['password'].update(signup=True),
                     lambda c: c['auth']['methods']['password'].update(adminPassword='synthetic-not-permitted'),
                     lambda c: c['auth']['methods']['proxy'].update(enabled=True),
                     lambda c: c['userDefaults']['account']['permissions'].update(share=True),
                     lambda c: c['server']['sources'][0]['config'].update(private=1)]
        for edit in mutations:
            value = p.config(); edit(value)
            with self.assertRaises(ValueError): p.validate_config(value)

    def test_symlink_and_lostfound_rules_cannot_be_removed(self):
        value = p.config(); value['server']['sources'][0]['config']['rules'] = []
        with self.assertRaises(ValueError): p.validate_config(value)
        rules = p.config()['server']['sources'][0]['config']['rules']
        self.assertEqual(rules, [{'folderPath': '/lost+found'}, {'folderPath': '/', 'ignoreSymlinks': True}])

    def test_new_file_permissions_and_private_metadata(self):
        value = p.config()['server']
        self.assertEqual(value['filesystem'], {'createFilePermission': '660', 'createDirectoryPermission': '2770'})
        self.assertEqual(value['database']['path'], '/var/lib/dell-filebrowser/database.sqlite')
        self.assertEqual(value['cacheDir'], '/var/lib/dell-filebrowser/cache')
        self.assertEqual(value['logging'][0]['levels'], 'warning|error')
        self.assertEqual(value['logging'][0]['apiFilter'], '^/')
        self.assertEqual(value['logging'][0]['apiLevels'], '')

    def test_release_drift_or_non_native_or_auto_update_rejected(self):
        value = json.loads((HERE / 'upstream.lock.json').read_text()); p.validate_lock(value)
        for edit in [lambda c: c.update(tag='main'), lambda c: c.update(native_install=False),
                     lambda c: c.update(automatic_upgrades=True),
                     lambda c: c['asset'].update(name='linux-arm64-filebrowser'),
                     lambda c: c['asset'].update(digest='sha256:' + '0' * 64),
                     lambda c: c['asset'].update(url='https://example.invalid/filebrowser'),
                     lambda c: c['asset'].update(size=1)]:
            bad = copy.deepcopy(value); edit(bad)
            with self.assertRaises(ValueError): p.validate_lock(bad)


class LaunchContract(unittest.TestCase):
    def setUp(self):
        self.launch = generated('launch.py')
        self.secrets = {'jwt-key': b'A' * 64, 'admin-password': b'Synthetic-Password-Only-123',
                        'tls-key': b'SYNTHETIC-ONLY PRIVATE KEY-----NOT-A-REAL-KEY'}

    def test_failure_diagnostic_allows_only_bounded_code_and_class(self):
        self.assertEqual(self.launch.failure_summary(ValueError('invalid-credential-file')), {
            'error': 'dell-filebrowser-launch-failed', 'failure_code': 'invalid-credential-file', 'exception_class': 'ValueError'})
        for message in ['synthetic secret with spaces', '/run/credentials/private-path', 'line1\nline2', 'x' * 81, '', 'secret=value']:
            result = self.launch.failure_summary(RuntimeError(message))
            self.assertEqual(result['failure_code'], 'withheld')
            self.assertEqual(result['exception_class'], 'RuntimeError')
            self.assertNotIn(message, json.dumps(result)) if message else None
        result = self.launch.failure_summary(PermissionError(13, 'Permission denied', '/synthetic/private-path'))
        self.assertEqual(result['failure_code'], 'withheld')
        self.assertEqual(result['exception_class'], 'PermissionError')

    def test_first_boot_injects_secret_only_into_fresh_environment(self):
        reads = []
        def reader(name):
            reads.append(name)
            return self.secrets[name]
        with patch.dict(self.launch.os.environ, {'FILEBROWSER_ADMIN_PASSWORD': 'INHERITED-WRONG', 'FILEBROWSER_PORT': '1234', 'DELL_FB_JWT_KEY': 'WRONG'}):
            env = self.launch.environment(False, reader)
        self.assertEqual(reads, ['jwt-key', 'tls-key', 'admin-password'])
        self.assertEqual(env['FILEBROWSER_ADMIN_PASSWORD'], self.secrets['admin-password'].decode())
        self.assertEqual(env['DELL_FB_JWT_KEY'], 'A' * 64)
        self.assertNotIn('FILEBROWSER_PORT', env)
        self.assertEqual(env['FILEBROWSER_DISABLE_AUTOMATIC_BACKUP'], 'true')

    def test_marker_complete_never_reads_or_reinjects_admin_password(self):
        reads = []
        def reader(name):
            reads.append(name)
            if name == 'admin-password': raise AssertionError('must not read bootstrap secret')
            return self.secrets[name]
        with patch.dict(self.launch.os.environ, {'FILEBROWSER_ADMIN_PASSWORD': 'INHERITED-WRONG'}):
            env = self.launch.environment(True, reader)
        self.assertEqual(reads, ['jwt-key', 'tls-key'])
        self.assertNotIn('FILEBROWSER_ADMIN_PASSWORD', env)
        self.assertNotIn('DELL_FB_ADMIN_PASSWORD', env)
        self.assertEqual(env['FILEBROWSER_DISABLE_AUTOMATIC_BACKUP'], 'true')
        self.assertEqual(str(self.launch.MARKER), '/etc/dell-filebrowser/bootstrap.complete')

    def test_bootstrap_marker_is_root_read_only_and_not_app_state(self):
        import stat
        state = types.SimpleNamespace(st_mode=stat.S_IFDIR | 0o700, st_uid=2000, st_gid=2980)
        root = types.SimpleNamespace(st_mode=stat.S_IFDIR | 0o755, st_uid=0, st_gid=0)
        def fake_stat(path):
            return state if path == self.launch.STATE else root
        with patch.object(self.launch.Path, 'lstat', fake_stat), patch.object(self.launch.Path, 'is_symlink', return_value=False), patch.object(self.launch.Path, 'exists', return_value=True), patch.object(self.launch, 'trusted_file', return_value=b'complete') as trusted:
            self.assertTrue(self.launch.bootstrapped())
            trusted.assert_called_once_with(self.launch.MARKER, 1024, 0o644)
        with patch.object(self.launch.Path, 'lstat', fake_stat), patch.object(self.launch.Path, 'is_symlink', return_value=False), patch.object(self.launch.Path, 'exists', return_value=False), patch.object(self.launch, 'trusted_file') as trusted:
            self.assertFalse(self.launch.bootstrapped())
            trusted.assert_not_called()

    def test_writable_bootstrap_parent_rejected(self):
        import stat
        state = types.SimpleNamespace(st_mode=stat.S_IFDIR | 0o700, st_uid=2000, st_gid=2980)
        writable = types.SimpleNamespace(st_mode=stat.S_IFDIR | 0o777, st_uid=0, st_gid=0)
        with patch.object(self.launch.Path, 'lstat', lambda path: state if path == self.launch.STATE else writable):
            with self.assertRaises(ValueError): self.launch.bootstrapped()

    def test_bad_credentials_rejected_without_any_exec(self):
        for name, data in [('jwt-key', b'short'), ('jwt-key', b'A' * 32 + b'"\nconfig:'),
                           ('admin-password', b'short'), ('admin-password', b'A' * 20 + b'\x00'),
                           ('tls-key', b'not-a-key')]:
            secrets = dict(self.secrets); secrets[name] = data
            with self.assertRaises(ValueError): self.launch.environment(False, secrets.__getitem__)

    def test_exec_argv_is_only_fixed_binary_and_config_and_environment_is_separate(self):
        with patch.object(self.launch.os, 'geteuid', return_value=2000), patch.object(self.launch.os, 'getegid', return_value=2980), patch.object(self.launch.socket, 'gethostname', return_value='resource-service'), patch.object(self.launch.Path, 'exists', return_value=False), patch.object(self.launch, 'trusted_file', side_effect=[self.launch.EXPECTED_CONFIG, b'binary']), patch.object(self.launch.hashlib, 'sha256') as hashfn, patch.object(self.launch, 'bootstrapped', return_value=True), patch.object(self.launch, 'environment', return_value={'DELL_FB_JWT_KEY': 'SYNTHETIC-NOT-AN-ARGV'}), patch.object(self.launch.os, 'execve') as execute:
            # The binary-length guard rejects this mock first; it must not exec an unverified binary.
            hashfn.return_value.hexdigest.return_value = p.BINARY_SHA256
            with self.assertRaises(ValueError): self.launch.main()
            execute.assert_not_called()
        source = p.render()['launch.py']
        self.assertIn("os.execve(BINARY, [BINARY, '--no-input', '-c', str(CONFIG)], env)", source)
        self.assertNotIn('print(env)', source)

    def test_successful_exec_has_no_password_or_JWT_in_argv(self):
        class SizedBinary:
            def __len__(self): return 29064968
        env = {'DELL_FB_JWT_KEY': 'SYNTHETIC-JWT-NOT-ARGV', 'FILEBROWSER_ADMIN_PASSWORD': 'SYNTHETIC-PASSWORD-NOT-ARGV'}
        with patch.object(self.launch.os, 'geteuid', return_value=2000), patch.object(self.launch.os, 'getegid', return_value=2980), patch.object(self.launch.socket, 'gethostname', return_value='resource-service'), patch.object(self.launch.Path, 'exists', return_value=False), patch.object(self.launch, 'trusted_file', side_effect=[self.launch.EXPECTED_CONFIG, SizedBinary()]), patch.object(self.launch.hashlib, 'sha256') as hashfn, patch.object(self.launch, 'bootstrapped', return_value=False), patch.object(self.launch, 'environment', return_value=env), patch.object(self.launch.os, 'umask') as mask, patch.object(self.launch.os, 'execve') as execute:
            hashfn.return_value.hexdigest.return_value = p.BINARY_SHA256
            self.launch.main()
            mask.assert_called_once_with(0o002)
            binary, argv, actual_environment = execute.call_args.args
            self.assertEqual(binary, p.BINARY)
            self.assertEqual(argv, [p.BINARY, '--no-input', '-c', '/etc/dell-filebrowser/config.yaml'])
            self.assertEqual(actual_environment, env)
            self.assertFalse(any(value in ' '.join(argv) for value in env.values()))

    def test_identity_or_configuration_drift_fail_closed(self):
        with patch.object(self.launch.os, 'geteuid', return_value=0):
            with self.assertRaises(ValueError): self.launch.main()
        with patch.object(self.launch.os, 'geteuid', return_value=2000), patch.object(self.launch.os, 'getegid', return_value=2980), patch.object(self.launch.socket, 'gethostname', return_value='resource-service'), patch.object(self.launch.Path, 'exists', return_value=False), patch.object(self.launch, 'trusted_file', return_value=b'{}'), patch.object(self.launch.os, 'execve') as execute:
            with self.assertRaises(ValueError): self.launch.main()
            execute.assert_not_called()


class SystemdCredentialACL(unittest.TestCase):
    def setUp(self):
        self.launch = generated('launch.py')

    def acl(self, directory=False, entries=None, version=2):
        import struct
        permission = 5 if directory else 4
        undefined = 0xffffffff
        if entries is None:
            entries = [(1, permission, undefined), (2, permission, 2000), (4, 0, undefined), (16, permission, undefined), (32, 0, undefined)]
        return struct.pack('<I', version) + b''.join(struct.pack('<HHI', *entry) for entry in entries)

    def test_exact_native_systemd_root_ACL_allowed(self):
        for directory, mode in [(True, 0o550), (False, 0o440)]:
            self.assertTrue(self.launch.readonly_systemd_acl(self.acl(directory), directory))
            self.assertTrue(self.launch.credential_access_allowed(0, 0, mode, self.acl(directory), directory))

    def test_original_owner_only_branch_preserved(self):
        for uid, mode, directory in [(0, 0o500, True), (2000, 0o500, True), (0, 0o400, False), (2000, 0o600, False)]:
            self.assertTrue(self.launch.credential_access_allowed(uid, 2980, mode, None, directory))
        self.assertFalse(self.launch.credential_access_allowed(1000, 0, 0o400))

    def test_group_read_without_exact_ACL_never_allowed(self):
        for uid, gid, mode in [(0, 0, 0o440), (2000, 0, 0o440), (0, 2980, 0o440), (0, 0, 0o444), (0, 0, 0o640), (0, 0, 0o2440)]:
            self.assertFalse(self.launch.credential_access_allowed(uid, gid, mode))
        self.assertFalse(self.launch.credential_access_allowed(0, 2980, 0o440, self.acl()))
        self.assertFalse(self.launch.credential_access_allowed(0, 0, 0o444, self.acl()))

    def test_extra_named_user_or_group_rejected(self):
        import struct
        raw = self.acl()
        for extra in [(2, 4, 2001), (8, 4, 2980)]:
            self.assertFalse(self.launch.readonly_systemd_acl(raw + struct.pack('<HHI', *extra)))
        entries = [(1, 4, 0xffffffff), (2, 4, 2001), (4, 0, 0xffffffff), (16, 4, 0xffffffff), (32, 0, 0xffffffff)]
        self.assertFalse(self.launch.readonly_systemd_acl(self.acl(entries=entries)))

    def test_group_obj_other_or_write_perms_rejected(self):
        base = [(1, 4, 0xffffffff), (2, 4, 2000), (4, 0, 0xffffffff), (16, 4, 0xffffffff), (32, 0, 0xffffffff)]
        for index, permission in [(0, 6), (1, 6), (2, 4), (3, 6), (4, 4), (4, 2)]:
            entries = list(base); tag, _, identity = entries[index]; entries[index] = (tag, permission, identity)
            self.assertFalse(self.launch.readonly_systemd_acl(self.acl(entries=entries)))

    def test_malformed_unknown_version_or_identity_rejected(self):
        for raw in [None, b'', self.acl()[:-1], self.acl() + b'x', self.acl(version=1), self.acl(version=3), b'\x00' * 44]:
            self.assertFalse(self.launch.readonly_systemd_acl(raw))
        base = [(1, 4, 0xffffffff), (2, 4, 2000), (4, 0, 0xffffffff), (16, 4, 0xffffffff), (32, 0, 0xffffffff)]
        for index in [0, 2, 3, 4]:
            entries = list(base); tag, permission, _ = entries[index]; entries[index] = (tag, permission, 0)
            self.assertFalse(self.launch.readonly_systemd_acl(self.acl(entries=entries)))

    def test_descriptor_metadata_used_and_unreadable_ACL_fails_closed(self):
        st = types.SimpleNamespace(st_uid=0, st_gid=0, st_mode=0o440)
        with patch.object(self.launch.os, 'getxattr', return_value=self.acl(), create=True) as get:
            self.assertTrue(self.launch.credential_access(st, 99))
            get.assert_called_once_with(99, 'system.posix_acl_access')
        with patch.object(self.launch.os, 'getxattr', side_effect=OSError(), create=True):
            self.assertFalse(self.launch.credential_access(st, 99))
        st.st_mode = 0o400
        with patch.object(self.launch.os, 'getxattr', create=True) as get:
            self.assertTrue(self.launch.credential_access(st, 99))
            get.assert_not_called()


class FirewallAndUnit(unittest.TestCase):
    def setUp(self):
        self.firewall = generated('firewall.py')

    def test_first_apply_only_creates_own_table(self):
        data = self.firewall.transaction({'nftables': [{'table': {'family': 'inet', 'name': 'dell_resources_input'}}]})
        self.assertEqual(data, p.input_nft().encode())
        self.assertNotIn(b'delete table', data)

    def test_reapply_single_transaction_deletes_only_owned_table(self):
        tables = {'nftables': [{'table': {'family': 'inet', 'name': 'dell_resources_input'}}, {'table': {'family': 'inet', 'name': 'dell_filebrowser_input'}}, {'table': {'family': 'bridge', 'name': 'dell19_acl'}}]}
        data = self.firewall.transaction(tables)
        self.assertTrue(data.startswith(b'delete table inet dell_filebrowser_input\n'))
        self.assertEqual(data.count(b'delete table'), 1)
        self.assertNotIn(b'flush ruleset', data)
        self.assertNotIn(b'delete table inet dell_resources_input', data)
        self.assertNotIn(b'delete table bridge', data)

    def test_exact_input_and_no_NFS_or_route_or_NAT_mutations(self):
        nft = p.input_nft(); self.firewall.validate_input(nft.encode())
        self.assertIn('192.168.21.0/24, 10.66.66.0/24, 192.168.19.80', nft)
        self.assertIn('tcp dport 8080 counter drop', nft)
        self.assertIn('udp dport 8080 counter drop', nft)
        for value in [nft.replace('192.168.21.0/24', '0.0.0.0/0'), nft.replace('8080', '2049')]:
            with self.assertRaises(ValueError): self.firewall.validate_input(value.encode())
        for word in ['2049', 'forward', 'masquerade', ' snat ', ' dnat ']: self.assertNotIn(word, nft)

    def test_duplicate_owned_table_model_refused(self):
        row = {'table': {'family': 'inet', 'name': 'dell_filebrowser_input'}}
        with self.assertRaises(ValueError): self.firewall.transaction({'nftables': [row, row]})

    def test_unit_keeps_mount_gate_identity_credentials_and_resource_limits(self):
        unit = p.render()['dell-filebrowser.service']
        for setting in ['User=filebrowser', 'Group=resources', 'UMask=0002', 'RequiresMountsFor=/srv/resources', 'BindsTo=srv-resources.mount dell-filebrowser-firewall.service', 'ExecStartPre=+/usr/bin/python3 -I -B /opt/dell/resources/guard.py --role server', 'MemoryMax=384M', 'CPUQuota=100%', 'ReadWritePaths=/srv/resources /var/lib/dell-filebrowser', 'ProtectSystem=strict', 'ProtectHome=yes', 'PrivateTmp=yes', 'NoNewPrivileges=yes']:
            self.assertIn(setting, unit)
        self.assertEqual(unit.count('LoadCredential='), 3)
        self.assertNotIn('Environment=FILEBROWSER_ADMIN_PASSWORD', unit)
        self.assertNotIn('docker', unit.lower())
        self.assertNotIn('java', unit.lower())
        self.assertNotIn('ExecStop=', p.render()['dell-filebrowser-firewall.service'])


if __name__ == '__main__':
    unittest.main()
