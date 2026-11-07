#!/usr/bin/env python3
"""Initialize verified local Jellyfin using stdin secrets; never echoes credentials or sessions."""
from pathlib import Path
import json,os,socket,subprocess,sys,time,urllib.request,urllib.error
assert os.geteuid()==0 and socket.gethostname()=='nas-media'
values=json.loads(sys.stdin.read());base='http://127.0.0.1:8096';token=None
class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,*a,**k):return None
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect)
client='MediaBrowser Client="DellAcceptance", Device="NASSetup", DeviceId="dell-nas-acceptance", Version="1.0"'
def call(method,path,body=None):
 headers={'Authorization':client+(', Token="'+token+'"' if token else ''),'Accept':'application/json; profile="PascalCase"'}
 raw=None if body is None else json.dumps(body).encode()
 if raw is not None:headers['Content-Type']='application/json'
 for attempt in range(6):
  try:
   with opener.open(urllib.request.Request(base+path,data=raw,method=method,headers=headers),timeout=20) as r:
    data=r.read(12*1024*1024);return json.loads(data) if data else None
  except urllib.error.HTTPError as e:
   if method=='GET' and e.code==503 and attempt<5:
    time.sleep(2);continue
   raise RuntimeError('Jellyfin HTTP '+str(e.code)+' for '+path) from None
info=call('GET','/System/Info/Public');assert info['Version']=='12.4.0','Review APIs for changed image version'
if not info.get('StartupWizardCompleted'):
 call('POST','/Startup/Configuration',{'ServerName':'Dell Home Media','UICulture':'zh-CN','MetadataCountryCode':'CN','PreferredMetadataLanguage':'zh-CN'})
 initial=call('GET','/Startup/User')  # Server InitializeAsync creates the initial user, per actual StartupController.
 if initial.get('Name')!='delladmin':
  call('POST','/Startup/User',{'Name':'delladmin','Password':values['admin']})
 call('POST','/Startup/RemoteAccess',{'EnableRemoteAccess':False})
 call('POST','/Startup/Complete')
auth=call('POST','/Users/AuthenticateByName',{'Username':'delladmin','Pw':values['admin']});token=auth['AccessToken'];admin=auth['User'];assert admin['Name']=='delladmin' and admin.get('Policy',{}).get('IsAdministrator') is True
# Inspect actual configuration models before changing the LAN-only network fields.
network=call('GET','/System/Configuration/network')
assert 'LocalNetworkSubnets' in network and 'EnableRemoteAccess' in network
previous_network=json.dumps(network,sort_keys=True)
docker_network=json.loads(subprocess.check_output(['docker','network','inspect','dell-nas_default'],text=True))[0]
gateways=[c['Gateway']+'/32' for c in docker_network['IPAM']['Config'] if c.get('Gateway') and ':' not in c['Gateway']]
network['LocalNetworkSubnets']=['10.63.40.0/24','192.168.21.0/24','127.0.0.0/8']+gateways
network['EnableRemoteAccess']=False
if 'EnableUPnP' in network:network['EnableUPnP']=False
if json.dumps(network,sort_keys=True)!=previous_network:call('POST','/System/Configuration/network',network)
users=call('GET','/Users');existing=[u for u in users if u['Name']=='dellviewer']
if existing:viewer=existing[0]
else:viewer=call('POST','/Users/New',{'Name':'dellviewer','Password':values['viewer']})
viewer_auth=call('POST','/Users/AuthenticateByName',{'Username':'dellviewer','Pw':values['viewer']})
assert viewer_auth.get('AccessToken') and not viewer_auth['User'].get('Policy',{}).get('IsAdministrator')
# Only models/field names, not auth results, are persisted for subsequent library setup.
doc=call('GET','/api-docs/openapi.json');wanted=['CreateUserByName','AddVirtualFolderDto','LibraryOptions','NetworkConfiguration','UserPolicy','UserPolicyDto','DeviceProfile','PlaybackInfoDto','PlaybackInfoResponse']
models={k:v for k,v in doc.get('components',{}).get('schemas',{}).items() if k in wanted}
path=Path('/root/private/dell-nas/jellyfin-api-models.json');path.write_text(json.dumps({'schemas':models,'security_schemes':doc.get('components',{}).get('securitySchemes',{}),'paths':{k:v for k,v in doc['paths'].items() if k.startswith('/Users/') or k.startswith('/Libraries/') or k.startswith('/Library/VirtualFolders') or 'PlaybackInfo' in k}},indent=2)+'\n');path.chmod(0o600)
result={'status':'strong-accounts-initialized-loopback-only','version':info['Version'],'admin_user':'delladmin','viewer_user':'dellviewer','admin_login_verified':True,'viewer_login_verified':True,'viewer_is_admin':False,'startup_complete':True,'remote_access_enabled':False,'LAN_subnets_configured':True,'token_or_password_emitted':False}
p=Path('/root/private/dell-nas/jellyfin-initialization-result.json');p.write_text(json.dumps(result,indent=2)+'\n');p.chmod(0o600)
print(json.dumps(result))
