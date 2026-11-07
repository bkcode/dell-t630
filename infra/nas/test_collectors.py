#!/usr/bin/env python3
"""Offline safety checks: no SSH, packages, disks or containers are touched."""
import argparse
import ast
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import verify_guest as guest
import verify_stack as stack


class CollectorSafetyTests(unittest.TestCase):
    def test_embedded_programs_are_valid_python(self):
        ast.parse(guest.GUEST_SOURCE)
        ast.parse(stack.STACK_SOURCE)

    def test_verified_ssh_on_both_hops_and_ub_target(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as tmp:
            key = Path(tmp) / 'identity'
            key.write_text('offline-test-marker')
            key.chmod(0o600)
            known = Path(tmp) / 'known_hosts'
            known.write_text('')
            args = argparse.Namespace(identity=str(key), port=22, timeout=120,
                known_hosts=str(known), host='10.63.40.10', jump_host='192.168.21.22', jump_port=22)
            command = guest.ssh_command(args)
            self.assertIn('StrictHostKeyChecking=yes', command)
            self.assertIn('BatchMode=yes', command)
            self.assertIn('ub@10.63.40.10', command)
            proxy = next(x for x in command if x.startswith('ProxyCommand='))
            self.assertIn('StrictHostKeyChecking=yes', proxy)
            self.assertIn('root@192.168.21.22', proxy)
            self.assertIn(str(key), proxy)
            self.assertIn('-W %h:%p', proxy)
            key.chmod(0o644)
            with self.assertRaises(ValueError):
                guest.ssh_command(args)

    def test_remote_failure_does_not_emit_stderr_or_stdout(self):
        args = argparse.Namespace(timeout=20)
        result = subprocess.CompletedProcess([], 255, stdout='private-output-marker',
                                             stderr='Permission denied secret-marker')
        with mock.patch.object(guest, 'ssh_command', return_value=['not-executed']), \
             mock.patch.object(guest.subprocess, 'run', return_value=result):
            record, code = guest.remote_json(args, 'print(1)', {})
        encoded = json.dumps(record)
        self.assertEqual(code, 2)
        self.assertEqual(record['error_category'], 'public_key_or_privilege_denied')
        self.assertNotIn('secret-marker', encoded)
        self.assertNotIn('private-output-marker', encoded)

    def test_non_json_result_is_withheld(self):
        args = argparse.Namespace(timeout=20)
        result = subprocess.CompletedProcess([], 0, stdout='secret-marker', stderr='')
        with mock.patch.object(guest, 'ssh_command', return_value=['not-executed']), \
             mock.patch.object(guest.subprocess, 'run', return_value=result):
            record, code = guest.remote_json(args, 'print(1)', {})
        self.assertEqual(code, 2)
        self.assertNotIn('secret-marker', json.dumps(record))

    def test_endpoint_rejects_credentials_query_and_write_routes(self):
        for value in ['x=http://user:pass@localhost/health',
                      'x=http://localhost/health?token=sensitive',
                      'x=http://localhost/api/delete', 'x=file:///etc/shadow']:
            with self.assertRaises(argparse.ArgumentTypeError):
                stack.endpoint(value)
        self.assertEqual(stack.endpoint('jellyfin=http://127.0.0.1:8096/health')['name'], 'jellyfin')

    def test_unmounted_data_path_fails_closed(self):
        import runpy
        source = Path(__file__).parent / 'check-data-mount.py'
        args = ['check-data-mount.py', '--mountpoint', '/srv/dev-disk-by-uuid-11111111-1111-1111-1111-111111111111',
                '--uuid', '11111111-1111-1111-1111-111111111111']
        capture = io.StringIO()
        with mock.patch.object(sys, 'argv', args), mock.patch('os.path.ismount', return_value=False), \
             contextlib.redirect_stdout(capture), self.assertRaises(SystemExit) as outcome:
            runpy.run_path(str(source), run_name='__main__')
        self.assertEqual(outcome.exception.code, 1)
        self.assertEqual(json.loads(capture.getvalue())['status'], 'failed')


if __name__ == '__main__':
    unittest.main()
