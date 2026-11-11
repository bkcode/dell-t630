#!/usr/bin/env python3
"""Bounded metadata-only observer. Never mutates Penpot, Docker or credentials."""
import datetime,json,os,socket,subprocess,time
from pathlib import Path
from zoneinfo import ZoneInfo
assert os.geteuid()==0 and socket.gethostname()=='penpot-service'and not Path('/etc/pve').exists()
os.umask(0o077);ROOT=Path('/root/dell-penpot-hourly-observe-20261111');ROOT.mkdir(mode=0o700,exist_ok=True);ROOT.chmod(0o700);OUT=ROOT/'events.jsonl';STATE=Path('/run/dell-penpot-supervision-state.json')
fd=os.open(OUT,os.O_WRONLY|os.O_CREAT|os.O_APPEND|os.O_NOFOLLOW,0o600)
last=None;last_frame=None;deadline=time.monotonic()+4500;saw_failure=False;recovered=False

def emit(event):
 event['at']=datetime.datetime.now(ZoneInfo('Asia/Shanghai')).isoformat();os.write(fd,(json.dumps(event)+'\n').encode());os.fsync(fd)

def frame():
 ids=subprocess.check_output(['docker','ps','-aq','--filter','label=com.docker.compose.project=penpot'],timeout=10).decode().split()
 fmt='{"name":{{json .Name}},"running":{{json .State.Running}},"OOM":{{json .State.OOMKilled}},"exit":{{json .State.ExitCode}},"health":{{if .State.Health}}{{json .State.Health.Status}}{{else}}null{{end}},"failing_streak":{{if .State.Health}}{{json .State.Health.FailingStreak}}{{else}}0{{end}}}'
 if not ids:return[]
 p=subprocess.run(['docker','inspect','--format',fmt,*ids],capture_output=True,text=True,timeout=15);assert p.returncode==0
 return sorted([json.loads(line)for line in p.stdout.splitlines()],key=lambda x:x['name'])

emit({'event':'observer-started','workload_mutations':False});next_frame=0
try:
 while time.monotonic()<deadline:
  try:
   raw=json.loads(STATE.read_text());safe={k:v for k,v in raw.items()if k in ['phase','time_utc','ready','consecutive_bad','error_category','reason','group_stopped']};signature={k:v for k,v in safe.items()if k!='time_utc'}
   if signature!=last:
    emit({'event':'supervisor-state-change','state':safe});last=signature
    if raw.get('phase')in['failed','failed-stopped']:saw_failure=True
    if saw_failure and raw.get('phase')=='ready':recovered=True
   if time.monotonic()>=next_frame or raw.get('phase')not in['ready']:
    current=frame()
    if current!=last_frame:emit({'event':'container-health-change','containers':current});last_frame=current
    next_frame=time.monotonic()+5
   if recovered:
    emit({'event':'failure-and-recovery-captured'});break
  except Exception as e:emit({'event':'observer-read-error','category':type(e).__name__})
  time.sleep(1)
 result={'finished_at':datetime.datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),'captured_failure':saw_failure,'captured_recovery':recovered,'expired_without_failure':not saw_failure,'Penpot_or_Docker_mutations':False};p=ROOT/'result.json';p.write_text(json.dumps(result));p.chmod(0o600)
finally:os.close(fd)
