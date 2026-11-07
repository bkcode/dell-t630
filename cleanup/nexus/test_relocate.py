import importlib.util,json,unittest
from pathlib import Path
s=importlib.util.spec_from_file_location('r',Path(__file__).with_name('relocate.py'));r=importlib.util.module_from_spec(s);s.loader.exec_module(r)

class RelocationTests(unittest.TestCase):
 def test_only_expected_hostname_changes(self):
  value={'expected_guest_ip':r.IP,'expected_hostname':r.SOURCE_HOST,'storage':{'filesystem_uuid':r.DATA_UUID,'data_path':'/srv/nexus/data'},'role':'artifact-service','created_at':'original'}
  result=json.loads(r.target_json(json.dumps(value).encode()));result['expected_hostname']=r.SOURCE_HOST;self.assertEqual(result,value)
 def test_initial_marker_proof_is_preserved(self):
  value={'expected_guest_ip':r.IP,'expected_hostname':r.SOURCE_HOST,'filesystem_uuid':r.DATA_UUID,'mode':'new-instance-application-export-import','old_h2_or_credentials_imported':False,'empty_data_verified_at':'original'}
  result=json.loads(r.target_json(json.dumps(value).encode()));self.assertEqual(result['expected_hostname'],r.TARGET_HOST)
  self.assertFalse(result['old_h2_or_credentials_imported']);self.assertEqual(result['empty_data_verified_at'],'original')
 def test_wrong_identity_or_data_volume_is_rejected(self):
  for field,value in [('expected_guest_ip','wrong'),('expected_hostname','wrong'),('filesystem_uuid','wrong')]:
   original={'expected_guest_ip':r.IP,'expected_hostname':r.SOURCE_HOST,'filesystem_uuid':r.DATA_UUID};original[field]=value
   with self.assertRaises(ValueError):r.target_json(json.dumps(original).encode())
 def test_two_public_images_become_exact_actual_config_id_only(self):
  raw=b'name: nexus\n'+b''.join(('    image: '+key+'\n').encode() for key in r.IMAGES)+b'    mem_limit: 3g\n    internal: true\n'
  result=r.compose_ids(raw)
  for key,value in r.IMAGES.items():self.assertIn(value.encode(),result);result=result.replace(value.encode(),key.encode())
  self.assertEqual(result,raw)
 def test_unknown_or_duplicate_image_is_rejected(self):
  raw=b''.join(('    image: '+key+'\n').encode() for key in r.IMAGES)
  with self.assertRaises(ValueError):r.compose_ids(raw+raw)
 def test_bundle_excludes_all_publisher_and_SSH_identity_paths(self):
  for name,path in r.FILES.items():
   self.assertNotIn('.ssh',path);self.assertNotIn('dell-publisher',path);self.assertNotIn('ssh_host_',path)
  self.assertEqual(len([x for x in r.FILES if x.startswith('secret/')]),3)

if __name__=='__main__':unittest.main()
