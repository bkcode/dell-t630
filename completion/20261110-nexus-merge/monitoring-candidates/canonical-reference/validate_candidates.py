#!/usr/bin/env python3
"""Local pure-function checks only: no guest, daemon, HTTP, package or unit calls."""
import copy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import unittest

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = next(parent for parent in HERE.parents if (parent / 'infra/ops/guest-baseline').is_dir())
SOURCE = ROOT / 'infra/ops/guest-baseline'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


old = load('before_baseline', SOURCE / 'install-guest-baseline.py')
new = load('candidate_baseline', HERE / 'install-guest-baseline.py')
collector = load('unchanged_collector', SOURCE / 'collect-guest-health.py')
merge = load('pure_publisher_delta', HERE / 'merge_publisher_health.py')
before = json.loads((SOURCE / 'guest-targets.json').read_text())
after = json.loads((HERE / 'guest-targets.json').read_text())
manifest = json.loads((HERE / 'manifest.json').read_text())


class CandidateTests(unittest.TestCase):
    def test_public_source_cas_is_unchanged(self):
        for name, entry in manifest['files'].items():
            self.assertEqual(hashlib.sha256((ROOT / entry['source']).read_bytes()).hexdigest(), entry['before_SHA256'])
            self.assertEqual(hashlib.sha256((HERE / name).read_bytes()).hexdigest(), entry['new_SHA256'])
        self.assertEqual(hashlib.sha256((SOURCE / 'collect-guest-health.py').read_bytes()).hexdigest(),
                         manifest['collector_source_SHA256_unchanged'])

    def test_only_artifact_registry_row_and_enum_retired(self):
        self.assertEqual(after['roles'], [row for row in before['roles'] if row['role'] != 'artifact-service'])
        self.assertEqual(new.ROLES, old.ROLES - {'artifact-service'})
        self.assertEqual({row['role'] for row in after['roles']}, new.ROLES)
        self.assertEqual(len(after['roles']), 10)
        for key in set(before) - {'roles', 'scope'}:
            self.assertEqual(after[key], before[key])
        for row in after['roles']:
            self.assertEqual(new.target_for(row['role'], row['hostname']), row)
        with self.assertRaises(RuntimeError):
            new.target_for('artifact-service', 'artifact-service')

    def test_remaining_profiles_and_unit_text_are_identical(self):
        for row in after['roles']:
            with self.subTest(role=row['role']):
                self.assertEqual(new.unit_text(row, 'prometheus', 'prometheus'),
                                 old.unit_text(row, 'prometheus', 'prometheus'))
                if row['role'] != 'publish-service':
                    self.assertEqual(new.role_health_profile(row), old.role_health_profile(row))
                    self.assertEqual(new.candidates(row), old.candidates(row))
        resource = next(row for row in after['roles'] if row['role'] == 'resource-service')
        self.assertEqual(new.role_health_profile(resource), old.role_health_profile(resource))

    def test_publisher_component_profile_is_on_alias31(self):
        row = new.target_for('publish-service', 'publish-service')
        self.assertEqual(row['private_ip'], '192.168.19.30')
        self.assertEqual(new.role_health_profile(row), {
            'services': ['dell-nexus.service'], 'http_checks': [merge.NEXUS_CHECK]})
        candidate = new.candidates(row)
        self.assertEqual(candidate['candidate_service_units'], ['docker.service', 'dell-nexus.service'])
        self.assertEqual(candidate['candidate_http_checks'], [merge.NEXUS_CHECK])
        self.assertNotIn('192.168.19.30:8081', json.dumps(candidate))

    def test_alias_health_requires_actual_local_alias_binding(self):
        candidate = new.candidates(new.target_for('publish-service', 'publish-service'))
        self.assertEqual(collector.validate(candidate, {'192.168.19.30', '192.168.19.31'}), candidate)
        with self.assertRaises(ValueError):
            collector.validate(candidate, {'192.168.19.30'})

    def test_live_profile_delta_preserves_existing_native_checks(self):
        fixture = {
            'role': 'publish-service', 'private_ip': '192.168.19.30',
            'textfile_directory': '/var/lib/prometheus/node-exporter-textfile',
            'services': ['ssh.service', 'qemu-guest-agent.service', 'prometheus-node-exporter.service',
                         'dell-service-directory.service', 'puyu-deploy-mcp.service'],
            'http_checks': [{'name': 'navigation', 'url': 'http://192.168.19.30:9080/'}],
            'candidate_service_units': ['dell-service-directory.service', 'puyu-deploy-mcp.service'],
            'candidate_http_checks': [], 'notes': 'Synthetic compatibility fixture, not a guest export',
        }
        saved = copy.deepcopy(fixture)
        result = merge.merge_publisher_health(fixture)
        self.assertEqual(fixture, saved)
        for key in ['role', 'private_ip', 'textfile_directory', 'notes']:
            self.assertEqual(result[key], fixture[key])
        self.assertEqual(result['services'][:-2], fixture['services'])
        self.assertEqual(result['http_checks'][:-1], fixture['http_checks'])
        self.assertEqual(result['http_checks'][-1], merge.NEXUS_CHECK)
        self.assertEqual(merge.merge_publisher_health(result), result)
        self.assertEqual(collector.validate(result, {'192.168.19.30', '192.168.19.31'}), result)

    def test_live_profile_delta_rejects_other_roles_or_endpoint_conflict(self):
        with self.assertRaises(ValueError):
            merge.merge_publisher_health({'role': 'resource-service', 'private_ip': '192.168.19.80'})
        with self.assertRaises(ValueError):
            merge.merge_publisher_health({'role': 'publish-service', 'private_ip': '192.168.19.30',
                'http_checks': [{'name': 'nexus-status', 'url': 'http://192.168.19.30:8081/service/rest/v1/status'}]})


if __name__ == '__main__':
    report = unittest.TextTestRunner(stream=io.StringIO(), verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(CandidateTests))
    value = {'status': 'passed' if report.wasSuccessful() else 'failed', 'tests_run': report.testsRun,
             'failures': len(report.failures), 'errors': len(report.errors),
             'scope': 'local pure-function/source-CAS checks; publisher fixture is synthetic',
             'other_role_profiles_unchanged': report.wasSuccessful(),
             'resource280_and_FileBrowser_sources_unchanged': report.wasSuccessful(),
             'server_connections_or_changes': False, 'canonical_source_files_written': False}
    (HERE / 'validation.json').write_text(json.dumps(value, indent=2) + '\n')
    print(json.dumps(value, indent=2))
    raise SystemExit(0 if report.wasSuccessful() else 1)
