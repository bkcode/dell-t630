#!/usr/bin/python3
"""Initialize only the new manager's daily user; no resource-file writes or secret output."""
import datetime,json,os,pathlib,re,socket,ssl,urllib.request,urllib.parse,urllib.error
C=pathlib.Path('/etc/dell-filebrowser');M=pathlib.Path('/var/lib/dell-filebrowser-manager');BASE='https://192.168.19.80:8080';PERMS={'view':True,'download':True,'create':True,'modify':False,'delete':False,'configured':True}
def need(v,c):
 if not v:raise RuntimeError(c)
class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,*a,**k):return None
class API:
 def __init__(self):self.op=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect(),urllib.request.HTTPSHandler(context=ssl.create_default_context(cafile=str(C/'tls.crt'))))
 def request(self,method,path,body=None,token=None,password=None):
  need(path.startswith(('/health','/api/auth/login','/api/users','/api/settings')),'fixed-bootstrap-API-path');h={}
  if token:h['Authorization']='Bearer '+token
  if password:h['X-Password']=urllib.parse.quote(password,safe='')
  if body is not None:h['Content-Type']='application/json';body=json.dumps(body).encode()
  try:
   with self.op.open(urllib.request.Request(BASE+path,data=body,method=method,headers=h),timeout=15)as r:return r.status,r.read(2097152)
  except urllib.error.HTTPError as e:code=e.code;e.close();return code,b''
 def login(self,user,password):
  code,b=self.request('POST','/api/auth/login?'+urllib.parse.urlencode({'username':user}),password=password);need(code==200,'fresh-user-login-failed');s=b.decode().strip()
  try:s=json.loads(s)
  except ValueError:pass
  need(isinstance(s,str)and re.fullmatch(r'[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+',s)is not None,'JWT-response-required');return s

def main():
 os.umask(0o077);need(os.geteuid()==0 and socket.gethostname()=='resource-service','new-manager-root-only');need(not(C/'bootstrap.complete').exists(),'manager-already-initialized-no-reset')
 login=json.loads((C/'secrets/login.json').read_text());api=API();code,b=api.request('GET','/health');need(code==200 and json.loads(b).get('message')=='ok','native-HTTPS-not-ready');admin=api.login(login['admin']['username'],login['admin']['password'])
 code,b=api.request('GET','/api/users',token=admin);need(code==200,'initial-user-read-failed');users=json.loads(b);need({u['username']for u in users}<={'admin','anonymous'},'existing-unknown-user-refuse')
 data={'username':'resources','password':login['operator']['password'],'loginMethod':'password','permissions':{'admin':False,'api':False,'share':False,'realtime':False},'scopes':[{'name':'resources','scope':'/','permissions':PERMS}]}
 code,_=api.request('POST','/api/users',body={'data':data,'which':[]},token=admin,password=login['admin']['password']);need(code in [200,201],'daily-user-create-failed')
 operator=api.login('resources',login['operator']['password']);code,b=api.request('GET','/api/users?username=resources',token=admin);need(code==200,'daily-user-readback-failed');u=json.loads(b);need(isinstance(u,dict),'one-daily-user-required');need(u['username']=='resources'and u.get('loginMethod')=='password','daily-user-identity')
 globalp=u.get('permissions',{});need(all(not globalp.get(k,False)for k in ['admin','api','share','realtime']),'daily-global-permissions')
 scopes=u.get('scopes',[]);need(len(scopes)==1 and scopes[0].get('name')=='resources'and scopes[0].get('scope')=='/','daily-source-scope');need(all(scopes[0].get('permissions',{}).get(k,False)==v for k,v in PERMS.items()),'daily-source-permissions')
 code,b=api.request('GET','/api/settings',token=admin);need(code==200,'admin-settings-readback');known=[login['admin']['password'],login['operator']['password'],(C/'secrets/jwt-key').read_text().strip()];need(all(v.encode()not in b for v in known),'known-secret-exposed-by-settings')
 operator_settings,_=api.request('GET','/api/settings',token=operator);need(operator_settings in [401,403],'daily-admin-settings-not-denied')
 marker=C/'bootstrap.complete';fd=os.open(marker,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o644);os.fchmod(fd,0o644)
 with os.fdopen(fd,'w')as f:f.write('initialized-admin-and-restricted-daily-user\n');f.flush();os.fsync(f.fileno())
 out={'at':datetime.datetime.now().astimezone().isoformat(),'status':'daily-user-initialized-and-settings-secret-redaction-passed','daily_username':'resources','maintenance_username':'admin','daily_global_permissions':{k:False for k in ['admin','api','share','realtime']},'daily_source_permissions':PERMS,'source':'resources','scope':'/','HTTPS_chain_and_hostname_verified':True,'fresh_admin_and_daily_login':True,'known_secrets_absent_from_admin_settings_API':True,'daily_admin_settings_denied':operator_settings,'root_owned_initialization_marker_created':True,'resource_files_modified':False,'real_credentials_or_tokens_output':False,'application_restart_acceptance_pending':True};p=M/'bootstrap-result.json';need(not p.exists(),'bootstrap-result-exists');fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
 with os.fdopen(fd,'w')as f:json.dump(out,f,indent=2);f.write('\n')
 print(json.dumps(out))
if __name__=='__main__':
 try:main()
 except Exception as e:print(json.dumps({'status':'bootstrap-not-confirmed','error_type':type(e).__name__,'failure_code':str(e)if re.fullmatch('[A-Za-z0-9-]{1,100}',str(e))else'private-response-withheld'}));raise SystemExit(1)
