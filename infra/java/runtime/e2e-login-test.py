#!/usr/bin/env python3
"""Normal captcha login of the sole approved synthetic test identity."""
from pathlib import Path
import sys,json,base64,hashlib,importlib.util,shlex
sys.dont_write_bytecode=True
BASE=Path(__file__).resolve().parents[3];record=BASE/'evidence/implementation/java-test-business-acceptance.json';proof=json.loads(record.read_text());private=Path(proof['private_state_file']);state=json.loads(private.read_text());assert state['captcha_id']!='0xFFFFFFFF'
spec=importlib.util.spec_from_file_location('control',BASE/'scripts/control.py');control=importlib.util.module_from_spec(spec);spec.loader.exec_module(control)
v={'client_id':'finger-admin','username':'FNTEST0001','client_secret':(BASE/'private/java/secrets/oauth-finger-admin-secret').read_text().strip(),'password':(BASE/'private/java/secrets/admin-password').read_text().strip(),'captcha_id':state['captcha_id'],'captcha_code':state['normal_captcha_answer']}
code=r'''
from pathlib import Path
import socket,json,sys,base64,urllib.parse,urllib.request,urllib.error,datetime
assert socket.gethostname()=='java-test-01' and not Path('/etc/pve').exists() and Path('/opt/finger/current-test').resolve().name==EXPECTED_RELEASE
v=json.loads(sys.stdin.read());assert v['client_id']=='finger-admin' and v['username']=='FNTEST0001' and v['captcha_id']!='0xFFFFFFFF'
body=urllib.parse.urlencode({'grant_type':'captcha','username':v['username'],'password':v['password'],'captchaId':v['captcha_id'],'captchaCode':v['captcha_code'],'scope':'openid','type':'0','ut':'0'}).encode();basic=base64.b64encode((v['client_id']+':'+v['client_secret']).encode()).decode()
class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,*args,**kwargs):return None
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect());req=urllib.request.Request('http://10.63.20.20:9999/finger-auth/oauth2/token',data=body,method='POST',headers={'Authorization':'Basic '+basic,'Content-Type':'application/x-www-form-urlencoded'})
try:
 with opener.open(req,timeout=30) as r:status=r.status;response=json.loads(r.read(1024*1024))
except urllib.error.HTTPError as error:status=error.code;response=json.loads(error.read(262144));error.close()
print(json.dumps({'at':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),'http_status':status,'private_response':response}))
'''.replace('EXPECTED_RELEASE',repr(proof['release_id']))
r=control.guest(240,'sudo -n python3 -c '+shlex.quote(code),data=json.dumps(v).encode(),timeout=60,info=state['target'])
if r['exit_code']:raise SystemExit('Login transport failed; private output suppressed')
result=json.loads(r['stdout']);body=result['private_response'];tokens=body.get('data') if isinstance(body.get('data'),dict) else body;ok=result['http_status']==200 and isinstance(tokens.get('access_token'),str)
step={'name':'normal-prefixed-captcha-oauth-login','at':result['at'],'http_status':result['http_status'],'api_code':body.get('code'),'status':'passed' if ok else 'failed','client_id':'finger-admin','synthetic_account':'FNTEST0001','magic_captcha_bypass_used':False,'captcha_answer_logged':False,'secrets_values_emitted':False}
if ok:
 token=tokens['access_token'];parts=token.split('.');assert len(parts)==3;decode=lambda s:json.loads(base64.urlsafe_b64decode(s+'='*(-len(s)%4)));header=decode(parts[0]);claims=decode(parts[1]);assert claims['iss']=='http://192.168.21.22:19999' and str(claims.get('ui'))=='900000000001' and header.get('kid') in [j.get('kid') for j in state['jwks_public_keys']]
 state['tokens']=tokens;state['captcha_was_normally_solved']=True;state.pop('normal_captcha_answer');private.write_text(json.dumps(state)+'\n');private.chmod(0o600);step.update(access_token_received=True,access_token_sha256=hashlib.sha256(token.encode()).hexdigest(),jwt_algorithm=header['alg'],jwt_kid_matches_advertised_jwks=True,issuer_matches_candidate=True,synthetic_user_id_matches=True,claims_root_flag=claims.get('ir'),claims_role_id=claims.get('ri'),refresh_token_received=isinstance(tokens.get('refresh_token'),str))
proof['steps'].append(step);proof['status']='authenticated-e2e-in-progress' if ok else 'failed-normal-captcha-login';record.write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n');print(json.dumps(step))
