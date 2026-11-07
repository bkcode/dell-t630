#!/usr/bin/env python3
"""220/221 exact configuration paths only; URL fields exported, credential/key content never output."""
import concurrent.futures,json,sys
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts'));import control
control.BASE+=['-o','ForwardAgent=no'];targets=json.loads((ROOT/'network19/evidence/migrated-access.json').read_text())['targets']
SCRIPT=r'''
import datetime,json,os,re,socket,urllib.parse
from pathlib import Path
import xml.etree.ElementTree as ET
ROLE=ROLE_ID
assert os.geteuid()==0 and socket.gethostname().split('.')[0]=={220:'publish-service',221:'artifact-service'}[ROLE] and not Path('/etc/pve').exists()
paths=['/etc/maven/settings.xml','/etc/gradle/gradle.properties','/etc/profile.d/dell-tools.sh','/root/.gradle/gradle.properties','/root/.m2/settings.xml','/root/.npmrc','/home/ub/.gradle/gradle.properties','/home/ub/.m2/settings.xml','/home/ub/.npmrc','/var/lib/dell-publisher/.gradle/gradle.properties','/var/lib/dell-publisher/.m2/settings.xml','/var/lib/dell-publisher/.npmrc','/srv/dell-build/gradle/gradle.properties','/srv/dell-build/maven/settings.xml','/etc/dell-publisher/client-test240.json'] if ROLE==220 else ['/etc/nexus.env','/opt/dell/nexus/assignment.json','/opt/dell/nexus/fresh-instance.json','/etc/dell-guest-monitoring/health.json']
result=[]
def url(value):
 try:u=urllib.parse.urlsplit(value.strip())
 except ValueError:return None
 if u.scheme not in ['http','https'] or not u.hostname:return None
 if u.username or u.password or u.query:return '[URL-present-private-parts-withheld]'
 return urllib.parse.urlunsplit((u.scheme,u.netloc,u.path,'',''))
for name in paths:
 p=Path(name)
 if not p.exists():result.append({'path':name,'exists':False});continue
 if p.is_symlink() or not p.is_file() or p.stat().st_size>262144:result.append({'path':name,'exists':True,'read':'rejected-symlink/type/size'});continue
 raw=p.read_text();selected=[]
 if p.suffix=='.xml':
  root=ET.fromstring(raw)
  for element in root.iter():
   if element.tag.split('}')[-1]=='url' and element.text:
    value=url(element.text)
    if value:selected.append({'selector':'xml:URL','value':value})
 elif p.name=='client-test240.json':
  value=json.loads(raw);selected=[{'selector':k,'value':value[k]} for k in ['source_ip','target_host','target_user','host_key_alias'] if k in value]
 elif p.name=='health.json':
  value=json.loads(raw)
  selected=[{'selector':'http_checks.'+str(x.get('name'))+'.url','value':url(x['url'])} for x in value.get('http_checks',[]) if isinstance(x,dict) and x.get('url')]
 elif p.name in ['assignment.json','fresh-instance.json']:
  value=json.loads(raw);selected=[{'selector':k,'value':value[k]} for k in ['role','expected_guest_ip','expected_hostname'] if k in value]
 else:
  for i,line in enumerate(raw.splitlines(),1):
   if not line.strip() or line.lstrip().startswith('#'):continue
   m=re.match(r'\s*([A-Za-z_][A-Za-z0-9_.-]*)\s*=\s*(.*?)\s*$',line)
   if m and not re.search('password|passwd|token|secret|auth',m[1],re.I):
    value=url(m[2].strip("'\""))
    if value:selected.append({'selector':m[1],'line':i,'value':value})
 result.append({'path':name,'exists':True,'selected_nonsecret_fields':selected,'contains19_31_literal': '192.168.19.31'in raw})
print(json.dumps({'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'vmid':ROLE,'readonly':True,'whitelist_configuration_locations':result,'key_or_credentials_values_exported':False,'no_recursive_home_or_publisher_backup':True}))
'''
def run(role):
 r=control.guest(role,'sudo python3 -',data=SCRIPT.replace('ROLE_ID',str(role)).encode(),timeout=90,info=targets[str(role)])
 if r['exit_code']:return {'vmid':role,'status':'URL-inventory-unconfirmed'}
 return json.loads(r['stdout'])
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:values=list(pool.map(run,[220,221]))
Path(__file__).with_name('consumer-url-locations.json').write_text(json.dumps(values,indent=2)+'\n')
for v in values:print(json.dumps({'vmid':v['vmid'],'locations_with19_31':[x['path'] for x in v.get('whitelist_configuration_locations',[]) if x.get('contains19_31_literal')],'credential_values_exported':False}))
