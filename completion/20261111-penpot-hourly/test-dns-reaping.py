#!/usr/bin/env python3
"""Isolated local Docker A/B: original DNS health with/without init, no production data/network."""
import datetime,json,os,shutil,subprocess,tempfile,time,uuid
from pathlib import Path
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).with_name('dns-reaping-ab.json')
def run(args,check=True,timeout=25):
 p=subprocess.run(args,capture_output=True,text=True,timeout=timeout)
 if check and p.returncode:raise RuntimeError('fixed-isolated-command-failed:'+args[0])
 return p
image=json.loads(run(['docker','image','inspect','adguard/dnsproxy:v0.86.0']).stdout)[0];identity=image['Id'];scratch=Path(tempfile.mkdtemp(prefix='dns-reaper-ab-'));scratch.chmod(0o755)
(scratch/'hosts').write_text('192.0.2.53 dell-penpot-health.invalid\n');(scratch/'health.sh').write_bytes((ROOT/'infra/penpot/runtime/health-supervision/dns-health.sh').read_bytes());(scratch/'hosts').chmod(0o644);(scratch/'health.sh').chmod(0o644)
created=[];results=[]

def snapshot(name):
 p=run(['docker','exec',name,'/bin/busybox','ps','-o','pid,ppid,stat,comm']);rows=[]
 for line in p.stdout.splitlines()[1:]:
  f=line.split()
  if len(f)>=4:rows.append({'pid':int(f[0]),'parent':int(f[1]),'state':f[2],'name':f[3]})
 # Only numeric process metadata, never command arguments or credentials.
 return {'zombies':sum(x['state'].startswith('Z')for x in rows),'process_rows':len(rows)}
try:
 for enabled,count in [(False,12),(True,140)]:
  name='dell-dns-reap-'+('init-'if enabled else'noinit-')+uuid.uuid4().hex[:8]
  args=['docker','run','-d','--name',name,'--network','none','--read-only','--user','65532:65532','--pids-limit','32','--memory','64m','--cpus','0.25','--cap-drop','ALL','--cap-add','NET_BIND_SERVICE','--security-opt','no-new-privileges','--restart','no','--mount','type=bind,src='+str(scratch/'hosts')+',dst=/run/dell-health/hosts,readonly','--mount','type=bind,src='+str(scratch/'health.sh')+',dst=/run/dell-health/health.sh,readonly']
  if enabled:args+=['--init']
  args += [identity,'--listen=0.0.0.0','--port=53','--upstream=127.0.0.2:5353','--cache','--cache-max-ttl=300','--timeout=8s','--hosts-file-enabled','--hosts-files=/run/dell-health/hosts'];run(args);created.append(name)
  for _ in range(20):
   p=run(['docker','exec',name,'/bin/sh','/run/dell-health/health.sh'],check=False,timeout=10)
   if p.returncode==0:break
   time.sleep(.2)
  else:raise RuntimeError('isolated-DNS-startup-failed')
  time.sleep(1.2);before=snapshot(name);passed=0
  for _ in range(count):
   p=run(['docker','exec',name,'/bin/sh','/run/dell-health/health.sh'],check=False,timeout=10);assert p.returncode==0,'original-health-helper-failed';passed+=1;time.sleep(1.1)
  time.sleep(1.2);after=snapshot(name)
  if enabled:assert after['zombies']==0 and before['zombies']==0
  else:assert after['zombies']>=before['zombies']+count-1
  wrong=run(['docker','exec',name,'/bin/busybox','timeout','4','/bin/busybox','nslookup','-type=A','unconfigured-dell-health.invalid','127.0.0.1'],check=False,timeout=8);assert '192.0.2.53'not in wrong.stdout and wrong.returncode!=0
  details=json.loads(run(['docker','inspect',name]).stdout)[0];assert details['HostConfig']['NetworkMode']=='none'and not details['NetworkSettings'].get('Ports')and details['HostConfig']['ReadonlyRootfs']and details['HostConfig']['PidsLimit']==32
  results.append({'init_enabled':enabled,'completed_original_probe_runs':passed,'before':before,'after':after,'wrong_name_rejected':True,'network_none':True,'ports_published':False,'readonly':True,'UID':'65532:65532','pids_limit':32})
  run(['docker','rm','-f',name]);created.remove(name)
finally:
 for name in created:run(['docker','rm','-f',name],check=False)
 shutil.rmtree(scratch)
value={'at':datetime.datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),'status':'same-image-original-probe-zombie-leak-reproduced-and-init-reaping-verified','local_image_ID':identity,'local_architecture':image['Architecture'],'version':'v0.86.0','cases':results,'local_or_server_production_containers_touched':False,'public_upstream_or_data_volume_used':False,'temporary_containers_and_directory_removed':True};OUT.write_text(json.dumps(value,indent=2)+'\n');print(json.dumps(value))
