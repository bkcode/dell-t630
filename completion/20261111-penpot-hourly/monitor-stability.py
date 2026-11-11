#!/usr/bin/env python3
"""Bounded post-fix metadata stability observer. Never mutates workloads or credentials."""
import datetime,json,os,socket,subprocess,time
from pathlib import Path
from zoneinfo import ZoneInfo
assert os.geteuid()==0 and socket.gethostname()=='penpot-service';os.umask(0o077)
ROOT=Path('/root/dell-penpot-dns-init-fix-20261111');OUT=ROOT/'stability.json';start=time.monotonic();samples=[]
def cmd(args):return subprocess.check_output(args,stderr=subprocess.PIPE,timeout=20).decode().strip()
initial=json.loads(cmd(['docker','inspect','penpot-penpot-dns-1']))[0];assert initial['HostConfig'].get('Init')is True
baseline=cmd(['systemctl','show','dell-penpot.service','-p','NRestarts','--value']);failed=None

def put(status):
 value={'status':status,'started_at':started_at,'elapsed_seconds':round(time.monotonic()-start,2),'required_seconds':4200,'baseline_NRestarts':baseline,'sample_count':len(samples),'samples':samples,'failure':failed,'application_or_data_mutations':False};p=OUT.with_suffix('.tmp');p.write_text(json.dumps(value,indent=2)+'\n');p.chmod(0o600);os.replace(p,OUT)
started_at=datetime.datetime.now(ZoneInfo('Asia/Shanghai')).isoformat();put('observing')
while time.monotonic()-start<4200:
 try:
  ids=cmd(['docker','ps','-aq','--filter','label=com.docker.compose.project=penpot']).split();rows=json.loads(cmd(['docker','inspect',*ids]))
  assert len(rows)==11 and all(r['State']['Running']and r['State'].get('Health',{}).get('Status')=='healthy'for r in rows)
  dns=next(r for r in rows if r['Name']=='/penpot-penpot-dns-1');assert dns['Id']==initial['Id']and dns['HostConfig'].get('Init')is True and dns['HostConfig']['PidsLimit']==128
  assert cmd(['systemctl','is-active','dell-penpot.service'])=='active'and cmd(['systemctl','show','dell-penpot.service','-p','NRestarts','--value'])==baseline
  pid=dns['State']['Pid'];parents={pid};proc=[]
  for line in cmd(['ps','-eo','pid,ppid,stat,comm']).splitlines()[1:]:
   f=line.split()
   if len(f)>=4:proc.append((int(f[0]),int(f[1]),f[2]))
  parents.update(r[0]for r in proc if r[1]==pid);zombies=sum(r[1]in parents and r[2].startswith('Z')for r in proc);assert zombies==0
  cg=Path('/sys/fs/cgroup')/Path('/proc/'+str(pid)+'/cgroup').read_text().strip().split(':',2)[-1].lstrip('/');samples.append({'at':datetime.datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),'all_eleven_healthy':True,'DNS_zombies':0,'DNS_pids':int((cg/'pids.current').read_text()),'NRestarts':baseline});put('observing')
 except Exception as e:failed={'category':type(e).__name__,'at':datetime.datetime.now(ZoneInfo('Asia/Shanghai')).isoformat()};put('failed-read-only-observation');raise
 time.sleep(min(30,max(0,4200-(time.monotonic()-start))))
put('seventy-minute-native-stability-passed')
