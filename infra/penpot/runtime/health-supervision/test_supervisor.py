import copy,importlib.util,os,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
spec=importlib.util.spec_from_file_location('penpot_supervisor',Path(__file__).with_name('supervisor.py'));s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s)
def fixture():
 lock={'services':{},'storage':{'mountpoint':'/srv/penpot','filesystem_uuid':'expected-UUID','docker_root_dir':'/srv/penpot/docker'}};frame={}
 for name in s.EXPECTED:
  lock['services'][name]={'image_id':'sha256:expected','pids_limit_proposed':128,'memory_bytes':256*1024**2,'nano_cpus':10**9,'expected_mounts':[],'container_name':'penpot-'+name+'-1'}
  frame[name]={'image':'sha256:expected','pids':128,'memory':256*1024**2,'nano_cpus':10**9,'restart':'no','mounts':[],'running':True,'status':'running','oom':False,'health':'healthy'}
 lock['services']['penpot-dns']['require_init']=True;frame['penpot-dns']['init']=True
 return lock,frame
class ContractTests(unittest.TestCase):
 def test_full_eleven_healthy(self):
  lock,frame=fixture();self.assertTrue(s.validate_frame(frame,lock))
 def test_wrong_UUID_and_RootDir_refused(self):
  lock,_=fixture();fs={'target':'/srv/penpot','uuid':'expected-UUID','fstype':'ext4'};daemon={'root_dir':'/srv/penpot/docker','driver':'overlay2','name':'penpot-service','arch':'x86_64','os':'linux'}
  s.validate_storage(lock,fs,daemon)
  for badfs,badd in [(dict(fs,uuid='wrong'),daemon),(fs,dict(daemon,root_dir='/var/lib/docker')),(fs,dict(daemon,driver='overlayfs'))]:
   with self.assertRaises(s.Failure):s.validate_storage(lock,badfs,badd)
 def test_tag_repoint_and_ARM_image_rejected(self):
  s.validate_image_metadata('sha256:expected',{'id':'sha256:expected','arch':'amd64','os':'linux'})
  for m in [{'id':'sha256:repointed','arch':'amd64','os':'linux'},{'id':'sha256:expected','arch':'arm64','os':'linux'}]:
   with self.assertRaises(s.Failure):s.validate_image_metadata('sha256:expected',m)
 def test_missing_is_not_ready_and_runtime_fatal(self):
  lock,frame=fixture();frame.pop(next(iter(frame)));self.assertFalse(s.validate_frame(frame,lock,starting=True))
  with self.assertRaises(s.Failure):s.validate_frame(frame,lock)
 def test_extra_service_rejected_even_startup(self):
  lock,frame=fixture();frame['unapproved']={}
  with self.assertRaises(s.Failure):s.validate_frame(frame,lock,starting=True)
 def test_stopped_OOM_image_pids_restart_and_mount_rejected(self):
  lock,original=fixture();name=next(iter(original))
  for fields in [{'running':False},{'oom':True},{'image':'sha256:other'},{'pids':None},{'restart':'always'},{'mounts':[{'source':'/var/run/docker.sock','destination':'/socket','rw':True}]}]:
   frame=copy.deepcopy(original);frame[name].update(fields)
   with self.assertRaises(s.Failure):s.validate_frame(frame,lock)
 def test_null_unhealthy_or_starting_never_healthy(self):
  lock,frame=fixture();name=next(iter(frame))
  for value in [None,'unhealthy','starting']:
   frame[name]['health']=value;self.assertFalse(s.validate_frame(frame,lock,starting=True))
class MonitorTests(unittest.TestCase):
 def test_three_bad_required_and_good_resets(self):
  monitor=s.Monitor();monitor.update(False);monitor.update(False);monitor.update(True);self.assertEqual(monitor.consecutive_bad,0)
  monitor.update(False);monitor.update(False)
  with self.assertRaises(s.Failure):monitor.update(False)
class StopTests(unittest.TestCase):
 def test_stops_only_fixed_running_names_without_compose(self):
  lock,_=fixture();allowed=next(iter(lock['services'].values()))['container_name'];calls=[]
  def docker(*args,**kwargs):
   calls.append(args)
   if args[0]=='ps':return SimpleNamespace(returncode=0,stdout='own-id\nforeign-id\n')
   if args[0]=='inspect':return SimpleNamespace(returncode=0,stdout='/'+(allowed if args[-1]=='own-id' else 'foreign-container')+'\n')
   return SimpleNamespace(returncode=0,stdout='')
  with patch.object(s,'docker',side_effect=docker):self.assertTrue(s.stop_group(lock))
  self.assertEqual([x for x in calls if x[0]=='stop'],[('stop','--time','30','own-id')]);self.assertFalse(any('compose' in x for x in calls))
 def test_daemon_loss_never_creates_fallback_directory(self):
  lock,_=fixture()
  with patch.object(s,'docker',return_value=SimpleNamespace(returncode=1,stdout='')),patch.object(Path,'mkdir') as mkdir:self.assertFalse(s.stop_group(lock))
  mkdir.assert_not_called()
 def test_no_running_containers_means_no_second_stop(self):
  lock,_=fixture()
  with patch.object(s,'docker',return_value=SimpleNamespace(returncode=0,stdout='')) as docker:self.assertTrue(s.stop_group(lock))
  self.assertEqual(docker.call_count,1)
class LifecycleTests(unittest.TestCase):
 def run_lifecycle(self,scenario):
  lock,frame=fixture();events=[];calls=0;ticks=0
  def scan():
   nonlocal calls
   calls+=1
   if calls==2 and scenario in ('wait-until-full','stop-during-start'):
    events.append('incomplete');return dict(list(frame.items())[:-1])
   if calls>=3 and scenario=='runtime-fault':raise s.Failure('injected-stopped-frontend')
   events.append('complete');return frame
  def wait(_):
   nonlocal ticks
   ticks+=1
   if scenario=='stop-during-start' or (scenario=='wait-until-full' and ticks==2):s.SHUTDOWN=True
  with patch.dict(os.environ,{'INVOCATION_ID':'unit-test','DELL_MOUNT_GATED':'1','NOTIFY_SOCKET':'synthetic-only'}),patch.object(s,'SHUTDOWN',False),patch.object(s,'guest_guard'),patch.object(s,'storage_guard'),patch.object(s,'verify_files_and_images'),patch.object(s,'check_config'),patch.object(s,'state'),patch.object(s,'record_failure'),patch.object(s,'run'),patch.object(s,'scan',side_effect=scan),patch.object(s,'wait_tick',side_effect=wait),patch.object(s,'notify',side_effect=lambda _:events.append('READY')),patch.object(s,'stop_group',return_value=True) as stop:
   code=s.supervise(lock);self.assertEqual(stop.call_count,1)
  return code,events
 def test_READY_only_after_full_set_and_clean_shutdown(self):
  code,events=self.run_lifecycle('wait-until-full');self.assertEqual(code,0);self.assertLess(events.index('incomplete'),events.index('READY'));self.assertEqual(events.count('READY'),1)
 def test_signal_during_start_stops_once_without_READY(self):
  code,events=self.run_lifecycle('stop-during-start');self.assertEqual(code,0);self.assertNotIn('READY',events)
 def test_runtime_failure_stops_once_and_exits_nonzero(self):
  code,events=self.run_lifecycle('runtime-fault');self.assertEqual(code,1);self.assertEqual(events.count('READY'),1)
if __name__=='__main__':unittest.main()
