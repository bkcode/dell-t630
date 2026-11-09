#!/usr/bin/env python3
"""Offline synthetic SQL/filesystem/mocked Docker restore tests. No live service."""
import contextlib
import copy
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import Mock, patch

spec = importlib.util.spec_from_file_location('restore_target', Path(__file__).with_name('target-worker.py'))
w = importlib.util.module_from_spec(spec)
spec.loader.exec_module(w)
PURE = w.snapshot_module()
RUN, CID = 'a' * 32, 'b' * 64
TABLES = ['users', 'roles', 'permissions', 'config_info'] + ['test_table_' + str(n) for n in range(8)]
DBS = 'information_schema\nmysql\nperformance_schema\nsys\n'


def fixture_sql():
    output = ['CREATE DATABASE `nacos_prod`; USE `nacos_prod`;']
    for table in TABLES:
        if table == 'users':
            columns = "  `username` varchar(64),\n  `password` varchar(255),\n  `enabled` int"
            values = "('synthetic-user','synthetic-only',1)"
        else:
            columns = "  `id` int,\n  `value` text COMMENT 'space  stays'"
            values = "(1,NULL),(2,'')"
        output += ['CREATE TABLE `' + table + '` (\n' + columns + '\n) ENGINE=InnoDB;',
                   'INSERT INTO `' + table + '` VALUES ' + values + ';']
    return '\n'.join(output).encode()


def expected(raw):
    return {'version': 1, 'run_id': RUN, 'source_run_id': 'c' * 32,
            'archive_bytes': len(raw), 'archive_sha256': hashlib.sha256(raw).hexdigest(),
            'image_id': w.IMAGE, 'databases': ['nacos_prod'], 'table_counts': {'nacos_prod': 12}}


@contextlib.contextmanager
def synthetic_owners():
    """Only test UID is virtualized; actual mode/types/links remain checked."""
    real_fstat = os.fstat
    def fake(fd):
        s = real_fstat(fd)
        parts = list(s)
        parts[4] = 0
        return os.stat_result(parts)
    with patch.object(w.os, 'fstat', side_effect=fake), \
         patch.object(w.os, 'fchown'), patch.object(w.os, 'chown'):
        yield


class TargetTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name).resolve() / 'root'
        self.base.mkdir(mode=0o700)
        (self.base / 'reports').mkdir(mode=0o700)
        self.base_patch = patch.object(w, 'BASE', self.base)
        self.base_patch.start()
        self.addCleanup(self.base_patch.stop)
        self.work = self.base / RUN

    def prepare(self, populated=True):
        with synthetic_owners():
            w.prepare(RUN)
        if populated:
            raw = gzip.compress(fixture_sql(), mtime=0)
            (self.work / 'mysql.sql.gz').write_bytes(raw)
            (self.work / 'expected.json').write_text(json.dumps(expected(raw)))
        return self.work

    def loaded(self):
        self.prepare()
        with synthetic_owners():
            return w.load_snapshot(self.work, expected((self.work / 'mysql.sql.gz').read_bytes()))

    def test_prepare_only_three_empty_private_inputs(self):
        work = self.prepare(False)
        self.assertEqual({x.name for x in work.iterdir()}, w.INITIAL)
        self.assertEqual((work / 'mysql.sql.gz').stat().st_size, 0)
        self.assertEqual((work / 'expected.json').stat().st_size, 0)
        self.assertTrue(all(stat.S_IMODE(p.stat().st_mode) == 0o600 for p in work.iterdir()))
        self.assertEqual(stat.S_IMODE(work.stat().st_mode), 0o700)

    def test_bad_expected_image_scope_bytes_and_run(self):
        e = expected(b'x')
        for key, value in [('image_id', 'sha256:' + '0' * 64), ('databases', ['mysql']),
                           ('archive_bytes', 0), ('run_id', 'd' * 32),
                           ('table_counts', {'nacos_prod': 11})]:
            with self.subTest(key=key), self.assertRaises(w.Rejected):
                w.validate_expected({**e, key: value}, RUN)

    def test_archive_SHA_and_gzip_CRC_rejected(self):
        work = self.prepare()
        raw = (work / 'mysql.sql.gz').read_bytes()
        with synthetic_owners():
            with self.assertRaises(w.Rejected):
                w.load_snapshot(work, {**expected(raw), 'archive_sha256': '0' * 64})
            broken = raw[:-5] + bytes([raw[-5] ^ 1]) + raw[-4:]
            (work / 'mysql.sql.gz').write_bytes(broken)
            with self.assertRaises((gzip.BadGzipFile, EOFError)):
                w.load_snapshot(work, expected(broken))

    def test_expanded_budget_rejected(self):
        work = self.prepare()
        raw = (work / 'mysql.sql.gz').read_bytes()
        with synthetic_owners(), patch.object(w, 'MAX_SQL', 10):
            with self.assertRaises(w.Rejected):
                w.load_snapshot(work, expected(raw))

    def test_pure_module_full_rows_and_DDL_no_legacy_worker(self):
        raw, tables, module = self.loaded()
        self.assertEqual(len(tables), 12)
        self.assertEqual(tables['users']['rows'], 1)
        self.assertEqual(tables['roles']['rows'], 2)
        self.assertTrue(all('create_statement' in m for m in tables.values()))
        self.assertEqual(module.row_digest([(None,), (b'',)]), PURE.row_digest([(b'',), (None,)]))
        self.assertNotEqual(module.row_digest([(None,)]), module.row_digest([(b'NULL',)]))

    def test_global_DDL_rejected_before_import(self):
        self.prepare()
        raw = gzip.compress(fixture_sql() + b'\nGRANT ALL ON *.* TO x;')
        (self.work / 'mysql.sql.gz').write_bytes(raw)
        with synthetic_owners(), self.assertRaises(w.Rejected):
            w.load_snapshot(self.work, expected(raw))

    def test_ddl_whitespace_only_outside_comment_literal(self):
        first = "CREATE TABLE `x` ( `a` int COMMENT 'two  spaces', `b` text COMMENT 'it\\'s ok' ) ENGINE=InnoDB;"
        second = first.replace(' ( ', '\n(\n').replace(' ) ', '\n)\n')
        self.assertEqual(w.canonical_ddl(first, PURE), w.canonical_ddl(second, PURE))
        self.assertNotEqual(w.canonical_ddl(first, PURE), w.canonical_ddl(first.replace('two  spaces', 'two spaces'), PURE))

    def fake_sql(self, tables, *, ddl_change=None, bad_columns=False, bad_rows=False):
        def call(cid, work, run_id, query, importer=False):
            if query == 'SHOW DATABASES;':
                return DBS + 'nacos_prod\n'
            if '@@character_set_client' in query:
                return 'utf8mb4\tutf8mb4\n'
            if '@@event_scheduler' in query:
                return 'DISABLED\t0\tNULL\t0\t1\n'
            if 'information_schema.PLUGINS' in query:
                return '0\n'
            if 'FROM information_schema.COLLATIONS' in query:
                return 'utf8mb3_bin\tutf8mb3\nutf8mb3_general_ci\tutf8mb3\nutf8mb4_unicode_ci\tutf8mb4\nlatin1_swedish_ci\tlatin1\n'
            if 'JSON_ARRAY(TABLE_NAME' in query:
                return '\n'.join(json.dumps([t, 'BASE TABLE', 'InnoDB']) for t in TABLES) + '\n'
            if 'SELECT COUNT(*)' in query:
                return '0\n'
            if 'column_name' in query:
                table = query.split("table_name='")[1].split("'")[0]
                return '\n'.join(tables[table]['columns'][::-1] if bad_columns else tables[table]['columns']) + '\n'
            table = query.split('`nacos_prod`.`')[1].split('`')[0]
            if query.startswith('SHOW CREATE'):
                ddl = tables[table]['create_statement']
                if ddl_change:
                    ddl = ddl_change(ddl)
                return table + '\t' + ddl + '\n'
            if query.startswith('CHECK TABLE'):
                return 'nacos_prod.' + table + '\tcheck\tstatus\tOK\n'
            if table == 'users':
                cells = [b'synthetic-user', b'synthetic-only', b'1']
                return '\t'.join(c.hex().upper() for c in cells) + '\n'
            return '31\tNULL\n32\t' + ('41' if bad_rows else '') + '\n'
        return call

    def test_full_compare_rows_NULL_empty_columns_DDL_and_checks(self):
        _, tables, pure = self.loaded()
        with patch.object(w, 'sql', side_effect=self.fake_sql(tables)):
            result = w.compare(CID, self.work, RUN, tables, pure)
        self.assertTrue(result['full_table_DDL_match'] and result['row_digests_match'])
        self.assertEqual(result['row_count'], 23)
        self.assertNotIn('digest":', json.dumps(result))

    def test_changed_column_order_or_data_fails(self):
        _, tables, pure = self.loaded()
        for changed in ['columns', 'rows']:
            with self.subTest(changed=changed), patch.object(w, 'sql', side_effect=self.fake_sql(
                    tables, bad_columns=changed == 'columns', bad_rows=changed == 'rows')):
                with self.assertRaises(w.Rejected):
                    w.compare(CID, self.work, RUN, tables, pure)

    def test_changed_DDL_type_or_index_fails(self):
        _, tables, pure = self.loaded()
        changes = [lambda s: s.replace('varchar(64)', 'varchar(128)'),
                   lambda s: s.replace(') ENGINE=InnoDB', ', KEY `extra_index` (`username`)) ENGINE=InnoDB')]
        for change in changes:
            with self.subTest(change=change), patch.object(w, 'sql', side_effect=self.fake_sql(tables, ddl_change=change)):
                with self.assertRaises(w.Rejected):
                    w.compare(CID, self.work, RUN, tables, pure)

    def owned(self):
        return {'Id': CID, 'Name': '/' + w.container_name(RUN), 'Image': w.IMAGE, 'User': '999:999',
                'Labels': {'run': RUN, 'owner': w.OWNER}, 'Ports': {'3306/tcp': None},
                'Host': {'NetworkMode': 'none', 'ReadonlyRootfs': True, 'Privileged': False,
                         'CapAdd': None, 'CapDrop': ['ALL'], 'SecurityOpt': ['no-new-privileges:true'],
                         'NanoCpus': 1000000000, 'Memory': 1024 ** 3, 'MemorySwap': 1024 ** 3,
                         'PidsLimit': 256, 'PortBindings': {}},
                'Mounts': [{'Type': 'bind', 'Source': str(self.work / name), 'Destination': dest, 'RW': writable}
                           for name, dest, writable in [('mysql-data', '/var/lib/mysql', True),
                              ('root-password', '/run/secrets/root-password', False),
                              ('import-password', '/run/secrets/import-password', False)]]}

    def test_wrong_label_image_network_budget_and_mount_refused(self):
        self.assertEqual(w.owned(self.owned(), self.work, RUN), CID)
        for field in ['nonce', 'image', 'network', 'memory', 'mount']:
            c = self.owned()
            if field == 'nonce': c['Labels']['run'] = 'd' * 32
            if field == 'image': c['Image'] = 'sha256:' + '0' * 64
            if field == 'network': c['Host']['NetworkMode'] = 'host'
            if field == 'memory': c['Host']['Memory'] *= 2
            if field == 'mount': c['Mounts'][0]['Source'] = '/srv/dell-data/test-data/mysql'
            with self.subTest(field=field), self.assertRaises(w.Rejected):
                w.owned(c, self.work, RUN)

    def test_official_bug110825_equivalence_requires_server_mapping(self):
        source = "CREATE TABLE `t` (`v` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci"
        target = source.replace('varchar(100) COLLATE', 'varchar(100) CHARACTER SET utf8mb4 COLLATE')
        mapping = {'utf8mb4_unicode_ci': 'utf8mb4'}
        self.assertEqual(w.semantic_ddl(source, mapping), w.semantic_ddl(target, mapping))
        current = "CREATE TABLE `t` (`v` text COLLATE utf8mb3_bin COMMENT '原文')"
        replay = current.replace('text COLLATE', 'text CHARACTER SET utf8mb3 COLLATE')
        self.assertEqual(w.semantic_ddl(current, {'utf8mb3_bin': 'utf8mb3'}),
                         w.semantic_ddl(replay, {'utf8mb3_bin': 'utf8mb3'}))

    def test_compare_accepts_only_authoritative_redundant_charset(self):
        _, tables, pure = self.loaded()
        for meta in tables.values():
            meta['create_statement'] = meta['create_statement'].replace('text COMMENT', 'text COLLATE utf8mb3_bin COMMENT')
        replay = lambda ddl: ddl.replace('text COLLATE utf8mb3_bin', 'text CHARACTER SET utf8mb3 COLLATE utf8mb3_bin')
        with patch.object(w, 'sql', side_effect=self.fake_sql(tables, ddl_change=replay)):
            result = w.compare(CID, self.work, RUN, tables, pure)
        self.assertTrue(result['full_table_DDL_match'])
        self.assertTrue(result['charset_collation_semantics_verified'])
        self.assertTrue(result['row_digests_match'])

    def test_charset_mismatch_unknown_collation_and_real_collation_change_fail(self):
        mapping = {'utf8mb3_bin': 'utf8mb3', 'utf8mb3_general_ci': 'utf8mb3'}
        source = 'CREATE TABLE `t` (`v` text COLLATE utf8mb3_bin)'
        for ddl in ['CREATE TABLE `t` (`v` text CHARACTER SET utf8mb4 COLLATE utf8mb3_bin)',
                    'CREATE TABLE `t` (`v` text CHARACTER SET utf8mb3 COLLATE unknown_bin)']:
            with self.subTest(ddl=ddl), self.assertRaises(w.Rejected):
                w.semantic_ddl(ddl, mapping)
        self.assertNotEqual(w.semantic_ddl(source, mapping),
                            w.semantic_ddl(source.replace('utf8mb3_bin', 'utf8mb3_general_ci'), mapping))

    def test_semantics_never_normalize_comment_literals_or_identifier(self):
        mapping = {'utf8mb3_bin': 'utf8mb3'}
        ddl = "CREATE TABLE `CHARACTER SET utf8mb3 COLLATE utf8mb3_bin` (`v` text COMMENT 'fake CHARACTER SET utf8mb3 COLLATE utf8mb3_bin; it\\'s literal')"
        self.assertEqual(w.semantic_ddl(ddl, mapping), ddl)
        unmatched = "CREATE TABLE `t` (`v` text CHARACTER SET utf8mb3 NOT NULL COLLATE utf8mb3_bin)"
        self.assertEqual(w.semantic_ddl(unmatched, mapping), unmatched)
        no_collate = 'CREATE TABLE `t` (`v` text CHARACTER SET utf8mb3)'
        self.assertEqual(w.semantic_ddl(no_collate, mapping), no_collate)

    def test_DDL_diagnostic_literals_vs_structural_no_values_or_hash(self):
        original = "CREATE TABLE `t` (`v` varchar(64) COMMENT 'SOURCE_PRIVATE设计')"
        changed = original.replace('SOURCE_PRIVATE设计', 'TARGET_PRIVATE??')
        d = w.ddl_difference(original, changed, 't', 'utf8mb4\tutf8mb4\n')
        self.assertTrue(d['only_quoted_literals_differ'] and d['non_ascii_positions_differ'])
        self.assertTrue(d['charset_names_available'])
        text = json.dumps(d)
        self.assertNotIn('SOURCE_PRIVATE', text)
        self.assertNotIn('TARGET_PRIVATE', text)
        self.assertNotIn('CREATE TABLE', text)
        self.assertFalse(w.ddl_difference(original, original.replace('varchar(64)', 'varchar(128)'), 't')['only_quoted_literals_differ'])

    def test_DDL_mismatch_has_charset_classification_still_fails(self):
        _, tables, pure = self.loaded()
        change = lambda s: s.replace('varchar(64)', 'varchar(128)')
        with patch.object(w, 'sql', side_effect=self.fake_sql(tables, ddl_change=change)):
            with self.assertRaises(w.Rejected) as error:
                w.compare(CID, self.work, RUN, tables, pure)
        self.assertEqual(str(error.exception), 'full-table-ddl-mismatch')
        d = error.exception.ddl_difference
        self.assertEqual(d['table'], 'users')
        self.assertEqual(d['character_set_client'], 'utf8mb4')
        self.assertEqual(d['character_set_results'], 'utf8mb4')
        self.assertFalse(d['only_quoted_literals_differ'])

    def test_import_client_never_root_and_binary_mode_no_secret_argv(self):
        with patch.object(w, 'guard_cid'), patch.object(w, 'docker', return_value=(0, b'')) as d:
            w.sql(CID, self.work, RUN, b'-- SYNTHETIC_SQL_ONLY', importer=True)
        argv = d.call_args.args
        self.assertIn('--binary-mode', argv[-1])
        self.assertIn('--default-character-set=utf8mb4', argv[-1])
        self.assertIn('--user=restore_importer', argv[-1])
        self.assertNotIn('--user=root', argv[-1])
        self.assertNotIn('SYNTHETIC_SQL_ONLY', ' '.join(argv))
        self.assertEqual(d.call_args.kwargs['data'], b'-- SYNTHETIC_SQL_ONLY')

    def test_importer_bootstrap_no_precreated_database_or_global_grant(self):
        self.work.mkdir(mode=0o700)
        (self.work / 'import-password').write_text('f' * 64)
        grants = 'GRANT USAGE ON *.* TO `restore_importer`@`localhost`\nGRANT ALL PRIVILEGES ON `nacos_prod`.* TO `restore_importer`@`localhost`\n'
        with patch.object(w, 'sql', side_effect=['', grants]) as sql:
            w.import_user(CID, self.work, RUN)
        bootstrap = sql.call_args_list[0].args[3]
        self.assertNotIn('CREATE DATABASE', bootstrap)
        self.assertNotIn('GRANT ALL PRIVILEGES ON *.*', bootstrap)
        self.assertNotIn('GRANT OPTION', bootstrap)
        self.assertIn('CREATE USER', bootstrap)

    def cleanup(self, allow_report=False):
        with synthetic_owners(), patch.object(w, 'trusted_dir'), patch.object(w, 'all_containers', return_value=[]):
            return w.cleanup(self.work, RUN, allow_report=allow_report)

    def test_cleanup_unknown_entry_preserves_prepared_inputs(self):
        self.prepare()
        (self.work / 'unrelated').mkdir()
        with self.assertRaises(w.Rejected): self.cleanup()
        self.assertEqual({p.name for p in self.work.iterdir()}, w.INITIAL | {'unrelated'})

    def test_cleanup_symlink_or_foreign_marker_refused(self):
        self.prepare()
        marker = self.work / 'marker.json'
        before = marker.read_bytes()
        marker.unlink()
        external = self.base / 'external'
        external.write_bytes(before)
        external.chmod(0o600)
        marker.symlink_to(external)
        with self.assertRaises(OSError): self.cleanup()
        self.assertEqual(external.read_bytes(), before)

    def test_cleanup_other_container_reference_prevents_delete(self):
        self.prepare()
        foreign = {'Name': '/other', 'Labels': {'run': None},
                   'Mounts': [{'Source': str(self.work / 'mysql-data')}]}
        with synthetic_owners(), patch.object(w, 'trusted_dir'), \
             patch.object(w, 'all_containers', return_value=[foreign]), self.assertRaises(w.Rejected):
            w.cleanup(self.work, RUN)
        self.assertTrue((self.work / 'mysql.sql.gz').exists())

    def test_cleanup_success_idempotent_after_report_never_deletes_report(self):
        self.prepare()
        self.assertTrue(self.cleanup())
        report = self.base / 'reports' / (RUN + '.json')
        report.write_text(json.dumps({'format': w.FORMAT, 'run_id': RUN, 'status': 'passed'}))
        report.chmod(0o600)
        before = report.read_bytes()
        self.assertTrue(self.cleanup(True))
        self.assertEqual(report.read_bytes(), before)

    def test_wrong_run_or_missing_marker_not_cleaned(self):
        self.prepare()
        with self.assertRaises(w.Rejected):
            w.cleanup(self.base / '..', '../outside')
        (self.work / 'marker.json').unlink()
        with self.assertRaises(FileNotFoundError): self.cleanup()
        self.assertTrue((self.work / 'mysql.sql.gz').exists())

    def restore_mocks(self, *, import_error=False, source_changed=False, early_error=False):
        self.prepare()
        before = {'four_sources': 'before'}
        after = {'four_sources': 'changed' if source_changed else 'before'}
        result = {'table_count': 12, 'row_count': 23, 'column_names_order_match': True,
                  'row_digests_match': True, 'CHECK_TABLE_passed': True,
                  'event_scheduler_DISABLED': True, 'full_table_DDL_match': True}
        def sql(cid, work, run_id, query, importer=False):
            if importer and import_error: raise w.Rejected('synthetic-import-denied')
            return DBS if query == 'SHOW DATABASES;' else ''
        def sources():
            if early_error: raise w.Rejected('source-not-ready')
            return before if not getattr(sources, 'called', False) else after
        calls = []
        def snapshot():
            calls.append(1)
            if early_error: raise w.Rejected('source-not-ready')
            return before if len(calls) == 1 else after
        with synthetic_owners(), patch.object(w, 'trusted_dir'), \
             patch.object(w, 'source_snapshot', side_effect=snapshot), \
             patch.object(w, 'all_containers', return_value=[]), \
             patch.object(w, 'cached_image_and_uid'), patch.object(w, 'create', return_value=CID), \
             patch.object(w, 'ready'), patch.object(w, 'server_restrictions'), \
             patch.object(w, 'import_user'), patch.object(w, 'sql', side_effect=sql), \
             patch.object(w, 'compare', side_effect=[result, result]), \
             patch.object(w, 'guard_cid'), patch.object(w, 'docker', return_value=(0, b'')) as docker:
            output = w.restore(RUN)
        if not early_error and not import_error:
            docker.assert_called_once_with('restart', '--time=30', CID, timeout=60)
        return output

    def test_complete_restore_restart_report_has_no_SQL_SHA_or_rowdigest(self):
        output = self.restore_mocks()
        self.assertEqual(output['status'], 'passed')
        self.assertTrue(output['full_table_DDL_match'] and output['restart_persistence_verified'])
        self.assertFalse(self.work.exists())
        raw = json.dumps(output)
        self.assertNotIn('synthetic-user', raw)
        self.assertNotIn('create_statement', raw)
        self.assertNotIn(expected(b'x')['archive_sha256'], raw)
        self.assertNotIn('digest":', raw)

    def test_import_failure_or_source_change_fails_and_cleans(self):
        output = self.restore_mocks(import_error=True)
        self.assertEqual(output['status'], 'failed')
        self.assertFalse(self.work.exists())
        self.assertFalse(output['cleanup_failed'])

    def test_early_precheck_failure_still_cleans_prepared_SQL(self):
        output = self.restore_mocks(early_error=True)
        self.assertEqual(output['status'], 'failed')
        self.assertFalse(self.work.exists())
        self.assertFalse(output['cleanup_failed'])

    def test_source_identity_change_refuses_pass(self):
        output = self.restore_mocks(source_changed=True)
        self.assertEqual(output['status'], 'failed')
        self.assertFalse(output['source_containers_unchanged'])

    def test_bounded_subprocess_timeout_and_output(self):
        with self.assertRaises(w.Rejected):
            w.run([sys.executable, '-c', 'print("x"*10000)'], limit=100)
        with self.assertRaises(w.Rejected):
            w.run([sys.executable, '-c', 'import time;time.sleep(5)'], timeout=.02)


if __name__ == '__main__':
    unittest.main()
