#!/usr/bin/env python3
"""Regression for exact service readability under a restrictive parent umask."""
import importlib.util,os,pathlib,stat,tempfile,unittest
p=pathlib.Path(__file__).with_name('gateway-dns.py');spec=importlib.util.spec_from_file_location('dns_update',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class DNSPermissions(unittest.TestCase):
 def test_dns_readable_with_private_umask_and_root_config_private(self):
  with tempfile.TemporaryDirectory()as d:
   old=os.umask(0o077)
   try:
    for n,mode in [('dnsmasq.conf',0o644),('config.json',0o600)]:
     dest=pathlib.Path(d)/n;m.put(dest,b'synthetic\n',mode);self.assertEqual(stat.S_IMODE(dest.stat().st_mode),mode);self.assertEqual(dest.read_bytes(),b'synthetic\n')
   finally:os.umask(old)
if __name__=='__main__':unittest.main()
