#!/usr/bin/env python3
"""Accept only on new assigned Nexus, after explicit user authorization recorded by manager."""
import sys,json,urllib.request,base64,hashlib,datetime,argparse
from pathlib import Path
from target_guard import verify_target
p=argparse.ArgumentParser();p.add_argument('--explicit-user-authorization-recorded',action='store_true');a=p.parse_args();assert a.explicit_user_authorization_recorded
c,d=verify_target();assert Path(__file__).with_name('fresh-instance.json').is_file()
secret=Path('/root/dell-nexus-secrets/admin-password').read_text().strip();base='http://10.63.30.20:8081';headers={'Authorization':'Basic '+base64.b64encode(('admin:'+secret).encode()).decode()}
class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,*a,**k):return None
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect)
def req(method,path,body=None):
 h=dict(headers);data=None
 if body is not None:h['Content-Type']='application/json';data=json.dumps(body).encode()
 with opener.open(urllib.request.Request(base+path,data=data,method=method,headers=h),timeout=15) as r:return json.loads(r.read()) if r.status!=204 else None
assert req('GET','/service/rest/swagger.json')['info']['version']=='3.84.0-03'
state=req('GET','/service/rest/v1/system/eula');before=state['accepted'];assert 'https://links.sonatype.com/products/nxrm/ce-eula' in state['disclaimer']
if not before:state['accepted']=True;req('POST','/service/rest/v1/system/eula',state)
after=req('GET','/service/rest/v1/system/eula');assert after['accepted'] is True
print(json.dumps({'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'EULA-explicitly-user-authorized-and-accepted-on-new-instance','target':'10.63.30.20:8081','version':'3.84.0-03','previously_accepted':before,'accepted':True,'disclaimer_sha256':hashlib.sha256(state['disclaimer'].encode()).hexdigest(),'source_or_upstream_credentials_used':False}))
