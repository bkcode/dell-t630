#!/usr/bin/env python3
"""Local installer failure checks. No guest calls, privileged writes, or real credentials."""
import contextlib
import importlib.util
import json
import io
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('filebrowser_installer', Path(__file__).with_name('install.py'))
i = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(i)


class InstallationFailures(unittest.TestCase):
    def test_umask077_public_and_private_directory_modes(self):
        with tempfile.TemporaryDirectory() as root, patch.object(i, 'trusted'), patch.object(i.os, 'chown'):
            old = os.umask(0o077)
            try:
                for name, mode in [('public', 0o755), ('secrets', 0o700), ('manager', 0o700), ('state', 0o700)]:
                    p = Path(root) / name
                    i.directory(p, mode)
                    self.assertEqual(stat.S_IMODE(p.stat().st_mode), mode)
                f = Path(root) / 'secrets/key'
                i.fresh(f, b'not-a-real-credential', 0o600)
                self.assertEqual(stat.S_IMODE(f.stat().st_mode), 0o600)
                public = Path(root) / 'public/config'
                i.fresh(public, b'public configuration', 0o644)
                self.assertEqual(stat.S_IMODE(public.stat().st_mode), 0o644)
            finally:
                os.umask(old)

    def test_existing_symlink_directory_never_chowned_or_chmodded(self):
        with tempfile.TemporaryDirectory() as root, patch.object(i, 'trusted'), patch.object(i.os, 'chown') as chown:
            p = Path(root) / 'alias'
            p.symlink_to(root, target_is_directory=True)
            with self.assertRaisesRegex(RuntimeError, 'directory-identity-mismatch'):
                i.directory(p, 0o755)
            chown.assert_not_called()

    def test_fresh_does_not_overwrite_existing_file(self):
        with tempfile.TemporaryDirectory() as root, patch.object(i, 'trusted'):
            p = Path(root) / 'preserved'
            p.write_bytes(b'original')
            with self.assertRaisesRegex(RuntimeError, 'existing-config-refused'):
                i.fresh(p, b'replacement', 0o600)
            self.assertEqual(p.read_bytes(), b'original')

    @contextlib.contextmanager
    def activation(self, hashes=None, native_failure=False, receipt_failure=False):
        with tempfile.TemporaryDirectory() as root, contextlib.ExitStack() as stack:
            manager = Path(root)
            (manager / 'prepared.json').write_text(json.dumps({'status': 'management-configuration-prepared-not-started', 'public_files_sha256': {'unit': 'expected'}}))
            (manager / 'before-services.json').write_text(json.dumps({'protected': 'unchanged'}))
            stack.enter_context(patch.object(i, 'MANAGER', manager))
            for name in ['identity', 'private_preflight', 'trusted']:
                stack.enter_context(patch.object(i, name))
            stack.enter_context(patch.object(i, 'public_hashes', return_value=hashes or {'unit': 'expected'}))
            stack.enter_context(patch.object(i, 'metadata', return_value={'protected': 'unchanged'}))
            calls = []
            def run(args, **kwargs):
                calls.append(args)
                if native_failure and args[:3] == ['systemctl', 'enable', '--now']:
                    raise RuntimeError('fixed-native-operation-failed')
                return b'active\n'
            stack.enter_context(patch.object(i, 'run', side_effect=run))
            if receipt_failure:
                stack.enter_context(patch.object(i, 'fresh', side_effect=OSError('synthetic write failure')))
            yield manager, calls

    def test_public_drift_blocks_before_any_native_activation(self):
        with self.activation(hashes={'unit': 'changed'}) as (_, calls):
            with self.assertRaisesRegex(RuntimeError, 'prepared-public-files-drifted'):
                i.activate()
            self.assertEqual(calls, [])

    def test_protected_drift_blocks_before_any_native_activation(self):
        with self.activation() as (_, calls), patch.object(i, 'metadata', return_value={'protected': 'drift'}):
            with self.assertRaisesRegex(RuntimeError, 'protected-services-drifted-before-start'):
                i.activate()
            self.assertEqual(calls, [])

    def test_failed_start_disables_only_new_app_and_keeps_firewall(self):
        with self.activation(native_failure=True) as (manager, calls):
            with self.assertRaisesRegex(RuntimeError, 'fixed-native-operation-failed'):
                i.activate()
            self.assertEqual(calls[-1], ['systemctl', 'disable', '--now', 'dell-filebrowser.service'])
            self.assertFalse((manager / 'activated.json').exists())
            self.assertFalse(any('nfs-server.service' in cmd for cmd in calls))

    def test_failed_receipt_write_cannot_leave_unconfirmed_app_enabled(self):
        with self.activation(receipt_failure=True) as (_, calls):
            with self.assertRaises(OSError):
                i.activate()
            self.assertEqual(calls[-1], ['systemctl', 'disable', '--now', 'dell-filebrowser.service'])

    def test_renderer_credentials_match_installer_paths_and_exact_six_files(self):
        spec = importlib.util.spec_from_file_location('fb_renderer_cross_check', Path(__file__).with_name('prepare.py'))
        renderer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(renderer)
        files = renderer.render()
        self.assertEqual(set(files), set(i.destinations()))
        loaded = {}
        for line in files['dell-filebrowser.service'].splitlines():
            if line.startswith('LoadCredential='):
                name, path = line.split('=', 1)[1].split(':', 1)
                loaded[name] = Path(path)
        self.assertEqual(loaded, i.credential_sources())

    def test_fresh_HTTP_prepare_writes_only_account_and_JWT_secrets_without_openssl(self):
        with tempfile.TemporaryDirectory() as root, contextlib.ExitStack() as stack:
            root = Path(root)
            config, state, manager, code = [root / name for name in ['config', 'state', 'manager', 'code']]
            binary = code / 'releases/v2.1.4-beta/filebrowser'
            binary.parent.mkdir(parents=True)
            binary.write_bytes(b'synthetic binary; integrity is mocked by identity')
            for name, value in [('CONFIG', config), ('STATE', state), ('MANAGER', manager), ('CODE', code), ('BINARY', binary)]:
                stack.enter_context(patch.object(i, name, value))
            for name in ['identity', 'trusted', 'private_preflight']:
                stack.enter_context(patch.object(i, name))
            stack.enter_context(patch.object(i.os, 'chown'))
            stack.enter_context(patch.object(i, 'directory', side_effect=lambda path, *args: path.mkdir(parents=True, exist_ok=True)))
            stack.enter_context(patch.object(i.pwd, 'getpwnam', side_effect=KeyError))
            stack.enter_context(patch.object(i.pwd, 'getpwuid', side_effect=KeyError))
            stack.enter_context(patch.object(i.socket, 'socket'))
            stack.enter_context(patch.object(i, 'metadata', return_value={'protected': 'unchanged'}))
            mapping = {name: (root / name, mode) for name, (_, mode) in i.destinations().items()}
            stack.enter_context(patch.object(i, 'destinations', return_value=mapping))
            native = stack.enter_context(patch.object(i, 'run', return_value=b''))
            data = {'admin_password': 'Synthetic_admin_password_only_123456',
                    'operator_password': 'Synthetic_operator_password_only_1234', 'jwt_key': 'A' * 64}
            stack.enter_context(patch.object(i.sys, 'stdin', io.StringIO(json.dumps(data))))
            output = stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
            i.prepare()
            self.assertEqual({path.name for path in (config / 'secrets').iterdir()}, {'admin-password', 'jwt-key', 'login.json'})
            self.assertFalse((config / 'tls.crt').exists())
            self.assertFalse(any(call.args[0][0] == 'openssl' for call in native.call_args_list))
            self.assertEqual((config / 'secrets/admin-password').read_text(), data['admin_password'] + '\n')
            self.assertEqual((config / 'secrets/jwt-key').read_text(), data['jwt_key'] + '\n')
            login = json.loads((config / 'secrets/login.json').read_text())
            self.assertEqual(login['URL'], 'http://192.168.19.80:8080/')
            receipt = json.loads((manager / 'prepared.json').read_text())
            self.assertEqual(receipt['transport'], 'HTTP')
            self.assertEqual(receipt['HTTP_policy'], 'production-internal-management-HTTP-user-authorized')
            self.assertNotIn('certificate_fingerprint', receipt)
            for value in data.values():
                self.assertNotIn(value, output.getvalue())

    def test_successful_activation_records_HTTP_and_preserves_protected_services(self):
        with self.activation() as (manager, calls), contextlib.redirect_stdout(io.StringIO()):
            i.activate()
            receipt = json.loads((manager / 'activated.json').read_text())
            self.assertEqual(receipt['transport'], 'HTTP')
            self.assertIs(receipt['HTTPS'], False)
            self.assertIs(receipt['protected_service_identities_unchanged'], True)
            self.assertFalse(any('nfs-server.service' in cmd for cmd in calls))

    def test_duplicate_activation_rejected_without_starting_services(self):
        with self.activation() as (manager, calls):
            (manager / 'activated.json').write_text('{}')
            with self.assertRaisesRegex(RuntimeError, 'management-already-activated'):
                i.activate()
            self.assertEqual(calls, [])


if __name__ == '__main__':
    unittest.main()
