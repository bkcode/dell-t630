import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('probe', Path(__file__).with_name('probe.py'))
probe = importlib.util.module_from_spec(spec); spec.loader.exec_module(probe)


class StateTests(unittest.TestCase):
    def setUp(self):
        self.state = probe.empty_state()
        self.up = {k: True for k in probe.KEYS[1:]}
        probe.transition(self.state, self.up, 100)
        probe.transition(self.state, self.up, 160)

    def twice(self, obs, start=220):
        probe.transition(self.state, obs, start)
        return probe.transition(self.state, obs, start + 60)

    def test_failure_debounce_recovery_debounce_and_dedup(self):
        down = {**self.up, 'penpot': False}
        self.assertEqual(probe.transition(self.state, down, 220), [])
        pending = probe.transition(self.state, down, 280)
        self.assertEqual([(x['check'], x['phase']) for x in pending], [('penpot', 'firing')])
        sent = []
        probe.deliver_one(self.state, pending, 280, lambda p: sent.append(json.loads(p)) or True)
        self.assertEqual(probe.transition(self.state, down, 340), [])
        self.assertEqual(probe.transition(self.state, self.up, 400), [])
        resolved = probe.transition(self.state, self.up, 460)
        self.assertEqual(resolved[0]['phase'], 'resolved')
        probe.deliver_one(self.state, resolved, 460, lambda p: sent.append(json.loads(p)) or True)
        self.assertEqual(probe.transition(self.state, self.up, 520), [])
        self.assertEqual(len(sent), 2)
        self.assertTrue(all(x['msg_type'] == 'text' for x in sent))

    def test_double_management_failure_merges_and_suppresses_services(self):
        all_down = {k: False for k in self.up}
        events = self.twice(all_down)
        self.assertEqual([(x['check'], x['phase']) for x in events], [('pve-host', 'firing')])
        probe.deliver_one(self.state, events, 280, lambda p: True)
        self.assertEqual(self.twice(all_down, 340), [])
        events = self.twice(self.up, 460)
        self.assertEqual([(x['check'], x['phase']) for x in events], [('pve-host', 'resolved')])

    def test_one_management_port_failure_does_not_report_host(self):
        events = self.twice({**self.up, 'pve-ssh': False})
        self.assertEqual([(x['check'], x['phase']) for x in events], [('pve-ssh', 'firing')])

    def test_preexisting_service_alert_resolves_after_host_recovers(self):
        events = self.twice({**self.up, 'nexus': False})
        probe.deliver_one(self.state, events, 280, lambda p: True)
        events = self.twice({k: False for k in self.up}, 340)
        probe.deliver_one(self.state, events, 400, lambda p: True)
        events = self.twice(self.up, 460)
        self.assertEqual({(x['check'], x['phase']) for x in events}, {('pve-host', 'resolved'), ('nexus', 'resolved')})

    def test_failed_attempts_bounded_and_same_event_id_reused(self):
        events = self.twice({**self.up, 'penpot': False})
        ids = []
        for stamp in [280, 340, 400, 460, 520]:
            events = probe.transition(self.state, {**self.up, 'penpot': False}, stamp)
            result = probe.deliver_one(self.state, events, stamp, lambda p: False)
            if result:ids.append(result['id'])
        self.assertEqual(len(ids), 3)
        self.assertEqual(len(set(ids)), 1)
        self.assertTrue(self.state['incidents']['penpot']['pending']['exhausted'])

    def test_crash_after_third_reserved_attempt_never_sends_fourth(self):
        events = self.twice({**self.up, 'penpot': False})
        events[0].update(attempts=3, exhausted=False)
        with patch.object(probe, 'payload', side_effect=AssertionError('must not send')):
            self.assertIsNone(probe.deliver_one(self.state, events, 999, lambda p: True))
        self.assertTrue(events[0]['exhausted'])

    def test_recovery_before_failed_firing_delivery_cancels_stale_notice(self):
        events = self.twice({**self.up, 'nexus': False})
        probe.deliver_one(self.state, events, 280, lambda p: False)
        self.assertEqual(self.twice(self.up, 340), [])

    def test_sleep_gap_requires_two_fresh_observations(self):
        down = {**self.up, 'penpot': False}
        self.assertEqual(probe.transition(self.state, down, 220), [])
        self.assertEqual(probe.transition(self.state, down, 1000), [])
        self.assertEqual(probe.transition(self.state, down, 1060)[0]['phase'], 'firing')

    def test_gap_queued_unacknowledged_fault_never_sends_on_first_waking_up(self):
        events=self.twice({**self.up,'penpot':False})
        self.assertEqual(events[0]['phase'],'firing')
        first=probe.transition(self.state,self.up,1000)
        self.assertEqual(first,[])
        self.assertIsNone(probe.deliver_one(self.state,first,1000,lambda p: self.fail('stale firing')))
        self.assertEqual(probe.transition(self.state,self.up,1060),[])
        self.assertIsNone(self.state['incidents']['penpot']['pending'])

    def test_gap_acknowledged_fault_requires_two_fresh_up_before_recovery(self):
        events=self.twice({**self.up,'penpot':False})
        probe.deliver_one(self.state,events,280,lambda p:True)
        self.assertEqual(probe.transition(self.state,self.up,1000),[])
        events=probe.transition(self.state,self.up,1060)
        self.assertEqual([(x['check'],x['phase']) for x in events],[('penpot','resolved')])

    def test_gap_still_down_preserves_exhausted_event_and_budget(self):
        down={**self.up,'penpot':False}
        events=self.twice(down)
        for stamp in (280,340,400):
            events=probe.transition(self.state,down,stamp)
            probe.deliver_one(self.state,events,stamp,lambda p:False)
        old=json.loads(json.dumps(self.state['incidents']['penpot']['pending']))
        self.assertEqual(probe.transition(self.state,down,1000),[])
        events=probe.transition(self.state,down,1060)
        self.assertEqual(events[0],old)
        self.assertIsNone(probe.deliver_one(self.state,events,1060,lambda p:self.fail('budget reset')))

    def test_clock_rollback_holds_stale_fault_then_cancels_after_two_up(self):
        self.twice({**self.up,'nexus':False})
        self.assertEqual(probe.transition(self.state,self.up,100),[])
        self.assertIsNone(self.state['checks']['nexus']['stable'])
        self.assertEqual(probe.transition(self.state,self.up,160),[])
        self.assertIsNone(self.state['incidents']['nexus']['pending'])

    def test_clock_rollback_acknowledged_fault_needs_two_up_for_resolved(self):
        events=self.twice({**self.up,'jellyfin':False})
        probe.deliver_one(self.state,events,280,lambda p:True)
        self.assertEqual(probe.transition(self.state,self.up,100),[])
        events=probe.transition(self.state,self.up,160)
        self.assertEqual([(x['check'],x['phase']) for x in events],[('jellyfin','resolved')])

    def test_clock_rollback_preserves_ack_and_exhausted_budget(self):
        down={**self.up,'nexus':False}
        events=self.twice(down)
        for stamp in (280,340,400):
            events=probe.transition(self.state,down,stamp)
            probe.deliver_one(self.state,events,stamp,lambda p:False)
        old=json.loads(json.dumps(self.state['incidents']['nexus']['pending']))
        self.assertEqual(probe.transition(self.state,down,100),[])
        events=probe.transition(self.state,down,160)
        self.assertEqual(events[0],old)
        self.assertIsNone(probe.deliver_one(self.state,events,160,lambda p:self.fail('budget reset')))

    def test_restart_persists_dedup_and_attempt_budget(self):
        events = self.twice({**self.up, 'jellyfin': False})
        probe.deliver_one(self.state, events, 280, lambda p: False)
        restarted = json.loads(json.dumps(self.state))
        events = probe.transition(restarted, {**self.up, 'jellyfin': False}, 340)
        event = probe.deliver_one(restarted, events, 340, lambda p: True)
        self.assertEqual(event['attempt'], 2)
        self.assertEqual(probe.transition(restarted, {**self.up, 'jellyfin': False}, 400), [])


class SafetyTests(unittest.TestCase):
    HOOK = b'https://open.larksuite.com/open-apis/bot/v2/hook/00000000-0000-0000-0000-000000000000'

    def test_webhook_rejects_other_hosts_redirect_targets_and_credentials(self):
        for raw in [b'http://open.larksuite.com/open-apis/bot/v2/hook/00000000-0000-0000-0000-000000000000',
                    self.HOOK + b'?x=y', self.HOOK + b'#x', self.HOOK.replace(b'open.larksuite.com', b'other.invalid'),
                    self.HOOK.replace(b'open.larksuite.com', b'user:pass@open.larksuite.com'), self.HOOK + b'\nheader=x']:
            with self.assertRaises(probe.Rejected):probe.validate_hook(raw)
        self.assertTrue(probe.validate_hook(self.HOOK).startswith('https:'))

    def test_native_http_fixed_no_proxy_no_body_no_redirect(self):
        with patch.object(probe.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, b'200')) as run:
            result = probe.probe_one(probe.CHECKS[2])
        self.assertTrue(result['ok'])
        args, kw = run.call_args
        self.assertEqual(args[0][0:2], ['/usr/bin/curl', '-q'])
        for opt in ['--noproxy', '--output', '--max-redirs']:self.assertIn(opt, args[0])
        self.assertIn('/dev/null', args[0]);self.assertNotIn('--location', args[0]);self.assertNotIn('--insecure', args[0])
        self.assertEqual(kw['env'], probe.ENV)
        with self.assertRaises(probe.Rejected):probe.probe_one(('arbitrary', 'http', 1234, '/'))

    def test_notification_secret_and_payload_stdin_only_and_code_zero_required(self):
        body = b'{"msg_type":"text","content":{"text":"mock"}}'
        for response, expected in [(b'{"code":0}\n200', True), (b'{"code":1}\n200', False),
                                   (b'{"StatusCode":0}\n200', False), (b'{"code":false}\n200', False),
                                   (b'{"code":0}\n302', False), (b'not json\n200', False)]:
            with patch.object(probe, 'read_private', return_value=self.HOOK), patch.object(probe.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, response)) as run:
                self.assertEqual(probe.send_lark(body), expected)
            args, kw = run.call_args
            self.assertNotIn(self.HOOK.decode(), ' '.join(args[0]))
            self.assertNotIn('msg_type', ' '.join(args[0]))
            self.assertIn(self.HOOK, kw['input']);self.assertIn(b'msg_type', kw['input'])
            self.assertEqual(kw['env'], probe.ENV)
            self.assertEqual(args[0][0:4], ['/usr/bin/curl', '-q', '--config', '-'])
            self.assertNotIn('--insecure', args[0]);self.assertNotIn('--location', args[0])

    def test_private_file_rejects_permissive_mode_and_symlink(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / 's';p.write_bytes(b'mock');p.chmod(0o644)
            with self.assertRaises(probe.Rejected):probe.read_private(p)
            p.chmod(0o600);self.assertEqual(probe.read_private(p), b'mock')
            link = Path(td) / 'link';link.symlink_to(p)
            with self.assertRaises(OSError):probe.read_private(link)

    def test_dry_run_never_reads_hook_or_calls_sender(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td);path.chmod(0o700)
            with patch.object(probe, 'PRIVATE', path), patch.object(probe, 'private_dir'), patch.object(probe, 'sample', return_value={'at':'mock','results':[{'name':k,'ok':False} for k in probe.KEYS[1:]]}), patch.object(probe, 'send_lark', side_effect=AssertionError('must not send')):
                probe.run(False);result=probe.run(False)
            self.assertEqual(result['delivery']['pending_count'], 1)
            for item in path.iterdir():self.assertEqual(item.stat().st_mode & 0o777, 0o600)


class AcceptanceTests(unittest.TestCase):
    def module(self):
        spec = importlib.util.spec_from_file_location('acceptance', Path(__file__).with_name('acceptance.py'))
        module = importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        return module

    def test_acceptance_plan_does_not_read_hook(self):
        module=self.module()
        with patch.object(module.probe,'read_private',side_effect=AssertionError('must not read')):
            self.assertFalse(module.execute('firing',False)['hook_read'])
            self.assertFalse(module.execute('resolved',False)['hook_read'])

    def test_fixed_acceptance_order_code_ack_and_duplicate(self):
        module=self.module()
        with tempfile.TemporaryDirectory() as td:
            path=Path(td);path.chmod(0o700)
            with patch.object(module.probe,'PRIVATE',path), patch.object(module.probe,'private_dir'), patch.object(module.probe,'send_lark',return_value=True) as sender:
                with self.assertRaises(module.probe.Rejected):module.execute('resolved',True)
                self.assertTrue(module.execute('firing',True)['acknowledged'])
                self.assertEqual(module.execute('firing',True)['mode'],'already-acknowledged')
                self.assertTrue(module.execute('resolved',True)['acknowledged'])
                self.assertEqual(sender.call_count,2)
                for call in sender.call_args_list:
                    data=json.loads(call.args[0]);self.assertIn('【验收】',data['content']['text'])
                    self.assertIn('DellMacExternalProbeAcceptance',data['content']['text'])
            self.assertFalse((path/'state.json').exists())
            for item in path.iterdir():self.assertEqual(item.stat().st_mode&0o777,0o600)

    def test_acceptance_failure_reserves_attempt_and_blocks_resolved(self):
        module=self.module()
        with tempfile.TemporaryDirectory() as td:
            path=Path(td);path.chmod(0o700)
            with patch.object(module.probe,'PRIVATE',path), patch.object(module.probe,'private_dir'), patch.object(module.probe,'send_lark',return_value=False) as sender:
                self.assertFalse(module.execute('firing',True)['acknowledged'])
                with self.assertRaises(module.probe.Rejected):module.execute('resolved',True)
                with self.assertRaises(module.probe.Rejected):module.execute('firing',True)
                self.assertEqual(sender.call_count,1)


if __name__ == '__main__':
    unittest.main()
