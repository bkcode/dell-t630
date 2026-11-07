import importlib.util
import unittest
from pathlib import Path
s=importlib.util.spec_from_file_location('changes',Path(__file__).with_name('changes.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m)

class SourceRecognitionTests(unittest.TestCase):
    def fixture(self,newline='\n'):
        return ('<?xml version="1.0"?>'+newline+'<NetworkConfiguration>'+newline+'  <EnableRemoteAccess>false</EnableRemoteAccess>'+newline+'  <EnableUPnP>false</EnableUPnP>'+newline+'  <CertificatePassword>fixture-keep-exact-not-real-secret</CertificatePassword>'+newline+'  <LocalNetworkSubnets>'+newline+''.join('    <string>'+x+'</string>'+newline for x in m.JF_OLD)+'  </LocalNetworkSubnets>'+newline+'</NetworkConfiguration>'+newline).encode()

    def test_smb_only_hostsallow_is_appended_and_original_untouched(self):
        before={'uuid':'same','hostsallow':m.SMB_OLD,'hostsdeny':'','readonly':False,'guest':'no','extraoptions':'unchanged','write_list':['naswriter']}
        after=m.smb_parameters(before)
        self.assertEqual(after['hostsallow'],m.SMB_NEW)
        restored=dict(after,hostsallow=m.SMB_OLD);self.assertEqual(restored,before)
        self.assertEqual(before['hostsallow'],m.SMB_OLD)
        after['write_list'].append('test');self.assertEqual(before['write_list'],['naswriter'])

    def test_smb_drift_or_duplicate_fails_closed(self):
        for value in [m.SMB_NEW,'ALL','192.168.19.0/24','10.66.66.3']:
            with self.assertRaises(ValueError):m.smb_parameters({'hostsallow':value})

    def test_xml_only_one_new_member_bytes_added_lf(self):
        raw=self.fixture();result=m.xml_append(raw)
        insertion=b'    <string>10.66.66.0/24</string>\n'
        self.assertEqual(result.replace(insertion,b'',1),raw)
        self.assertIn(b'<CertificatePassword>fixture-keep-exact-not-real-secret</CertificatePassword>',result)

    def test_xml_crlf_and_other_values_preserved(self):
        raw=self.fixture('\r\n');result=m.xml_append(raw)
        self.assertEqual(result.replace(b'    <string>10.66.66.0/24</string>\r\n',b'',1),raw)

    def test_compact_xml_append_without_reformat(self):
        raw=self.fixture().replace(b'\n',b'').replace(b'  ',b'')
        result=m.xml_append(raw)
        self.assertEqual(result.replace(b'<string>10.66.66.0/24</string>',b'',1),raw)

    def test_jellyfin_mixed_format_inline_closing_tag_preserves_all_old_bytes(self):
        raw=self.fixture().replace(b'\n  </LocalNetworkSubnets>',b'</LocalNetworkSubnets>')
        result=m.xml_append(raw)
        self.assertEqual(result.replace(b'<string>10.66.66.0/24</string>',b'',1),raw)

    def test_xml_duplicate_vpn_and_wrong_old_subnet_rejected(self):
        for raw in [m.xml_append(self.fixture()),self.fixture().replace(b'192.168.19.0/24',b'192.168.20.0/24')]:
            with self.assertRaises(ValueError):m.xml_append(raw)

    def test_xml_auth_safety_policy_must_already_be_disabled(self):
        for key in [b'EnableRemoteAccess',b'EnableUPnP']:
            raw=self.fixture().replace(b'<'+key+b'>false</'+key+b'>',b'<'+key+b'>true</'+key+b'>')
            with self.assertRaises(ValueError):m.xml_append(raw)

if __name__=='__main__':unittest.main()
