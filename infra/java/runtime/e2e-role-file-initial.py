#!/usr/bin/env python3
"""Approved synthetic role/permission and <=4KiB upload checks; no restart."""
from pathlib import Path
import sys,importlib.util,json,base64,hashlib,struct,zlib,shlex
sys.dont_write_bytecode=True
BASE=Path(__file__).resolve().parents[3];record=BASE/'evidence/implementation/java-test-business-acceptance.json';proof=json.loads(record.read_text());state_path=Path(proof['private_state_file']);state=json.loads(state_path.read_text());assert state.get('tokens',{}).get('access_token')
spec=importlib.util.spec_from_file_location('control',BASE/'scripts/control.py');control=importlib.util.module_from_spec(spec);spec.loader.exec_module(control)
def chunk(kind,data):return struct.pack('!I',len(data))+kind+data+struct.pack('!I',zlib.crc32(kind+data)&0xffffffff)
nonce=state['run_id'];pixels=hashlib.sha256(nonce.encode()).digest();raw=b''.join(b'\x00'+bytes(pixels[(y*24+x)%len(pixels)] for x in range(24)) for y in range(8));png=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('!IIBBBBB',8,8,8,2,0,0,0))+chunk(b'tEXt',b'dell-e2e\x00'+nonce.encode())+chunk(b'IDAT',zlib.compress(raw))+chunk(b'IEND',b'');assert len(png)<=4096
payload={'run_id':nonce,'access_token':state['tokens']['access_token'],'image_base64':base64.b64encode(png).decode(),'image_sha256':hashlib.sha256(png).hexdigest(),'known_secrets_to_scan':{'client_secret':(BASE/'private/java/secrets/oauth-finger-admin-secret').read_text().strip(),'admin_password':(BASE/'private/java/secrets/admin-password').read_text().strip(),'access_token':state['tokens']['access_token'],'refresh_token':state['tokens'].get('refresh_token','')}}
code=r'''
from pathlib import Path
import socket,json,sys,urllib.request,urllib.error,urllib.parse,base64,hashlib,re,datetime
assert socket.gethostname()=='java-test-01' and not Path('/etc/pve').exists() and Path('/opt/finger/current-test').resolve().name==EXPECTED_RELEASE
v=json.loads(sys.stdin.read());assert re.fullmatch('[a-f0-9]{32}',v['run_id']);image=base64.b64decode(v['image_base64']);assert len(image)<=4096 and hashlib.sha256(image).hexdigest()==v['image_sha256'];token=v['access_token']
class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,*args,**kwargs):return None
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect());steps=[];result={'at':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),'status':'in-progress','steps':steps,'secret_values_emitted':False,'controlled_restart_performed':False};stage='initial'
def request(path,method='GET',data=None,bearer=token,port=9999,content_type='application/json'):
 headers={}
 if bearer is not None:headers['Authorization']='Bearer '+bearer
 if data is not None:headers['Content-Type']=content_type
 req=urllib.request.Request('http://10.63.20.20:'+str(port)+path,data=data,method=method,headers=headers)
 try:
  with opener.open(req,timeout=20) as r:return r.status,r.read(1024*1024)
 except urllib.error.HTTPError as e:
  status=e.code;body=e.read(262144);e.close();return status,body
def api(path,method='POST',data=b'{}',bearer=token,port=9999):
 status,body=request(path,method,data,bearer,port);parsed=json.loads(body);return status,parsed
def denied(status,body):return status in [401,403] or (status==200 and body.get('code') in [10008,10009,10010,10015,10016,10018])
try:
 stage='application-log-secret-check';matches=[]
 for name in ['finger-auth','finger-gateway-mobile','finger-bff-system','finger-service-system','finger-service-coms']:
  p=Path('/var/log/finger')/name/'app.log'
  if not p.exists():continue
  raw=p.read_bytes()
  found=[label for label,secret in v['known_secrets_to_scan'].items() if secret and secret.encode() in raw]
  if found:matches.append({'service':name,'matched_secret_categories':found})
 steps.append({'name':stage,'status':'passed' if not matches else 'failed','matches':matches,'raw_logs_saved':False});assert not matches,'Known test secret present in application log'
 stage='unauthenticated-role-denied';status,body=api('/finger-bff-system/sys-api/v1/role/get-list',bearer=None);ok=denied(status,body);steps.append({'name':stage,'status':'passed' if ok else 'failed','http_status':status,'api_code':body.get('code')});assert ok
 stage='forged-signature-role-denied';pieces=token.split('.');sig=bytearray(base64.urlsafe_b64decode(pieces[2]+'='*(-len(pieces[2])%4)));sig[0]^=1;bad='.'.join(pieces[:2]+[base64.urlsafe_b64encode(sig).decode().rstrip('=')]);status,body=api('/finger-bff-system/sys-api/v1/role/get-list',bearer=bad);ok=denied(status,body);steps.append({'name':stage,'status':'passed' if ok else 'failed','http_status':status,'api_code':body.get('code'),'original_token_unchanged':True});assert ok
 stage='authenticated-role-list-through-gateway-bff-system';status,body=api('/finger-bff-system/sys-api/v1/role/get-list');roles=body.get('data');ids=[str(x.get('id')) for x in roles] if isinstance(roles,list) else [];ok=status==200 and body.get('code')==0 and '900000000002'in ids;steps.append({'name':stage,'status':'passed' if ok else 'failed','http_status':status,'api_code':body.get('code'),'role_count':len(ids),'synthetic_role_present':'900000000002'in ids});assert ok
 stage='authenticated-role-permission-read';status,body=api('/finger-bff-system/sys-api/v1/role/get-role-permissions',data=json.dumps({'id':900000000002}).encode());perms=body.get('data');ok=status==200 and body.get('code')==0 and isinstance(perms,list);steps.append({'name':stage,'status':'passed' if ok else 'failed','http_status':status,'api_code':body.get('code'),'permission_count':len(perms) if isinstance(perms,list) else None,'nonroot_identity_matrix':'not-tested-no-second-identity-authorized'});assert ok
 stage='internal-coms-synthetic-png-upload';boundary='dell-e2e-'+v['run_id'];filename='dell-e2e-'+v['run_id']+'.png';multipart=('--'+boundary+'\r\nContent-Disposition: form-data; name="file"; filename="'+filename+'"\r\nContent-Type: image/png\r\n\r\n').encode()+image+('\r\n--'+boundary+'--\r\n').encode();status,raw=request('/inner/coms/v1/upload/image','POST',multipart,port=10202,content_type='multipart/form-data; boundary='+boundary);body=json.loads(raw);data=body.get('data');ok=status==200 and body.get('code')==0 and isinstance(data,dict) and data.get('fileId') is not None;steps.append({'name':stage,'status':'passed' if ok else 'failed','http_status':status,'api_code':body.get('code'),'fixture_bytes':len(image),'fixture_sha256':v['image_sha256']});assert ok
 result['upload_info']={k:data.get(k) for k in ['fileId','objectKey','url','fileSize','type']};key=data['objectKey'];assert re.fullmatch(r'image/[0-9]{4}-[0-9]{2}/[a-f0-9]{32}\.png',key)
 owned=Path('/var/lib/finger/finger-service-coms/uploads')/key;assert owned.resolve().is_relative_to(Path('/var/lib/finger/finger-service-coms/uploads')) and owned.is_file();assert hashlib.sha256(owned.read_bytes()).hexdigest()==v['image_sha256'];result['owned_file_path']=str(owned)
 path=urllib.parse.urlsplit(data['url']).path;assert path=='/finger-bff-system/dell-test-files/'+key
 stage='unauthenticated-issued-file-path-denied';status,raw=request(path,bearer=None)
 try:body=json.loads(raw)
 except ValueError:body={}
 ok=denied(status,body);steps.append({'name':stage,'status':'passed' if ok else 'failed','http_status':status,'api_code':body.get('code')});assert ok
 stage='authenticated-gateway-file-read-before-restart';status,raw=request(path);sha=hashlib.sha256(raw).hexdigest();ok=status==200 and sha==v['image_sha256'];steps.append({'name':stage,'status':'passed' if ok else 'failed','http_status':status,'bytes':len(raw),'sha256':sha});assert ok
 result['status']='role-permission-and-file-initial-passed';result['file_request_path']=path;result['fixture_image_sha256']=v['image_sha256'];result['fixture_image_bytes']=len(image)
except Exception as error:result['status']='failed-stopped-no-restart';result['failed_stage']=stage;result['error_type']=type(error).__name__
print(json.dumps(result))
'''
code=code.replace('EXPECTED_RELEASE',repr(proof['release_id']))
r=control.guest(240,'sudo -n python3 -c '+shlex.quote(code),data=json.dumps(payload).encode(),timeout=150,info=state['target'])
if r['exit_code']:raise SystemExit('Role/file transport failure; output suppressed')
result=json.loads(r['stdout']);proof['steps'].extend(result['steps']);proof['role_file_initial_status']=result['status'];proof['status']='file-written-persistence-test-pending' if result['status']=='role-permission-and-file-initial-passed' else result['status']
for key in ['upload_info','owned_file_path','file_request_path','fixture_image_sha256','fixture_image_bytes']:
 if key in result:state[key]=result[key]
state['fixture_image_base64']=base64.b64encode(png).decode();state_path.write_text(json.dumps(state)+'\n');state_path.chmod(0o600)
if result['status'].startswith('failed'):proof['failure_detail']={k:result[k] for k in ['failed_stage','error_type'] if k in result}
record.write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k not in ['owned_file_path','upload_info']},ensure_ascii=False))
