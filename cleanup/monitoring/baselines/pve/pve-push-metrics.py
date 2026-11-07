#!/usr/bin/env python3
"""PVE metadata/RAID read-only collection; push via existing QGA, no host listener/key."""
import json,subprocess,time,os,datetime
from pathlib import Path
assert Path('/etc/pve').exists() and os.geteuid()==0

def run(a,timeout=20):
 p=subprocess.run(a,capture_output=True,text=True,timeout=timeout)
 if p.returncode:raise RuntimeError('Metadata collector command failed: '+a[0])
 return p.stdout

def label(value):return json.dumps(str(value),ensure_ascii=True)
lines=['# Dell PVE metadata via existing QGA; contains no credentials or user content']
def metric(name,value,**labels):
 suffix='{'+','.join(k+'='+label(v) for k,v in sorted(labels.items()))+'}' if labels else ''
 lines.append(name+suffix+' '+str(float(value)))
metric('dell_pve_collector_timestamp_seconds',time.time())
mem={x.split(':',1)[0]:int(x.split()[1])*1024 for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith(('MemTotal:','MemAvailable:'))}
for k,v in mem.items():metric('dell_pve_'+('memory_total_bytes' if k=='MemTotal' else 'memory_available_bytes'),v)
metric('dell_pve_cpu_logical_count',os.cpu_count());metric('dell_pve_load1',os.getloadavg()[0])
for r in json.loads(run(['pvesh','get','/cluster/resources','--type','vm','--output-format','json'])):
 args={'vmid':r['vmid'],'role':r.get('name','unknown')};metric('dell_pve_guest_running',r.get('status')=='running',**args)
 metric('dell_pve_guest_memory_bytes',r.get('mem',0),**args);metric('dell_pve_guest_memory_limit_bytes',r.get('maxmem',0),**args)
for r in json.loads(run(['pvesh','get','/nodes/pve/storage','--output-format','json'])):
 for key in ['total','avail','used']:
  if key in r:metric('dell_pve_storage_'+key+'_bytes',r[key],storage=r['storage'])
program='/root/dell-bootstrap/perccli-extracted/opt/MegaRAID/perccli/perccli64'
controller=json.loads(run([program,'/c0','show','J']))['Controllers'][0]['Response Data']
for r in controller.get('VD LIST',[]):metric('dell_pve_raid_virtual_optimal',r['State']=='Optl',array=r['DG/VD'],raid=r['TYPE'])
for r in controller.get('PD LIST',[]):metric('dell_pve_raid_member_online',r['State']=='Onln',slot=r['EID:Slt'])
for r in controller.get('BBU_Info',[]):metric('dell_pve_bbu_optimal',r.get('State')=='Optimal')
p=subprocess.run(['pct','exec','100','--','systemctl','is-active','cloudflared'],capture_output=True,text=True,timeout=10);metric('dell_cf_cloudflared_active',p.returncode==0 and p.stdout.strip()=='active')
text='\n'.join(lines)+'\n'
writer='''import os,sys,socket,uuid
from pathlib import Path
assert socket.gethostname()=='ops-service' and not Path('/etc/pve').exists()
p=Path('/var/lib/prometheus/node-exporter-textfile');assert p.resolve()==p
fd=os.open(p,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
name='.dell-pve-'+uuid.uuid4().hex+'.tmp'
try:
 out=os.open(name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o644,dir_fd=fd)
 with os.fdopen(out,'wb') as f:f.write(sys.stdin.buffer.read());f.flush();os.fsync(f.fileno())
 os.replace(name,'dell-pve.prom',src_dir_fd=fd,dst_dir_fd=fd)
finally:os.close(fd)
'''
p=subprocess.run(['qm','guest','exec','270','--pass-stdin','1','--','python3','-c',writer],input=text,capture_output=True,text=True,timeout=30)
if p.returncode:raise RuntimeError('QGA metric delivery failed')
value=json.loads(p.stdout)
if value.get('exitcode')!=0:raise RuntimeError('Guest metric file write failed')
print(json.dumps({'at':datetime.datetime.now().isoformat(),'metric_lines':len(lines),'delivery':'existing-QGA-to-Ops-textfile','host_listener_created':False,'credentials_read':False}))
