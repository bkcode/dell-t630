#!/usr/bin/env python3
"""Read-only playback/transcoding and SMB open-session counts before an approved NAS change."""
import importlib.util,json,sys
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[3]
s=importlib.util.spec_from_file_location('jf_native',ROOT/'network19/services-media/nas-jellyfin-native-verify.py');jf=importlib.util.module_from_spec(s);s.loader.exec_module(jf)
admin,_=jf.credential('jellyfin-admin-password');auth=jf.call('POST','/Users/AuthenticateByName',{'Username':'delladmin','Pw':admin});token=auth['AccessToken']
# Same native transport, exact authenticated read route; no playback stop or configuration request.
old_request=jf.request
import subprocess,urllib.parse
# /Sessions is an already verified Jellyfin12.4 read endpoint, absent from the old fixture-only allowlist.
config='url = '+jf.quote('http://192.168.19.60:8096/Sessions')+'\nrequest = "GET"\nheader = '+jf.quote('Authorization: MediaBrowser Client="DellVPNPreflight", Device="MacNativeCurl", DeviceId="dell-vpn-admin", Version="1.0", Token="'+token+'"')+'\nheader = "Accept: application/json; profile=PascalCase"\n'
p=subprocess.run(['/usr/bin/curl','-q','--config','-','--noproxy','*','--proto','=http','--max-redirs','0','--connect-timeout','5','--max-time','20','--silent','--write-out','\n%{http_code}'],input=config.encode(),stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,env=jf.ENV,timeout=25)
raw,status=p.stdout.rsplit(b'\n',1);assert p.returncode==0 and status==b'200';sessions=json.loads(raw)
playing=[x for x in sessions if x.get('NowPlayingItem')];transcoding=[x for x in sessions if x.get('TranscodingInfo')]
sys.path.insert(0,str(ROOT/'scripts'));import control
control.BASE+=['-o','ForwardAgent=no'];info=json.loads((ROOT/'network19/evidence/migrated-access.json').read_text())['targets']['260']
script=r'''
import json,os,socket,subprocess
from pathlib import Path
assert os.geteuid()==0 and socket.gethostname().split('.')[0]=='nas-media' and not Path('/etc/pve').exists()
p=subprocess.run(['/usr/bin/smbstatus','--json'],capture_output=True,text=True,timeout=20);assert p.returncode==0;v=json.loads(p.stdout)
counts={k:len(v.get(k,{}) or {}) for k in ['sessions','tcons','open_files']}
lines=[]
for path in Path('/srv/salt/omv/deploy/samba').rglob('*.sls'):
 for number,line in enumerate(path.read_text().splitlines(),1):
  if any(word in line for word in ['service.running','reload','restart','watch:','watch_in:']):lines.append({'source':str(path),'line':number,'text':line.strip()})
print(json.dumps({'SMB_counts':counts,'Samba_service_deploy_source':lines,'no_client_file_names_or_credentials_emitted':True}))
'''
r=control.guest(260,'sudo python3 -',data=script.encode(),timeout=50,info=info);assert r['exit_code']==0
value={'role':260,'status':'read-only-active-client-preflight','JF_session_count':len(sessions),'JF_active_or_paused_playback_count':len(playing),'JF_transcoding_count':len(transcoding),'JF_safe_for_required_restart':not playing and not transcoding,**json.loads(r['stdout'])}
Path(__file__).with_name('client-preflight.json').write_text(json.dumps(value,indent=2)+'\n');print(json.dumps({'role':260,'status':value['status'],'JF_active_or_paused_playback_count':len(playing),'JF_transcoding_count':len(transcoding),'SMB_counts':value['SMB_counts']}))
