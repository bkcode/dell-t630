#!/usr/bin/env python3
"""Host safety tests use only synthetic temp files and mocks; no PVE/QGA/SQL."""
import copy
import datetime as dt
import gzip
import hashlib
import importlib.util
import json
import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location('prod_db_host', HERE/'host-worker.py')
HOST = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(HOST)
POLICY = json.loads((HERE/'policy-host.json').read_text())

def ident(number): return format(number, '032x')
def row(number, finish): return {'run_id': ident(number), 'finished_at': finish}

class HostSafetyTests(unittest.TestCase):
    def test_daily_and_ISO_week_keep_uses_Shanghai_calendar(self):
        # UTC15:59 and16:01 straddle Shanghai midnight, not UTC midnight.
        rows = [row(1, '2026-11-08T16:01:00+00:00'),
                row(2, '2026-11-08T15:59:00+00:00'),
                row(3, '2026-11-08T15:58:00+00:00')]
        self.assertEqual(HOST.retention_ids(rows, last=1, daily=2, weekly=0), {ident(1), ident(2)})
        # Jan1 belongs to ISOweek2020-W53; Jan4 is2021-W01.
        weeks = [row(4, '2021-01-04T01:00:00+00:00'),
                 row(5, '2021-01-01T01:00:00+00:00'),
                 row(6, '2020-12-31T01:00:00+00:00')]
        self.assertEqual(HOST.retention_ids(weeks, last=1, daily=0, weekly=2), {ident(4), ident(5)})

    def make_run(self, base, number, finished):
        folder = base/ident(number); folder.mkdir(mode=0o700)
        payload = gzip.compress(('synthetic-backup-fixture-'+str(number)).encode())
        archive = folder/'mysql.sql.gz'; archive.write_bytes(payload)
        digest = hashlib.sha256(payload).hexdigest()
        manifest = {'run_id': folder.name, 'databases': ['nacos_prod'], 'status': 'complete', 'sha256': digest}
        manifest_path = folder/'manifest.json'; manifest_path.write_text(json.dumps(manifest))
        receipt = {'run_id': folder.name, 'status': 'verified', 'finished_at': finished,
                   'archive_bytes': len(payload), 'archive_sha256': digest,
                   'manifest_sha256': hashlib.sha256(manifest_path.read_bytes()).hexdigest()}
        (folder/'receipt.json').write_text(json.dumps(receipt))
        for file in folder.iterdir(): file.chmod(0o600)
        return folder

    def test_current_run_is_retained_even_with_clock_rollback(self):
        with tempfile.TemporaryDirectory(prefix='prod-db-host-test-') as tmp, patch.object(HOST, 'secure', side_effect=lambda path, mode=None: path):
            base = Path(tmp)
            current = self.make_run(base, 1, '2020-01-01T00:00:00+00:00')
            ancient_other = self.make_run(base, 2, '2020-01-02T00:00:00+00:00')
            for n in range(10):
                finish = dt.datetime(2026, 10, 1, tzinfo=dt.timezone.utc)+dt.timedelta(days=7*n)
                self.make_run(base, 100+n, finish.isoformat())
            partial = base/'.partial-synthetic'; partial.mkdir(); (partial/'keep.txt').write_text('only-test-data')
            unknown = base/'manual-notes'; unknown.mkdir()
            count = HOST.prune(base, POLICY, current.name)
            self.assertGreater(count, 0)
            self.assertTrue(current.is_dir())
            self.assertEqual({p.name for p in current.iterdir()}, HOST.FILES)
            self.assertFalse(ancient_other.exists())
            self.assertTrue((partial/'keep.txt').exists())
            self.assertTrue(unknown.is_dir())

    def test_same_size_archive_corruption_aborts_before_any_prune(self):
        with tempfile.TemporaryDirectory(prefix='prod-db-host-test-') as tmp, patch.object(HOST, 'secure', side_effect=lambda path, mode=None: path):
            base = Path(tmp)
            old = self.make_run(base, 1, '2020-01-01T00:00:00+00:00')
            current = self.make_run(base, 2, '2026-11-09T00:00:00+00:00')
            data = bytearray((current/'mysql.sql.gz').read_bytes()); data[-1] ^= 1
            (current/'mysql.sql.gz').write_bytes(data)
            before = {str(p.relative_to(base)): p.read_bytes() for p in base.rglob('*') if p.is_file()}
            with self.assertRaises(AssertionError): HOST.prune(base, POLICY, current.name)
            after = {str(p.relative_to(base)): p.read_bytes() for p in base.rglob('*') if p.is_file()}
            self.assertEqual(after, before)
            self.assertTrue(old.exists())

    def test_invalid_policy_rejected_before_paths_backup_or_prune(self):
        original_is_dir = Path.is_dir
        def fake_is_dir(path): return True if str(path) == '/etc/pve' else original_is_dir(path)
        for update in [{'keep_last': 0}, {'keep_daily': 0}, {'keep_weekly': -1},
                       {'keep_last': True}, {'keep_weekly': '4'},
                       {'maximum_archive_bytes': 1073741825}, {'minimum_free_bytes': 0},
                       {'databases': ['nacos_prod', 'test']}, {'whole_VM_backup': True}]:
            with self.subTest(update=update), patch.object(HOST.os, 'geteuid', return_value=0), patch.object(HOST.os, 'umask'), patch.object(HOST.socket, 'gethostname', return_value='pve'), patch.object(Path, 'is_dir', fake_is_dir), patch.object(HOST, 'load', return_value={**POLICY, **update}), patch.object(HOST, 'secure') as secure, patch.object(HOST, 'native') as native, patch.object(HOST, 'prune') as prune:
                with self.assertRaises(AssertionError): HOST.main()
                secure.assert_not_called(); native.assert_not_called(); prune.assert_not_called()

    def test_atomic_metadata_flushes_file_and_directory(self):
        with tempfile.TemporaryDirectory(prefix='prod-db-host-test-') as tmp, patch.object(HOST, 'secure', side_effect=lambda path, mode=None: path):
            destination = Path(tmp)/'status.json'; observed = []; real_sync = os.fsync
            def sync(fd):
                mode = os.fstat(fd).st_mode
                observed.append('directory' if stat.S_ISDIR(mode) else 'file')
                real_sync(fd)
            with patch.object(HOST.os, 'fsync', side_effect=sync): HOST.atomic(destination, {'status': 'synthetic-only'})
            self.assertEqual(json.loads(destination.read_text()), {'status': 'synthetic-only'})
            self.assertEqual(observed, ['file', 'directory'])
            self.assertEqual(stat.S_IMODE(destination.stat().st_mode), 0o600)
            self.assertEqual([p.name for p in Path(tmp).iterdir()], ['status.json'])

if __name__ == '__main__': unittest.main()
