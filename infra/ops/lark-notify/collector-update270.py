#!/usr/bin/env python3
"""Reviewed270-only append of an active local unit, no URL/ACL expansion."""
import datetime,importlib.util,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
s=importlib.util.spec_from_file_location('control',ROOT/'scripts/control.py');c=importlib.util.module_from_spec(s);s.loader.exec_module(c)
CODE=r'''import copy,hashlib,importlib.util,json,os,socket,subprocess,tempfile,time,urllib.parse,urllib.request
from pathlib import Path
if os.geteuid()!=0 or Path('/etc/pve').exists() or socket.gethostname().split('.')[0]!='ops-service':raise SystemExit('ops270 only')
unit='dell-lark-notify.service'
subprocess.run(['systemctl','is-active','--quiet',unit],check=True)
config=Path('/etc/dell-guest-monitoring/health.json');collector=Path('/opt/dell/guest-monitoring/collect-guest-health.py')
for file in [config,collector]:
 if file.is_symlink() or file.stat().st_uid!=0 or file.stat().st_mode&0o022:raise SystemExit('trusted root collector paths required')
before=json.loads(config.read_text());after=copy.deepcopy(before)
if before.get('role')!='ops-service' or before.get('private_ip')!='10.63.30.40':raise SystemExit('fixed role/IP config required')
if unit not in after['services']:after['services'].append(unit)
s=importlib.util.spec_from_file_location('collector_check',collector);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);m.validate(after,m.local_addresses())
fd,path=tempfile.mkstemp(prefix='.notify-unit-',dir=config.parent)
try:
 with os.fdopen(fd,'w') as out:json.dump(after,out,indent=2);out.write('\n')
 os.chown(path,0,0);os.chmod(path,config.stat().st_mode&0o777);os.replace(path,config)
finally:Path(path).unlink(missing_ok=True)
other_before={k:v for k,v in before.items() if k!='services'};other_after={k:v for k,v in json.loads(config.read_text()).items() if k!='services'}
if other_before!=other_after:raise SystemExit('unexpected other config/URL change')
r=subprocess.run(['runuser','--user','prometheus','--','/usr/bin/python3',str(collector),'--check'],capture_output=True,timeout=50)
if r.returncode:raise SystemExit('unprivileged collector check failed; raw output withheld')
started=time.time();subprocess.run(['systemctl','start','dell-guest-health.service'],capture_output=True,check=True,timeout=60)
text=Path('/var/lib/prometheus/node-exporter-textfile/dell_guest_health.prom').read_text();tag='role="ops-service",service="dell-lark-notify.service"';metric='dell_guest_service_active{'+tag+'} 1';present='dell_guest_service_present{'+tag+'} 1'
if metric not in text or present not in text:raise SystemExit('textfile native unit metric not active/present')
op=urllib.request.build_opener(urllib.request.ProxyHandler({}));end=time.monotonic()+40;seen=False
query=urllib.parse.urlencode({'query':'dell_guest_service_active{role="ops-service",service="dell-lark-notify.service"}'})
while time.monotonic()<end:
 with op.open('http://10.63.30.40:9090/api/v1/query?'+query,timeout=5) as response:values=json.loads(response.read(65536))['data']['result']
 if len(values)==1 and values[0]['value'][1]=='1':seen=True;break
 time.sleep(1)
if not seen:raise SystemExit('new service metric not observed by Prometheus')
print(json.dumps({'status':'ops270-native-notifier-monitored','services_before':before['services'],'services_after':after['services'],'URLs_and_all_other_fields_unchanged':True,'unprivileged_check':'passed','sampled_once':True,'textfile_present_active':True,'Prometheus_service_active':1,'notifications_sent_by_this_action':False}))'''
def main():
 target=next(r['target'] for r in json.loads((ROOT/'evidence/implementation/private-guest-access.json').read_text())['roles'] if r['target']['vmid']==270);r=c.guest(270,'sudo -n python3 -',data=CODE.encode(),timeout=150,info=target)
 if r['exit_code']:raise RuntimeError('fixed collector addition failed; raw output withheld')
 result={'at':datetime.datetime.now().astimezone().isoformat(),'target':'ops270','result':json.loads(r['stdout'])};(ROOT/'evidence/implementation/lark-notify-collector270.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
