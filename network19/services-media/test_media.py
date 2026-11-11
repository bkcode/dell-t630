import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch as mockpatch

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('patches',HERE/'patches.py');p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
spec=importlib.util.spec_from_file_location('transaction',HERE/'guest_transaction.py');t=importlib.util.module_from_spec(spec);spec.loader.exec_module(t)
ROOT=HERE.parents[1]


def pen_fixture():
 base='/opt/dell/penpot/';src=ROOT/'infra/penpot';here=base+'runtime/health-supervision/'
 historical=HERE/'fixtures/penpot-pre-network'
 # Frozen migration input from before the network19 patch.  These public files
 # are test fixtures only and must never be replayed onto the current server.
 lock=json.loads((historical/'deployment-lock.json').read_text())
 paths={base+'assignment.json',base+'compose.fresh.yaml',base+'application/target-api.py',here+'supervisor.py',here+'node-health.mjs'}
 for group,prefix in [('package_file_sha256',base),('supervision_file_sha256',here)]:
  paths|={prefix+x for x in lock[group]}
 files={x:(src/x.removeprefix(base)).read_bytes() for x in paths}
 for name in ('supervisor.py','node-health.mjs','compose.health-supervision.yaml'):
  files[here+name]=(historical/name).read_bytes()
 # Synthetic consistent lock exercises transformations; not a claim about guest state.
 for group,prefix in [('package_file_sha256',base),('supervision_file_sha256',here)]:
  for rel in lock[group]:lock[group][rel]=p.sha(files[prefix+rel])
 files[here+'deployment-lock.json']=(json.dumps(lock)+'\n').encode()
 files['/etc/penpot/.env']=b"PENPOT_PUBLIC_URI='http://192.168.21.22:9001'\nPENPOT_SECRET_KEY='TEST-ONLY-fixture'\nPENPOT_DATABASE_PASSWORD='TEST-ONLY-fixture2'\nPENPOT_WORKER_FILE_ID='unchanged-fixture-id'\n"
 return files


class PatchTests(unittest.TestCase):
 def test_env_keeps_every_unlisted_byte_and_quotes(self):
  raw=b"# comment\r\nPUBLIC='old'\r\nPASSWORD='TEST-only\\$bytes'\r\nEXTRA=unchanged\r\n"
  got,proof=p.env_patch(raw,{'PUBLIC':({'old'},'new')})
  self.assertEqual(got,raw.replace(b"PUBLIC='old'",b"PUBLIC='new'"))
  self.assertEqual(proof,p.sha(b"# comment\r\nPASSWORD='TEST-only\\$bytes'\r\nEXTRA=unchanged\r\n"))

 def test_env_rejects_missing_duplicate_old_or_injection(self):
  for raw,change in [(b'A=old\nA=old\n',{'A':({'old'},'new')}),(b'A=old\n',{'B':({'old'},'new')}),(b'A=foreign\n',{'A':({'old'},'new')}),(b'A=old\n',{'A':({'old'},'new\nPASSWORD=bad')})]:
   with self.assertRaises(p.Rejected):p.env_patch(raw,change)

 def test_penpot_complete_exact_transform_and_lock_hashes(self):
  files=pen_fixture();result,proof=p.penpot(files);here='/opt/dell/penpot/runtime/health-supervision/'
  before=json.loads(files[here+'deployment-lock.json']);after=json.loads(result[here+'deployment-lock.json'])
  self.assertEqual(after['guest']['ip'],'192.168.19.50')
  for key in ('services','storage','Git'):self.assertEqual(after[key],before[key])
  for group,prefix in [('package_file_sha256','/opt/dell/penpot/'),('supervision_file_sha256',here)]:
   for rel,digest in after[group].items():self.assertEqual(digest,p.sha(result.get(prefix+rel,files[prefix+rel])))
  self.assertEqual(proof['protected_env_bytes_sha256'],t.current_env_proof(250,result['/etc/penpot/.env']))
  self.assertNotIn(b'10.63.30.30',result[here+'supervisor.py'])
  self.assertNotIn(b'192.168.21.22:9001',result[here+'node-health.mjs'])
  self.assertIn(b'192.168.19.50:9001:8080',result['/opt/dell/penpot/compose.fresh.yaml'])
  self.assertEqual(result['/opt/dell/penpot/compose.fresh.yaml'].count(b'--upstream=192.168.19.1:53'),1)
  self.assertNotIn(b'https://1.1.1.1/dns-query',result['/opt/dell/penpot/compose.fresh.yaml'])
  self.assertNotIn(b'https://1.0.0.1/dns-query',result['/opt/dell/penpot/compose.fresh.yaml'])
  compile(result[here+'supervisor.py'],'new-supervisor','exec')

 def test_penpot_tampered_baseline_lock_rejected(self):
  files=pen_fixture();files['/opt/dell/penpot/target_guard.py']+=b'\n# unexpected drift\n'
  with self.assertRaises(p.Rejected):p.penpot(files)

 def test_penpot_old_selector_count_must_be_exact(self):
  files=pen_fixture();files['/opt/dell/penpot/compose.fresh.yaml']=files['/opt/dell/penpot/compose.fresh.yaml'].replace(b'0.0.0.0:9001:8080',b'127.0.0.1:9001:8080')
  with self.assertRaises(p.Rejected):p.penpot(files)

 def test_penpot_unreviewed_DNS_upstream_rejected(self):
  files=pen_fixture();files['/opt/dell/penpot/compose.fresh.yaml']=files['/opt/dell/penpot/compose.fresh.yaml'].replace(b'https://1.1.1.1/dns-query',b'https://unreviewed.invalid/dns-query')
  with self.assertRaises(p.Rejected):p.penpot(files)

 def test_new_admin_health_accepts_new_origin_rejects_old(self):
  result,_=p.penpot(pen_fixture());raw=result['/opt/dell/penpot/runtime/health-supervision/node-health.mjs']
  with tempfile.TemporaryDirectory() as td:
   module=Path(td)/'health.mjs';module.write_bytes(raw)
   code='const m=await import('+json.dumps(module.as_uri())+');const u="http://192.168.19.50:9001/#/auth/login?callback-url="+encodeURIComponent("http://192.168.19.50:9001/admin-console/");if(!m.validAdminRedirect(307,u)||m.validAdminRedirect(307,u.replaceAll("192.168.19.50","192.168.21.22")))process.exit(1);'
   subprocess.run(['node','--input-type=module','-e',code],check=True,capture_output=True)

 def test_nexus_marker_only_address_changes(self):
  b='/opt/dell/nexus/';marker={'expected_guest_ip':'10.63.30.20','expected_hostname':'artifact-service','old_h2_or_credentials_imported':False,'empty_data_verified_at':'original-time','filesystem_uuid':'same-uuid'}
  files={b+'assignment.json':json.dumps(marker).encode(),b+'fresh-instance.json':json.dumps(marker).encode(),'/etc/nexus.env':b'NEXUS_DATA_DIR=/srv/nexus/data\nNEXUS_BIND_ADDRESS=0.0.0.0\nSECRET=TEST-ONLY\n',b+'application-import.py':b"ORIGIN = 'http://127.0.0.1:8081'\n"}
  result,_=p.nexus(files)
  changed=json.loads(result[b+'fresh-instance.json']);changed['expected_guest_ip']=marker['expected_guest_ip'];self.assertEqual(changed,marker)
  self.assertIn(b'SECRET=TEST-ONLY\n',result['/etc/nexus.env'])
  self.assertIn(b'192.168.19.31:8081',result[b+'application-import.py'])

 def nasfiles(self):
  return {'/opt/dell/nas/.env':b'NAS_BIND_IP=10.63.40.10\nJELLYFIN_PUBLIC_URL=http://192.168.21.22:8096\nNAS_DATA_UUID=same-fixture\n',p.NAS_NETWORK:b'<NetworkConfiguration><EnableRemoteAccess>false</EnableRemoteAccess><EnableUPnP>false</EnableUPnP><LocalNetworkSubnets><string>10.63.40.0/24</string><string>192.168.21.0/24</string><string>127.0.0.0/8</string><string>172.18.0.1/32</string></LocalNetworkSubnets></NetworkConfiguration>'}

 def test_nas_xml_changes_exact_one_subnet_preserves_remote_policy(self):
  files=self.nasfiles();result,proof=p.nas(files)
  self.assertEqual(result[p.NAS_NETWORK],files[p.NAS_NETWORK].replace(b'10.63.40.0/24',b'192.168.19.0/24'))
  self.assertEqual(proof['protected_env_bytes_sha256'],t.current_env_proof(260,result['/opt/dell/nas/.env']))

 def test_nas_unsupported_or_remote_enabled_model_fails_closed(self):
  for key in [b'<EnableRemoteAccess>true</EnableRemoteAccess>',b'<EnableRemoteAccess />']:
   files=self.nasfiles();files[p.NAS_NETWORK]=files[p.NAS_NETWORK].replace(b'<EnableRemoteAccess>false</EnableRemoteAccess>',key)
   with self.assertRaises(p.Rejected):p.nas(files)

 def test_mac_scoped_old_new_transition_not_arbitrary_alias(self):
  r=t.ROLES[250]
  def row(mac,ip):return {'address':mac,'addr_info':[{'local':ip,'prefixlen':24}]}
  self.assertTrue(t.matches_address([row(r['mac'],r['old'])],r,'old'))
  self.assertFalse(t.matches_address([row(r['mac'],r['old'])],r,'new'))
  self.assertTrue(t.matches_address([row(r['mac'],r['new'])],r,'new'))
  self.assertFalse(t.matches_address([row('wrong-mac',r['new'])],r,'new'))
  self.assertFalse(t.matches_address([row(r['mac'],'203.0.113.1'),row('docker-alias',r['new'])],r,'transition'))


class OmvPayloadTests(unittest.TestCase):
 def test_actual_installed_model_payload_changes_only_network_keys(self):
  spec=importlib.util.spec_from_file_location('omv',HERE/'omv_payload.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
  nas=next(x for x in json.loads((HERE/'active-readonly-preflight.json').read_text()) if x['role']==260)
  schema=json.loads((HERE/'omv-ethernet-rpc-schema.json').read_text())['matching_schemas'][0]['schema']
  result=m.build(nas['OMV_wired_object'],schema);old=result['old_RPC']['params'];new=result['new_RPC']['params']
  self.assertEqual(set(old),set(new));self.assertEqual(new['address'],'192.168.19.60');self.assertEqual(new['gateway'],'192.168.19.1');self.assertEqual(new['dnsnameservers'],'192.168.19.1')
  self.assertEqual({k for k in old if old[k]!=new[k]},{'address','gateway','dnsnameservers'})
  self.assertEqual(new['uuid'],old['uuid']);self.assertEqual(new['method6'],'manual');self.assertEqual((new['routemetric'],new['routemetric6']),(0,1))
  wrong=dict(nas['OMV_wired_object'],devicename='wrong-interface')
  with self.assertRaises(ValueError):m.build(wrong,schema)


class StandbyRemediationTests(unittest.TestCase):
 def test_role_driver_pin_and_precommit_network_failure_rollback(self):
  self.assertEqual(t.ROLES[250]['driver'],'overlay2');self.assertEqual(t.ROLES[221]['driver'],'overlay2');self.assertEqual(t.ROLES[260]['driver'],'overlayfs')
  self.assertTrue(t.rollback_permitted('quiesced'));self.assertTrue(t.rollback_permitted('applied-await-start'));self.assertFalse(t.rollback_permitted('staged'));self.assertFalse(t.rollback_permitted('arbitrary'))


class RuntimeWaiterTests(unittest.TestCase):
 def test_transient_missing_owned_name_is_not_ready_and_retries(self):
  r={'unit':'test.service','names':['owned']};good=[{'name':'/owned','image':'same','running':True,'health':'healthy'}];journal={'before_containers':good}
  response=type('Reply',(),{'stdout':b'ActiveState=active\nSubState=running\n'})()
  with mockpatch.object(t,'command',return_value=response),mockpatch.object(t,'state',side_effect=[t.patch.Rejected('fixed command failed'),good]) as state,mockpatch.object(t.time,'sleep'):
   t.start_wait(r,journal,False)
  self.assertEqual(state.call_count,2)

 def test_persistently_missing_frame_hits_original_deadline(self):
  r={'unit':'test.service','names':['owned']};journal={'before_containers':[{'name':'/owned','image':'same'}]}
  response=type('Reply',(),{'stdout':b'ActiveState=active\nSubState=running\n'})()
  with mockpatch.object(t,'command',return_value=response),mockpatch.object(t,'state',side_effect=t.patch.Rejected('fixed command failed')),mockpatch.object(t.time,'sleep'),mockpatch.object(t.time,'monotonic',side_effect=[0,0,601]):
   with self.assertRaises(t.patch.Rejected):t.start_wait(r,journal,False)


class FileTransactionTests(unittest.TestCase):
 def fixture(self,root):
  files=[]
  for i in range(2):
   dest=root/('target'+str(i));dest.write_bytes(b'old'+bytes([i]));old=dest.read_bytes();new=b'new'+bytes([i])
   (root/(str(i)+'.old')).write_bytes(old);(root/(str(i)+'.new')).write_bytes(new)
   files.append({'path':str(dest),'old_sha':p.sha(old),'new_sha':p.sha(new),'index':i,'mode':0o600,'uid':os.getuid(),'gid':os.getgid()})
  return {'files':files}

 def test_all_targets_preflight_before_any_overwrite(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td).resolve();j=self.fixture(root);(root/'target1').write_bytes(b'third-party')
   with self.assertRaises(t.patch.Rejected):t.install_files(root,j,True)
   self.assertEqual((root/'target0').read_bytes(),b'old\x00')

 def test_backups_corrupt_preflight_before_any_overwrite(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td).resolve();j=self.fixture(root);(root/'1.new').write_bytes(b'corrupt')
   with self.assertRaises(t.patch.Rejected):t.install_files(root,j,True)
   self.assertEqual((root/'target0').read_bytes(),b'old\x00')

 def test_interrupted_mixed_old_new_rollback_and_third_party_refusal(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td).resolve();j=self.fixture(root);(root/'target0').write_bytes((root/'0.new').read_bytes())
   with mockpatch.object(t,'save',lambda *a:None):t.install_files(root,j,False)
   self.assertEqual((root/'target0').read_bytes(),b'old\x00');self.assertEqual((root/'target1').read_bytes(),b'old\x01')
   (root/'target1').write_bytes(b'foreign-edit')
   with self.assertRaises(t.patch.Rejected):t.install_files(root,j,False)
   self.assertEqual((root/'target1').read_bytes(),b'foreign-edit')


if __name__=='__main__':unittest.main()
