#!/usr/bin/env python3
"""Pure local reproduction and scope regressions; never contacts PVE/GW."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
spec = importlib.util.spec_from_file_location('bridge_renderer', HERE / 'render-bridge-acl.py')
renderer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(renderer)
PLAN = json.loads((ROOT / 'migration-plan.json').read_text())
INVENTORY = json.loads((HERE / 'nic-registry-current.json').read_text())
LAN_LINE = '    ip saddr 192.168.21.0/24 ip daddr 192.168.19.0/24 counter accept comment "trusted-LAN21-to-server19"\n'


class TrustedLAN(unittest.TestCase):
    def test_reproduces_confirmed_bridge_bytes(self):
        historical_plan = json.loads((ROOT / 'lan-trusted-20261109/master-candidate.json').read_text())
        historical_inventory = json.loads((ROOT / 'lan-trusted-20261109/nic-registry-at-confirmation.json').read_text())
        text, metadata = renderer.render(historical_plan, historical_inventory)
        self.assertEqual(text, (ROOT / 'lan-trusted-20261109/bridge-candidate.nft').read_text())
        self.assertEqual(len(metadata['rows']), 15)
        self.assertFalse(metadata['old_ops_transition_exception'])

    def test_current_resource_addition_is_exact_and_reproducible(self):
        text, metadata = renderer.render(PLAN, INVENTORY)
        self.assertEqual(text, (ROOT.parent / 'completion/20261109-resources/bridge-candidate.nft').read_text())
        self.assertEqual(len(metadata['rows']), 16)
        for source in ['192.168.19.40', '192.168.19.45']:
            self.assertIn(source + ' . 192.168.19.80 . 2049', text)
        self.assertNotIn('192.168.19.20 . 192.168.19.80 . 2049', text)
        for key,value in [('tcp',[2049,111]),('ip','192.168.19.81'),('clients',{'230':'192.168.19.40','240':'192.168.19.45','210':'192.168.19.20'})]:
            bad=copy.deepcopy(PLAN);bad['shared_resource_service'][key]=value
            with self.subTest(key=key),self.assertRaises(AssertionError):
                renderer.render(bad,INVENTORY)

    def test_new_permission_stays_after_identity_and_invalid_checks(self):
        text, _ = renderer.render(PLAN, INVENTORY)
        self.assertEqual(text.count(LAN_LINE), 1)
        before = text.split(LAN_LINE)[0]
        self.assertIn('unknown-port-or-source-MAC', before)
        self.assertIn('approved-destination-IP-only', before)
        self.assertIn('ct state invalid', before)
        self.assertIn('LAN-test-Nacos-only', before)
        self.assertIn('trusted-WireGuard-to-server19', before)
        self.assertIn('counter drop', text.split(LAN_LINE)[1])

    def test_optional_feature_changes_only_the_owned_permission_line(self):
        old = copy.deepcopy(PLAN)
        old['gateway_policy'].pop('LAN_trusted_client_access')
        baseline, meta = renderer.render(old, INVENTORY)
        current, newmeta = renderer.render(PLAN, INVENTORY)
        self.assertEqual(current.replace(LAN_LINE, ''), baseline)
        self.assertEqual(meta['rows'], newmeta['rows'])
        self.assertEqual(meta['peer_tcp_tuple_count'], newmeta['peer_tcp_tuple_count'])
        for word in ['masquerade', ' snat ', ' dnat ', 'flush ruleset']:
            self.assertNotIn(word, current.lower())

    def test_broader_or_different_scope_and_missing_provenance_rejected(self):
        for key, value in [('source', '0.0.0.0/0'), ('destination', '0.0.0.0/0'),
                           ('protocols', 'tcp'), ('gateway_local_addresses', ['192.168.21.1']),
                           ('no_NAT', False), ('reason', ''), ('evidence', '')]:
            with self.subTest(key=key):
                bad = copy.deepcopy(PLAN)
                bad['gateway_policy']['LAN_trusted_client_access'][key] = value
                with self.assertRaises(AssertionError):
                    renderer.render(bad, INVENTORY)
        bad = copy.deepcopy(PLAN)
        bad['gateway_policy']['LAN_trusted_client_access']['extra'] = True
        with self.assertRaises(AssertionError):
            renderer.render(bad, INVENTORY)

    def test_template_and_retired_identities_remain_quarantined(self):
        _, metadata = renderer.render(PLAN, INVENTORY)
        rows = metadata['rows']
        self.assertFalse({row['vmid'] for row in rows} & set(PLAN['retired_vmids']))
        templates = [row for row in rows if row['template']]
        self.assertEqual({row['vmid'] for row in templates}, {9001, 9010, 9011})
        self.assertTrue(all(not row['ips'] for row in templates))


if __name__ == '__main__':
    unittest.main()
