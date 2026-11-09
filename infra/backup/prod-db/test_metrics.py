#!/usr/bin/env python3
"""Pure IO/systemctl mocks; never imports or runs the host collector."""
import ast
import copy
import datetime
import json
import subprocess
import sys
import types
import unittest
from pathlib import Path
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
TREE = ast.parse((HERE/'metrics-block.py.txt').read_text())
# Remove only the explicit collector integration call, retain actual functions.
assert isinstance(TREE.body[-1], ast.Expr) and isinstance(TREE.body[-1].value, ast.Call)
assert TREE.body[-1].value.func.id == '_pdb_emit'
TREE.body.pop()
NS = {'_db_read_json': lambda *a, **k: (_ for _ in ()).throw(AssertionError('real IO forbidden'))}
exec(compile(TREE, 'actual-metrics-block', 'exec'), NS)
NOW = 1800000000.0

def stamp(seconds):
    return datetime.datetime.fromtimestamp(seconds, datetime.timezone.utc).isoformat()
POLICY = json.loads((HERE/'policy-host.json').read_text())
STATE = {'version': 1, 'source_vmid': 200, 'databases': ['nacos_prod'],
         'status': 'success', 'run_id': 'a'*32, 'started_at': stamp(NOW-60),
         'finished_at': stamp(NOW-30), 'last_success_timestamp': NOW-30,
         'last_run_success': 1, 'archive_bytes': 1024}
OLD = ['dell_pve_local_backup_enabled 0.0', 'dell_pve_local_backup_state_valid 1.0']

class MetricsTests(unittest.TestCase):
    def collect(self, state=None, policy=None, prior_lines=None, responses=None, command=None, clock=None, worker=None):
        data = {'/etc/dell-prod-db-backup/policy.json': copy.deepcopy(policy if policy is not None else POLICY),
                '/var/lib/dell-prod-db-backup/status.json': copy.deepcopy(state if state is not None else STATE)}
        reads, calls = [], []
        def reader(path):
            reads.append(path)
            if isinstance(data[path], Exception): raise data[path]
            return data[path]
        if worker is None:
            running = isinstance(data['/var/lib/dell-prod-db-backup/status.json'], dict) and data['/var/lib/dell-prod-db-backup/status.json'].get('status') == 'running'
            worker = ('ActiveState=active\nSubState=running\nResult=success\nExecMainStatus=0\n' if running else 'ActiveState=inactive\nSubState=dead\nResult=success\nExecMainStatus=0\n')
        replies = iter((responses or [(0, 'enabled\n'), (0, 'active\n')]) + [(0, worker)])
        def mocked(args, **kwargs):
            calls.append((args, kwargs))
            self.assertEqual(args[:1], ['systemctl'])
            if args[1] == 'show':
                self.assertEqual(args[2:], ['dell-prod-db-backup.service', '--property=ActiveState,SubState,Result,ExecMainStatus'])
            else: self.assertEqual(args[2:], ['dell-prod-db-backup.timer'])
            self.assertGreater(kwargs['timeout'], 0)
            self.assertLessEqual(kwargs['timeout'], 8)
            code, text = next(replies)
            return types.SimpleNamespace(returncode=code, stdout=text)
        result = NS['_pdb_collect'](read_json=reader, command=command or mocked, now=NOW,
                                    monotonic=clock or (lambda: 10.0),
                                    prior_lines=OLD if prior_lines is None else prior_lines)
        self.assertEqual(set(reads), set(data))
        return result

    def test_success_enabled(self):
        self.assertEqual(self.collect(), {'enabled': 1, 'state_valid': 1, 'running': 0,
                                         'last_run_success': 1, 'last_success_timestamp_seconds': NOW-30,
                                         'archive_bytes': 1024})

    def test_disabled_and_inactive_not_invalid(self):
        result = self.collect(responses=[(1, 'disabled\n'), (3, 'inactive\n')])
        self.assertEqual((result['enabled'], result['state_valid']), (0, 1))

    def test_enabled_timer_inactive_reports_disabled(self):
        self.assertEqual(self.collect(responses=[(0, 'enabled\n'), (3, 'inactive\n')])['enabled'], 0)

    def test_running_keeps_previous_success(self):
        state = {**STATE, 'status': 'running', 'started_at': stamp(NOW-5)}
        state.pop('finished_at')
        result = self.collect(state=state)
        self.assertEqual(result['running'], 1)
        self.assertEqual(result['last_run_success'], 1)
        self.assertEqual(result['last_success_timestamp_seconds'], NOW-30)

    def test_running_keeps_previous_failure(self):
        state = {**STATE, 'status': 'running', 'started_at': stamp(NOW-5), 'last_run_success': 0}
        state.pop('finished_at')
        result = self.collect(state=state)
        self.assertEqual((result['running'], result['last_run_success']), (1, 0))
        self.assertEqual(result['last_success_timestamp_seconds'], NOW-30)

    def test_initial_running_no_success(self):
        state = {**STATE, 'status': 'running', 'last_success_timestamp': 0,
                 'last_run_success': 0, 'archive_bytes': 0}
        state.pop('finished_at')
        self.assertEqual(self.collect(state=state)['state_valid'], 1)

    def test_old_success_new_failure_is_not_success(self):
        state = {**STATE, 'status': 'failed', 'last_run_success': 0,
                 'started_at': stamp(NOW-10), 'finished_at': stamp(NOW-1)}
        result = self.collect(state=state)
        self.assertEqual(result['last_run_success'], 0)
        self.assertEqual(result['last_success_timestamp_seconds'], NOW-30)

    def test_bad_states_and_types(self):
        for key, value in [('version', True), ('version', 2), ('source_vmid', 201),
                           ('databases', ['nacos_prod', 'mysql']), ('status', 'verified'),
                           ('run_id', '../escape'), ('last_run_success', True),
                           ('last_run_success', 2), ('archive_bytes', True),
                           ('archive_bytes', -1), ('archive_bytes', 1073741825),
                           ('last_success_timestamp', '1800000000'),
                           ('last_success_timestamp', float('nan')),
                           ('last_success_timestamp', float('inf'))]:
            with self.subTest(key=key, value=value), self.assertRaises((ValueError, TypeError)):
                self.collect(state={**STATE, key: value})

    def test_missing_required_state(self):
        for key in STATE:
            state = dict(STATE); state.pop(key)
            with self.subTest(key=key), self.assertRaises((ValueError, TypeError, KeyError)):
                self.collect(state=state)

    def test_future_clock_bound(self):
        for key, value in [('started_at', stamp(NOW+61)), ('finished_at', stamp(NOW+61)),
                           ('last_success_timestamp', NOW+61)]:
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.collect(state={**STATE, key: value})

    def test_UTC_order_and_naive_dates_rejected(self):
        for patch in [{'started_at': '2026-01-01T00:00:00'},
                      {'started_at': '2026-01-01T08:00:00+08:00'},
                      {'finished_at': stamp(NOW-61)},
                      {'status': 'running'}]:
            with self.subTest(patch=patch), self.assertRaises(ValueError):
                self.collect(state={**STATE, **patch})

    def test_success_cannot_be_empty_or_failed(self):
        for patch in [{'last_success_timestamp': 0}, {'last_run_success': 0}, {'archive_bytes': 0},
                      {'status': 'failed'}]:
            with self.subTest(patch=patch), self.assertRaises(ValueError):
                self.collect(state={**STATE, **patch})

    def test_policy_extra_database_and_drift(self):
        for patch in [{'databases': ['nacos_prod', 'finger_prod']}, {'vmid': 201},
                      {'whole_VM_backup': True}, {'independent_destination': True},
                      {'backup_root': '/tmp/backup'}, {'state_dir': '/var/lib/wrong'},
                      {'filesystem_uuid': 'different'}, {'maximum_archive_bytes': 1073741825}]:
            with self.subTest(patch=patch), self.assertRaises(ValueError):
                self.collect(policy={**POLICY, **patch})

    def test_old_job_enabled_or_unknown_does_not_prove_disabled(self):
        for old in [[], ['dell_pve_local_backup_enabled 0'],
                    ['dell_pve_local_backup_enabled 1', OLD[1]],
                    [OLD[0], 'dell_pve_local_backup_state_valid 0'],
                    [OLD[0], OLD[0], OLD[1]],
                    ['dell_pve_local_backup_enabled NaN', OLD[1]]]:
            with self.subTest(old=old), self.assertRaises(ValueError): self.collect(prior_lines=old)

    def test_systemctl_timeout_and_unknown_fail_closed(self):
        for replies in [[(1, 'enabled'), (0, 'active')], [(0, 'enabled-runtime'), (0, 'active')],
                        [(0, 'enabled'), (4, 'unknown')], [(0, 'enabled'), (0, 'activating')]]:
            with self.subTest(replies=replies), self.assertRaises(ValueError): self.collect(responses=replies)
        def timeout(*args, **kwargs): raise subprocess.TimeoutExpired(args[0], kwargs['timeout'])
        with self.assertRaises(subprocess.TimeoutExpired): self.collect(command=timeout)

    def test_total_deadline_not_two_independent20s_calls(self):
        times = iter([0, 0, 19])
        with self.assertRaises(ValueError): self.collect(clock=lambda: next(times))

    def test_read_error_safe_defaults_and_no_secret_output(self):
        records = []
        def broken(): raise PermissionError('SECRET_PATH_PASSWORD_SHOULD_NOT_APPEAR')
        NS['_pdb_emit'](lambda name, value: records.append((name, value)), collect=broken)
        self.assertEqual(dict(records), {'dell_prod_db_backup_'+key: value
                                         for key, value in NS['_PDB_DEFAULTS'].items()})
        self.assertNotIn('SECRET', repr(records))
        self.assertEqual(len(records), 6)

    def test_actual_IO_errors_go_to_defaults(self):
        for error in [PermissionError(), FileNotFoundError(), ValueError('bad JSON')]:
            records = []
            NS['_pdb_emit'](lambda n, v: records.append((n, v)),
                            collect=lambda error=error: self.collect(state=error))
            self.assertEqual(dict(records)['dell_prod_db_backup_state_valid'], 0)

    def test_failed_worker_overrides_old_success(self):
        for worker in ['ActiveState=failed\nSubState=failed\nResult=timeout\nExecMainStatus=15\n',
                       'ActiveState=inactive\nSubState=dead\nResult=signal\nExecMainStatus=0\n',
                       'ActiveState=inactive\nSubState=dead\nResult=success\nExecMainStatus=1\n']:
            result = self.collect(worker=worker)
            self.assertEqual((result['state_valid'], result['running'], result['last_run_success']), (1, 0, 0))
            self.assertEqual(result['last_success_timestamp_seconds'], NOW-30)

    def test_timedout_worker_overrides_stale_running(self):
        state = {**STATE, 'status': 'running', 'started_at': stamp(NOW-5)}
        state.pop('finished_at')
        result = self.collect(state=state, worker='ActiveState=failed\nSubState=failed\nResult=timeout\nExecMainStatus=15\n')
        self.assertEqual((result['running'], result['last_run_success']), (0, 0))

    def test_inactive_worker_cannot_prove_running_even_exit0(self):
        state = {**STATE, 'status': 'running', 'started_at': stamp(NOW-5)}
        state.pop('finished_at')
        result = self.collect(state=state, worker='ActiveState=inactive\nSubState=dead\nResult=success\nExecMainStatus=0\n')
        self.assertEqual((result['running'], result['last_run_success']), (0, 0))

    def test_activating_worker_retains_prior_completed_result(self):
        state = {**STATE, 'status': 'running', 'started_at': stamp(NOW-5)}
        state.pop('finished_at')
        result = self.collect(state=state, worker='ActiveState=activating\nSubState=start\nResult=success\nExecMainStatus=0\n')
        self.assertEqual((result['running'], result['last_run_success']), (1, 1))

    def test_bad_worker_metadata_rejected(self):
        for worker in ['ActiveState=inactive\n',
                       'ActiveState=failed\nActiveState=active\nSubState=running\nResult=success\nExecMainStatus=0\n',
                       'ActiveState=active\nSubState=running\nResult=success\nExecMainStatus=nan\n']:
            with self.subTest(worker=worker), self.assertRaises(ValueError): self.collect(worker=worker)

    def test_worker_show_shares_total_deadline(self):
        times = iter([0, 0, 0, 1, 2, 3, 19])
        with self.assertRaises(ValueError): self.collect(clock=lambda: next(times))

    def test_invalid_metadata_preserves_prior_collector_output(self):
        prior = [('dell_pve_raid_virtual_optimal', 1)]
        def broken(): raise ValueError('secret details withheld')
        NS['_pdb_emit'](lambda n, v: prior.append((n, v)), collect=broken)
        self.assertEqual(prior[0], ('dell_pve_raid_virtual_optimal', 1))
        self.assertEqual(len(prior), 7)
        self.assertEqual(dict(prior)['dell_prod_db_backup_state_valid'], 0)

    def test_only_six_unlabelled_metrics(self):
        records = []
        NS['_pdb_emit'](lambda n, v: records.append((n, v)), collect=self.collect)
        self.assertEqual(len(records), 6)
        self.assertTrue(all(name.startswith('dell_prod_db_backup_') and '{' not in name for name, _ in records))
        self.assertTrue(all(type(value) in (int, float) for _, value in records))

if __name__ == '__main__': unittest.main()
