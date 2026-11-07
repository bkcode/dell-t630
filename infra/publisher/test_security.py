#!/usr/bin/env python3
"""Offline publisher negative cases and rollback fault injection; no guest/SSH actions."""
import contextlib,hashlib,importlib.util,io,json,os,sys,tarfile,tempfile,unittest,zipfile
from pathlib import Path
from unittest.mock import patch
import yaml
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent

def load(name,file):
 s=importlib.util.spec_from_file_location(name,HERE/file);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
p=load('pub_protocol','publisher_protocol.py');fixed=load('pub_fixed','fixed-deploy-test-chain.py');rpc=load('pub_rpc','publisher_root.py')
RID='20261106T120000';OLD='20261106T110000';NS='12345678-1234-4234-8234-123456789abc'

def make_bundle(path):
 path.mkdir()
 rows=[]
 for name in p.NAMES:
  folder=path/name;folder.mkdir()
  with zipfile.ZipFile(folder/'app.jar','w') as z:z.writestr('META-INF/MANIFEST.MF','Manifest-Version: 1.0\n')
  cfg={'spring':{'application':{'name':name},'profiles':{'active':'dell-test'},'config':{'import':['nacos:finger-common.yaml?group=DELL_TEST&refreshEnabled=false','nacos:'+p.CONFIG_IDS[name]+'?group=DELL_TEST&refreshEnabled=false']},'cloud':{'nacos':{'server-addr':'10.63.20.10:8848','discovery':{'namespace':NS,'group':'DELL_TEST'},'config':{'namespace':NS,'group':'DELL_TEST'}}}},'server':{'address':'10.63.20.20','port':p.PORTS[name]}}
  cfg['snowflake']={'data-center-id':1,'worker-id':p.SNOWFLAKE[name]}
  if name=='finger-service-coms':cfg['file']={'upload':{'domain':'http://192.168.21.22:19999/finger-bff-system/dell-test-files','path':'/var/lib/finger/finger-service-coms/uploads'}}
  if name=='finger-auth':cfg['finger']={'auth':{'bootstrap':{'issuer':'http://192.168.21.22:19999'}}}
  (folder/'application.yaml').write_text(yaml.safe_dump(cfg));rows.append({'name':name,'port':p.PORTS[name],'xms_mib':128,'xmx_mib':p.HEAPS[name],'metaspace_mib':256,'memory_max_mib':1024 if p.HEAPS[name]==512 else 1536,'jar_sha256':p.sha(folder/'app.jar'),'config_sha256':p.sha(folder/'application.yaml')})
 m={'schema_version':1,'release_id':RID,'target_hostname':'java-test-01','target_ip':'10.63.20.20','data_ip':'10.63.20.10','profile':'dell-test','issuer':'http://192.168.21.22:19999','services':rows}
 (path/'manifest.json').write_text(json.dumps(m));return m

def header(name,kind=tarfile.REGTYPE,size=1):
 item=tarfile.TarInfo(name);item.type=kind;item.size=size;item.mode=0o600;item.uid=item.gid=item.mtime=0;item.uname=item.gname='';return item.tobuf(format=tarfile.USTAR_FORMAT)

class ProtocolSafety(unittest.TestCase):
 def test_status_canonical(self):self.assertEqual(p.parse_ssh('dell-publish-v1 status'),{'action':'status'})
 def test_stage_canonical(self):self.assertEqual(p.parse_ssh('dell-publish-v1 stage '+RID+' '+'a'*64+' 10240')['archive_bytes'],10240)
 def test_shell_subsystem_and_injection_rejected(self):
  for text in ['id','bash','scp -t /tmp','internal-sftp','env X=1 dell-publish-v1 status','dell-publish-v1 status;id','dell-publish-v1 status\nid','dell-publish-v1  status','dell-publish-v1\tstatus']:
   with self.assertRaises(p.Rejected):p.parse_ssh(text)
 def test_extra_prod_target_marker_fields_rejected(self):
  for extra in [{'target':'prod'},{'ready_marker':'/tmp/true.json'},{'script':'evil.py'}]:
   with self.assertRaises(p.Rejected):p.validate_header({'action':'activate','release_id':RID,**extra})
 def test_bool_or_oversize_archive_rejected(self):
  for n in [True,0,p.MAX_ARCHIVE+1]:
   with self.assertRaises(p.Rejected):p.validate_header({'action':'stage','release_id':RID,'archive_sha256':'a'*64,'archive_bytes':n})
 def test_traversal_release_id_rejected(self):
  with self.assertRaises(p.Rejected):p.release_id('../../root')
 def test_duplicate_json_and_unsafe_yaml_rejected(self):
  with self.assertRaises(p.Rejected):p.json_read('{"action":"status","action":"stage"}')
  with self.assertRaises(p.Rejected):p.parse_yaml(b'a: 1\na: 2\n')
  with self.assertRaises(p.Rejected):p.parse_yaml(b'!!python/object/apply:os.system [id]')

class ArchiveSafety(unittest.TestCase):
 def setUp(self):
  parent=HERE.parents[1]/'private/publisher';parent.mkdir(parents=True,exist_ok=True)
  self.tmp=tempfile.TemporaryDirectory(prefix='security-fixtures-',dir=parent);self.root=Path(self.tmp.name).resolve();self.bundle=self.root/'bundle';make_bundle(self.bundle)
 def tearDown(self):self.tmp.cleanup()
 def test_canonical_roundtrip(self):
  archive=p.build_canonical_archive(self.bundle,self.root/'bundle.tar',RID,NS);m,ns=p.extract_archive(archive,self.root/'pending',RID,NS)
  self.assertEqual(ns,NS);self.assertEqual(m['release_id'],RID)
 def reject_header(self,kind,size=1024**3,name='pax'):
  archive=self.root/'bad.tar';archive.write_bytes(header(name,kind,size))
  with self.assertRaises(p.Rejected):p.extract_archive(archive,self.root/'pending',RID,NS)
 def test_pax_giant_metadata_rejected_at_first512_header(self):self.reject_header(tarfile.XHDTYPE)
 def test_gnu_longname_rejected_at_first_header(self):self.reject_header(tarfile.GNUTYPE_LONGNAME)
 def test_symlink_hardlink_device_rejected(self):
  for kind in [tarfile.SYMTYPE,tarfile.LNKTYPE,tarfile.CHRTYPE]:
   archive=self.root/('bad-'+kind.decode()+'.tar');archive.write_bytes(header('manifest.json',kind,1))
   with self.assertRaises(p.Rejected):p.extract_archive(archive,self.root/('pending-'+kind.decode()),RID,NS)
 def test_traversal_member_rejected(self):self.reject_header(tarfile.REGTYPE,1,'../root')
 def test_giant_manifest_claim_rejected_without_payload(self):self.reject_header(tarfile.REGTYPE,128*1024+1,'manifest.json')
 def test_compressed_input_never_decompressed(self):
  import gzip
  archive=self.root/'compressed.tar';archive.write_bytes(gzip.compress(b'X'*1024*1024));archive.write_bytes(archive.read_bytes()+bytes((-archive.stat().st_size)%512))
  with self.assertRaises(p.Rejected):p.extract_archive(archive,self.root/'pending',RID,NS)
 def test_member12_rejected_before_any_payload(self):
  canonical=p.build_canonical_archive(self.bundle,self.root/'canonical.tar',RID,NS).read_bytes();pos=0
  for _ in range(11):
   size=p.octal(canonical[pos+124:pos+136]);pos+=512+((size+511)//512)*512
  archive=self.root/'twelve.tar';archive.write_bytes(canonical[:pos]+header('member12',tarfile.REGTYPE,1024**3))
  with self.assertRaisesRegex(p.Rejected,'member12'):p.extract_archive(archive,self.root/'pending',RID,NS)
 def test_stage_persistent_config_is_root600(self):
  releases=self.root/'releases';releases.mkdir();manifest=json.loads((self.bundle/'manifest.json').read_text())
  with patch.object(fixed,'ROOT',self.root),patch.object(fixed,'RELEASES',releases),patch.object(fixed.shutil,'chown') as chown:
   destination=fixed.stage(self.bundle,manifest)
  for name in p.NAMES:
   cfg=destination/name/'application.yaml';self.assertEqual(cfg.stat().st_mode&0o777,0o600)
   self.assertTrue(any(call.args[0]==cfg and call.kwargs=={'user':'root','group':'root'} for call in chown.call_args_list))
 def test_exact_order_and_extra_script_rejected(self):
  archive=self.root/'script.tar';archive.write_bytes(header('deploy.py',tarfile.REGTYPE,1)+b'x'+bytes(511)+bytes(1024))
  with self.assertRaises(p.Rejected):p.extract_archive(archive,self.root/'pending',RID,NS)
 def test_wrong_snowflake_or_old_coms_domain_rejected(self):
  cfg=p.parse_yaml((self.bundle/'finger-service-coms/application.yaml').read_bytes());cfg['snowflake']['worker-id']=1
  with self.assertRaisesRegex(p.Rejected,'Snowflake'):p.check_config(cfg,'finger-service-coms',NS)
  cfg['snowflake']['worker-id']=4;cfg['file']['upload']['domain']='http://192.168.21.22:19999/old-files'
  with self.assertRaisesRegex(p.Rejected,'upload contract'):p.check_config(cfg,'finger-service-coms',NS)
 def test_mutated_config_hash_rejected(self):
  (self.bundle/'finger-auth/application.yaml').write_text('secret: not-output\n')
  with self.assertRaises(p.Rejected):p.check_release(self.bundle,RID,NS)
 def test_prod_nested_nacos_and_unit_fields_rejected(self):
  cfg=p.parse_yaml((self.bundle/'finger-auth/application.yaml').read_bytes());cfg['spring']['cloud']['nacos']['config']['server-addr']='10.63.10.11:8848'
  with self.assertRaises(p.Rejected):p.check_config(cfg,'finger-auth',NS)
  manifest=json.loads((self.bundle/'manifest.json').read_text());manifest['services'][0]['ExecStart']='/bin/sh';(self.bundle/'manifest.json').write_text(json.dumps(manifest))
  with self.assertRaises(p.Rejected):p.check_release(self.bundle,RID,NS)

class StopQuiescence(unittest.TestCase):
 def test_nonzero_stop_only_passes_after_quiescence_verification(self):
  import types
  with patch.object(fixed,'NAMES',['finger-auth']),patch.object(fixed.subprocess,'run',return_value=types.SimpleNamespace(returncode=1)),patch.object(fixed,'unit_quiescent',return_value=True):
   self.assertEqual(fixed.stop_all(),[])
  with patch.object(fixed,'NAMES',['finger-auth']),patch.object(fixed.subprocess,'run',return_value=types.SimpleNamespace(returncode=1)),patch.object(fixed,'unit_quiescent',return_value=False):
   with self.assertRaisesRegex(RuntimeError,'stop failed'):fixed.stop_all()
 def test_failed_unit_with_live_pid_is_not_quiescent(self):
  import types
  state=types.SimpleNamespace(returncode=0,stdout='ActiveState=failed\nMainPID=234\nControlGroup=\n')
  with patch.object(fixed.subprocess,'run',return_value=state):self.assertFalse(fixed.unit_quiescent('finger-auth'))
 def test_lingering_cgroup_children_block_stop_success(self):
  import types
  parent=HERE.parents[1]/'private/publisher'
  with tempfile.TemporaryDirectory(dir=parent) as tmp:
   root=Path(tmp);group=root/'system.slice/test.service';group.mkdir(parents=True);events=group/'cgroup.events';state=types.SimpleNamespace(returncode=0,stdout='ActiveState=failed\nMainPID=0\nControlGroup=/system.slice/test.service\n')
   with patch.object(fixed,'CGROUP_ROOT',root),patch.object(fixed.subprocess,'run',return_value=state):
    events.write_text('populated 1\nfrozen 0\n');self.assertFalse(fixed.unit_quiescent('finger-auth'))
    events.write_text('populated 0\nfrozen 0\n');self.assertTrue(fixed.unit_quiescent('finger-auth'))

class RecoveryFaults(unittest.TestCase):
 def setUp(self):
  parent=HERE.parents[1]/'private/publisher';self.tmp=tempfile.TemporaryDirectory(prefix='rollback-fixtures-',dir=parent);self.root=Path(self.tmp.name).resolve();self.old=self.root/OLD;self.old.mkdir();self.new=self.root/RID;self.new.mkdir()
 def tearDown(self):self.tmp.cleanup()
 def test_previous_checked_before_any_stop(self):
  with patch.object(fixed,'check_staged_units'),patch.object(fixed,'RELEASES',self.root),patch.object(fixed,'check_manifest',side_effect=RuntimeError('previous invalid')),patch.object(fixed,'stop_all') as stop:
   with self.assertRaisesRegex(RuntimeError,'previous invalid'):fixed.transition(self.new,{'release_id':RID},self.old)
   stop.assert_not_called()
 def test_pointer_failure_attempts_rollback_and_start_old(self):
  events=[]
  def point(path):
   events.append(('pointer',path.name))
   if path==self.new:raise RuntimeError('injected pointer failure')
  with patch.object(fixed,'check_staged_units'),patch.object(fixed,'RELEASES',self.root),patch.object(fixed,'check_manifest',return_value={'release_id':OLD}),patch.object(fixed,'stop_all',side_effect=lambda *a,**k:events.append(('stop',k.get('strict',True)))),patch.object(fixed,'pointer',side_effect=point),patch.object(fixed,'start_all',side_effect=lambda m:events.append(('start',m['release_id']))):
   with self.assertRaisesRegex(RuntimeError,'injected pointer failure'):fixed.transition(self.new,{'release_id':RID},self.old)
  self.assertEqual(events,[('stop',True),('pointer',RID),('stop',False),('pointer',OLD),('start',OLD)])
 def test_stop_failure_still_attempts_old_restore(self):
  events=[]
  def stop(strict=True):
   events.append(('stop',strict))
   if strict:raise RuntimeError('injected stop failure')
  with patch.object(fixed,'check_staged_units'),patch.object(fixed,'RELEASES',self.root),patch.object(fixed,'check_manifest',return_value={'release_id':OLD}),patch.object(fixed,'stop_all',side_effect=stop),patch.object(fixed,'pointer',side_effect=lambda path:events.append(('pointer',path.name))),patch.object(fixed,'start_all',side_effect=lambda m:events.append(('start',m['release_id']))):
   with self.assertRaisesRegex(RuntimeError,'injected stop failure'):fixed.transition(self.new,{'release_id':RID},self.old)
  self.assertIn(('pointer',OLD),events);self.assertIn(('start',OLD),events);self.assertNotIn(('pointer',RID),events)
 def test_status_main_does_not_acquire_modify_lock(self):
  with patch.object(sys,'argv',['rpc']),patch.object(rpc,'load_protocol',return_value=p),patch.object(rpc,'guard',return_value={}),patch.object(rpc,'read_header',return_value={'action':'status'}),patch.object(rpc,'status',return_value={'busy':True}),patch.object(rpc.fcntl,'flock') as flock,contextlib.redirect_stdout(io.StringIO()):rpc.main()
  flock.assert_not_called()
 def test_status_filters_private_receipt_and_reports_busy(self):
  (self.root/'last-transaction.json').write_text(json.dumps({'action':'activate','release_id':RID,'status':'running','secret':'DO_NOT_RETURN','raw_config':'DO_NOT_RETURN'}));(self.root/'busy.json').write_text(json.dumps({'pid':123,'process_start_ticks':'42','transaction_id':'id','action':'activate','release_id':RID}))
  with patch.object(rpc,'STATE',self.root),patch.object(rpc,'owned',side_effect=lambda path,*a:path),patch.object(rpc,'process_start_ticks',return_value='42'):
   state=rpc.transaction_state()
  self.assertTrue(state['busy']);self.assertNotIn('DO_NOT_RETURN',json.dumps(state))
 def test_missing_fixed_unit_is_rejected(self):
  with self.assertRaises(AssertionError):fixed.check_staged_units(self.old,{'services':[{'name':'finger-auth','xms_mib':128,'xmx_mib':768,'metaspace_mib':256,'memory_max_mib':1536}]})
 def test_fixed_units_use_credentials_and_never_persistent_secret_path_argv(self):
  row={'name':'finger-auth','xms_mib':128,'xmx_mib':768,'metaspace_mib':256,'memory_max_mib':1536};unit=fixed.unit(row)
  self.assertIn('LoadCredential=application.yaml:/opt/finger/current-test/finger-auth/application.yaml',unit);self.assertIn('--spring.config.location=file:%d/application.yaml',unit);self.assertIn('User=finger',unit)
  exec_line=next(x for x in unit.splitlines() if x.startswith('ExecStart='));self.assertNotIn('current-test/finger-auth/application.yaml',exec_line)

if __name__=='__main__':unittest.main()
