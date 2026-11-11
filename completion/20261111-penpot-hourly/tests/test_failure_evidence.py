"""Offline candidate diagnostics: temporary files and mocked Docker only."""
import ast
import copy
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import signal
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('hourly_evidence_candidate', ROOT / 'candidate/supervisor.py')
s = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(s)


def fixture():
    lock = {'services': {}}
    frame = {}
    for name in s.EXPECTED:
        lock['services'][name] = {'image_id': 'sha256:fixed', 'pids_limit_proposed': 128,
                                 'memory_bytes': 256 * 1024**2, 'nano_cpus': 10**9,
                                 'expected_mounts': [], 'container_name': 'penpot-' + name + '-1'}
        frame[name] = {'image': 'sha256:fixed', 'pids': 128, 'memory': 256 * 1024**2,
                       'nano_cpus': 10**9, 'restart': 'no', 'mounts': [], 'running': True,
                       'status': 'running', 'oom': False, 'health': 'healthy', 'failing_streak': 0}
    lock['services']['penpot-dns']['require_init'] = True
    frame['penpot-dns']['init'] = True
    return lock, frame


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.directory = self.root / 'evidence'
        self.uid_patch = patch.object(s, 'EVIDENCE_UID', os.getuid())
        self.dir_patch = patch.object(s, 'EVIDENCE_DIR', self.directory)
        self.uid_patch.start(); self.dir_patch.start()
        self.addCleanup(self.uid_patch.stop); self.addCleanup(self.dir_patch.stop)

    def record(self, error, frame=None, observed='2026-11-11T06:00:00Z'):
        journal = io.StringIO()
        with patch.object(s.sys, 'stderr', journal):
            s.record_failure(error, frame, observed)
        return journal.getvalue()

    def records(self):
        return [json.loads(line) for line in (self.directory / 'failures.jsonl').read_text().splitlines()]

    def test_metadata_only_record_and_minimal_journal(self):
        _, frame = fixture()
        frame['penpot-worker'].update(health='unhealthy', failing_streak=7)
        frame['penpot-postgres'].update(oom=True, running=False, status='exited')
        frame['penpot-worker'].update(Env=['password=must-never-appear'],
                                     mounts=[{'source': 'token=must-never-appear'}],
                                     command='password=must-never-appear', health_response='must-never-appear')
        frame['unknown-service-secret'] = {'password': 'must-never-appear'}
        journal = self.record(s.Failure('consecutive-health-failure'), frame)
        record = self.records()[0]
        self.assertEqual(record['reason'], 'consecutive-health-failure')
        self.assertEqual(record['error_category'], 'Failure')
        self.assertEqual(set(record['services']), s.EXPECTED)
        self.assertEqual(record['services']['penpot-worker']['failing_streak'], 7)
        self.assertEqual(record['failed_services'], ['penpot-postgres', 'penpot-worker'])
        self.assertEqual(set(record['services']['penpot-worker']),
                         {'running', 'status', 'health', 'oom', 'failing_streak'})
        self.assertNotIn('must-never-appear', json.dumps(record) + journal)
        self.assertNotIn('unknown-service-secret', json.dumps(record) + journal)
        summary = json.loads(journal)
        self.assertNotIn('services', summary)
        self.assertEqual(summary['failed_services'], record['failed_services'])
        self.assertEqual(self.directory.stat().st_mode & 0o777, 0o700)
        self.assertEqual((self.directory / 'failures.jsonl').stat().st_mode & 0o777, 0o600)

    def test_non_failure_messages_are_never_formatted_or_persisted(self):
        class NoStringError(RuntimeError):
            def __str__(self):
                raise AssertionError('exception string must not be evaluated')
        _, frame = fixture()
        journal = self.record(NoStringError('password=not-a-reason-code'), frame)
        record = self.records()[0]
        self.assertEqual(record['error_category'], 'NoStringError')
        self.assertEqual(record['reason'], 'details-suppressed')
        self.assertNotIn('not-a-reason-code', journal + json.dumps(record))

    def test_unrecognized_failure_reason_and_untrusted_status_are_suppressed(self):
        _, frame = fixture()
        frame['penpot-frontend'].update(status='password=hidden', health='token=hidden',
                                       failing_streak='password=hidden', running='secret', oom='secret')
        journal = self.record(s.Failure('password=hidden'), frame, 'token=hidden')
        record = self.records()[0]
        self.assertEqual(record['reason'], 'unrecognized-failure-code')
        self.assertIsNone(record['frame_observed_at_utc'])
        self.assertEqual(record['services']['penpot-frontend'],
                         {'running': None, 'status': 'unknown', 'health': None,
                          'oom': None, 'failing_streak': None})
        self.assertNotIn('hidden', json.dumps(record) + journal)
        self.assertNotIn('secret', json.dumps(record) + journal)

    def test_unobserved_and_missing_services_are_not_confused(self):
        self.record(s.Failure('fixed-command-failed'))
        first = self.records()[0]
        self.assertFalse(first['frame_available'])
        self.assertEqual(first['failed_services'], [])
        _, frame = fixture(); frame.pop('penpot-dns')
        self.record(s.Failure('required-service-missing'), frame)
        second = self.records()[1]
        self.assertTrue(second['frame_available'])
        self.assertEqual(second['failed_services'], ['penpot-dns'])
        self.assertEqual(second['services']['penpot-dns']['status'], 'missing')

    def test_three_file_rotation_is_size_bounded_and_keeps_other_logs(self):
        _, frame = fixture()
        self.record(s.Failure('fixed-command-failed'), frame)
        unrelated = self.directory / 'unrelated.log'
        unrelated.write_text('retain-this-log')
        with patch.object(s, 'LEDGER_MAX_BYTES', 2200):
            for _ in range(10):
                self.record(s.Failure('fixed-command-failed'), frame)
            ledgers = sorted(self.directory.glob('failures.jsonl*'))
            self.assertEqual([path.name for path in ledgers], sorted(s.LEDGER_NAMES))
            self.assertTrue(all(path.stat().st_size <= 2200 for path in ledgers))
            self.assertTrue(all(path.stat().st_mode & 0o777 == 0o600 for path in ledgers))
            self.assertTrue(all(json.loads(line) for path in ledgers for line in path.read_text().splitlines()))
        self.assertEqual(unrelated.read_text(), 'retain-this-log')

    def test_directory_symlink_is_rejected_without_touching_target(self):
        target = self.root / 'outside'; target.mkdir(mode=0o700)
        self.directory.symlink_to(target, target_is_directory=True)
        journal = self.record(s.Failure('fixed-command-failed'))
        self.assertEqual(list(target.iterdir()), [])
        self.assertIn('failure-evidence-write-failed', journal)

    def test_ledger_or_archive_symlinks_are_rejected(self):
        self.directory.mkdir(mode=0o700)
        outside = self.root / 'do-not-modify'
        outside.write_text('private-content'); outside.chmod(0o600)
        for name in ('failures.jsonl', 'failures.jsonl.1'):
            with self.subTest(name=name):
                link = self.directory / name
                link.symlink_to(outside)
                journal = self.record(s.Failure('fixed-command-failed'))
                self.assertIn('failure-evidence-write-failed', journal)
                self.assertEqual(outside.read_text(), 'private-content')
                link.unlink()

    def test_mode_owner_hardlink_and_size_guards_do_not_repair_unknown_files(self):
        self.directory.mkdir(mode=0o755)
        self.assertIn('failure-evidence-write-failed', self.record(s.Failure('fixed-command-failed')))
        self.assertEqual(self.directory.stat().st_mode & 0o777, 0o755)
        self.directory.chmod(0o700)
        with patch.object(s, 'EVIDENCE_UID', os.getuid() + 10000):
            self.assertIn('failure-evidence-write-failed', self.record(s.Failure('fixed-command-failed')))
        path = self.directory / 'failures.jsonl'
        path.write_text('retain'); path.chmod(0o644)
        self.assertIn('failure-evidence-write-failed', self.record(s.Failure('fixed-command-failed')))
        self.assertEqual(path.read_text(), 'retain')
        path.chmod(0o600)
        alias = self.root / 'hardlink'; os.link(path, alias)
        self.assertIn('failure-evidence-write-failed', self.record(s.Failure('fixed-command-failed')))
        self.assertEqual(alias.read_text(), 'retain')
        alias.unlink()
        path.write_bytes(b'x' * (s.LEDGER_MAX_BYTES + 1))
        self.assertIn('failure-evidence-write-failed', self.record(s.Failure('fixed-command-failed')))
        self.assertEqual(path.stat().st_size, s.LEDGER_MAX_BYTES + 1)

    def test_partial_append_failure_restores_existing_ledger_bytes(self):
        self.record(s.Failure('fixed-command-failed'))
        ledger = self.directory / 'failures.jsonl'
        original = ledger.read_bytes()
        real_write = s.os.write
        writes = 0
        def broken_write(fd, body):
            nonlocal writes
            writes += 1
            if writes == 1:
                return real_write(fd, body[:len(body) // 2])
            raise OSError('password=must-never-log-disk-error')
        with patch.object(s.os, 'write', side_effect=broken_write):
            journal = self.record(s.Failure('fixed-command-failed'))
        self.assertIn('failure-evidence-write-failed', journal)
        self.assertNotIn('must-never-log-disk-error', journal)
        self.assertEqual(ledger.read_bytes(), original)

    def test_record_size_cap_refuses_output_before_creating_directory(self):
        with patch.object(s, 'LEDGER_MAX_RECORD_BYTES', 32):
            journal = self.record(s.Failure('fixed-command-failed'))
        self.assertIn('failure-evidence-write-failed', journal)
        self.assertFalse(self.directory.exists())

    def test_journal_failure_does_not_stop_ledger_attempt(self):
        class BrokenJournal:
            def write(self, value): raise OSError('no-journal')
            def flush(self): raise OSError('no-journal')
        with patch.object(s.sys, 'stderr', BrokenJournal()):
            s.record_failure(RuntimeError('must-not-be-printed'))
        self.assertEqual(self.records()[0]['reason'], 'details-suppressed')

    def lifecycle(self, error=None, writer=None, stop_signal=False, expect_ledger=True):
        lock, frame = fixture()
        sequence = []
        scanned = 0
        def scan():
            nonlocal scanned
            scanned += 1
            if scanned >= 3 and error is not None:
                if isinstance(error, s.Failure):
                    bad = copy.deepcopy(frame)
                    bad['penpot-worker'].update(health='unhealthy', failing_streak=3)
                    return bad
                raise error
            return frame
        def wait(_):
            if stop_signal:
                s.shutdown(signal.SIGTERM, None)
        def stop(_):
            sequence.append('stop')
            if error is not None and writer is None and expect_ledger:
                self.assertTrue((self.directory / 'failures.jsonl').exists())
            return True
        original = s.record_failure
        def record(*args):
            sequence.append('record')
            return original(*args)
        journal = io.StringIO()
        with patch.dict(os.environ, {'INVOCATION_ID': 'fixture', 'DELL_MOUNT_GATED': '1', 'NOTIFY_SOCKET': 'fixture'}), \
             patch.object(s, 'SHUTDOWN', False), patch.object(s, 'guest_guard'), patch.object(s, 'storage_guard'), \
             patch.object(s, 'verify_files_and_images'), patch.object(s, 'check_config'), \
             patch.object(s, 'run'), patch.object(s, 'notify'), patch.object(s, 'state') as state, \
             patch.object(s, 'scan', side_effect=scan), patch.object(s, 'wait_tick', side_effect=wait), \
             patch.object(s, 'stop_group', side_effect=stop) as stopped, \
             patch.object(s, 'record_failure', side_effect=record) as recorder, \
             patch.object(s.sys, 'stderr', journal):
            if writer is None:
                code = s.supervise(lock)
            else:
                with patch.object(s, '_append_failure_record', side_effect=writer):
                    code = s.supervise(lock)
            self.assertEqual(stopped.call_count, 1)
            state_calls = state.call_args_list
        return code, sequence, recorder.call_count, state_calls, journal.getvalue()

    def test_record_is_before_stop_and_original_three_bad_threshold_is_kept(self):
        code, events, calls, states, journal = self.lifecycle(s.Failure('consecutive-health-failure'))
        self.assertEqual(code, 1)
        self.assertEqual(events, ['record', 'stop'])
        self.assertEqual(calls, 1)
        self.assertEqual(self.records()[0]['reason'], 'consecutive-health-failure')
        self.assertEqual(self.records()[0]['failed_services'], ['penpot-worker'])
        self.assertEqual(self.records()[0]['services']['penpot-worker']['failing_streak'], 3)
        self.assertEqual(states[-1].kwargs['reason'], 'consecutive-health-failure')

    def test_writer_failure_preserves_reason_exit_and_stop(self):
        code, events, calls, states, journal = self.lifecycle(s.Failure('consecutive-health-failure'),
                                                           PermissionError('password=do-not-log'))
        self.assertEqual(code, 1)
        self.assertEqual(events, ['record', 'stop'])
        self.assertEqual(states[-1].kwargs['reason'], 'consecutive-health-failure')
        self.assertIn('failure-evidence-write-failed', journal)
        self.assertNotIn('do-not-log', journal)

    def test_symlink_rejection_still_follows_original_stop_behavior(self):
        outside = self.root / 'outside'; outside.mkdir(mode=0o700)
        self.directory.symlink_to(outside, target_is_directory=True)
        code, events, calls, states, journal = self.lifecycle(s.Failure('consecutive-health-failure'),
                                                           writer=None, expect_ledger=False)
        self.assertEqual(code, 1)
        self.assertEqual(events, ['record', 'stop'])
        self.assertEqual(list(outside.iterdir()), [])
        self.assertIn('failure-evidence-write-failed', journal)

    def test_non_failure_lifecycle_does_not_publish_raw_error(self):
        code, events, calls, states, journal = self.lifecycle(RuntimeError('Bearer must-not-leak'))
        self.assertEqual(code, 1)
        self.assertEqual(states[-1].kwargs['reason'], 'details-suppressed')
        self.assertNotIn('must-not-leak', journal + (self.directory / 'failures.jsonl').read_text())

    def test_clean_SIGTERM_creates_no_failure_record(self):
        code, events, calls, states, journal = self.lifecycle(stop_signal=True)
        self.assertEqual(code, 0)
        self.assertEqual(events, ['stop'])
        self.assertEqual(calls, 0)
        self.assertFalse(self.directory.exists())
        self.assertEqual(journal, '')


class DnsInitPolicyTests(unittest.TestCase):
    def test_DNS_runtime_init_is_true_in_both_startup_and_running_frames(self):
        lock, frame = fixture()
        self.assertTrue(s.validate_frame(frame, lock, starting=True))
        self.assertTrue(s.validate_frame(frame, lock))
        for value in ('missing', False, None, 1, 'true'):
            for startup in (False, True):
                bad = copy.deepcopy(frame)
                if value == 'missing':
                    bad['penpot-dns'].pop('init')
                else:
                    bad['penpot-dns']['init'] = value
                with self.subTest(value=value, startup=startup), self.assertRaisesRegex(s.Failure, '^DNS-init-reaper-required$'):
                    s.validate_frame(bad, lock, starting=startup)

    def test_non_DNS_init_values_have_no_new_constraint(self):
        lock, frame = fixture()
        for name in frame:
            if name == 'penpot-dns':
                continue
            for value in (False, None, True, 'unchanged-policy'):
                frame[name]['init'] = value
                with self.subTest(service=name, value=value):
                    self.assertTrue(s.validate_frame(frame, lock))
            frame[name].pop('init')
        self.assertTrue(s.validate_frame(frame, lock))

    def test_load_lock_requires_exact_true_DNS_policy(self):
        lock, _ = fixture()
        lock['guest'] = {'vmid': 250, 'hostname': 'penpot-service', 'ip': '192.168.19.50', 'arch': 'amd64'}
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'lock.json'
            with patch.object(s, 'LOCK', path), patch.object(s, 'owned', side_effect=lambda value, *args: value):
                path.write_text(json.dumps(lock))
                self.assertIs(s.load_lock()['services']['penpot-dns']['require_init'], True)
                for value in ('missing', False, None, 1, 'true'):
                    bad = copy.deepcopy(lock)
                    if value == 'missing':
                        bad['services']['penpot-dns'].pop('require_init')
                    else:
                        bad['services']['penpot-dns']['require_init'] = value
                    path.write_text(json.dumps(bad))
                    with self.subTest(value=value), self.assertRaisesRegex(s.Failure, '^DNS-init-reaper-required$'):
                        s.load_lock()

    def test_DNS_policy_reason_is_safe_and_diagnostic_names_the_offender(self):
        _, frame = fixture()
        frame['penpot-dns']['init'] = False
        self.assertIn('DNS-init-reaper-required', s.FAILURE_CODES)
        self.assertEqual(s._failure_fields(s.Failure('DNS-init-reaper-required'))['reason'], 'DNS-init-reaper-required')
        safe, failed, available = s._safe_services(frame)
        self.assertTrue(available)
        self.assertEqual(failed, ['penpot-dns'])
        self.assertNotIn('init', safe['penpot-dns'])


class BaselineSafetyTests(unittest.TestCase):
    def test_actual_baseline_is_exact_captured_source(self):
        self.assertEqual(hashlib.sha256((ROOT / 'baseline/supervisor.py').read_bytes()).hexdigest(),
                         'fdd384bf5470890eb1802cc2eacb49bcc0c0d96013cfe57b257c5021af3b0448')

    def test_guard_validation_monitor_and_remediation_functions_are_unchanged(self):
        before = {node.name: node for node in ast.parse((ROOT / 'baseline/supervisor.py').read_text()).body
                  if isinstance(node, (ast.FunctionDef, ast.ClassDef))}
        after = {node.name: node for node in ast.parse((ROOT / 'candidate/supervisor.py').read_text()).body
                 if isinstance(node, (ast.FunctionDef, ast.ClassDef))}
        names = ['load_lock', 'guest_guard', 'validate_storage', 'storage_guard', 'validate_image_metadata',
                 'verify_files_and_images', 'compose', 'check_config', 'validate_frame', 'Monitor',
                 'stop_group', 'wait_tick', 'shutdown', 'main']
        lock_addition = ast.parse("if lock['services']['penpot-dns'].get('require_init') is not True: raise Failure('DNS-init-reaper-required')").body[0]
        frame_addition = ast.parse("if name=='penpot-dns' and c.get('init') is not True: raise Failure('DNS-init-reaper-required')").body[0]
        for name in names:
            with self.subTest(function=name):
                candidate = copy.deepcopy(after[name])
                if name == 'load_lock':
                    matches = [item for item in candidate.body if ast.dump(item) == ast.dump(lock_addition)]
                    self.assertEqual(len(matches), 1)
                    candidate.body = [item for item in candidate.body if ast.dump(item) != ast.dump(lock_addition)]
                elif name == 'validate_frame':
                    loops = [item for item in candidate.body if isinstance(item, ast.For)]
                    self.assertEqual(len(loops), 1)
                    matches = [item for item in loops[0].body if ast.dump(item) == ast.dump(frame_addition)]
                    self.assertEqual(len(matches), 1)
                    loops[0].body = [item for item in loops[0].body if ast.dump(item) != ast.dump(frame_addition)]
                self.assertEqual(ast.dump(before[name]), ast.dump(candidate))

    def test_scan_uses_safe_optional_Init_lookup_for_existing_containers(self):
        from types import SimpleNamespace
        for host_config in ({}, {'Init': None}, {'Init': True}):
            def docker(*args, **kwargs):
                if args[0] == 'ps':
                    return SimpleNamespace(stdout='existing-container')
                template = args[2]
                self.assertIn('{{json (index .HostConfig "Init")}}', template)
                self.assertNotIn('{{json .HostConfig.Init}}', template)
                # Native Docker optional-key behavior is separately verified by
                # the parent. This fixture locks the safe template and JSON path.
                return SimpleNamespace(stdout=json.dumps({'name': '/penpot-penpot-dns-1',
                    'status': 'exited', 'running': False, 'health': None, 'oom': False,
                    'failing_streak': 0, 'init': host_config.get('Init')}))
            with self.subTest(host_config=host_config), patch.object(s, 'docker', side_effect=docker):
                self.assertIs(s.scan()['penpot-dns']['init'], host_config.get('Init'))

    def test_scan_adds_only_failure_streak_and_init_metadata(self):
        fmt = []
        def docker(*args, **kwargs):
            from types import SimpleNamespace
            if args[0] == 'ps':
                return SimpleNamespace(stdout='fixture-id')
            fmt.append(args[2])
            return SimpleNamespace(stdout=json.dumps({'name': '/penpot-penpot-worker-1',
                'running': True, 'status': 'running', 'health': 'healthy', 'oom': False, 'failing_streak': 4, 'init': False}))
        with patch.object(s, 'docker', side_effect=docker):
            result = s.scan()['penpot-worker']
            self.assertEqual(result['failing_streak'], 4)
            self.assertFalse(result['init'])
        self.assertIn('.State.Health.FailingStreak', fmt[0])
        self.assertIn('(index .HostConfig \"Init\")', fmt[0])
        self.assertNotIn('{{json .HostConfig.Init}}', fmt[0])
        before = next(node for node in ast.parse((ROOT / 'baseline/supervisor.py').read_text()).body
                      if isinstance(node, ast.FunctionDef) and node.name == 'scan')
        candidate = next(node for node in ast.parse((ROOT / 'candidate/supervisor.py').read_text()).body
                         if isinstance(node, ast.FunctionDef) and node.name == 'scan')
        old_fmt = next(node for node in before.body if isinstance(node, ast.Assign)
                       and any(isinstance(target, ast.Name) and target.id == 'fmt' for target in node.targets))
        new_fmt = next(node for node in candidate.body if isinstance(node, ast.Assign)
                       and any(isinstance(target, ast.Name) and target.id == 'fmt' for target in node.targets))
        permitted = ('\"failing_streak\":{{if (index .State \"Health\")}}{{json .State.Health.FailingStreak}}{{else}}0{{end}},',
                     '\"init\":{{json (index .HostConfig \"Init\")}},')
        value = new_fmt.value.value
        for field in permitted:
            self.assertEqual(value.count(field), 1)
            value = value.replace(field, '', 1)
        self.assertEqual(value, old_fmt.value.value)
        new_fmt.value = copy.deepcopy(old_fmt.value)
        self.assertEqual(ast.dump(candidate), ast.dump(before))


if __name__ == '__main__':
    unittest.main()
