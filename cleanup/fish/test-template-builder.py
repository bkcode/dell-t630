#!/usr/bin/env python3
"""Pure fixtures; no remote/PVE/package/service/mount operations."""
import copy,datetime,hashlib,importlib.util,json,sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.dont_write_bytecode=True
spec=importlib.util.spec_from_file_location('builder',Path(__file__).with_name('template-builder.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
BASE={'schema_version':1,'vmid':9040,'source_template':9010,'hostname':'fish-build-linux','ip':'192.168.19.197','mac':'bc:24:11:11:22:33','fish_version':'4.0.2-1','no_chsh':True}
class Fixture(unittest.TestCase):
 def test_exact_three(self):
  for vmid,(source,name,ip) in m.ROLES.items():
   c={**BASE,'vmid':vmid,'source_template':source,'hostname':name,'ip':ip};self.assertEqual(m.validate_contract(c),c)
 def test_excluded_or_live_target(self):
  for vmid in [100,190,200,201,210,220,230,240,250,260,270,9001,9010,9011,9012]:
   with self.assertRaises(m.Refused):m.validate_contract({**BASE,'vmid':vmid})
 def test_wrong_source_ip_name_mac_version_and_shell(self):
  for key,value in [('source_template',9001),('hostname','data-test'),('ip','192.168.19.20'),('mac',''),('mac','ff:ff:ff:ff:ff:ff'),('fish_version','latest'),('no_chsh',False)]:
   with self.assertRaises(m.Refused):m.validate_contract({**BASE,key:value})
 def test_window_exact_phase_and_canonical_contract(self):
  good={'vmid':9040,'allowed_phase':'install','contract_sha256':hashlib.sha256(json.dumps(BASE,sort_keys=True,separators=(',',':')).encode()).hexdigest(),'expires_at':(datetime.datetime.now(datetime.timezone.utc)+datetime.timedelta(minutes=1)).isoformat()}
  class Fake:
   def read_text(self):return json.dumps(good)
  with patch.object(m,'secure',return_value=Fake()):
   m.window(BASE,'install','ignored')
   with self.assertRaises(m.Refused):m.window(BASE,'seal','ignored')
   good['contract_sha256']='0'*64
   with self.assertRaises(m.Refused):m.window(BASE,'install','ignored')
 def test_expired_window(self):
  w={'vmid':9040,'allowed_phase':'seal','contract_sha256':hashlib.sha256(json.dumps(BASE,sort_keys=True,separators=(',',':')).encode()).hexdigest(),'expires_at':'2020-01-01T00:00:00+00:00'}
  class Fake:
   def read_text(self):return json.dumps(w)
  with patch.object(m,'secure',return_value=Fake()):
   with self.assertRaises(m.Refused):m.window(BASE,'seal','ignored')
 def test_observed_exact_netplan_without_comment(self):
  document={'network':{'version':2,'ethernets':{'eth0':{'match':{'macaddress':BASE['mac']},'addresses':[BASE['ip']+'/24'],'nameservers':{'addresses':['192.168.19.1'],'search':[]},'set-name':'eth0','routes':[{'to':'default','via':'192.168.19.1'}]}}}}
  self.assertTrue(m.exact_cloudinit_netplan('/etc/netplan/50-cloud-init.yaml',json.dumps(document),BASE))
  self.assertFalse(m.exact_cloudinit_netplan('/etc/netplan/custom.yaml',json.dumps(document),BASE))
 def test_netplan_extra_or_wrong_fields_refused(self):
  original={'network':{'version':2,'ethernets':{'eth0':{'match':{'macaddress':BASE['mac']},'addresses':[BASE['ip']+'/24'],'nameservers':{'addresses':['192.168.19.1'],'search':[]},'set-name':'eth0','routes':[{'to':'default','via':'192.168.19.1'}]}}}}
  for key,value in [('addresses',['192.168.19.20/24']),('match',{'macaddress':'bc:24:11:11:22:44'}),('routes',[{'to':'default','via':'192.168.19.2'}]),('nameservers',{'addresses':['1.1.1.1'],'search':[]}),('password','fixture-no-secret')]:
   document=copy.deepcopy(original);document['network']['ethernets']['eth0'][key]=value
   self.assertFalse(m.exact_cloudinit_netplan('/etc/netplan/50-cloud-init.yaml',json.dumps(document),BASE))
 def test_approved_original_Docker_profile(self):
  c={**BASE,'docker_profile':{'driver':'overlayfs','live_restore':True,'containerd_snapshotter':'default-enabled'},'docker_daemon_sha256':'fixtureSHA'}
  info={'DockerRootDir':'/var/lib/docker','Driver':'overlayfs','LiveRestoreEnabled':True}
  settings={'live-restore':True}
  m.check_docker_profile(c,info,settings,'fixtureSHA')
  for changed in [{**info,'Driver':'overlay2'},{**info,'LiveRestoreEnabled':False},{**info,'DockerRootDir':'/srv/other'}]:
   with self.assertRaises(m.Refused):m.check_docker_profile(c,changed,settings,'fixtureSHA')
  with self.assertRaises(m.Refused):m.check_docker_profile(c,info,settings,'changedSHA')
  with self.assertRaises(m.Refused):m.check_docker_profile(c,info,{'features':{'containerd-snapshotter':False},'live-restore':True},'fixtureSHA')
 def test_failed_guard_never_installs_or_seals(self):
  class Fake:
   def read_text(self):return json.dumps(BASE)
  with patch.object(sys,'argv',['builder','--contract','x','--phase','seal','--window','y']),patch.object(m,'secure',return_value=Fake()),patch.object(m,'guard',side_effect=m.Refused('fixture-wrong-MAC')),patch.object(m,'window') as win,patch.object(m,'seal') as seal:
   with self.assertRaises(m.Refused):m.main()
   win.assert_not_called();seal.assert_not_called()
 def test_preserve_shell_and_code(self):
  from types import SimpleNamespace
  before={'shells':{'root':'/bin/bash','ub':'/bin/bash'},'files':{'/fixture':'abc'}}
  with patch.object(m.pwd,'getpwnam',return_value=SimpleNamespace(pw_shell='/bin/bash')),patch.object(m,'sha',return_value='abc'):m.check_preserved(before,BASE)
  with patch.object(m.pwd,'getpwnam',return_value=SimpleNamespace(pw_shell='/usr/bin/fish')),patch.object(m,'sha',return_value='abc'):
   with self.assertRaises(m.Refused):m.check_preserved(before,BASE)
  with patch.object(m.pwd,'getpwnam',return_value=SimpleNamespace(pw_shell='/bin/bash')),patch.object(m,'sha',return_value='different'):
   with self.assertRaises(m.Refused):m.check_preserved(before,BASE)
if __name__=='__main__':unittest.main()
