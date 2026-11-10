#!/usr/bin/env python3
"""Validate actual-runtime candidate deltas locally; no network or install calls."""
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
ROOT = HERE.parents[2]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


old = module('actual_old_monitor', HERE / 'before/install-guest-baseline.py')
new = module('runtime_candidate_monitor', HERE / 'install-guest-baseline.py')
merge = module('actual_publisher_merge', HERE / 'merge_publisher_health.py')
collector = module('unchanged_canonical_collector', ROOT / 'infra/ops/guest-baseline/collect-guest-health.py')
manifest = json.loads((HERE / 'manifest.json').read_text())
vm270 = json.loads((ROOT / manifest['runtime_capture_sources'][0]).read_text())
vm220 = json.loads((ROOT / manifest['runtime_capture_sources'][1]).read_text())
old_cat = json.loads((HERE / 'before/guest-targets.json').read_text())
new_cat = json.loads((HERE / 'guest-targets.json').read_text())
old_nodes = json.loads((HERE / 'before/guest-node.json').read_text())
new_nodes = json.loads((HERE / 'guest-node.json').read_text())
old_health = json.loads((HERE / 'before/publisher-health.json').read_text())
new_health = json.loads((HERE / 'publisher-health.json').read_text())


class RuntimeTests(unittest.TestCase):
    def test_source_and_candidate_SHA_match_actual_captures(self):
        for name, entry in manifest['files'].items():
            capture = (vm220 if name == 'publisher-health.json' else vm270)['files'][entry['server_path']]
            self.assertEqual(capture['sha256'], entry['before_SHA256'])
            self.assertEqual(hashlib.sha256(capture['text'].encode()).hexdigest(), entry['before_SHA256'])
            self.assertEqual((HERE / 'before' / name).read_bytes(), capture['text'].encode())
            self.assertEqual(hashlib.sha256((HERE / name).read_bytes()).hexdigest(), entry['new_SHA256'])

    def test_nodes_drop_only_retired221_and_keep_resource280(self):
        self.assertEqual(new_nodes, [row for row in old_nodes if row['labels']['vmid'] != '221'])
        self.assertEqual((len(old_nodes), len(new_nodes)), (11, 10))
        for node in ['220', '280']:
            self.assertEqual([row for row in new_nodes if row['labels']['vmid'] == node],
                             [row for row in old_nodes if row['labels']['vmid'] == node])
        self.assertEqual(manifest['expected_total_targets_after'], 10 + 5)
        self.assertFalse(any('192.168.19.31:9100' in row['targets'] for row in new_nodes))

    def test_runtime_registry_and_enum_are_paired_without_inventing280(self):
        self.assertEqual(new_cat['roles'], [row for row in old_cat['roles'] if row['role'] != 'artifact-service'])
        self.assertEqual((len(old_cat['roles']), len(new_cat['roles'])), (10, 9))
        self.assertEqual(new.ROLES, old.ROLES - {'artifact-service'})
        self.assertEqual(new.ROLES, {row['role'] for row in new_cat['roles']})
        self.assertFalse(any(row['vmid'] == 280 for row in old_cat['roles'] + new_cat['roles']))
        for key in set(old_cat) - {'roles', 'scope'}:
            self.assertEqual(new_cat[key], old_cat[key])
        for row in new_cat['roles']:
            self.assertEqual(new.target_for(row['role'], row['hostname']), row)

    def test_other_runtime_candidate_profiles_and_unit_texts_identical(self):
        for row in new_cat['roles']:
            with self.subTest(role=row['role']):
                self.assertEqual(new.unit_text(row, 'prometheus', 'prometheus'),
                                 old.unit_text(row, 'prometheus', 'prometheus'))
                if row['role'] != 'publish-service':
                    self.assertEqual(new.candidates(row), old.candidates(row))

    def test_publisher_candidate_has_nexus_alias_and_native_units(self):
        row = new.target_for('publish-service', 'publish-service')
        self.assertEqual(row['private_ip'], '192.168.19.30')
        candidate = new.candidates(row)
        self.assertEqual(candidate['candidate_http_checks'], [merge.NEXUS_CHECK])
        self.assertEqual(candidate['candidate_service_units'],
                         ['docker.service', 'dell-nexus.service', 'puyu-deploy-mcp.service', 'dell-service-directory.service'])
        self.assertNotIn('192.168.19.30:8081', json.dumps(candidate))

    def test_actual220_profile_preserves_old4_and_adds_only3_units(self):
        saved = copy.deepcopy(old_health)
        self.assertEqual(new_health, merge.merge_publisher_health(old_health))
        self.assertEqual(old_health, saved)
        self.assertEqual(len(old_health['services']), 4)
        self.assertEqual(len(new_health['services']), 7)
        self.assertEqual(new_health['services'][:4], old_health['services'])
        self.assertEqual(new_health['services'][4:], merge.ADDED_UNITS)
        self.assertEqual(new_health['http_checks'], old_health['http_checks'] + [merge.NEXUS_CHECK])
        self.assertEqual(new_health['notes'], old_health['notes'])
        self.assertEqual(merge.merge_publisher_health(new_health), new_health)
        self.assertFalse(any('18765' in row['url'] for row in new_health['http_checks']))

    def test_alias31_local_contract_and_merge_conflicts(self):
        self.assertEqual(collector.validate(new_health, {'192.168.19.30', '192.168.19.31'}), new_health)
        with self.assertRaises(ValueError):
            collector.validate(new_health, {'192.168.19.30'})
        with self.assertRaises(ValueError):
            merge.merge_publisher_health({'role': 'resource-service', 'private_ip': '192.168.19.80'})
        conflict = copy.deepcopy(old_health)
        conflict['http_checks'] = [{'name': 'nexus-status', 'url': 'http://192.168.19.30:8081/service/rest/v1/status'}]
        with self.assertRaises(ValueError):
            merge.merge_publisher_health(conflict)

    def test_canonical_and_FileBrowser_collector_sources_remain_unchanged(self):
        reference = json.loads((HERE / 'canonical-reference/manifest.json').read_text())
        for name, entry in reference['files'].items():
            self.assertEqual(hashlib.sha256((ROOT / entry['source']).read_bytes()).hexdigest(), entry['before_SHA256'])
        self.assertEqual(hashlib.sha256((ROOT / 'infra/ops/guest-baseline/collect-guest-health.py').read_bytes()).hexdigest(),
                         reference['collector_source_SHA256_unchanged'])


if __name__ == '__main__':
    result = unittest.TextTestRunner(stream=io.StringIO(), verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(RuntimeTests))
    report = {'status': 'passed' if result.wasSuccessful() else 'failed', 'tests_run': result.testsRun,
              'failures': len(result.failures), 'errors': len(result.errors),
              'scope': 'local pure checks against exact captured runtime bytes; no server operations',
              'actual_runtime_baseline_used': True, 'old220_native_checks_preserved': True,
              'MCP_unit_added_without_HTTP_auth_probe': True, 'Prometheus280_target_preserved': True,
              'canonical_or_FileBrowser_sources_written': False, 'server_connections_or_writes': False}
    (HERE / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if result.wasSuccessful() else 1)
