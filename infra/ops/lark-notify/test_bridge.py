#!/usr/bin/env python3
"""Pure/mock/loopback tests. Never read the supplied webhook or send to Lark."""
import contextlib,copy,http.client,importlib.util,io,json,socket,subprocess,sys,threading,time,unittest,urllib.error
from pathlib import Path
from unittest.mock import patch
sys.dont_write_bytecode=True;sys.path.insert(0,str(Path(__file__).resolve().parent))
import bridge as b
import configuration as c
TOKEN='A'*64;FAKE_URL='https://open.larksuite.com/open-apis/bot/v2/hook/'+'00000000-0000-0000-0000-000000000000'
def fixture(phase='firing'):
 return {'version':'4','status':phase,'receiver':'lark-acceptance','externalURL':'DO_NOT_FORWARD','groupKey':'DO_NOT_FORWARD','alerts':[{'status':phase,'startsAt':'2026-11-06T04:00:00.123456789Z','fingerprint':'0123456789abcdef','labels':{'alertname':'DellLarkNotificationAcceptance','role':'ops-service','severity':'info','dell_acceptance':'lark-notify','acceptance_run':'a'*32,'password':'DO_NOT_FORWARD'},'annotations':{'summary':'DO_NOT_FORWARD','description':FAKE_URL},'generatorURL':'DO_NOT_FORWARD'}]}
def raw(value=None):return json.dumps(fixture() if value is None else value).encode()
class Validation(unittest.TestCase):
 def test_exact_https_url_allowlist(self):
  self.assertEqual(b.validate_url(FAKE_URL),FAKE_URL)
  for value in [FAKE_URL.replace('https:','http:'),FAKE_URL.replace('open.larksuite.com','open.larksuite.com.evil'),FAKE_URL.replace('open.larksuite.com','u@open.larksuite.com'),FAKE_URL.replace('open.larksuite.com','open.larksuite.com:443'),FAKE_URL+'?leak=x',FAKE_URL+'#x',FAKE_URL+'/',FAKE_URL.replace('/hook/','/hook/../hook/')]:
   with self.assertRaises(b.Rejected):b.validate_url(value)
 def test_payload_only_whitelisted_labels_and_static_descriptions(self):
  payload,receipt=b.render(raw(),'acceptance');text=payload.decode();self.assertNotIn('DO_NOT_FORWARD',text);self.assertNotIn(FAKE_URL,text);self.assertIn('验收',text);self.assertEqual(receipt['phase'],'firing');self.assertLess(len(payload),b.MAX_LARK)
 def test_resolved_separate_message(self):
  first,_=b.render(raw(),'acceptance');second,r=b.render(raw(fixture('resolved')),'acceptance');self.assertNotEqual(first,second);self.assertIn('恢复',second.decode());self.assertEqual(r['phase'],'resolved')
 def test_real_alert_rejected_in_acceptance_mode(self):
  f=fixture();f['alerts'][0]['labels']={'alertname':'PveRaidDegraded','severity':'critical'}
  with self.assertRaises(b.Rejected):b.render(raw(f),'acceptance')
  text,_=b.render(raw(f),'active');self.assertIn('RAID',text.decode())
 def test_unknown_alert_and_malformed_or_secret_like_labels_rejected(self):
  for name,value in [('alertname','Untrusted'),('role','unknown-role'),('check','https://secret.example/'),('unit','<at>'),('severity','very-high')]:
   f=fixture();f['alerts'][0]['labels'][name]=value
   with self.assertRaises(b.Rejected):b.render(raw(f),'active')
 def test_acceptance_requires_exact_labels(self):
  for name in ['dell_acceptance','acceptance_run','role','severity']:
   f=fixture();f['alerts'][0]['labels'].pop(name)
   with self.assertRaises(b.Rejected):b.render(raw(f),'acceptance')
 def test_duplicate_json_and_batch_overflow_rejected(self):
  with self.assertRaises(b.Rejected):b.render(b'{"version":"4","version":"4"}','acceptance')
  f=fixture();f['alerts']*=17
  with self.assertRaises(b.Rejected):b.render(raw(f),'acceptance')
 def test_group_phase_consistent(self):
  f=fixture();f['status']='resolved'
  with self.assertRaises(b.Rejected):b.render(raw(f),'acceptance')
 def test_policy_routes_acceptance_only_then_whitelisted_active(self):
  initial=c.render('acceptance');active=c.render('active');self.assertEqual(initial['route']['receiver'],'local-only');self.assertEqual(len(initial['route']['routes']),1);self.assertEqual(len(active['route']['routes']),2);text=json.dumps(active);self.assertNotIn('open.larksuite.com',text);self.assertIn('credentials_file',text)
class Delivery(unittest.TestCase):
 def test_lark_200_integer_code_zero_required(self):
  class Response:
   def __init__(self,value,status=200):self.value=value;self.status=status
   def __enter__(self):return self
   def __exit__(self,*a):pass
   def read(self,n):return self.value
  sender=b.LarkSender(FAKE_URL)
  for value in [{'code':1},{'StatusCode':0},{'code':False},{'code':'0'},None]:
   with patch.object(sender.opener,'open',return_value=Response(json.dumps(value).encode())):
    with self.assertRaises(b.DeliveryFailed):sender(b'{}')
  with patch.object(sender.opener,'open',return_value=Response(b'{"code":0}')):self.assertEqual(sender(b'{}'),0)
  with patch.object(sender.opener,'open',return_value=Response(b'{"code":0}',302)):
   with self.assertRaises(b.DeliveryFailed):sender(b'{}')
 def test_redirects_disabled_and_proxy_handler_empty(self):
  self.assertIsNone(b.NoRedirect().redirect_request(None,None,302,'','',FAKE_URL));sender=b.LarkSender(FAKE_URL)
  self.assertFalse(any(isinstance(x,__import__('urllib.request',fromlist=['ProxyHandler']).ProxyHandler) and x.proxies for x in sender.opener.handlers))
 def test_absolute_worker_deadline_and_no_secret_argv_env(self):
  sender=b.BoundedSender(Path('/run/credentials/test'))
  with patch.object(b.subprocess,'run',side_effect=subprocess.TimeoutExpired('fixed-worker',15)) as run:
   with self.assertRaises(b.DeliveryFailed):sender(b'{}')
   self.assertEqual(run.call_args.kwargs['timeout'],15);self.assertNotIn(FAKE_URL,str(run.call_args.args)+str(run.call_args.kwargs['env']))
 def test_new_failure_cycle_after_resolved_is_not_suppressed(self):
  calls=[];ctx=b.Context(TOKEN,'acceptance',lambda p:calls.append(p));first=fixture();resolved=fixture('resolved');again=fixture();again['alerts'][0]['startsAt']='2026-11-06T04:01:00.123456789Z'
  with contextlib.redirect_stdout(io.StringIO()):
   a=ctx.deliver(raw(first));self.assertTrue(ctx.deliver(raw(first))['cached']);ctx.deliver(raw(resolved));n=ctx.deliver(raw(again));self.assertTrue(ctx.deliver(raw(again))['cached'])
  self.assertEqual(len(calls),3);self.assertEqual(calls[0],calls[2]);self.assertEqual(a['payload_sha256'],n['payload_sha256']);self.assertNotEqual(a['event_key_sha256'],n['event_key_sha256']);self.assertFalse(n['cached'])
 def test_identity_uses_full_nanoseconds_and_normalizes_timezone(self):
  f=fixture();p1,r1=b.render(raw(f),'acceptance');f['alerts'][0]['startsAt']='2026-11-06T12:00:00.123456789+08:00';p2,r2=b.render(raw(f),'acceptance');self.assertEqual(r1['event_key_sha256'],r2['event_key_sha256'])
  f['alerts'][0]['startsAt']='2026-11-06T12:00:00.123456790+08:00';p3,r3=b.render(raw(f),'acceptance');self.assertEqual(p1,p3);self.assertNotEqual(r1['event_key_sha256'],r3['event_key_sha256'])
 def test_event_identity_required_and_validated(self):
  for key,value in [('startsAt',None),('startsAt','2026-02-30T00:00:00Z'),('startsAt','0001-01-01T00:00:00Z'),('startsAt','2026-11-06T00:00:00'),('fingerprint','bad'),('fingerprint',None)]:
   f=fixture();f['alerts'][0][key]=value
   with self.assertRaises(b.Rejected):b.render(raw(f),'acceptance')
 def test_current_service_metric_label_is_forwarded_safely(self):
  f=fixture();f['alerts'][0]['labels']['service']='dell-ops.service';payload,_=b.render(raw(f),'acceptance');self.assertIn('service=dell-ops.service',payload.decode());self.assertNotIn('startsAt',payload.decode());self.assertNotIn('fingerprint',payload.decode())
 def test_static_existing_compose_network_reserves_am_source(self):
  import yaml
  model=yaml.safe_load((Path(__file__).resolve().parent.parent/'compose.yaml').read_text());self.assertEqual(model['networks']['default']['ipam']['config'],[{'subnet':'172.18.0.0/16','gateway':'172.18.0.1'}]);ips=[row['networks']['default']['ipv4_address'] for row in model['services'].values()];self.assertEqual(len(set(ips)),4);self.assertEqual(model['services']['alertmanager']['networks']['default']['ipv4_address'],b.SOURCE);self.assertTrue(all(row['pids_limit']==1024 for row in model['services'].values()))
 def test_success_deduplicated_failed_request_retried(self):
  calls=[];ctx=b.Context(TOKEN,'acceptance',lambda p:calls.append(p));sink=io.StringIO()
  with contextlib.redirect_stdout(sink):self.assertFalse(ctx.deliver(raw())['cached']);self.assertTrue(ctx.deliver(raw())['cached']);ctx.deliver(raw(fixture('resolved')))
  self.assertEqual(len(calls),2);self.assertNotIn(FAKE_URL,sink.getvalue());self.assertNotIn('DO_NOT_FORWARD',sink.getvalue())
  def fail(p):raise OSError('DO_NOT_FORWARD '+FAKE_URL)
  ctx=b.Context(TOKEN,'acceptance',fail)
  with contextlib.redirect_stdout(sink):
   for _ in range(2):
    with self.assertRaises(b.DeliveryFailed):ctx.deliver(raw())
  self.assertFalse(ctx.inflight);self.assertNotIn(FAKE_URL,sink.getvalue())
class SecretLifecycle(unittest.TestCase):
 @staticmethod
 def load(name,path):
  spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
 def test_stable_secret_preserved_and_conflict_refused(self):
  import tempfile
  prep=self.load('ops_prepare',Path(__file__).resolve().parent.parent/'prepare.py')
  with tempfile.TemporaryDirectory() as tmp:
   private=Path(tmp).resolve();bundle=private/'bundle';bundle.mkdir()
   self.assertEqual(prep.stable_bridge_token(private,bundle),'generated');first=(private/'lark-bridge-token').read_bytes();self.assertEqual(prep.stable_bridge_token(private,bundle),'preserved');self.assertEqual((bundle/'secrets/lark-bridge-token').read_bytes(),first)
   (bundle/'secrets/lark-bridge-token').write_text('B'*64+'\n')
   with self.assertRaisesRegex(ValueError,'differ'):prep.stable_bridge_token(private,bundle)
 def test_generic_prepare_refuses_existing_receiver_or_state(self):
  import tempfile
  prep=self.load('ops_prepare',Path(__file__).resolve().parent.parent/'prepare.py')
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp).resolve();bundle=root/'bundle';config=bundle/'config/alertmanager';config.mkdir(parents=True);baseline=root/'baseline';baseline.write_text('local-only\n');(config/'alertmanager.yml').write_bytes(baseline.read_bytes());prep.guard_notification_reprepare(bundle,baseline)
   (config/'alertmanager.yml').write_text(c.dump('active'))
   with self.assertRaisesRegex(ValueError,'preserved'):prep.guard_notification_reprepare(bundle,baseline)
   (config/'alertmanager.yml').write_bytes(baseline.read_bytes());(bundle/'lark-notify-state.json').write_text('{}')
   with self.assertRaisesRegex(ValueError,'state'):prep.guard_notification_reprepare(bundle,baseline)
 def test_future_native_config_check_has_private_readonly_secret_mount(self):
  import tempfile
  manage=self.load('ops_manage',Path(__file__).resolve().parent.parent/'scripts/manage.py')
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp).resolve();(root/'images.lock.json').write_text(json.dumps({'images':{name:{'reference':'fixture@sha256:'+'a'*64} for name in ['prometheus','alertmanager','blackbox']}}))
   with patch.object(manage,'BUNDLE',root),patch.object(manage,'run',return_value='') as runner:manage.validate_native_config()
   args=next(call.args[0] for call in runner.call_args_list if '--entrypoint' in call.args[0] and '/bin/amtool' in call.args[0]);self.assertIn('type=bind,src='+str(root/'secrets/lark-bridge-token')+',dst=/run/secrets/lark-bridge-token,readonly',args);self.assertIn('none',args)
 def test_secret_never_public_config_and_forced_uid600(self):
  import tempfile
  prep=self.load('ops_prepare',Path(__file__).resolve().parent.parent/'prepare.py');manage=self.load('ops_manage',Path(__file__).resolve().parent.parent/'scripts/manage.py')
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp).resolve();bundle=root/'bundle';config=bundle/'config/alertmanager';config.mkdir(parents=True);baseline=root/'baseline';baseline.write_text('local-only\n');(config/'alertmanager.yml').write_bytes(baseline.read_bytes());(config/'bridge-auth').write_text('synthetic')
   with self.assertRaisesRegex(ValueError,'public config'):prep.guard_notification_reprepare(bundle,baseline)
   (bundle/'secrets').mkdir();token=bundle/'secrets/lark-bridge-token';token.write_text('A'*64+'\n')
   with patch.object(manage,'BUNDLE',bundle),patch.object(manage,'owner') as owner:manage.protect_bridge_token();owner.assert_called_once_with(token,(65534,65534),0o600)
   token.unlink();token.symlink_to(baseline)
   with patch.object(manage,'BUNDLE',bundle):
    with self.assertRaisesRegex(RuntimeError,'symlink'):manage.protect_bridge_token()

class NetworkDelta(unittest.TestCase):
 @staticmethod
 def tool():
  spec=importlib.util.spec_from_file_location('ops_net_rebuild',Path(__file__).resolve().parent/'rebuild270-network.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
 @staticmethod
 def models():
  before={'services':{name:{'image':'fixture@sha256:'+'a'*64,'pids_limit':1024,'mem_limit':'128m','networks':{'default':None},'ports':[],'volumes':[{'source':'/srv/dell-data/ops/'+name,'target':'/data'}]} for name in ['prometheus','alertmanager','grafana','blackbox']},'secrets':{},'networks':{'default':{'name':'dell-ops_default'}}};after=copy.deepcopy(before);ip={'prometheus':'172.18.0.2','alertmanager':'172.18.0.3','blackbox':'172.18.0.4','grafana':'172.18.0.5'}
  for name,row in after['services'].items():row['networks']={'default':{'ipv4_address':ip[name]}}
  after['services']['alertmanager']['secrets']=[{'source':'lark-bridge-token','target':'/run/secrets/lark-bridge-token'}];after['secrets']['lark-bridge-token']={'file':'/opt/dell/ops/secrets/lark-bridge-token'};after['networks']['default']={'name':'dell-ops_default','driver':'bridge','ipam':{'config':[{'subnet':'172.18.0.0/16','gateway':'172.18.0.1'}]}};return before,after
 def test_only_static_network_and_am_secret_delta_allowed(self):
  m=self.tool();before,after=self.models();m.validate_delta(before,after)
  for key,value in [('mem_limit','256m'),('pids_limit',128),('ports',[{'target':80}]),('volumes',[{'source':'/tmp/unsafe','target':'/data'}])]:
   bad=copy.deepcopy(after);bad['services']['grafana'][key]=value
   with self.assertRaisesRegex(RuntimeError,'drift'):m.validate_delta(before,bad)
 def test_changed_subnet_or_dynamic_am_source_rejected(self):
  m=self.tool();before,after=self.models();bad=copy.deepcopy(after);bad['networks']['default']['ipam']['config'][0]['subnet']='172.19.0.0/16'
  with self.assertRaises(RuntimeError):m.validate_delta(before,bad)
  bad=copy.deepcopy(after);bad['services']['alertmanager']['networks']={'default':None}
  with self.assertRaises(RuntimeError):m.validate_delta(before,bad)
 def test_extra_foreign_endpoint_rejects_before_down(self):
  from types import SimpleNamespace
  m=self.tool();n={'Driver':'bridge','IPAM':{'Config':[{'Subnet':'172.18.0.0/16','Gateway':'172.18.0.1'}]},'Containers':{name:{'Name':'dell-ops-'+name+'-1'} for name in m.NAMES}}
  with patch.object(m.subprocess,'run',return_value=SimpleNamespace(returncode=0,stdout=json.dumps([n]).encode())):self.assertIsNotNone(m.network())
  n['Containers']['foreign']={'Name':'foreign-app'}
  with patch.object(m.subprocess,'run',return_value=SimpleNamespace(returncode=0,stdout=json.dumps([n]).encode())):
   with self.assertRaisesRegex(RuntimeError,'exactly'):m.network()

class MetadataContract(unittest.TestCase):
 @staticmethod
 def load(name,path):
  spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
 def setup_contract(self,root,mode):
  bundle=root/'bundle';(bundle/'secrets').mkdir(parents=True);primary=root/'primary';primary.write_text('A'*64+'\n');primary.chmod(0o600);copy=bundle/'secrets/lark-bridge-token';copy.write_bytes(primary.read_bytes());copy.chmod(0o600)
  state=bundle/'lark-notify-state.json';state.write_text(json.dumps({'mode':mode,'owner':'native-lark-notify','generic_prepare':'refuse-reset'}));state.chmod(0o600)
  model={'services':{'alertmanager':{'secrets':[{'source':'lark-bridge-token','target':'/run/secrets/lark-bridge-token'}]}},'secrets':{'lark-bridge-token':{'file':str(copy)}}};return bundle,primary,model
 def test_no_marker_pseudo_active_is_rejected(self):
  import tempfile
  validator=self.load('ops_validate',Path(__file__).resolve().parent.parent/'validate.py')
  with tempfile.TemporaryDirectory() as tmp:
   bundle=Path(tmp).resolve()
   with self.assertRaises(AssertionError):validator.validate_notification_contract(c.render('active'),{},bundle)
   self.assertIsNone(validator.validate_notification_contract({'route':{'receiver':'local-only'},'receivers':[{'name':'local-only'}]}, {},bundle))
 def test_marker_acceptance_and_active_require_exact_renderer_and_mount(self):
  import tempfile
  validator=self.load('ops_validate',Path(__file__).resolve().parent.parent/'validate.py')
  for mode in ['acceptance','active']:
   with tempfile.TemporaryDirectory() as tmp:
    bundle,primary,model=self.setup_contract(Path(tmp).resolve(),mode);self.assertEqual(validator.validate_notification_contract(c.render(mode),model,bundle,primary),mode)
    wrong=c.render(mode);wrong['receivers'][1]['webhook_configs'][0]['url']='http://unreviewed.example/'
    with self.assertRaises(AssertionError):validator.validate_notification_contract(wrong,model,bundle,primary)
    wrong_model=copy.deepcopy(model);wrong_model['services']['alertmanager']['secrets']=[]
    with self.assertRaises(AssertionError):validator.validate_notification_contract(c.render(mode),wrong_model,bundle,primary)
 def test_bad_token_permissions_or_rotated_value_rejected(self):
  import tempfile
  validator=self.load('ops_validate',Path(__file__).resolve().parent.parent/'validate.py')
  with tempfile.TemporaryDirectory() as tmp:
   bundle,primary,model=self.setup_contract(Path(tmp).resolve(),'active');token=bundle/'secrets/lark-bridge-token';token.chmod(0o644)
   with self.assertRaises(AssertionError):validator.validate_notification_contract(c.render('active'),model,bundle,primary)
   token.chmod(0o600);token.write_text('B'*64+'\n')
   with self.assertRaises(AssertionError):validator.validate_notification_contract(c.render('active'),model,bundle,primary)
 def test_health_needs_legal_state_and_active_unit_without_sending(self):
  import tempfile
  from types import SimpleNamespace
  manage=self.load('ops_health',Path(__file__).resolve().parent.parent/'scripts/manage.py')
  with tempfile.TemporaryDirectory() as tmp:
   bundle,_,_=self.setup_contract(Path(tmp).resolve(),'active')
   with patch.object(manage,'BUNDLE',bundle),patch.object(manage.subprocess,'run',return_value=SimpleNamespace(returncode=0)):
    value=manage.notification_metadata();self.assertEqual(value['status'],'lark-active');self.assertFalse(value['health_check_sends_notifications']);self.assertIn('not-probed',value['supplier_reachability'])
   with patch.object(manage,'BUNDLE',bundle),patch.object(manage.subprocess,'run',return_value=SimpleNamespace(returncode=3)):self.assertEqual(manage.notification_metadata()['status'],'lark-unit-inactive')
   state=bundle/'lark-notify-state.json';state.write_text(json.dumps({'mode':'active','owner':'unknown','generic_prepare':'refuse-reset'}))
   with patch.object(manage,'BUNDLE',bundle),patch.object(manage.subprocess,'run') as runner:self.assertEqual(manage.notification_metadata()['status'],'invalid-notification-state');runner.assert_not_called()
 def test_pve_missing_stale_and_future_clock_never_claim_fresh(self):
  manage=self.load('ops_health',Path(__file__).resolve().parent.parent/'scripts/manage.py');cfg={'SERVICE_IP':'10.63.30.40'}
  for values,status in [([], 'missing'),([{'value':[0,'181']}], 'stale-or-clock-skew'),([{'value':[0,'-1']}], 'stale-or-clock-skew'),([{'value':[0,'NaN']}], 'invalid'),([{'value':[0,'60']}], 'fresh')]:
   with patch.object(manage,'get_http',return_value=json.dumps({'status':'success','data':{'result':values}}).encode()):
    result=manage.pve_collector_metadata(cfg);self.assertEqual(result['status'],status);self.assertEqual(result['fresh'],status=='fresh')

class HTTP(unittest.TestCase):
 def setUp(self):
  self.sent=[];self.ctx=b.Context(TOKEN,'acceptance',lambda p:self.sent.append(p));self.server=b.Server(('127.0.0.1',0),self.ctx,allowed_source='127.0.0.1');self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
 def tearDown(self):self.server.shutdown();self.server.server_close();self.thread.join()
 def req(self,body=None,headers=None,path=b.PATH,method='POST'):
  connection=http.client.HTTPConnection(*self.server.server_address,timeout=3);connection.request(method,path,body=raw() if body is None else body,headers=headers if headers is not None else {'Authorization':'Bearer '+TOKEN,'Content-Type':'application/json'});r=connection.getresponse();code=r.status;r.read();connection.close();return code
 def test_authenticated_delivery_firing_and_resolved(self):
  with contextlib.redirect_stdout(io.StringIO()):self.assertEqual(self.req(),200);self.assertEqual(self.req(raw(fixture('resolved'))),200)
  self.assertEqual(len(self.sent),2)
 def test_auth_source_path_method_reject_without_send(self):
  self.assertEqual(self.req(headers={'Content-Type':'application/json'}),401);self.assertEqual(self.req(path='/other'),403);self.assertEqual(self.req(method='GET'),405);self.server.allowed_source='172.18.0.3';self.assertEqual(self.req(),403);self.assertEqual(self.sent,[])
 def test_oversized_wrong_type_duplicate_length_reject(self):
  self.assertEqual(self.req(body=b'x'*65537),413);self.assertEqual(self.req(headers={'Authorization':'Bearer '+TOKEN,'Content-Type':'text/plain'}),415)
  conn=http.client.HTTPConnection(*self.server.server_address,timeout=3);conn.putrequest('POST',b.PATH);conn.putheader('Authorization','Bearer '+TOKEN);conn.putheader('Content-Type','application/json');conn.putheader('Content-Length','1');conn.putheader('Content-Length','2');conn.endheaders(b'{}');r=conn.getresponse();self.assertEqual(r.status,400);r.read();conn.close();self.assertEqual(self.sent,[])
 def test_upstream_failure_is_503_not_acknowledged(self):
  def fail(p):raise b.DeliveryFailed()
  self.ctx.sender=fail
  with contextlib.redirect_stdout(io.StringIO()):self.assertEqual(self.req(),503)
 def test_worker_concurrency_is_bounded(self):
  sockets=[]
  try:
   for _ in range(2):
    s=socket.create_connection(self.server.server_address,timeout=2);s.sendall(b'POST /v1/alertmanager HTTP/1.1\r\n');sockets.append(s)
   end=time.monotonic()+2
   while self.server.slots._value!=0 and time.monotonic()<end:time.sleep(.01)
   third=socket.create_connection(self.server.server_address,timeout=2);response=third.recv(512);third.close();self.assertIn(b'503 Service Unavailable',response)
  finally:
   for s in sockets:s.close()
if __name__=='__main__':unittest.main()
