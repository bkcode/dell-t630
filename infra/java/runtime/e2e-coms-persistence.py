#!/usr/bin/env python3
"""Exactly one approved COMS-only restart for the owned synthetic PNG."""
from pathlib import Path
import json,sys,importlib.util,shlex
sys.dont_write_bytecode=True
BASE=Path(__file__).resolve().parents[3];record=BASE/'evidence/implementation/java-test-business-acceptance.json';proof=json.loads(record.read_text());private=Path(proof['private_state_file']);state=json.loads(private.read_text());assert proof['role_file_initial_status']=='role-permission-and-file-initial-passed'
spec=importlib.util.spec_from_file_location('control',BASE/'scripts/control.py');control=importlib.util.module_from_spec(spec);spec.loader.exec_module(control)
payload={k:state[k] for k in ['run_id','upload_info','file_request_path','fixture_image_sha256','fixture_image_bytes','fixture_image_base64']};payload['access_token']=state['tokens']['access_token'];payload['known_secrets_to_scan']={p.name:p.read_text().strip() for p in (BASE/'private/java/secrets').iterdir() if p.is_file()};payload['known_secrets_to_scan'].update(access_token=state['tokens']['access_token'],refresh_token=state['tokens'].get('refresh_token',''))
code=r'''
from pathlib import Path
import socket,json,sys,subprocess,urllib.request,urllib.error,hashlib,base64,re,time,os,datetime,pwd
assert os.geteuid()==0 and socket.gethostname()=='java-test-01' and not Path('/etc/pve').exists() and Path('/opt/finger/current-test').resolve().name==EXPECTED_RELEASE
v=json.loads(sys.stdin.read());assert re.fullmatch('[a-f0-9]{32}',v['run_id']);image=base64.b64decode(v['fixture_image_base64']);assert len(image)<=4096 and len(image)==v['fixture_image_bytes'] and hashlib.sha256(image).hexdigest()==v['fixture_image_sha256']
key=v['upload_info']['objectKey'];assert re.fullmatch(r'image/[0-9]{4}-[0-9]{2}/[a-f0-9]{32}\.png',key)
owned=Path('/var/lib/finger/finger-service-coms/uploads')/key;assert owned.resolve()==owned and owned.is_file();before_disk=hashlib.sha256(owned.read_bytes()).hexdigest();assert before_disk==v['fixture_image_sha256']
folder=Path('/root/dell-java-e2e');folder.mkdir(mode=0o700,exist_ok=True);marker=folder/('coms-restart-'+v['run_id']+'.json');assert not marker.exists(),'Prior COMS restart record retained; no repeat'
names=['finger-service-system','finger-service-coms','finger-auth','finger-bff-system','finger-gateway-mobile'];finger_uid=pwd.getpwnam('finger').pw_uid

def states():
 out={}
 for name in names:
  text=subprocess.check_output(['systemctl','show','dell-finger-'+name+'.service','-p','MainPID','-p','ActiveState','-p','NRestarts'],text=True);row=dict(l.split('=',1) for l in text.splitlines() if '='in l);pid=int(row['MainPID']);row['actual_process_uid']=Path('/proc/'+str(pid)).stat().st_uid if pid else None;out[name]=row
 return out
before=states();assert all(x['ActiveState']=='active' and x['actual_process_uid']==finger_uid for x in before.values())
result={'at':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),'status':'restart-prepared','before':before,'owned_file_sha256_before':before_disk,'fixture_bytes':len(image),'restart_count_by_this_test':0,'other_units_touched':False,'steps':[],'secrets_values_emitted':False};marker.write_text(json.dumps(result)+'\n');marker.chmod(0o600)
class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,*args,**kwargs):return None
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect());token=v['access_token']
def request(path,method='GET',data=None,port=9999,content_type='application/json',authenticated=True):
 headers={'Authorization':'Bearer '+token} if authenticated else {}
 if data is not None:headers['Content-Type']=content_type
 req=urllib.request.Request('http://10.63.20.20:'+str(port)+path,data=data,method=method,headers=headers)
 try:
  with opener.open(req,timeout=10) as r:return r.status,r.read(1024*1024)
 except urllib.error.HTTPError as e:status=e.code;body=e.read(262144);e.close();return status,body
stage='controlled-coms-restart'
try:
 subprocess.run(['systemctl','restart','dell-finger-finger-service-coms.service'],check=True,capture_output=True,timeout=90);result['restart_count_by_this_test']=1;marker.write_text(json.dumps(result)+'\n')
 deadline=time.monotonic()+120;healthy=False
 while time.monotonic()<deadline:
  try:status,body=request('/actuator/health',port=10202,authenticated=False);healthy=status==200 and json.loads(body).get('status')=='UP'
  except Exception:healthy=False
  if healthy:break
  time.sleep(2)
 assert healthy,'COMS health deadline exceeded'
 after=states();assert before['finger-service-coms']['MainPID']!=after['finger-service-coms']['MainPID'];assert all(before[n]['MainPID']==after[n]['MainPID'] and after[n]['ActiveState']=='active' for n in names if n!='finger-service-coms');assert all(x['actual_process_uid']==finger_uid for x in after.values())
 result['after']=after;result['other_four_pids_unchanged']=True;after_disk=hashlib.sha256(owned.read_bytes()).hexdigest();assert after_disk==before_disk;result['owned_file_sha256_after']=after_disk;result['steps'].append({'name':'controlled-coms-restart-disk-persistence','status':'passed','sha256_before':before_disk,'sha256_after':after_disk,'other_four_pids_unchanged':True})
 stage='gateway-file-read-after-restart';attempts=[];matched=False
 for attempt in range(30):
  status,body=request(v['file_request_path']);sha=hashlib.sha256(body).hexdigest();attempts.append({'attempt':attempt+1,'http_status':status,'bytes':len(body),'sha256':sha if status==200 and sha==before_disk else None})
  if status==200 and sha==before_disk:matched=True;break
  transient=status in [502,503,504]
  if status==200:
   try:transient=json.loads(body).get('code') in [30001,30002,30007]
   except ValueError:pass
  if not transient:break
  time.sleep(2)
 assert matched,'File read after restart did not recover or SHA mismatched';result['steps'].append({'name':stage,'status':'passed','attempts':attempts,'expected_sha256':before_disk})
 stage='same-owned-file-metadata-dedup-after-restart';boundary='dell-e2e-'+v['run_id'];filename='dell-e2e-'+v['run_id']+'.png';multipart=('--'+boundary+'\r\nContent-Disposition: form-data; name="file"; filename="'+filename+'"\r\nContent-Type: image/png\r\n\r\n').encode()+image+('\r\n--'+boundary+'--\r\n').encode();status,body=request('/inner/coms/v1/upload/image','POST',multipart,port=10202,content_type='multipart/form-data; boundary='+boundary);reply=json.loads(body);data=reply.get('data');assert status==200 and reply.get('code')==0 and str(data.get('fileId'))==str(v['upload_info']['fileId']) and data.get('objectKey')==key and data.get('url')==v['upload_info']['url'];result['steps'].append({'name':stage,'status':'passed','same_file_id':True,'same_object_key':True,'same_issued_url':True,'new_logical_fixture_created':False})
 stage='final-five-health';health=[]
 for name,port in [('finger-service-system',10210),('finger-service-coms',10202),('finger-auth',10000),('finger-bff-system',10104),('finger-gateway-mobile',9999)]:
  status,body=request('/actuator/health',port=port,authenticated=False);assert status==200 and json.loads(body).get('status')=='UP';health.append({'service':name,'http_status':status,'status':'UP'})
 result['final_health']=health
 stage='final-known-secret-log-scan';matches=[]
 for name in names:
  path=Path('/var/log/finger')/name/'app.log';raw=path.read_bytes() if path.exists() else b'';found=[label for label,secret in v['known_secrets_to_scan'].items() if secret and secret.encode() in raw]
  if found:matches.append({'service':name,'matched_secret_categories':found})
 result['steps'].append({'name':stage,'status':'passed' if not matches else 'failed','matches':matches,'raw_logs_saved':False});assert not matches
 result['status']='owned-file-and-metadata-persistence-verified';result['completed_at']=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat();result['fixture_retained']=True;result['cleanup_limitation']='Owned synthetic file and its file_info row retained; no approved delete API was invoked and no direct SQL mutation used.'
except Exception as error:result['status']='failed-stopped-no-repeat';result['failed_stage']=stage;result['error_type']=type(error).__name__
marker.write_text(json.dumps(result)+'\n');print(json.dumps(result))
'''.replace('EXPECTED_RELEASE',repr(proof['release_id']))
r=control.guest(240,'sudo -n python3 -c '+shlex.quote(code),data=json.dumps(payload).encode(),timeout=350,info=state['target'])
if r['exit_code']:raise SystemExit('COMS persistence test transport failed; private output suppressed; do not repeat without inspecting marker')
result=json.loads(r['stdout']);proof['steps'].extend(result.get('steps',[]));proof['coms_persistence']=result;proof['status']='private-api-e2e-and-file-persistence-passed-lan-url-check-pending' if result['status']=='owned-file-and-metadata-persistence-verified' else result['status'];record.write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False))
