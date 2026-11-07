#!/usr/bin/env python3
"""Fetch normal captcha only after approved release is independently healthy."""
from pathlib import Path
import importlib.util,sys,json,base64,hashlib,uuid,argparse,shutil
sys.dont_write_bytecode=True
BASE=Path(__file__).resolve().parents[3]
spec=importlib.util.spec_from_file_location('control',BASE/'scripts/control.py');control=importlib.util.module_from_spec(spec);spec.loader.exec_module(control)
parser=argparse.ArgumentParser();parser.add_argument('--expected-release',required=True);args=parser.parse_args();a=json.loads((BASE/'evidence/implementation/java-test-activation.json').read_text());assert a['result']['exit_code']==0 and json.loads(a['result']['stdout'])['release_id']==args.expected_release
target=next(x['target'] for x in json.loads((BASE/'evidence/implementation/private-guest-access.json').read_text())['roles'] if x['target']['vmid']==240)
code=r'''
from pathlib import Path
import socket,json,urllib.request,datetime
assert socket.gethostname()=='java-test-01' and not Path('/etc/pve').exists()
root=Path('/opt/finger/current-test').resolve();assert root.name==EXPECTED_RELEASE;manifest=json.loads((root/'manifest.json').read_text());opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def get(path,port=9999):
 with opener.open('http://10.63.20.20:'+str(port)+path,timeout=10) as r:return r.status,json.loads(r.read(1024*1024))
health=[]
for row in manifest['services']:
 status,body=get('/actuator/health',row['port']);assert status==200 and body.get('status')=='UP';health.append({'service':row['name'],'status':'UP','http_status':status})
_,metadata=get('/.well-known/openid-configuration');_,jwks=get('/oauth2/jwks');assert metadata['issuer']=='http://192.168.21.22:19999' and jwks.get('keys')
status,captcha=get('/finger-auth/api/v1/auth/captcha');assert status==200 and captcha.get('code')==0 and isinstance(captcha.get('data'),dict)
print(json.dumps({'at':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),'release_id':root.name,'health':health,'oidc':{k:metadata.get(k) for k in ['issuer','authorization_endpoint','token_endpoint','jwks_uri']},'jwks_public_keys':jwks['keys'],'captcha':captcha['data']}))
'''
code=code.replace('EXPECTED_RELEASE',repr(args.expected_release))
r=control.guest(240,'sudo -n python3 -',data=code.encode(),timeout=100,info=target)
if r['exit_code']:raise SystemExit('Normal captcha fetch failed; raw private output suppressed')
value=json.loads(r['stdout']);captcha=value.pop('captcha');assert captcha['captchaId']!='0xFFFFFFFF';encoded=captcha['captchaBase64'];assert encoded.startswith('data:image/');image=base64.b64decode(encoded.split(',',1)[1],validate=True);assert image[:8]==b'\x89PNG\r\n\x1a\n'
run=uuid.uuid4().hex;folder=BASE/'private/java-e2e'/run;folder.mkdir(parents=True,mode=0o700);png=folder/'captcha.png';png.write_bytes(image);png.chmod(0o600)
state={'run_id':run,'target':target,'release_id':value['release_id'],'captcha_id':captcha['captchaId'],'image_file':str(png),'jwks_public_keys':value.pop('jwks_public_keys')};path=folder/'state.json';path.write_text(json.dumps(state)+'\n');path.chmod(0o600)
proof={'schema_version':1,'run_id':run,'status':'normal-captcha-fetched-e2e-in-progress','release_id':value['release_id'],'target':target,'initial_observations':value,'captcha':{'endpoint':'/finger-auth/api/v1/auth/captcha','normal_validation':True,'magic_skip_id_used':False,'id_sha256':hashlib.sha256(captcha['captchaId'].encode()).hexdigest(),'image_bytes':len(image),'image_sha256':hashlib.sha256(image).hexdigest(),'png_header_valid':True},'private_state_file':str(path),'steps':[],'secrets_values_emitted':False,'source_business_data_imported':False}
record=BASE/'evidence/implementation/java-test-business-acceptance.json'
if record.exists():
 previous=json.loads(record.read_text());archive=BASE/'evidence/implementation'/('java-test-business-attempt-'+previous['run_id']+'.json');assert not archive.exists();shutil.copyfile(record,archive);archive.chmod(0o600);proof['previous_attempts']=[str(archive.relative_to(BASE))]
record.write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n');record.chmod(0o600)
print(json.dumps({'run_id':run,'private_state_file':str(path),'captcha_png':str(png),'image_bytes':len(image),'five_services_up':True,'issuer':value['oidc']['issuer']}))
