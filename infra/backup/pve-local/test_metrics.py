#!/usr/bin/env python3
"""Offline metadata/parser/fail-closed tests; never run a backup or host probe."""
import copy
import datetime
import json
import os
from pathlib import Path
import stat
import subprocess
import tempfile
import time
import types
import unittest
from unittest.mock import patch

BASE = Path(__file__).resolve().parent
SOURCE = (BASE / 'metrics-block.py.txt').read_text()
assert SOURCE.count('\n_db_emit(metric)\n') == 1
NS = dict(json=json, subprocess=subprocess, time=time, os=os,
          datetime=datetime, Path=Path)
exec(compile(SOURCE.replace('\n_db_emit(metric)\n', '\n'), 'metrics-block', 'exec'), NS)
NOW = datetime.datetime(2026, 11, 9, 12, tzinfo=datetime.timezone.utc).timestamp()
START = '2026-11-09T10:00:00+00:00'
FINISH = '2026-11-09T11:00:00+00:00'


def ledger(status='verified', run_id='a' * 32, start=START, finish=FINISH):
    result = {'run_id': run_id, 'allowed_vmids': list(NS['_DB_ALLOWED']),
              'started_at': start, 'status': status, 'results': {}}
    if status != 'running':
        result['finished_at'] = finish
    if status == 'verified':
        result['results'] = {str(v): {'status': 'verified', 'zstd_verified': True,
                           'native_archive_verified': True, 'mode': '0600',
                           'bytes': 1000, 'checked_at': FINISH,
                           'archive': 'MUST_NOT_EMIT_PRIVATE_ARCHIVE',
                           'sha256': 'MUST_NOT_EMIT_PRIVATE_SHA'}
                           for v in NS['_DB_ALLOWED']}
    return result


class Fixture:
    def __init__(self):
        self.policy = json.loads((BASE / 'policy.json').read_text())
        self.current = ledger()
        self.success = copy.deepcopy(self.current)
        self.failure = None
        self.job = {'id': 'dell-local-nightly', 'enabled': 1, 'mode': 'snapshot',
                    'vmid': ','.join(map(str, NS['_DB_ALLOWED'])),
                    'storage': 'dell-local-backup',
                    'script': '/usr/local/libexec/dell-local-backup/hook.py',
                    'tmpdir': '/var/tmp/dell-local-backup',
                    'notification-mode': 'legacy-sendmail', 'mailto': ''}
        self.mount = {'filesystems': [{'target': NS['_DB_STORE'], 'fstype': 'ext4',
                                      'uuid': NS['_DB_UUID']}]}
        self.commands = []

    def read(self, path, **kwargs):
        return copy.deepcopy({'/etc/dell-local-backup/policy.json': self.policy,
                              NS['_DB_STATE'] + '/current.json': self.current,
                              NS['_DB_STATE'] + '/last-success.json': self.success,
                              NS['_DB_STATE'] + '/last-failure.json': self.failure}[path])

    def command(self, args):
        self.commands.append(args)
        return copy.deepcopy(self.job if args[0] == 'pvesh' else self.mount)

    def collect(self):
        return NS['_db_collect'](self.read, self.command, now=NOW, free_bytes=lambda: 12345)


class LogicTests(unittest.TestCase):
    def setUp(self):
        self.f = Fixture()

    def rejected(self, edit):
        edit(self.f)
        with self.assertRaises((ValueError, TypeError, KeyError)):
            self.f.collect()

    def test_verified_exact_eleven(self):
        m = self.f.collect()
        self.assertEqual((m['current_run_state'], m['last_run_success'],
                          m['verified_guest_count'], m['state_valid']), (0, 1, 11, 1))
        self.assertTrue(all(a[:3] == ['pvesh', 'get', '/cluster/backup/dell-local-nightly']
                            or a[0] == 'findmnt' for a in self.f.commands))

    def test_running_preserves_previous_completed_success(self):
        self.f.current = ledger('running', 'b' * 32, '2026-11-09T11:30:00Z')
        m = self.f.collect()
        self.assertEqual((m['running'], m['last_run_success'], m['verified_guest_count']), (1, 1, 0))

    def test_first_run_running_no_false_success(self):
        self.f.current = ledger('running')
        self.f.success = None
        m = self.f.collect()
        self.assertEqual((m['state_valid'], m['running'], m['last_run_success'],
                          m['last_success_timestamp_seconds']), (1, 1, 0, 0))

    def test_failed_without_previous_success(self):
        self.f.current, self.f.success = ledger('failed'), None
        m = self.f.collect()
        self.assertEqual((m['current_run_state'], m['last_run_success']), (2, 0))

    def test_new_guard_failure_overrides_old_verified_current(self):
        self.f.failure = {'failed_at': '2026-11-09T11:30:00Z', 'error_type': 'RuntimeError'}
        m = self.f.collect()
        self.assertEqual((m['current_run_state'], m['last_run_success']), (2, 0))

    def test_old_failure_does_not_override_later_success(self):
        self.f.failure = {'failed_at': '2026-11-09T09:00:00Z', 'statuses': {}}
        m = self.f.collect()
        self.assertEqual((m['current_run_state'], m['last_run_success']), (0, 1))

    def test_running_after_failure_stays_running_last_completed_failed(self):
        self.f.current = ledger('running', 'b' * 32, '2026-11-09T11:30:00Z')
        self.f.failure = {'failed_at': '2026-11-09T11:20:00Z', 'error_type': 'ValueError'}
        m = self.f.collect()
        self.assertEqual((m['current_run_state'], m['last_run_success']), (1, 0))

    def test_disabled_job_is_observable_not_falsified_enabled(self):
        self.f.job['enabled'] = 0
        self.assertEqual(self.f.collect()['enabled'], 0)

    def test_unknown_state(self):
        self.rejected(lambda f: f.current.update(status='done'))

    def test_partial_verified_run(self):
        self.rejected(lambda f: f.current['results'].pop('270'))

    def test_publisher_injected(self):
        self.rejected(lambda f: f.current['results'].update({'220': {'status': 'running'}}))

    def test_unverified_archive_flag(self):
        self.rejected(lambda f: f.current['results']['200'].update(native_archive_verified=False))

    def test_wrong_allowed_identity_list(self):
        self.rejected(lambda f: f.current.update(allowed_vmids=[200]))

    def test_non_UTC_time(self):
        self.rejected(lambda f: f.current.update(started_at='2026-11-09T10:00:00+08:00'))

    def test_naive_time(self):
        self.rejected(lambda f: f.current.update(started_at='2026-11-09T10:00:00'))

    def test_future_time(self):
        self.rejected(lambda f: f.current.update(started_at='2036-11-09T10:00:00Z'))

    def test_finished_before_started(self):
        self.rejected(lambda f: f.current.update(finished_at='2026-11-09T09:00:00Z'))

    def test_current_missing(self):
        self.rejected(lambda f: setattr(f, 'current', None))

    def test_verified_without_matching_success_receipt(self):
        self.rejected(lambda f: setattr(f, 'success', None))

    def test_bad_last_failure_time(self):
        self.rejected(lambda f: setattr(f, 'failure', {'failed_at': 'bad', 'statuses': {}}))

    def test_wrong_store_UUID(self):
        self.rejected(lambda f: f.mount['filesystems'][0].update(uuid='wrong'))

    def test_root_fallback_mount(self):
        self.rejected(lambda f: f.mount['filesystems'][0].update(target='/'))

    def test_duplicate_native_VM_list(self):
        self.rejected(lambda f: f.job.update(vmid=f.job['vmid'] + ',200'))

    def test_publisher_native_job(self):
        self.rejected(lambda f: f.job.update(vmid=f.job['vmid'].replace('200', '220')))

    def test_modified_notification_contract(self):
        self.rejected(lambda f: f.job.update(mailto='not-approved'))

    def test_modified_storage(self):
        self.rejected(lambda f: f.job.update(storage='local'))

    def test_bad_policy(self):
        self.rejected(lambda f: f.policy.update(state_dir='/tmp/backup'))

    def test_fault_does_not_break_original_metrics_or_leak(self):
        emitted, reports = [('existing_RAID_metric', 1)], []
        def fail():
            raise RuntimeError('MUST_NOT_EMIT_PRIVATE_ARCHIVE')
        NS['_db_emit'](lambda n, v: emitted.append((n, v)), fail, reports.append)
        self.assertEqual(emitted[0], ('existing_RAID_metric', 1))
        self.assertIn(('dell_pve_local_backup_metric_valid', 0), emitted)
        self.assertIn(('dell_pve_local_backup_current_run_state', 3), emitted)
        self.assertNotIn('MUST_NOT_EMIT', json.dumps(emitted + reports))

    def test_valid_metrics_have_no_paths_SHA_or_labels(self):
        emitted = []
        NS['_db_emit'](lambda n, v: emitted.append((n, v)), self.f.collect)
        self.assertNotIn('MUST_NOT_EMIT', json.dumps(emitted))
        self.assertTrue(all(isinstance(value, (int, float)) for _, value in emitted))

    def test_duplicate_JSON_key(self):
        with self.assertRaises(ValueError):
            NS['_db_json']('{"status":"failed","status":"verified"}')

    def test_nonfinite_JSON(self):
        with self.assertRaises(ValueError):
            NS['_db_json']('{"value":NaN}')

    def test_large_JSON(self):
        with self.assertRaises(ValueError):
            NS['_db_json'](' ' * 65537)


class CommandSafetyTests(unittest.TestCase):
    def test_small_valid_JSON(self):
        import sys
        self.assertEqual(NS['_db_command_json']([sys.executable, '-c', 'print("{}")']), {})

    def test_command_nonzero(self):
        import sys
        with self.assertRaises(ValueError):
            NS['_db_command_json']([sys.executable, '-c', 'raise SystemExit(2)'])

    def test_stdout_size_bound(self):
        import sys
        with self.assertRaises(ValueError):
            NS['_db_command_json']([sys.executable, '-c', 'print("x"*70000)'])

    def test_timeout_kills_local_fixture(self):
        import select
        import sys
        with patch.object(select, 'select', return_value=([], [], [])):
            with self.assertRaises(TimeoutError):
                NS['_db_command_json']([sys.executable, '-c', 'import time;time.sleep(30)'])


class FileSafetyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve() / 'state'
        self.base.mkdir(mode=0o700)
        self.path = self.base / 'current.json'
        self.path.write_text('{"status":"running"}')
        self.path.chmod(0o600)
        self.real_fstat = os.fstat
        self.parent_inode = self.base.stat().st_ino
        self.file_inode = self.path.stat().st_ino

    def read(self, wrong_owner=False, insecure_ancestor=False):
        # Native tests may run as an unprivileged Mac user. Only ownership and
        # external test-temporary ancestors are virtualized; open(O_NOFOLLOW),
        # actual file types, leaf directory mode, links and size remain real.
        def view(fd):
            s = self.real_fstat(fd)
            values = {k: getattr(s, k) for k in ['st_uid', 'st_mode', 'st_size', 'st_nlink']}
            values['st_uid'] = 1 if wrong_owner and s.st_ino == self.file_inode else 0
            if stat.S_ISDIR(s.st_mode) and s.st_ino != self.parent_inode:
                values['st_mode'] = stat.S_IFDIR | (0o777 if insecure_ancestor else 0o755)
            return types.SimpleNamespace(**values)
        with patch.object(os, 'fstat', side_effect=view):
            return NS['_db_read_json'](str(self.path))

    def test_private_regular_file(self):
        self.assertEqual(self.read()['status'], 'running')

    def test_wrong_file_owner(self):
        with self.assertRaises(ValueError):
            self.read(wrong_owner=True)

    def test_group_readable_secret_state(self):
        self.path.chmod(0o640)
        with self.assertRaises(ValueError):
            self.read()

    def test_parent_not_private(self):
        self.base.chmod(0o755)
        with self.assertRaises(ValueError):
            self.read()

    def test_insecure_ancestor(self):
        with self.assertRaises(ValueError):
            self.read(insecure_ancestor=True)

    def test_file_symlink(self):
        target = self.base / 'target'
        self.path.rename(target)
        self.path.symlink_to(target)
        with self.assertRaises(OSError):
            self.read()

    def test_hardlink(self):
        os.link(self.path, self.base / 'second-link')
        with self.assertRaises(ValueError):
            self.read()

    def test_large_file(self):
        self.path.write_bytes(b' ' * 65537)
        with self.assertRaises(ValueError):
            self.read()

    def test_FIFO_cannot_block(self):
        self.path.unlink()
        os.mkfifo(self.path, 0o600)
        with self.assertRaises(ValueError):
            self.read()

    def test_parent_symlink(self):
        renamed = self.base.with_name('real')
        self.base.rename(renamed)
        self.base.symlink_to(renamed, target_is_directory=True)
        with self.assertRaises(OSError):
            self.read()


if __name__ == '__main__':
    unittest.main()
