#!/usr/bin/env python3
"""Restore coordinator tests: synthetic local backups, all native operations mocked."""
import contextlib
import copy
import gzip
import hashlib
import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location('restore_host', HERE/'host-drill.py')
HOST = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(HOST)
SOURCE = 'b'*32
REPORT = {'status': 'passed', 'cleanup_failed': False, 'source_containers_unchanged': True,
          'restart_persistence_verified': True, 'row_digests_match': True,
          'full_table_DDL_match': True, 'table_count': 12}

class RestoreHostTests(unittest.TestCase):
    def exercise(self, *, failing_phase=None, report=None, corrupt_source=False):
        with tempfile.TemporaryDirectory(prefix='db-restore-host-test-') as tmp:
            root = Path(tmp); state = root/'state'; state.mkdir(mode=0o700)
            base = root/'backups'; base.mkdir(mode=0o700); source = base/SOURCE; source.mkdir(mode=0o700)
            payload = gzip.compress(b'-- synthetic SQL fixture; never executed\n-- Dump completed on fixture\n')
            archive = source/'mysql.sql.gz'; archive.write_bytes(payload); archive.chmod(0o600)
            digest = hashlib.sha256(payload).hexdigest()
            manifest = {'status': 'complete', 'databases': ['nacos_prod'],
                        'table_counts': {'nacos_prod': 12}, 'sha256': digest, 'compressed_bytes': len(payload)}
            (source/'manifest.json').write_text(json.dumps(manifest)); (source/'manifest.json').chmod(0o600)
            receipt = {'run_id': SOURCE, 'status': 'verified', 'databases': ['nacos_prod'],
                       'archive_sha256': digest, 'archive_bytes': len(payload)}
            if corrupt_source:
                changed = bytearray(payload); changed[-1] ^= 1; archive.write_bytes(changed)
            calls = []; selected_report = copy.deepcopy(REPORT if report is None else report)
            timer = 'ActiveState=active\nUnitFileState=enabled\nNextElapseUSecRealtime=fixed\n'
            def native(args, timeout=40):
                if args[0] == 'findmnt':
                    return json.dumps({'filesystems': [{'target': '/mnt/pve/store', 'uuid': '75e5b438-5ff3-4139-83d6-b6a6847aedac'}]})
                if args[0] == 'systemctl': return 'ActiveState=inactive\n' if args[2].endswith('.service') else timer
                self.assertEqual(args[:2], ['perl', HOST.BRIDGE]); phase, run = args[2:4]
                self.assertRegex(run, '^[0-9a-f]{32}$'); calls.append(phase)
                if phase == failing_phase: raise RuntimeError('synthetic-stage-error')
                if phase == 'read-report':
                    document = {**selected_report, 'run_id': run}
                    out = state/run/'guest-report.json'; out.write_text(json.dumps(document)); out.chmod(0o600)
                return '{}'
            actual_load = HOST.load
            def load(path):
                return receipt if str(path) == '/var/lib/dell-prod-db-backup/last-success.json' else actual_load(path)
            is_dir = Path.is_dir
            with patch.object(HOST, 'STATE', state), patch.object(HOST, 'BASE', base), \
                 patch.object(HOST, 'secure', side_effect=lambda p, mode: p), \
                 patch.object(HOST, 'load', side_effect=load), patch.object(HOST, 'native', side_effect=native), \
                 patch.object(HOST.os, 'geteuid', return_value=0), patch.object(HOST.os, 'umask'), \
                 patch.object(HOST.socket, 'gethostname', return_value='pve'), \
                 patch.object(Path, 'is_dir', lambda p: True if str(p) == '/etc/pve' else is_dir(p)), \
                 contextlib.redirect_stdout(io.StringIO()):
                try:
                    HOST.main()
                except (SystemExit, AssertionError) as error:
                    outcome = error.code if isinstance(error, SystemExit) else 'preflight-refused'
                else: self.fail('coordinator must return explicit result')
            results = list(state.glob('*/host-result.json'))
            result = json.loads(results[0].read_text()) if results else None
            self.assertEqual(archive.read_bytes(), bytes(changed) if corrupt_source else payload)
            return outcome, calls, result

    def test_exact_isolation_report_and_source_preservation(self):
        code, calls, result = self.exercise()
        self.assertEqual(code, 0)
        self.assertEqual(calls, ['prepare', 'write-expected', 'write-archive', 'restore', 'cleanup', 'read-report'])
        self.assertTrue(result['source_backup_SHA_unchanged'])
        self.assertTrue(result['backup_timer_unchanged'])
        self.assertFalse(result['production_import_performed'])
        self.assertFalse(result['business_RPO_RTO_verified'])

    def test_phase_failures_always_attempt_own_cleanup(self):
        for phase in ['prepare', 'write-expected', 'write-archive', 'restore']:
            with self.subTest(phase=phase):
                code, calls, result = self.exercise(failing_phase=phase)
                self.assertEqual(code, 1)
                self.assertIn('cleanup', calls)
                self.assertEqual(result['status'], 'failed')
                if phase != 'restore': self.assertNotIn('restore', calls)

    def test_cleanup_failure_cannot_pass(self):
        code, _, result = self.exercise(failing_phase='cleanup')
        self.assertEqual(code, 1)
        self.assertFalse(result['cleanup_command_succeeded'])

    def test_incomplete_guest_proofs_cannot_pass(self):
        for key, value in [('status', 'failed'), ('cleanup_failed', True),
                           ('source_containers_unchanged', False), ('restart_persistence_verified', False),
                           ('row_digests_match', False), ('full_table_DDL_match', False), ('table_count', 11)]:
            with self.subTest(key=key):
                code, _, result = self.exercise(report={**REPORT, key: value})
                self.assertEqual(code, 1)
                self.assertEqual(result['status'], 'failed')

    def test_source_hash_failure_never_contacts_target(self):
        code, calls, result = self.exercise(corrupt_source=True)
        self.assertEqual(code, 'preflight-refused')
        self.assertEqual(calls, [])
        self.assertIsNone(result)

if __name__ == '__main__': unittest.main()
