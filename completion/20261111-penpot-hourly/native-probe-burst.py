#!/usr/bin/env python3
"""Exercise original fixed local DNS health >hourly probe-count budget; no foreign query/data writes."""
import datetime,json,os,subprocess,time
from pathlib import Path
from zoneinfo import ZoneInfo
assert os.geteuid()==0 and __import__('socket').gethostname()=='penpot-service'
name='penpot-penpot-dns-1';initial=json.loads(subprocess.check_output(['docker','inspect',name]))[0];assert initial['HostConfig'].get('Init')is True and initial['HostConfig']['PidsLimit']==128
unit=subprocess.check_output(['systemctl','show','dell-penpot.service','-p','NRestarts','--value']).decode().strip()
def snapshot():
 v=json.loads(subprocess.check_output(['docker','inspect',name]))[0];assert v['Id']==initial['Id']and v['State']['Running'];pid=v['State']['Pid'];parents={pid};rows=[]
 for line in subprocess.check_output(['ps','-eo','pid,ppid,stat,comm']).decode().splitlines()[1:]:
  f=line.split()
  if len(f)>=4:rows.append((int(f[0]),int(f[1]),f[2],f[3]))
 for r in rows:
  if r[1]==pid:parents.add(r[0])
 cg=Path('/sys/fs/cgroup')/Path('/proc/'+str(pid)+'/cgroup').read_text().strip().split(':',2)[-1].lstrip('/')
 return {'zombie_children':sum(r[1]in parents and r[2].startswith('Z')for r in rows),'PID_count':int((cg/'pids.current').read_text()),'PID_max':int((cg/'pids.max').read_text()),'PID_events':(cg/'pids.events').read_text().strip(),'health':v['State']['Health']['Status']}
before=snapshot();assert before['zombie_children']==0;passed=0;checkpoints=[];started=time.monotonic()
for i in range(140):
 p=subprocess.run(['docker','exec',name,'/bin/busybox','sh','/opt/dell-health/dns-health.sh'],capture_output=True,timeout=10);assert p.returncode==0,'original-DNS-probe-failed';passed+=1;time.sleep(1.1)
 if(i+1)%20==0:
  current=snapshot();assert current['zombie_children']==0 and current['PID_max']==128;checkpoints.append({'probe_runs':i+1,**current})
time.sleep(1.2);after=snapshot();assert after['zombie_children']==0 and after['health']=='healthy';assert subprocess.check_output(['systemctl','show','dell-penpot.service','-p','NRestarts','--value']).decode().strip()==unit
value={'at':datetime.datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),'status':'native-original-DNS-health-140-runs-zero-zombie-growth','original_health_runs_passed':passed,'elapsed_seconds':round(time.monotonic()-started,2),'before':before,'after':after,'checkpoints':checkpoints,'NRestarts_unchanged':True,'NRestarts_baseline':unit,'health_interval_or_threshold_or_PIDlimit_changed':False,'DNS_image_ID':initial['Image'],'architecture':'amd64','public_upstream_or_design_data_requested':False,'full_seventy_minute_observation_claimed':False}
p=Path('/root/dell-penpot-dns-init-fix-20261111/native-burst.json');p.write_text(json.dumps(value,indent=2)+'\n');p.chmod(0o600);print(json.dumps(value))
