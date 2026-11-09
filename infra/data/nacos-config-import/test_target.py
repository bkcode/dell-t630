#!/usr/bin/python3
"""Offline negative tests for the Nacos target import worker."""
import copy
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('target_worker', HERE / 'target-worker.py')
worker = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(worker)

NS_A = '08e7191f-3ccd-411a-be00-56798d237533'
NS_B = '7bfe03c6-0590-4ff0-8def-e07015016b54'


def item(namespace_id, number):
    content = f'value: {number}\n'
    return {
        'namespace_id': namespace_id,
        'namespace_name': worker.SOURCE_NAMESPACES[namespace_id],
        'data_id': f'config-{number:02d}.yaml', 'group': 'DEFAULT_GROUP',
        'type': 'yaml', 'app_name': '', 'description': '', 'config_tags': '',
        'encrypted_data_key': '', 'content': content,
        'md5': hashlib.md5(content.encode()).hexdigest(),
    }


def source():
    rows = [item(NS_A, index) for index in range(32)]
    rows.extend(item(NS_B, index + 32) for index in range(4))
    return {'version': 1,
            'namespaces': [{'id': NS_A, 'name': worker.SOURCE_NAMESPACES[NS_A], 'count': 32},
                           {'id': NS_B, 'name': worker.SOURCE_NAMESPACES[NS_B], 'count': 4}],
            'items': rows}


class SourceValidation(unittest.TestCase):
    def test_accepts_exact_36_items(self):
        namespaces, rows = worker.validate_source(source())
        self.assertEqual(len(namespaces), 2)
        self.assertEqual(len(rows), 36)

    def test_rejects_missing_or_extra_item(self):
        for change in (lambda d: d['items'].pop(),
                       lambda d: d['items'].append(copy.deepcopy(d['items'][0]))):
            value = source(); change(value)
            with self.assertRaises(worker.Rejected):
                worker.validate_source(value)

    def test_rejects_duplicate_key_and_wrong_namespace_count(self):
        value = source(); value['items'][1]['data_id'] = value['items'][0]['data_id']
        with self.assertRaises(worker.Rejected): worker.validate_source(value)
        value = source(); value['items'][32]['namespace_id'] = NS_A
        value['items'][32]['namespace_name'] = worker.SOURCE_NAMESPACES[NS_A]
        with self.assertRaises(worker.Rejected): worker.validate_source(value)

    def test_rejects_encrypted_or_tagged_source(self):
        for key, value in [('encrypted_data_key', 'ciphertext'), ('config_tags', 'tag')]:
            payload = source(); payload['items'][0][key] = value
            with self.assertRaises(worker.Rejected): worker.validate_source(payload)

    def test_rejects_control_character_and_bad_md5(self):
        payload = source(); payload['items'][0]['content'] = 'bad\x00text'
        with self.assertRaises(worker.Rejected): worker.validate_source(payload)

    def test_null_optional_metadata_normalizes_but_preserves_content(self):
        payload = source()
        for key in ('description', 'config_tags'):
            payload['items'][0][key] = None
        _, rows = worker.validate_source(payload)
        self.assertEqual(rows[0]['description'], '')
        self.assertEqual(rows[0]['config_tags'], '')
        payload = source(); payload['items'][0]['md5'] = 'not-md5'
        with self.assertRaises(worker.Rejected): worker.validate_source(payload)


class StabilityValidation(unittest.TestCase):
    def before(self):
        row = {'namespace_id': NS_A, 'data_id': 'a.yaml', 'group': 'DEFAULT_GROUP',
               'md5': 'b' * 32, 'type': 'yaml', 'app_name': '', 'description': '',
               'encrypted_data_key': '', 'content': 'body\n', 'config_tags': ''}
        return {'version': 1, 'run_id': 'a' * 32, 'items': [row]}

    def test_metadata_drift_rejects_before_delete(self):
        before = self.before()
        class Fake:
            def request(self, *_args, **_kwargs):
                return 200, b'body\n'
        old_metadata, old_side = worker.mysql_metadata, worker.side_tables_empty
        worker.mysql_metadata = lambda: []
        worker.side_tables_empty = lambda: True
        try:
            with self.assertRaises(worker.Rejected): worker.require_stable_before(Fake(), before)
        finally:
            worker.mysql_metadata, worker.side_tables_empty = old_metadata, old_side

    def test_body_drift_rejects_before_delete(self):
        before = self.before()
        expected = [{key: row[key] for key in ('namespace_id', 'data_id', 'group', 'md5', 'type',
                                                 'app_name', 'description', 'encrypted_data_key')}
                    for row in before['items']]
        class Fake:
            def request(self, *_args, **_kwargs): return 200, b'changed\n'
        old_metadata, old_side = worker.mysql_metadata, worker.side_tables_empty
        worker.mysql_metadata = lambda: expected
        worker.side_tables_empty = lambda: True
        try:
            with self.assertRaises(worker.Rejected): worker.require_stable_before(Fake(), before)
        finally:
            worker.mysql_metadata, worker.side_tables_empty = old_metadata, old_side

    def test_nonempty_side_tables_reject_before_delete(self):
        before = self.before()
        expected = [{key: row[key] for key in ('namespace_id', 'data_id', 'group', 'md5', 'type',
                                                 'app_name', 'description', 'encrypted_data_key')}
                    for row in before['items']]
        class Fake:
            def request(self, *_args, **_kwargs): return 200, b'body\n'
        old_metadata, old_side = worker.mysql_metadata, worker.side_tables_empty
        worker.mysql_metadata = lambda: expected
        worker.side_tables_empty = lambda: False
        try:
            with self.assertRaises(worker.Rejected): worker.require_stable_before(Fake(), before)
        finally:
            worker.mysql_metadata, worker.side_tables_empty = old_metadata, old_side


class NativeShowAllShape(unittest.TestCase):
    def item(self):
        body = 'value: safe\n'
        return {'namespace_id': NS_A, 'data_id': 'safe.yaml', 'group': 'DEFAULT_GROUP',
                'md5': hashlib.md5(body.encode()).hexdigest(), 'type': 'yaml', 'app_name': '',
                'description': '', 'encrypted_data_key': ''}

    def test_plain_and_showall_json_crosscheck(self):
        item = self.item(); body = 'value: safe\n'
        class API:
            def request(self, method, path, values, **_kwargs):
                if values.get('show') == 'all':
                    detail = {'content': body, 'md5': item['md5'], 'dataId': item['data_id'],
                              'group': item['group'], 'tenant': item['namespace_id'],
                              'type': 'yaml', 'appName': None, 'desc': None,
                              'encryptedDataKey': ''}
                    return 200, __import__('json').dumps(detail).encode()
                return 200, body.encode()
        actual, detail = worker.config_all(API(), item)
        self.assertEqual(actual, body)
        self.assertEqual(detail['md5'], item['md5'])

    def test_showall_md5_or_content_mismatch_rejects(self):
        item = self.item(); body = 'value: safe\n'
        class API:
            def request(self, _method, _path, values, **_kwargs):
                if values.get('show') == 'all':
                    return 200, b'{"content":"wrong","md5":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"}'
                return 200, body.encode()
        with self.assertRaises(worker.Rejected):
            worker.config_all(API(), item)


class EventualControllerVisibility(unittest.TestCase):
    def item(self):
        body = 'value: safe\n'
        return {'namespace_id': NS_A, 'data_id': 'safe.yaml', 'group': 'DEFAULT_GROUP',
                'md5': hashlib.md5(body.encode()).hexdigest(), 'type': 'yaml', 'app_name': '',
                'description': '', 'encrypted_data_key': '', 'content': body, 'config_tags': ''}

    def detail(self, item):
        return {'content': item['content'], 'md5': item['md5'], 'dataId': item['data_id'],
                'group': item['group'], 'tenant': item['namespace_id'], 'type': item['type'],
                'appName': None, 'desc': None, 'encryptedDataKey': ''}

    def test_delete_waits_for_a_stale_but_identical_entry(self):
        item = self.item()
        class API:
            calls = 0
            showall_calls = 0
            def request(self, _method, _path, values, **_kwargs):
                if values.get('show') == 'all':
                    self.showall_calls += 1
                    return 404, b''  # Native-shaped: controller detail may disappear first.
                self.calls += 1
                return (404, b'') if self.calls >= 3 else (200, item['content'].encode())
        api = API()
        original = worker.time.sleep; worker.time.sleep = lambda _: None
        try: worker.wait_for_absent(api, item)
        finally: worker.time.sleep = original
        self.assertGreaterEqual(api.calls, 3)
        self.assertEqual(api.showall_calls, 0)

    def test_publish_waits_for_404_then_requires_exact_visible_body(self):
        item = self.item()
        class API:
            calls = 0
            def request(self, _method, _path, values, **_kwargs):
                if values.get('show') == 'all': return 200, json.dumps(self.detail).encode()
                self.calls += 1
                return (404, b'') if self.calls == 1 else (200, item['content'].encode())
        api = API(); api.detail = self.detail(item)
        original = worker.time.sleep; worker.time.sleep = lambda _: None
        try: worker.wait_for_present(api, item)
        finally: worker.time.sleep = original
        self.assertGreaterEqual(api.calls, 3)


class MetadataReporting(unittest.TestCase):
    def test_report_never_contains_body_or_md5_values(self):
        report = worker.result_row([item(NS_A, 0)])
        self.assertNotIn('content', report)
        self.assertNotIn('md5', report)
        self.assertEqual(report['config_count'], 1)

    def test_config_key_separates_namespaces(self):
        left, right = item(NS_A, 0), item(NS_B, 0)
        self.assertNotEqual(worker.config_key(left), worker.config_key(right))


class FakeController:
    def __init__(self, configs):
        self.configs = {worker.config_key(row): copy.deepcopy(row) for row in configs}
        self.namespaces = {'old-test': {'id': 'old-test', 'name': 'old-test', 'config_count': len(configs)}}

    def admin(self):
        return None

    def request(self, method, path, values=None, *, missing=False):
        values = values or {}
        if method == 'GET' and path == '/v1/console/namespaces':
            rows = []
            for ns in self.namespaces.values():
                count = sum(row['namespace_id'] == ns['id'] for row in self.configs.values())
                rows.append({'namespace': ns['id'], 'namespaceShowName': ns['name'], 'configCount': count})
            return 200, json.dumps({'data': rows}).encode()
        if path == '/v1/cs/configs':
            key = (values['tenant'], values['group'], values['dataId'])
            if method == 'GET':
                row = self.configs.get(key)
                if row is None:
                    return 404, b''
                if values.get('show') == 'all':
                    payload = {'content': row['content'], 'md5': row['md5'],
                               'dataId': row['data_id'], 'group': row['group'],
                               'tenant': row['namespace_id'], 'type': row['type'],
                               'appName': None if not row['app_name'] else row['app_name'],
                               'desc': None if not row['description'] else row['description'],
                               'encryptedDataKey': row['encrypted_data_key']}
                    return 200, json.dumps(payload).encode()
                return 200, row['content'].encode()
            if method == 'DELETE':
                if key not in self.configs:
                    return 404, b''
                self.configs.pop(key)
                return 200, b'true'
            if method == 'POST':
                if key in self.configs:
                    return 200, b'false'
                body = values['content']
                self.configs[key] = {'namespace_id': values['tenant'], 'namespace_name': worker.SOURCE_NAMESPACES[values['tenant']],
                                     'data_id': values['dataId'], 'group': values['group'],
                                     'type': values['type'], 'app_name': values.get('appName', ''),
                                     'description': values.get('desc', ''), 'config_tags': values.get('config_tags', ''),
                                     'encrypted_data_key': values.get('encryptedDataKey', ''), 'content': body,
                                     'md5': hashlib.md5(body.encode()).hexdigest()}
                return 200, b'true'
        if method == 'POST' and path == '/v1/console/namespaces':
            ident, name = values['customNamespaceId'], values['namespaceName']
            if ident in self.namespaces:
                return 200, b'false'
            self.namespaces[ident] = {'id': ident, 'name': name, 'config_count': 0}
            return 200, b'true'
        raise AssertionError((method, path, values))


class FullLifecycle(unittest.TestCase):
    def test_prepare_apply_verify_with_showall_json_and_nullable_list_md5(self):
        old = item(NS_A, 99)
        old.update(namespace_id='old-test', namespace_name='old-test', data_id='legacy.yaml')
        old['content'] = 'legacy: yes\n'; old['md5'] = hashlib.md5(old['content'].encode()).hexdigest()
        api = FakeController([old])
        original = {name: getattr(worker, name) for name in ('BASE', 'guard_host', 'secure_dir', 'read_json',
                                                               'mysql_metadata', 'side_tables_empty', 'Nacos')}
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            run = '1' * 32
            run_dir = base / run; run_dir.mkdir(mode=0o700)
            (run_dir / 'source.json').write_text(json.dumps(source()))
            def list_metadata():
                # Native-shaped list: md5 nullable, while ConfigAllInfo owns stored MD5.
                rows = []
                for row in sorted(api.configs.values(), key=worker.config_key):
                    rows.append({key: row[key] for key in ('namespace_id', 'data_id', 'group', 'type', 'app_name',
                                                            'description', 'encrypted_data_key')} | {'md5': ''})
                return rows
            try:
                worker.BASE = base
                worker.guard_host = lambda: None
                worker.secure_dir = lambda *_args, **_kwargs: None
                worker.read_json = lambda path, **_kwargs: json.loads(Path(path).read_text())
                worker.mysql_metadata = list_metadata
                worker.side_tables_empty = lambda: True
                worker.Nacos = lambda: api
                self.assertEqual(worker.prepare(run)['target_before_config_count'], 1)
                result = worker.apply(run)
                self.assertEqual(result['deleted_config_count'], 1)
                self.assertEqual(result['published_config_count'], 36)
                self.assertEqual(worker.verify(run)['config_count'], 36)
                self.assertEqual(len(api.configs), 36)
                self.assertIn(NS_A, api.namespaces)
                self.assertIn(NS_B, api.namespaces)
            finally:
                for name, value in original.items():
                    setattr(worker, name, value)


if __name__ == '__main__':
    unittest.main()
