#!/usr/bin/env python3
"""Fetch only approved Jackson 2.19.0 bytes from official Maven Central, without credentials."""
import hashlib,json,os,re,shutil,sys,urllib.request,zipfile,xml.etree.ElementTree as ET
from pathlib import Path
BASE=Path(__file__).resolve().parents[2];WORK=BASE/'private/java-build';REPO=WORK/'public-file-repo'
COORDS=[('com.fasterxml.jackson.module','jackson-module-blackbird'),('com.fasterxml.jackson.dataformat','jackson-dataformat-yaml'),('com.fasterxml.jackson.core','jackson-core'),('com.fasterxml.jackson.core','jackson-annotations'),('com.fasterxml.jackson.datatype','jackson-datatype-jsr310'),('com.fasterxml.jackson.core','jackson-databind')]
VERSION='2.19.0';ORIGIN='https://repo.maven.apache.org/maven2/'
class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,*args,**kwargs):return None
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect)
def fetch(url):
 assert url.startswith(ORIGIN) and '@' not in url and '?' not in url
 with opener.open(urllib.request.Request(url,method='GET',headers={'User-Agent':'DellOfflinePublicDependencyFetch/1'}),timeout=30) as response:
  assert response.status==200
  data=response.read(16*1024*1024+1)
  assert len(data)<=16*1024*1024
  return data

def main():
 manifest=WORK/'public-jackson-download.json'
 if manifest.exists():raise RuntimeError('Download manifest already exists; preserve existing evidence')
 records=[]
 for group,name in COORDS:
  for suffix in ['pom','jar']:
   filename=name+'-'+VERSION+'.'+suffix
   rel=group.replace('.','/')+'/'+name+'/'+VERSION+'/'+filename
   url=ORIGIN+rel;payload=fetch(url);checksum=fetch(url+'.sha1').decode().strip().split()[0].lower()
   assert re.fullmatch('[0-9a-f]{40}',checksum) and hashlib.sha1(payload).hexdigest()==checksum
   if suffix=='pom':ET.fromstring(payload)
   else:
    import io
    assert zipfile.is_zipfile(io.BytesIO(payload))
   target=REPO/rel;target.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
   if target.exists():assert target.read_bytes()==payload,'Existing public artifact differs'
   else:target.write_bytes(payload);target.chmod(0o400)
   sha=target.with_suffix(target.suffix+'.sha1')
   if not sha.exists():sha.write_text(checksum+'\n');sha.chmod(0o400)
   records.append({'coordinate':group+':'+name+':'+VERSION,'file':filename,'url':url,'checksum_url':url+'.sha1','sha1_verified':checksum,'sha256':hashlib.sha256(payload).hexdigest(),'bytes':len(payload),'authentication_supplied':False})
 # Make the approved file repository visible to buildscript plugin transitive dependencies.
 modified=[]
 for settings in (WORK/'repos').glob('*/settings.gradle.kts'):
  text=settings.read_text()
  if 'dellOfflineApprovedPublic' in text:continue
  for block in ['pluginManagement {','dependencyResolutionManagement {']:
   pos=text.index('repositories {',text.index(block))+len('repositories {')
   addition='\n        maven { name = "dellOfflineApprovedPublic"; url = uri('+json.dumps(REPO.as_uri())+'); content { includeGroupByRegex("com[.]fasterxml[.]jackson.*") } }\n'
   text=text[:pos]+addition+text[pos:]
  settings.write_text(text);modified.append(str(settings))
 result={'status':'downloaded-and-verified','source':'official Maven Central only','authentication_supplied':False,'gradle_network_policy_unchanged':'offline and external denied, loopback only','coordinates_version':VERSION,'files':records,'isolated_settings_modified':modified,'publish_executed':False,'source_repositories_modified':False}
 manifest.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');manifest.chmod(0o600)
 print(json.dumps({'status':result['status'],'files':len(records),'coordinates':len(COORDS),'authentication_supplied':False,'manifest':str(manifest)}))
if __name__=='__main__':
 try:main()
 except Exception as e:print(json.dumps({'status':'failed','error_category':type(e).__name__,'message':str(e)}));sys.exit(1)
