#!/usr/bin/env python3
"""Native Mac curl to NAS260's new address; existing identities/media only, no create/scan/play events."""
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import urllib.parse

BASE='http://192.168.19.60:8096'
ROOT=Path(__file__).resolve().parents[2]
ENV={'PATH':'/usr/bin:/bin','LANG':'C','LC_ALL':'C'}


def credential(name):
    path=ROOT/'private/nas/secrets'/name
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
    try:
        s=os.fstat(fd)
        if not stat.S_ISREG(s.st_mode) or s.st_uid!=os.getuid() or stat.S_IMODE(s.st_mode)!=0o600 or s.st_size>1024:raise RuntimeError('private NAS credential metadata rejected')
        raw=os.read(fd,1025)
    finally:os.close(fd)
    value=raw.decode().rstrip('\n')
    if len(value)<24 or any(x in value for x in '\r\n\0'):raise RuntimeError('private NAS credential format rejected')
    return value,hashlib.sha256(raw).hexdigest()


def quote(value):return '"'+value.replace('\\','\\\\').replace('"','\\"').replace('\r','\\r').replace('\n','\\n')+'"'


def request(method,path,body=None,token=None,device='admin'):
    allowed=path in ['/System/Info/Public','/Users/AuthenticateByName','/Library/VirtualFolders'] or path.startswith('/Items?') or re.fullmatch(r'/Items/[A-Fa-f0-9-]{16,80}/PlaybackInfo',path) or re.fullmatch(r'/Videos/[A-Fa-f0-9-]{16,80}/stream\?[^\r\n]+',path)
    if not allowed or method not in ('GET','POST') or '://' in path:raise RuntimeError('fixed NAS verification route rejected')
    if token and not re.fullmatch('[A-Za-z0-9._~-]{16,512}',token):raise RuntimeError('server token shape rejected')
    header='MediaBrowser Client="DellNetwork19Acceptance", Device="MacNativeCurl", DeviceId="dell-network19-'+device+'", Version="1.0"'+(', Token="'+token+'"' if token else '')
    config='url = '+quote(BASE+path)+'\nrequest = '+quote(method)+'\nheader = '+quote('Authorization: '+header)+'\nheader = "Accept: application/json; profile=PascalCase"\n'
    if body is not None:config+='header = "Content-Type: application/json"\ndata = '+quote(json.dumps(body,separators=(',',':')))+'\n'
    p=subprocess.run(['/usr/bin/curl','-q','--config','-','--noproxy','*','--proto','=http','--max-redirs','0','--connect-timeout','5','--max-time','25','--max-filesize','16777216','--silent','--write-out','\n%{http_code}'],input=config.encode(),stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,env=ENV,timeout=30)
    try:raw,status=p.stdout.rsplit(b'\n',1)
    except ValueError:raise RuntimeError('native NAS HTTP response unconfirmed') from None
    if p.returncode or status!=b'200':raise RuntimeError('native NAS HTTP status unconfirmed')
    return raw


def call(method,path,body=None,token=None,device='admin'):return json.loads(request(method,path,body,token,device))


def main():
    admin,ah=credential('jellyfin-admin-password');viewer,vh=credential('jellyfin-viewer-password')
    public=call('GET','/System/Info/Public');assert public['Version']=='12.4.0' and public['StartupWizardCompleted']
    a=call('POST','/Users/AuthenticateByName',{'Username':'delladmin','Pw':admin});at=a['AccessToken'];assert a['User']['Policy']['IsAdministrator']
    folders=call('GET','/Library/VirtualFolders',token=at);assert any(x.get('Name')=='Dell Acceptance' for x in folders),'Existing acceptance library absent; do not create'
    v=call('POST','/Users/AuthenticateByName',{'Username':'dellviewer','Pw':viewer},device='viewer');vt=v['AccessToken'];uid=v['User']['Id'];assert not v['User']['Policy']['IsAdministrator']
    items=call('GET','/Items?'+urllib.parse.urlencode({'UserId':uid,'Recursive':'true','Fields':'MediaSources,Path'}),token=vt,device='viewer')
    choices=[x for x in items.get('Items',[]) if x.get('Path','').endswith('/dell-acceptance-fixture.mp4')]
    assert len(choices)==1,'Existing original fixture ambiguous; no file/library generation'
    item=choices[0];assert re.fullmatch('[A-Fa-f0-9-]{16,80}',item['Id'])
    profile={'Name':'Dell original H264 AAC MP4 network19 client','MaxStreamingBitrate':20000000,'MaxStaticBitrate':20000000,'DirectPlayProfiles':[{'Container':'mp4,m4v','Type':'Video','VideoCodec':'h264','AudioCodec':'aac'}],'TranscodingProfiles':[],'CodecProfiles':[],'ContainerProfiles':[],'SubtitleProfiles':[]}
    playback=call('POST','/Items/'+item['Id']+'/PlaybackInfo',{'UserId':uid,'DeviceProfile':profile,'EnableDirectPlay':True,'EnableDirectStream':True,'EnableTranscoding':False,'MaxStreamingBitrate':20000000},token=vt,device='viewer')
    media=playback['MediaSources'][0];assert media.get('SupportsDirectPlay') is True
    stream=request('GET','/Videos/'+item['Id']+'/stream?'+urllib.parse.urlencode({'static':'true','MediaSourceId':media['Id']}),token=vt,device='viewer')
    digest=hashlib.sha256(stream).hexdigest();assert digest=='5b2499415295d67552b400a8d197fe11c61e73801b8c281247de04567d312905'
    assert credential('jellyfin-admin-password')[1]==ah and credential('jellyfin-viewer-password')[1]==vh
    result={'role':260,'status':'new-network-native-client-original-media-and-identities-verified','origin':BASE,'server_version':public['Version'],'existing_admin_and_viewer_login':True,'viewer_non_admin':True,'original_library_reused':True,'original_movie_fixture_SHA256':digest,'original_movie_bytes':len(stream),'playback_info_supports_DirectPlay':True,'original_static_stream_SHA_matches':True,'transcoding_enabled_in_request':False,'new_fixture_library_or_user_created':False,'playing_event_or_scan_requests':False,'credential_files_unchanged':True,'credentials_tokens_or_hashes_emitted':False,'secret_transport':'native curl STDIN config only, no argv/env/proxy/redirect','physical_TV_console_claimed':False}
    Path(__file__).with_name('nas-jellyfin-post-cutover-verification.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'role':260,'status':result['status']}))


if __name__=='__main__':
    try:main()
    except Exception:
        print(json.dumps({'role':260,'status':'native-Jellyfin-verification-unconfirmed','raw_response_withheld':True}));raise SystemExit(1)
