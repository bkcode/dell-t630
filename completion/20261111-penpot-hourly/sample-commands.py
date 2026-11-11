#!/usr/bin/env python3
"""Bounded procfs command-category sampler; never records argv values or environments."""
import collections,datetime,json,os,socket,time
from pathlib import Path
from zoneinfo import ZoneInfo
assert os.geteuid()==0 and socket.gethostname()=='penpot-service'
ROOT=Path('/root/dell-penpot-hourly-observe-20261111');os.umask(0o077);OUT=ROOT/'command-categories.jsonl';fd=os.open(OUT,os.O_WRONLY|os.O_CREAT|os.O_APPEND|os.O_NOFOLLOW,0o600);end=time.monotonic()+1500;seen={};history=collections.deque(maxlen=100);last_phase=None

def emit(v):v['at']=datetime.datetime.now(ZoneInfo('Asia/Shanghai')).isoformat();os.write(fd,(json.dumps(v)+'\n').encode())

def category(pid):
 raw=Path('/proc/'+pid+'/cmdline').read_bytes().split(b'\0');args=[x.decode(errors='replace')for x in raw if x];prog=Path(args[0]).name if args else''
 if prog=='docker':
  words=[x for x in args[1:]if x in ['compose','info','inspect','image','ps','stop','config','up','--services','--images']]
  return 'docker:'+','.join(words)
 if prog=='git':return 'git:status'if'status'in args else'git:rev-parse'if'rev-parse'in args else'git:other'
 if prog=='findmnt':return 'findmnt'
 return None
try:
 emit({'event':'category-sampler-started','argv_or_environment_values_recorded':False})
 while time.monotonic()<end:
  try:pids=Path('/sys/fs/cgroup/system.slice/dell-penpot.service/cgroup.procs').read_text().split()
  except OSError:pids=[]
  now=time.monotonic();current={}
  for pid in pids:
   try:kind=category(pid)
   except OSError:continue
   if kind:
    since=seen.get(pid,{}).get('since',now);current[pid]={'category':kind,'since':since}
    if pid not in seen:history.append({'category':kind,'at':datetime.datetime.now(ZoneInfo('Asia/Shanghai')).isoformat()})
  for pid,old in seen.items():
   if pid not in current and now-old['since']>=1:emit({'event':'long-command-finished','category':old['category'],'observed_seconds':round(now-old['since'],2)})
  seen=current
  try:state=json.loads(Path('/run/dell-penpot-supervision-state.json').read_text());phase=state.get('phase')
  except(OSError,ValueError):phase=None
  if phase!=last_phase:
   emit({'event':'phase-seen','phase':phase,'active_command_categories':[v['category']for v in seen.values()],'last_command_categories':list(history)[-35:]if phase in['failed','failed-stopped']else[]});last_phase=phase
  if phase in['failed','failed-stopped']:
   emit({'event':'failure-captured-with-command-history','last_command_categories':list(history),'active_command_categories':[v['category']for v in seen.values()]});break
  time.sleep(.1)
finally:os.close(fd)
