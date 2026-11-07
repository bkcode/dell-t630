"""One explicitly authorized guest at a time; strict fresh SSH verification after install."""
import argparse,datetime,json,shlex,sys
from pathlib import Path
sys.dont_write_bytecode=True
H=Path(__file__).resolve().parent;R=H.parents[1];sys.path.insert(0,str(R/'scripts'));import control
p=argparse.ArgumentParser();p.add_argument('--vmid',type=int,required=True,choices=[190,200,201,210,220,221,230,240,260]);a=p.parse_args()
if a.vmid==190:info=json.loads((R/'network19/evidence/gateway-initial-access.json').read_text())['target']
else:info=json.loads((R/'network19/evidence/migrated-access.json').read_text())['targets'][str(a.vmid)]
source=(H/'install-guest.py').read_text();command=shlex.join(['sudo','-n','python3','-I','-B','-c',source,'--vmid',str(a.vmid),'--apply'])
r=control.guest(a.vmid,command,timeout=900,info=info)
try:x=json.loads(r['stdout'])
except Exception:raise SystemExit('install did not return sanitized receipt; inspect role without blind retry')
e={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'exit_code':r['exit_code'],'result':x}
if r['exit_code']==0:
 q=control.guest(a.vmid,"python3 -B -c 'import json,pwd; print(json.dumps({\"user\":\"ub\",\"shell\":pwd.getpwnam(\"ub\").pw_shell}))'",timeout=25,info=info)
 e['new_strict_SSH_connection_verified']=q['exit_code']==0 and json.loads(q['stdout']).get('shell')==x['before_shells']['ub']
folder=H/'evidence';folder.mkdir(exist_ok=True);path=folder/('guest'+str(a.vmid)+'.json')
if path.exists():path.with_name(path.stem+'-previous-'+datetime.datetime.now().strftime('%H%M%S%f')+'.json').write_bytes(path.read_bytes())
path.write_text(json.dumps(e,indent=2)+'\n');print(json.dumps({k:v for k,v in x.items() if k not in ['core_before','core_after']}));print(json.dumps({'vmid':a.vmid,'strict_new_SSH':e.get('new_strict_SSH_connection_verified'),'exit_code':r['exit_code']}));raise SystemExit(r['exit_code'])
