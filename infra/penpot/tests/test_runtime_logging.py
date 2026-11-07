import copy
import importlib.util
import json
from pathlib import Path
import unittest

BASE = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('runtime_logging_under_test', BASE / 'runtime_logging.py')
runtime = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runtime)


class RuntimeLogging(unittest.TestCase):
    def config(self):
        lock = json.loads((BASE / 'runtime/logging/templates.lock.json').read_text())
        return {'services': {'penpot-frontend': {'volumes': [
            {'type': 'bind', 'source': str(BASE / item['runtime_source']),
             'target': item['source_image_path'], 'read_only': True,
             'bind': {'create_host_path': False}} for item in lock['templates'].values()]}}}

    def test_exact_readonly_binds_and_locked_templates_pass(self):
        runtime.validate_runtime_logging(self.config())

    def test_writable_template_bind_fails(self):
        config = self.config()
        config['services']['penpot-frontend']['volumes'][0]['read_only'] = False
        with self.assertRaisesRegex(RuntimeError, 'read-only'):
            runtime.validate_runtime_logging(config)

    def test_missing_template_bind_fails(self):
        config = self.config()
        config['services']['penpot-frontend']['volumes'].pop()
        with self.assertRaisesRegex(RuntimeError, 'Missing'):
            runtime.validate_runtime_logging(config)

    def test_auto_created_or_wrong_source_file_fails(self):
        for key, value in [('create_host_path', True), ('source', '/tmp/unreviewed.template')]:
            config = self.config()
            mount = config['services']['penpot-frontend']['volumes'][0]
            if key == 'source':
                mount[key] = value
            else:
                mount['bind'][key] = value
            with self.subTest(key=key), self.assertRaisesRegex(RuntimeError, 'read-only'):
                runtime.validate_runtime_logging(config)


if __name__ == '__main__':
    unittest.main()
