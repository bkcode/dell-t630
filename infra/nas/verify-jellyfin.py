#!/usr/bin/env python3
"""Generate an original fixture and verify Jellyfin DirectPlay-capable original-byte delivery."""
from pathlib import Path
import hashlib,json,os,socket,subprocess,sys,time,urllib.request,urllib.parse,urllib.error
assert os.geteuid()==0 and socket.gethostname()=='nas-media'
values=json.loads(sys.stdin.read());base='http://10.63.40.10:8096';opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
image='jellyfin/jellyfin@sha256:fea863d0cd9ec445985d9c75fc6ed64e38a1d2766cf0c250a33d553f4fc1b771'
folder=Path('/srv/dev-disk-by-uuid-5b19837c-128c-498a-b79d-563db810c34a/media/movies/DellAcceptance')
folder.mkdir(parents=True,exist_ok=True);os.chown(folder,2000,2000);folder.chmod(0o2775)
fixture=folder/'dell-acceptance-fixture.mp4'
if not fixture.exists():
 cmd=['docker','run','--rm','--network','none','--cpus','1','--memory','512m','--user','2000:2000','--mount','type=bind,source='+str(folder)+',target=/out','--entrypoint','/usr/lib/jellyfin-ffmpeg/ffmpeg',image,'-hide_banner','-loglevel','error','-nostdin','-f','lavfi','-i','testsrc2=size=640x360:rate=24','-f','lavfi','-i','sine=frequency=440:sample_rate=48000','-t','5','-c:v','libx264','-preset','ultrafast','-pix_fmt','yuv420p','-c:a','aac','-b:a','96k','-movflags','+faststart','/out/'+fixture.name]
 p=subprocess.run(cmd,capture_output=True,text=True,timeout=90);assert p.returncode==0,'Synthetic fixture generation failed; output withheld'
expected=hashlib.sha256(fixture.read_bytes()).hexdigest()
def call(method,path,body=None,token=None,device='admin'):
 header='MediaBrowser Client="DellAcceptance", Device="NASSynthetic", DeviceId="dell-nas-fixture-'+device+'", Version="1.0"'+(', Token="'+token+'"' if token else '')
 headers={'Authorization':header,'Accept':'application/json; profile="PascalCase"'}
 raw=None if body is None else json.dumps(body).encode()
 if raw is not None:headers['Content-Type']='application/json'
 try:
  with opener.open(urllib.request.Request(base+path,data=raw,method=method,headers=headers),timeout=20) as r:
   data=r.read(16*1024*1024)
   if not data:return None
   if 'json' in (r.headers.get('Content-Type') or ''):return json.loads(data)
   return data
 except urllib.error.HTTPError as e:raise RuntimeError('Jellyfin HTTP '+str(e.code)+' '+path.split('?')[0]) from None
admin=call('POST','/Users/AuthenticateByName',{'Username':'delladmin','Pw':values['admin']});at=admin['AccessToken']
folders=call('GET','/Library/VirtualFolders',token=at)
if not any(x.get('Name')=='Dell Acceptance' for x in folders):
 options={'EnableInternetProviders':False,'EnableRealtimeMonitor':False,'EnableLUFSScan':False,'EnableChapterImageExtraction':False,'EnableTrickplayImageExtraction':False,'AutomaticRefreshIntervalDays':0,'SaveLocalMetadata':False,'PathInfos':[{'Path':'/media/movies/DellAcceptance'}]}
 call('POST','/Library/VirtualFolders?'+urllib.parse.urlencode({'name':'Dell Acceptance','collectionType':'homevideos','refreshLibrary':'true'}),{'LibraryOptions':options},token=at)
viewer=call('POST','/Users/AuthenticateByName',{'Username':'dellviewer','Pw':values['viewer']},device='viewer');vt=viewer['AccessToken'];uid=viewer['User']['Id']
item=None
for _ in range(30):
 result=call('GET','/Items?'+urllib.parse.urlencode({'UserId':uid,'Recursive':'true','Fields':'MediaSources,Path'}),token=vt,device='viewer')
 choices=[x for x in result.get('Items',[]) if x.get('Path','').endswith('/'+fixture.name)]
 if choices:item=choices[0];break
 time.sleep(2)
assert item,'Synthetic fixture not indexed within bounded wait'
profile={'Name':'Dell synthetic H264 AAC MP4 client','MaxStreamingBitrate':20000000,'MaxStaticBitrate':20000000,'DirectPlayProfiles':[{'Container':'mp4,m4v','Type':'Video','VideoCodec':'h264','AudioCodec':'aac'}],'TranscodingProfiles':[],'CodecProfiles':[],'ContainerProfiles':[],'SubtitleProfiles':[]}
playback=call('POST','/Items/'+item['Id']+'/PlaybackInfo',{'UserId':uid,'DeviceProfile':profile,'EnableDirectPlay':True,'EnableDirectStream':True,'EnableTranscoding':False,'MaxStreamingBitrate':20000000},token=vt,device='viewer')
media=playback['MediaSources'][0];assert media.get('SupportsDirectPlay') is True,'Fixture is not DirectPlay-capable for declared client'
content=call('GET','/Videos/'+item['Id']+'/stream?'+urllib.parse.urlencode({'static':'true','MediaSourceId':media['Id']}),token=vt,device='viewer')
assert isinstance(content,bytes) and hashlib.sha256(content).hexdigest()==expected,'Original-byte static stream mismatch'
# Report an actual synthetic client session and inspect that no transcoding is associated with it.
session={'ItemId':item['Id'],'MediaSourceId':media['Id'],'PlaySessionId':playback.get('PlaySessionId'),'PlayMethod':'DirectPlay','PositionTicks':0,'CanSeek':True,'IsPaused':False,'IsMuted':False}
call('POST','/Sessions/Playing',session,token=vt,device='viewer')
sessions=call('GET','/Sessions',token=at)
matching=[x for x in sessions if x.get('DeviceId')=='dell-nas-fixture-viewer' and (x.get('NowPlayingItem') or {}).get('Id')==item['Id']]
assert matching and all(not x.get('TranscodingInfo') for x in matching),'Synthetic session unexpected transcoding or not observed'
call('POST','/Sessions/Playing/Stopped',{'ItemId':item['Id'],'MediaSourceId':media['Id'],'PlaySessionId':playback.get('PlaySessionId'),'PositionTicks':50000000},token=vt,device='viewer')
result={'status':'passed-synthetic-directplay-protocol','server_version':'12.4.0','fixture_name':fixture.name,'fixture_bytes':fixture.stat().st_size,'fixture_sha256':expected,'supports_direct_play':True,'original_stream_sha256_matches':True,'observed_session_without_transcoding':True,'admin_and_viewer_login_verified':True,'physical_TV_or_console_verified':False,'actual_movie_or_game_downloaded':False,'library_internet_providers':False,'hardware_transcoding_claimed':False}
p=Path('/root/private/dell-nas/acceptance/jellyfin-result.json');p.parent.mkdir(parents=True,exist_ok=True,mode=0o700);p.write_text(json.dumps(result,indent=2)+'\n');p.chmod(0o600)
print(json.dumps(result))
