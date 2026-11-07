#!/usr/bin/env python3
"""Read-only assigned250 deployment/endpoint/process inventory. No credentials opened."""
import json,os,socket,subprocess,sys,time,hashlib
from pathlib import Path
if os.geteuid()!=0 or socket.gethostname().split('.')[0]!='penpot-service' or Path('/etc/pve').exists():raise SystemExit('VM250 only')
D=['docker','--host','unix:///var/run/docker.sock']
def run(args,timeout=30):return subprocess.run(args,capture_output=True,text=True,timeout=timeout)
def docker(*args):return run(D+list(args))
base=Path('/opt/dell/penpot');files=['application/fresh-target.py','target_guard.py','compose.fresh.yaml','compose.fresh.core.yaml','runtime_logging.py','runtime/logging/templates/nginx.conf.template','runtime/logging/templates/nginx-mcp-locations.conf.template']
result={'target':'VM250','read_only':True,'package_files':{},'Git':{},'containers':[],'PID_samples':[]}
for name in files:
 p=base/name;result['package_files'][name]={'exists':p.is_file(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None}
result['Git']={'HEAD':run(['git','-C',str(base/'source'),'rev-parse','HEAD']).stdout.strip(),'dirty':run(['git','-C',str(base/'source'),'status','--porcelain=v1']).stdout.strip()}
ids=docker('ps','-q').stdout.split()
for cid in ids:
 fmt='{"id":{{json .Id}},"name":{{json .Name}},"pid":{{json .State.Pid}},"image":{{json .Image}},"working_dir":{{json .Config.WorkingDir}},"health":{{if (index .State "Health")}}{{json .State.Health.Status}}{{else}}null{{end}}}'
 c=json.loads(docker('inspect','--format',fmt,cid).stdout);root=Path('/proc')/str(c['pid'])/'root'
 c['root_directories']=[p.name for p in root.iterdir() if p.is_dir() and p.name not in ('proc','sys','dev','run','root','home','var','tmp')]
 c['app_paths']={}
 for name in ['app','opt','usr/src/app']:
  p=root/name
  if p.is_dir():c['app_paths']['/'+name]=[x.name for x in p.iterdir()][:35]
 c['available_tools']={tool:any((root/p/tool).is_file() for p in ['bin','usr/bin','usr/local/bin','sbin','usr/sbin']) for tool in ['sh','curl','wget','node','python3','nginx','busybox','nslookup','dig']}
 result['containers'].append(c)
for _ in range(6):
 p=docker('stats','--no-stream','--format','{{json .}}');rows=[]
 for line in p.stdout.splitlines():
  x=json.loads(line);rows.append({'name':x['Name'],'pids':int(x['PIDs']) if x['PIDs'].isdigit() else None})
 result['PID_samples'].append(rows);time.sleep(2)
print(json.dumps(result))
