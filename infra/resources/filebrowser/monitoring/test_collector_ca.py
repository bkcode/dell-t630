import http.server,importlib.util,json,os,ssl,stat,subprocess,tempfile,threading,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
BASE=Path(__file__).resolve().parent;SOURCE=BASE.parents[2]/'ops/guest-baseline/collect-guest-health.py'
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
new=load('newcollector',SOURCE);old=load('oldcollector',BASE/'collect-guest-health.before.py')
CA='/etc/dell-filebrowser/tls.crt'
def cfg(check=None):
 return {'role':'resource-service','private_ip':'192.168.19.80','textfile_directory':str(new.TEXTFILE_DIR),'services':['nfs-server.service','dell-resources-firewall.service','dell-filebrowser.service'],'http_checks':[check] if check else []}
class FakeParent:
 def __init__(self):self.parents=[]
 def lstat(self):return SimpleNamespace(st_mode=stat.S_IFDIR|0o755,st_uid=0)
class FakeCA:
 def __init__(self,uid=0,mode=0o644,payload=b'-----BEGIN CERTIFICATE-----\nPUBLIC\n-----END CERTIFICATE-----\n',symlink=False):self.parent=FakeParent();self.uid=uid;self.mode=mode;self.payload=payload;self.symlink=symlink
 def resolve(self,strict=False):return object() if self.symlink else self
 def lstat(self):return SimpleNamespace(st_mode=stat.S_IFREG|self.mode,st_uid=self.uid,st_size=len(self.payload))
 def read_bytes(self):return self.payload
class SchemaTests(unittest.TestCase):
 def test_exact_public_CA_allowed_only_verifiedHTTPS(self):
  with patch.object(new,'Path',return_value=FakeCA()),patch.object(new.os,'access',return_value=True):
   new.validate(cfg({'name':'filebrowser','url':'https://192.168.19.80:8080/health','ca_file':CA}),{'192.168.19.80'})
  for check in [{'name':'x','url':'http://192.168.19.80:8080/health','ca_file':CA},{'name':'x','url':'https://192.168.19.80:8080/health','ca_file':'/tmp/untrusted.crt'},{'name':'x','url':'https://192.168.19.80:8080/health','ca_file':None}]:
   with self.assertRaises(ValueError):new.validate(cfg(check),{'192.168.19.80'})
 def test_owner_mode_readable_symlink_privatekey_rejected(self):
  for fake in [FakeCA(uid=1000),FakeCA(mode=0o666),FakeCA(mode=0o600),FakeCA(symlink=True),FakeCA(payload=b'-----BEGIN CERTIFICATE-----\nSYNTHETIC PUBLIC DATA\nPRIVATE KEY material forbidden\n')]:
   with patch.object(new,'Path',return_value=fake),patch.object(new.os,'access',return_value=True):
    with self.assertRaises(ValueError):new.ca_file_for('https://192.168.19.80:8080/health',CA)
  with patch.object(new,'Path',return_value=FakeCA()),patch.object(new.os,'access',return_value=False):
   with self.assertRaises(ValueError):new.ca_file_for('https://192.168.19.80:8080/health',CA)
 def test_untrusted_ancestor_rejected(self):
  fake=FakeCA();fake.parent.lstat=lambda:SimpleNamespace(st_mode=stat.S_IFDIR|0o777,st_uid=0)
  with patch.object(new,'Path',return_value=fake):
   with self.assertRaises(ValueError):new.ca_file_for('https://192.168.19.80:8080/health',CA)
 def test_otherguest_auth_query_headers_still_rejected(self):
  cases=[{'name':'x','url':'https://192.168.19.50:8080/health','ca_file':CA},{'name':'x','url':'https://u:p@192.168.19.80:8080/health','ca_file':CA},{'name':'x','url':'https://192.168.19.80:8080/health?token=x','ca_file':CA},{'name':'x','url':'https://192.168.19.80:8080/health','ca_file':CA,'headers':{'Authorization':'x'}}]
  for check in cases:
   with self.assertRaises(ValueError):new.validate(cfg(check),{'192.168.19.80'})
 def test_legacyvalidate_and_collect_metrics_identical(self):
  for url in ['http://192.168.19.80:8080/health','https://192.168.19.80:8080/health','http://127.0.0.1:9999/actuator/health/readiness']:
   c=cfg({'name':'same','url':url});self.assertEqual(new.validate(c,{'192.168.19.80','127.0.0.1'}),old.validate(c,{'192.168.19.80','127.0.0.1'}))
   with patch.object(new,'unit_state',return_value=(1,1,True)),patch.object(new,'http_state',return_value=(1,200)) as newhttp,patch.object(old,'unit_state',return_value=(1,1,True)),patch.object(old,'http_state',return_value=(1,200)),patch.object(new.time,'time',return_value=123):
    self.assertEqual(new.collect(c),old.collect(c));self.assertEqual(newhttp.call_args.args,(url,))
 def test_legacy_opener_path_unchanged(self):
  response=SimpleNamespace(status=200,read=lambda n:b'public-health')
  class Context:
   def __enter__(self):return response
   def __exit__(self,*args):pass
  for module in [old,new]:
   with patch.object(module.urllib.request,'build_opener') as build:
    build.return_value.open.return_value=Context();self.assertEqual(module.http_state('http://127.0.0.1/health'),(1,200));self.assertEqual(build.call_args.args,(module.NoRedirect,));self.assertEqual(build.return_value.open.call_args.kwargs,{'timeout':3})
 def test_failure_status_remains_visible(self):
  c=cfg({'name':'filebrowser','url':'https://192.168.19.80:8080/health','ca_file':CA})
  with patch.object(new,'unit_state',return_value=(1,1,True)),patch.object(new,'http_state',return_value=(0,0)) as http:
   body,ok=new.collect(c)
  self.assertIn('dell_guest_http_up{role="resource-service",check="filebrowser"} 0',body);self.assertTrue(ok);self.assertEqual(http.call_args.args,(c['http_checks'][0]['url'],CA))
class LocalTLSTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tmp=tempfile.TemporaryDirectory();cls.base=Path(cls.tmp.name).resolve()
  for name,ip in [('good','127.0.0.1'),('other','127.0.0.1'),('wronghost','127.0.0.2')]:
   cert=cls.base/(name+'.crt');key=cls.base/(name+'.key')
   subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-days','1','-keyout',str(key),'-out',str(cert),'-subj','/CN=Dell-monitor-fixture','-addext','subjectAltName=IP:'+ip],capture_output=True,check=True,timeout=30);key.chmod(0o600)
 @classmethod
 def tearDownClass(cls):cls.tmp.cleanup()
 def server(self,name,status=200):
  class Handler(http.server.BaseHTTPRequestHandler):
   def do_GET(self):self.send_response(status);self.end_headers();self.wfile.write(b'public fixture')
   def log_message(self,*args):pass
  server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler);context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);context.load_cert_chain(self.base/(name+'.crt'),self.base/(name+'.key'));server.socket=context.wrap_socket(server.socket,server_side=True);threading.Thread(target=server.serve_forever,daemon=True).start();return server
 def test_real_dedicated_CA_success_system_CA_failure(self):
  server=self.server('good')
  try:
   url='https://127.0.0.1:'+str(server.server_port)+'/health'
   with patch.object(new,'ca_file_for',return_value=self.base/'good.crt'):self.assertEqual(new.http_state(url,CA),(1,200))
   self.assertEqual(new.http_state(url),(0,0))
  finally:server.shutdown();server.server_close()
 def test_wrong_CA_and_hostname_fail_with_validation_enabled(self):
  for name,ca in [('good','other'),('wronghost','wronghost')]:
   server=self.server(name)
   try:
    with patch.object(new,'ca_file_for',return_value=self.base/(ca+'.crt')):self.assertEqual(new.http_state('https://127.0.0.1:'+str(server.server_port)+'/health',CA),(0,0))
   finally:server.shutdown();server.server_close()
 def test_HTTPS_error_returns_real_status(self):
  server=self.server('good',503)
  try:
   with patch.object(new,'ca_file_for',return_value=self.base/'good.crt'):self.assertEqual(new.http_state('https://127.0.0.1:'+str(server.server_port)+'/health',CA),(0,503))
  finally:server.shutdown();server.server_close()
if __name__=='__main__':unittest.main()
