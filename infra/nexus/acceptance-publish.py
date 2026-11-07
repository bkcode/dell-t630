#!/usr/bin/env python3
"""Synthetic Maven publication/read/deny check using owned target only, credentials via stdin."""
import sys,json,urllib.request,urllib.error,base64,hashlib,io,zipfile,datetime,socket
from pathlib import Path
assert socket.gethostname()=='publish-service' and not Path('/etc/pve').exists()
m=json.load(sys.stdin);assert set(m)=={'publisher-password','reader-password'}
base='http://10.63.30.20:8081/repository/dell-acceptance/';version=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d%H%M%S')
root='com/dell/acceptance/repo-persistence/'+version+'/repo-persistence-'+version
buf=io.BytesIO()
with zipfile.ZipFile(buf,'w') as z:z.writestr('META-INF/MANIFEST.MF','Manifest-Version: 1.0\n');z.writestr('fixture.txt','dell synthetic repository persistence '+version+'\n')
jar=buf.getvalue();pom=('<project><modelVersion>4.0.0</modelVersion><groupId>com.dell.acceptance</groupId><artifactId>repo-persistence</artifactId><version>'+version+'</version></project>').encode()
class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,*a,**k):return None
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect)
def request(method,path,user=None,body=None):
 headers={}
 if user:headers['Authorization']='Basic '+base64.b64encode((user+':'+m['publisher-password' if user=='dell-publisher' else 'reader-password']).encode()).decode()
 if body is not None:headers['Content-Type']='application/octet-stream'
 try:
  with opener.open(urllib.request.Request(base+path,data=body,method=method,headers=headers),timeout=20) as r:return r.status,r.read(1024*1024)
 except urllib.error.HTTPError as e:return e.code,e.read(4096)
for ext,data in [('.pom',pom),('.jar',jar)]:
 status,_=request('PUT',root+ext,'dell-publisher',data);assert status in (200,201,204),'Publisher write failed '+str(status)
 status,actual=request('GET',root+ext,'dell-reader');assert status==200 and actual==data,'Reader bytes mismatch'
status,_=request('GET',root+'.jar');assert status in (401,403),'Anonymous read not denied'
read_deny,_=request('PUT',root+'-forbidden.jar','dell-reader',jar);assert read_deny==403,'Reader write not denied'
delete_deny,_=request('DELETE',root+'.jar','dell-publisher');assert delete_deny==403,'Publisher delete not denied'
r={'status':'synthetic-publication-read-and-privileges-verified','coordinate':'com.dell.acceptance:repo-persistence:'+version,'jar_path':root+'.jar','jar_sha256':hashlib.sha256(jar).hexdigest(),'jar_bytes':len(jar),'anonymous_read_denied':True,'reader_write_status':read_deny,'publisher_delete_status':delete_deny,'external_upstream_used':False,'source_repository_written':False,'fixture_retained_for_restart_verification':True}
p=Path('/srv/dell-build/nexus-acceptance.json');p.write_text(json.dumps(r,indent=2)+'\n');p.chmod(0o600);print(json.dumps(r))
