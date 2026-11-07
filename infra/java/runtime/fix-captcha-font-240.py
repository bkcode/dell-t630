#!/usr/bin/env python3
"""Approved VM240-only package repair and exactly one Auth restart."""
import os,socket,subprocess,json,re,datetime,time,urllib.request
from pathlib import Path
os.umask(0o077)
assert os.geteuid()==0 and socket.gethostname()=='java-test-01' and not Path('/etc/pve').exists()
assert '10.63.20.20'in {x.get('local') for row in json.loads(subprocess.check_output(['ip','-j','address'],text=True)) for x in row.get('addr_info',[]) if x.get('family')=='inet'}
assert Path('/opt/finger/current-test').resolve().name=='20261106T113449'
marker=Path('/root/dell-captcha-font-repair-20261106.json');assert not marker.exists(),'Prior repair marker retained; stop for manager review'
names=['finger-service-system','finger-service-coms','finger-auth','finger-bff-system','finger-gateway-mobile']
def states():
 result={}
 for name in names:
  out=subprocess.check_output(['systemctl','show','dell-finger-'+name+'.service','-p','MainPID','-p','ActiveState','-p','NRestarts'],text=True)
  result[name]=dict(l.split('=',1) for l in out.splitlines() if '='in l)
 return result
def now():return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat()
before=states();assert all(x['ActiveState']=='active' for x in before.values());assert before['finger-auth']['MainPID']=='4756','Auth changed since verified no-restart preflight'
jdk_before=subprocess.check_output(['dpkg-query','-W','-f=${Version}','openjdk-21-jdk-headless'],text=True)
apt=['apt-get','-o','APT::Get::AllowUnauthenticated=false','-o','Acquire::AllowInsecureRepositories=false']
p=subprocess.run(apt+['--simulate','install','--no-install-recommends','--no-upgrade','libharfbuzz0b'],capture_output=True,text=True,timeout=60);assert p.returncode==0
plan=[l for l in p.stdout.splitlines() if l.startswith(('Inst ','Remv '))]
assert not any(l.startswith('Remv ') or re.match(r'^Inst\s+\S+\s+\[[^]]+\]',l) or 'openjdk'in l.lower() for l in plan),'Unexpected upgrade/removal plan'
packages=[l.split()[1] for l in plan];assert set(packages)=={'libgraphite2-3','libharfbuzz0b'}
record={'started_at':now(),'stage':'approved-plan-before-install','before':before,'new_packages':packages,'auth_restart_completed':False,'secret_values_emitted':False};marker.write_text(json.dumps(record)+'\n');marker.chmod(0o600)
p=subprocess.run(apt+['install','--yes','--no-install-recommends','--no-upgrade','libharfbuzz0b'],env={**os.environ,'DEBIAN_FRONTEND':'noninteractive'},capture_output=True,text=True,timeout=300);assert p.returncode==0,'Package install failed; private output suppressed'
version=subprocess.check_output(['dpkg-query','-W','-f=${Version}','libharfbuzz0b'],text=True).strip();assert subprocess.check_output(['dpkg-query','-W','-f=${Version}','openjdk-21-jdk-headless'],text=True)==jdk_before
p=subprocess.run(['ldd','/opt/finger/java/lib/libfontmanager.so'],env={'PATH':'/usr/bin:/bin','LD_LIBRARY_PATH':'/opt/finger/java/lib/server:/opt/finger/java/lib'},capture_output=True,text=True,timeout=10);missing=[l.split()[0] for l in p.stdout.splitlines() if 'not found'in l];assert not missing
record.update(stage='package-installed-before-auth-restart',package_version=version,jdk_unchanged=True);marker.write_text(json.dumps(record)+'\n')
subprocess.run(['systemctl','restart','dell-finger-finger-auth.service'],check=True,capture_output=True,timeout=90);record['auth_restart_completed']=True;record['stage']='auth-restarted-waiting-health';marker.write_text(json.dumps(record)+'\n')
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}));deadline=time.monotonic()+120;healthy=False
while time.monotonic()<deadline:
 try:
  with opener.open('http://10.63.20.20:10000/actuator/health',timeout=3) as response:healthy=response.status==200 and json.loads(response.read(65536)).get('status')=='UP'
 except Exception:healthy=False
 if healthy:break
 time.sleep(2)
assert healthy,'Auth health deadline exceeded'
after=states();assert before['finger-auth']['MainPID']!=after['finger-auth']['MainPID']
assert all(before[n]['MainPID']==after[n]['MainPID'] and after[n]['ActiveState']=='active' for n in names if n!='finger-auth')
record.update(stage='completed',completed_at=now(),after=after,other_four_pids_unchanged=True,auth_health='UP',jdk_package_version=jdk_before.strip(),missing_font_libraries_after=missing,auth_restart_count_by_this_fix=1,coms_persistence_restart_used=False,scope='VM240 signed APT missing native dependency repair only');marker.write_text(json.dumps(record)+'\n');print(json.dumps(record))
