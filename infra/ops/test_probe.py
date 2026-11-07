#!/usr/bin/env python3
"""Offline validation of optional probe endpoint restrictions; no sockets opened."""
import importlib.util, json, sys, unittest
from pathlib import Path
from unittest.mock import MagicMock,patch
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('dell_ops_probe',HERE/'scripts'/'external-probe.py')
probe=importlib.util.module_from_spec(spec);spec.loader.exec_module(probe)

class ProbeSafety(unittest.TestCase):
    def test_credentials_rejected(self):
        with self.assertRaises(ValueError):probe.endpoint({'name':'bad','url':'http://user:pass@192.168.21.22/health'})
    def test_query_rejected(self):
        with self.assertRaises(ValueError):probe.endpoint({'name':'bad','url':'http://192.168.21.22/health?token=value'})
    def test_business_path_rejected(self):
        with self.assertRaises(ValueError):probe.endpoint({'name':'bad','url':'http://192.168.21.22/orders/create'})
    def test_public_address_rejected(self):
        with self.assertRaises(ValueError):probe.endpoint({'name':'bad','url':'https://8.8.8.8/health'})
    def test_hostname_does_not_trigger_dns_lookup(self):
        with self.assertRaises(ValueError):probe.endpoint({'name':'bad','url':'https://example.com/health'})
    def test_redirects_are_not_followed(self):
        self.assertIsNone(probe.NoRedirect().redirect_request(None,None,None,None,None,None))
    def test_http_body_not_in_report(self):
        item=probe.endpoint({'name':'health','url':'http://127.0.0.1:33000/api/health'})
        response=MagicMock();response.__enter__.return_value.status=200;response.__enter__.return_value.read.return_value=b'private-response-body'
        opener=MagicMock();opener.open.return_value=response
        with patch.object(probe.urllib.request,'build_opener',return_value=opener):result=probe.probe(item,1)
        self.assertEqual(result['status'],'passed');self.assertNotIn('private-response-body',json.dumps(result))
    def test_tcp_records_only_port_availability(self):
        item=probe.endpoint({'name':'pve-ssh','url':'tcp://192.168.21.22:22'})
        with patch.object(probe.socket,'create_connection',return_value=MagicMock()) as connect:
            result=probe.probe(item,1)
            connect.assert_called_once_with(('192.168.21.22',22),timeout=1)
        self.assertEqual(result['status'],'passed');self.assertIn('TCP connection only',result['evidence'])

class NativeHelpSafety(unittest.TestCase):
    def setUp(self):
        spec=importlib.util.spec_from_file_location('dell_ops_native',HERE/'validate-native.py')
        self.native=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.native)
    def test_optional_boolean_flag_is_recognized(self):
        self.assertTrue(self.native.supports_config_check('--[no-]config.check  validate then exit'))
    def test_plain_flag_is_recognized(self):
        self.assertTrue(self.native.supports_config_check('--config.check=true'))
    def test_server_only_flag_does_not_trigger_a_start(self):
        self.assertFalse(self.native.supports_config_check('--config.file blackbox.yml --web.listen-address=:9115'))

if __name__=='__main__':unittest.main()
