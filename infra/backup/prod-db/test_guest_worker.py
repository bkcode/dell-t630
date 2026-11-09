#!/usr/bin/env python3
"""Offline only: synthetic streams/metadata and mock clients, never MySQL/Docker."""
import contextlib
import copy
import gzip
import importlib.util
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import tempfile
import time
import types
import unittest
from unittest.mock import Mock, patch

spec = importlib.util.spec_from_file_location('prod_db_worker', Path(__file__).with_name('guest-worker.py'))
w = importlib.util.module_from_spec(spec)
spec.loader.exec_module(w)
RUN = 'a' * 32
POLICY = {'schema_version': 1, 'databases': ['nacos_prod'], 'nacos_database': 'nacos_prod',
          'expected_mysql_container': 'dell-data-prod-db-mysql-1',
          'expected_compose_project': 'dell-data-prod-db', 'data_uuid': w.UUID,
          'staging_root': w.STAGING, 'max_archive_bytes': w.MAX_BYTES}
IDENTITY = {'Id': 'b' * 64, 'Name': '/dell-data-prod-db-mysql-1',
            'State': {'Status': 'running', 'Health': 'healthy', 'StartedAt': 'fixed', 'Pid': 500},
            'RestartCount': 0,
            'Labels': {'project': 'dell-data-prod-db', 'service': 'mysql'}}
SCHEMA = {'columns': ['table_schema', 'table_name', 'engine', 'table_type'],
          'sha256': 'c' * 64, 'table_counts': {'nacos_prod': 12},
          'programmable_objects': {'routines': 0, 'events': 0, 'triggers': 0}}


@contextlib.contextmanager
def synthetic_root_metadata():
    """Only UID is virtualized on a nonroot Mac; real mode/link/ino checks stay."""
    fstat, stat_fn = os.fstat, os.stat
    def rootify(s):
        values = list(s)
        values[4] = 0
        return os.stat_result(values)
    with patch.object(w.os, 'fstat', side_effect=lambda fd: rootify(fstat(fd))), \
         patch.object(w.os, 'stat', side_effect=lambda *a, **k: rootify(stat_fn(*a, **k))):
        yield


class PolicyTests(unittest.TestCase):
    def reject(self, update):
        p = copy.deepcopy(POLICY)
        update(p)
        with self.assertRaises(w.Rejected):
            w.validate_policy(p)

    def test_current_policy(self):
        self.assertEqual(w.validate_policy(POLICY), POLICY)

    def test_system_DB(self):
        self.reject(lambda p: p['databases'].append('mysql'))

    def test_test_DB(self):
        self.reject(lambda p: p['databases'].append('finger_test'))

    def test_fixture_DB(self):
        self.reject(lambda p: p['databases'].append('fixture_backup'))

    def test_SQL_identifier_injection(self):
        self.reject(lambda p: p['databases'].append("a'; DROP DATABASE x;"))

    def test_duplicate_database(self):
        self.reject(lambda p: p['databases'].append('nacos_prod'))

    def test_nacos_omitted(self):
        self.reject(lambda p: p.update(nacos_database='other'))

    def test_wrong_project(self):
        self.reject(lambda p: p.update(expected_compose_project='test-data'))

    def test_wrong_UUID(self):
        self.reject(lambda p: p.update(data_uuid='wrong'))

    def test_staging_escape(self):
        self.reject(lambda p: p.update(staging_root='/srv/dell-data/../../tmp'))

    def test_unknown_policy_key(self):
        self.reject(lambda p: p.update(password='MUST_NOT_READ'))

    def test_raise_limit(self):
        self.reject(lambda p: p.update(max_archive_bytes=w.MAX_BYTES + 1))


class ContainerTests(unittest.TestCase):
    def value(self):
        value = copy.deepcopy(IDENTITY)
        value['Mounts'] = [{'Type': 'bind', 'Source': w.DATA, 'Destination': '/var/lib/mysql', 'RW': True}]
        return value

    def inspect(self, value, expected=None):
        with patch.object(w, 'small_command', return_value=json.dumps(value).encode()):
            return w.inspect_container(POLICY, time.monotonic() + 10, expected)

    def test_current_container_selected_metadata(self):
        self.assertEqual(self.inspect(self.value()), IDENTITY)
        self.assertNotIn('.Config.Env', w.INSPECT_FORMAT)
        self.assertNotIn('.Config.Cmd', w.INSPECT_FORMAT)
        self.assertNotIn('.State.Health.Log', w.INSPECT_FORMAT)

    def test_wrong_compose_role(self):
        value = self.value()
        value['Labels']['project'] = 'dell-data-test-data'
        with self.assertRaises(w.Rejected):
            self.inspect(value)

    def test_wrong_service(self):
        value = self.value()
        value['Labels']['service'] = 'redis'
        with self.assertRaises(w.Rejected):
            self.inspect(value)

    def test_wrong_mount(self):
        value = self.value()
        value['Mounts'][0]['Source'] = '/tmp/root-fallback'
        with self.assertRaises(w.Rejected):
            self.inspect(value)

    def test_container_restart_during_export(self):
        value = self.value()
        value['RestartCount'] = 1
        with self.assertRaises(w.Rejected):
            self.inspect(value, IDENTITY)

    def test_unhealthy(self):
        value = self.value()
        value['State']['Health'] = 'unhealthy'
        with self.assertRaises(w.Rejected):
            self.inspect(value)


class SchemaTests(unittest.TestCase):
    def mysql(self, *, extra_DB=False, engine='InnoDB', kind='BASE TABLE', programmable=False):
        m = Mock()
        def query(sql):
            if sql == 'SHOW DATABASES;':
                return '\n'.join(sorted(w.SYSTEM_DATABASES | {'nacos_prod'} | ({'new_prod'} if extra_DB else set()))) + '\n'
            if 'JSON_ARRAY' in sql:
                return json.dumps(['nacos_prod', 'config_info', engine, kind]) + '\n'
            return '1\n' if programmable else '0\n'
        m.query.side_effect = query
        return m

    def test_only_fixed_metadata_no_row_counts(self):
        m = self.mysql()
        result = w.schema_manifest(m, ['nacos_prod'])
        self.assertEqual(result['table_counts'], {'nacos_prod': 1})
        sql = '\n'.join(c.args[0] for c in m.query.call_args_list)
        self.assertNotIn('TABLE_ROWS', sql)
        self.assertNotIn('DATA_LENGTH', sql)
        self.assertNotIn('SELECT *', sql)

    def test_new_database_rejected(self):
        with self.assertRaises(w.Rejected):
            w.schema_manifest(self.mysql(extra_DB=True), ['nacos_prod'])

    def test_non_InnoDB(self):
        with self.assertRaises(w.Rejected):
            w.schema_manifest(self.mysql(engine='MyISAM'), ['nacos_prod'])

    def test_view(self):
        with self.assertRaises(w.Rejected):
            w.schema_manifest(self.mysql(kind='VIEW'), ['nacos_prod'])

    def test_routine_event_or_trigger(self):
        with self.assertRaises(w.Rejected):
            w.schema_manifest(self.mysql(programmable=True), ['nacos_prod'])

    def test_JSON_control_char_table_name(self):
        m = self.mysql()
        original = m.query.side_effect
        m.query.side_effect = lambda sql: json.dumps(['nacos_prod', 'table\tline\n', 'InnoDB', 'BASE TABLE']) + '\n' if 'JSON_ARRAY' in sql else original(sql)
        self.assertEqual(w.schema_manifest(m, ['nacos_prod'])['table_counts']['nacos_prod'], 1)


class FakeChild:
    def __init__(self, code=None):
        self.returncode = code
        self.stdin = io.BytesIO()
        self.stdout = io.BytesIO()
    def poll(self):
        return self.returncode
    def wait(self, timeout=None):
        if self.returncode is None:
            self.returncode = 0
        return self.returncode
    def terminate(self):
        self.returncode = -15
    def kill(self):
        self.returncode = -9


class LockTests(unittest.TestCase):
    def mysql(self):
        m = Mock(deadline=time.monotonic() + 100)
        m.start.return_value = FakeChild()
        m.own_session_exists.return_value = False
        return m

    def test_capture_connection_before_LOCK_and_confirm_release(self):
        m = self.mysql()
        lock = w.BackupLock(m, RUN)
        with patch.object(lock, 'line', side_effect=['SESSION:77', 'LOCKED_' + RUN]):
            lock.acquire()
        sql = lock.child.stdin.getvalue().decode()
        self.assertLess(sql.index('CONNECTION_ID'), sql.index('LOCK INSTANCE'))
        lock.release()
        self.assertTrue(lock.released)
        self.assertTrue(lock.child.stdin.closed)
        m.own_session_exists.assert_called_with(77, release=True)

    def test_acquire_failure_releases_owned_session(self):
        m = self.mysql()
        lock = w.BackupLock(m, RUN)
        with patch.object(lock, 'line', side_effect=['SESSION:77', w.Rejected('lock-timeout')]):
            with self.assertRaises(w.Rejected):
                lock.acquire()
        self.assertTrue(lock.released)
        m.own_session_exists.assert_called_with(77, release=True)

    def test_unconfirmed_lock_release_is_failure(self):
        m = self.mysql()
        m.own_session_exists.return_value = True
        lock = w.BackupLock(m, RUN)
        lock.child, lock.connection, lock.acquired = FakeChild(), 77, True
        with self.assertRaises(w.Rejected):
            lock.release()
        m.query.assert_called_once_with('KILL CONNECTION 77;', release=True)
        self.assertFalse(lock.released)

    def test_kill_only_our_known_session(self):
        m = self.mysql()
        m.own_session_exists.side_effect = [True, False]
        lock = w.BackupLock(m, RUN)
        lock.child, lock.connection, lock.acquired = FakeChild(), 77, True
        lock.release()
        m.query.assert_called_once_with('KILL CONNECTION 77;', release=True)
        self.assertTrue(lock.released)

    def test_abnormal_client_exit_never_success(self):
        m = self.mysql()
        lock = w.BackupLock(m, RUN)
        lock.child, lock.connection, lock.acquired = FakeChild(1), 77, True
        with self.assertRaises(w.Rejected):
            lock.release()
        self.assertTrue(lock.released)  # server absence proved, export still fails

    def test_dead_lock_aborts_dump_before_reading_SQL(self):
        m = self.mysql()
        lock = w.BackupLock(m, RUN)
        lock.child, lock.connection, lock.acquired = FakeChild(1), 77, True
        with self.assertRaises(w.Rejected):
            lock.ensure_alive()

    def test_no_secret_values_in_host_argv(self):
        with patch.object(w.os, 'readlink', return_value='pid:[owned]'):
            m = w.Mysql(IDENTITY, time.monotonic() + 100)
        command = m.args(w.MYSQL)
        self.assertEqual(command[:3], w.DOCKER)
        self.assertIn('--skip-reconnect', command[-1])
        self.assertIn('MYSQL_PWD="$(cat /run/secrets/mysql-root-password)"', command[-1])
        self.assertNotIn('-pPASSWORD', ' '.join(command))


class DumpOwnershipTests(unittest.TestCase):
    def owner(self):
        m = Mock(container='b' * 64, pid_namespace='pid:[owned]', deadline=time.monotonic() + 100)
        with patch.object(w.os, 'pidfd_open', create=True), patch.object(w.signal, 'pidfd_send_signal', create=True):
            owner = w.DumpOwner(m, RUN, time.monotonic() + 70)
        owner.owner, owner.created = (77, 123), True
        return owner

    def test_timeout_parent_child_owner_and_shell_syntax(self):
        owner = self.owner()
        with patch.object(owner, 'read_owner', return_value=None):
            command = owner.command('mysqldump --databases nacos_prod')
        parts = w.shlex.split(command)
        self.assertEqual(parts[0], '/usr/bin/timeout')
        self.assertEqual(parts[-3:-1], ['sh', '-ec'])
        self.assertIn('cat /proc/$$/stat', parts[-1])
        self.assertIn('exec mysqldump', parts[-1])
        self.assertEqual(subprocess.run(['/bin/sh', '-n', '-c', parts[-1]],
                                       capture_output=True).returncode, 0)

    def test_pidfd_not_numeric_kill(self):
        owner = self.owner()
        with patch.object(owner, 'matches', side_effect=[[501], [501]]), \
             patch.object(w.os, 'pidfd_open', return_value=55, create=True) as opened, \
             patch.object(w.signal, 'pidfd_send_signal', create=True) as sent, \
             patch.object(w.os, 'close') as closed:
            owner.signal_owned(w.signal.SIGTERM)
        opened.assert_called_once_with(501)
        sent.assert_called_once_with(55, w.signal.SIGTERM)
        closed.assert_called_once_with(55)

    def test_PID_changed_before_signal_refused(self):
        owner = self.owner()
        with patch.object(owner, 'matches', side_effect=[[501], []]), \
             patch.object(w.os, 'pidfd_open', return_value=55, create=True), \
             patch.object(w.signal, 'pidfd_send_signal', create=True) as sent, \
             patch.object(w.os, 'close'):
            owner.signal_owned(w.signal.SIGTERM)
        sent.assert_not_called()

    def test_abort_TERM_then_KILL_confirm_before_remove(self):
        owner = self.owner()
        with patch.object(owner, 'matches', return_value=[501]), \
             patch.object(owner, 'signal_owned') as sent, \
             patch.object(owner, 'wait_gone', side_effect=[False, True]), \
             patch.object(owner, 'metadata', return_value='REMOVED') as metadata:
            owner.stop_and_remove()
        self.assertEqual([x.args[0] for x in sent.call_args_list], [w.signal.SIGTERM, w.signal.SIGKILL])
        self.assertFalse(owner.created)
        self.assertIn('rmdir', metadata.call_args.args[0])
        self.assertNotIn('rm -r', metadata.call_args.args[0])

    def test_cannot_confirm_dump_exit_refuses_success_and_keeps_marker(self):
        owner = self.owner()
        with patch.object(owner, 'matches', return_value=[501]), \
             patch.object(owner, 'signal_owned'), \
             patch.object(owner, 'wait_gone', return_value=False), \
             patch.object(owner, 'metadata') as metadata:
            with self.assertRaises(w.Rejected):
                owner.stop_and_remove()
        metadata.assert_not_called()
        self.assertTrue(owner.created)

    def test_unknown_owner_never_report_stopped(self):
        owner = self.owner()
        owner.owner = None
        with patch.object(owner, 'read_owner', return_value=None):
            with self.assertRaises(w.Rejected):
                owner.stop_and_remove()

    def matches(self, *, ns='pid:[owned]', nspid=77, start=123, comm='mysqldump'):
        owner = self.owner()
        fields = ['S'] + ['0'] * 18 + [str(start)]
        text = {'status': 'Name:\tmysqldump\nNSpid:\t501\t' + str(nspid) + '\n',
                'stat': '501 (' + comm + ') ' + ' '.join(fields), 'comm': comm + '\n'}
        class Entry:
            name = '501'
            def __truediv__(self, part):
                return types.SimpleNamespace(read_text=lambda: text[part])
        fake_root = types.SimpleNamespace(iterdir=lambda: [Entry()])
        with patch.object(w, 'Path', return_value=fake_root), patch.object(w.os, 'readlink', return_value=ns):
            return owner.matches()

    def test_exact_PID_namespace_starttime_comm(self):
        self.assertEqual(self.matches(), [501])

    def test_other_namespace_never_targeted(self):
        self.assertEqual(self.matches(ns='pid:[other]'), [])

    def test_reused_PID_starttime_never_targeted(self):
        self.assertEqual(self.matches(start=124), [])

    def test_timeout_parent_NSpid_never_targeted(self):
        self.assertEqual(self.matches(nspid=76), [])

    def test_mysqld_server_comm_never_targeted(self):
        with self.assertRaises(w.Rejected):
            self.matches(comm='mysqld')

    def test_dump_stream_failure_stops_owned_exec_not_only_docker_client(self):
        owner = Mock()
        owner.command.return_value = 'synthetic-only'
        owner.capture.side_effect = w.Rejected('fixture capture failure')
        child = FakeChild()
        m = Mock(deadline=time.monotonic() + 100)
        m.start.return_value = child
        with patch.object(w, 'DumpOwner', return_value=owner), patch.object(w, 'stop_child') as stop:
            with self.assertRaises(w.Rejected):
                w.dump_stream(m, Mock(), ['nacos_prod'], -1, 100, time.monotonic() + 50, run_id=RUN)
        owner.stop_and_remove.assert_called_once()
        stop.assert_called_once_with(child, m.deadline)


class FilesAndTransactions(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.parent = os.open(self.base, os.O_RDONLY | os.O_DIRECTORY)
        self.addCleanup(os.close, self.parent)
        self.deadline = time.monotonic() + 100
        self.lock = Mock(acquired=True, released=False, connection=77)
        self.lock.acquire.return_value = self.lock
        self.lock.release.side_effect = lambda: setattr(self.lock, 'released', True)
        self.mysql = Mock()
        self.mysql.own_session_exists.return_value = True

    def stream(self, mysql, lock, databases, fd, maximum, deadline, **kwargs):
        data = gzip.compress(b'-- synthetic SQL fixture only\n', mtime=0)
        os.write(fd, data)
        return len(data)

    def export(self, *, dump=None, schemas=None, release_error=False):
        if release_error:
            self.lock.release.side_effect = w.Rejected('unlock-failed')
        with synthetic_root_metadata(), \
             patch.object(w, 'inspect_container', return_value=IDENTITY), \
             patch.object(w, 'BackupLock', return_value=self.lock), \
             patch.object(w, 'schema_manifest', side_effect=schemas or [copy.deepcopy(SCHEMA), copy.deepcopy(SCHEMA)]), \
             patch.object(w, 'dump_stream', side_effect=dump or self.stream):
            return w.export_run(POLICY, RUN, self.parent, self.deadline,
                                mysql_factory=lambda *a: self.mysql)

    def test_success_private_two_file_manifest(self):
        result = self.export()
        path = self.base / RUN
        self.assertEqual(set(p.name for p in path.iterdir()), w.FILES)
        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o700)
        self.assertTrue(all(stat.S_IMODE(p.stat().st_mode) == 0o600 for p in path.iterdir()))
        self.assertTrue(result['ddl_lock_held'] and result['lock_released'] and result['gzip_verified'])
        self.assertEqual(result['status'], 'complete')
        self.lock.release.assert_called_once()

    def test_dump_failure_always_releases_and_no_complete_marker(self):
        with self.assertRaises(w.Rejected):
            self.export(dump=lambda *a, **k: (_ for _ in ()).throw(w.Rejected('failed-dump')))
        self.assertTrue(self.lock.released)
        manifest = json.loads((self.base / RUN / 'manifest.json').read_text())
        self.assertEqual(manifest['status'], 'failed')
        self.assertTrue(manifest['lock_release_confirmed'])

    def test_schema_changed_always_releases_and_refuses_success(self):
        other = copy.deepcopy(SCHEMA)
        other['sha256'] = 'd' * 64
        with self.assertRaises(w.Rejected):
            self.export(schemas=[SCHEMA, other])
        self.assertTrue(self.lock.released)
        self.assertEqual(json.loads((self.base / RUN / 'manifest.json').read_text())['status'], 'failed')

    def test_release_failure_refuses_success(self):
        with self.assertRaises(w.Rejected):
            self.export(release_error=True)
        self.assertEqual(json.loads((self.base / RUN / 'manifest.json').read_text())['status'], 'failed')

    def test_bad_gzip_CRC_no_success(self):
        def corrupt(*args, **kwargs):
            os.write(args[3], b'not gzip or SQL')
        with self.assertRaises(gzip.BadGzipFile):
            self.export(dump=corrupt)
        self.assertTrue(self.lock.released)
        self.assertEqual(json.loads((self.base / RUN / 'manifest.json').read_text())['status'], 'failed')

    def test_output_size_limit(self):
        path = self.base / 'limited'
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            writer = w.LimitedWriter(fd, 4)
            writer.write(b'1234')
            with self.assertRaises(w.Rejected):
                writer.write(b'5')
            self.assertEqual(path.stat().st_size, 4)
        finally:
            os.close(fd)

    def test_existing_run_never_overwritten(self):
        self.export()
        original = (self.base / RUN / 'manifest.json').read_bytes()
        with self.assertRaises(FileExistsError):
            self.export()
        self.assertEqual((self.base / RUN / 'manifest.json').read_bytes(), original)

    def cleanup(self):
        with synthetic_root_metadata():
            w.cleanup_run(POLICY, RUN, self.parent)

    def test_cleanup_only_two_worker_files(self):
        self.export()
        self.cleanup()
        self.assertFalse((self.base / RUN).exists())

    def test_cleanup_unknown_extra_file_preserves_everything(self):
        self.export()
        (self.base / RUN / 'unrelated').write_text('keep')
        with self.assertRaises(w.Rejected):
            self.cleanup()
        self.assertEqual(set(p.name for p in (self.base / RUN).iterdir()), w.FILES | {'unrelated'})

    def test_cleanup_failed_run_refused(self):
        with self.assertRaises(w.Rejected):
            self.export(dump=lambda *a, **k: (_ for _ in ()).throw(w.Rejected('fail')))
        with self.assertRaises(w.Rejected):
            self.cleanup()
        self.assertTrue((self.base / RUN / 'mysql.sql.gz').exists())

    def test_cleanup_wrong_run_id_marker_refused(self):
        self.export()
        p = self.base / RUN / 'manifest.json'
        j = json.loads(p.read_text())
        j['run_id'] = 'b' * 32
        p.write_text(json.dumps(j))
        with self.assertRaises(w.Rejected):
            self.cleanup()
        self.assertTrue((self.base / RUN / 'mysql.sql.gz').exists())

    def test_cleanup_symlink_payload_refused_no_external_delete(self):
        self.export()
        external = self.base / 'keep'
        external.write_text('keep')
        target = self.base / RUN / 'mysql.sql.gz'
        target.unlink()
        target.symlink_to(external)
        with self.assertRaises(OSError):
            self.cleanup()
        self.assertEqual(external.read_text(), 'keep')
        self.assertTrue((self.base / RUN / 'manifest.json').exists())

    def test_cleanup_hardlink_refused(self):
        self.export()
        os.link(self.base / RUN / 'mysql.sql.gz', self.base / 'second-link')
        with self.assertRaises(w.Rejected):
            self.cleanup()
        self.assertTrue((self.base / RUN / 'manifest.json').exists())

    def test_cleanup_traversal_rejected(self):
        with self.assertRaises(w.Rejected):
            w.cleanup_run(POLICY, '../outside', self.parent)

    def test_cleanup_directory_symlink_rejected(self):
        self.export()
        (self.base / RUN).rename(self.base / 'real')
        (self.base / RUN).symlink_to(self.base / 'real', target_is_directory=True)
        with self.assertRaises(OSError):
            self.cleanup()
        self.assertTrue((self.base / 'real' / 'manifest.json').exists())

    def test_cleanup_bad_permissions_refused_before_any_delete(self):
        self.export()
        (self.base / RUN / 'mysql.sql.gz').chmod(0o644)
        with self.assertRaises(w.Rejected):
            self.cleanup()
        self.assertTrue((self.base / RUN / 'manifest.json').exists())


if __name__ == '__main__':
    unittest.main()
