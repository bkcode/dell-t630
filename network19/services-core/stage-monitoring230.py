#!/usr/bin/env python3
"""Explicit230 standby stage only; no OS/PVE/service changes or apply flag."""
import base64,datetime,hashlib,json,shlex,sys
from pathlib import Path
sys.dont_write_bytecode=True
H=Path(__file__).resolve().parent;R=H.parents[1];sys.path.insert(0,str(R/'scripts'));import control
base=H/'prepared/monitoring/vm230';files={str(p.relative_to(base)):base64.b64encode(p.read_bytes()).decode() for p in base.rglob('*') if p.is_file()};files['apply-monitoring.py']=base64.b64encode((H/'apply-monitoring.py').read_bytes()).decode();files['230.json']=base64.b64encode((R/'network19/contracts/230.json').read_bytes()).decode()
P=r'''import base64,json,os,socket,stat,subprocess,sys
from pathlib import Path
if os.geteuid()!=0 or socket.gethostname().split('.')[0]!='java-prod-01' or Path('/etc/pve').exists():raise SystemExit('standby230 only')
values=json.loads(sys.stdin.read());root=Path('/root/dell-network19/staged/core-monitoring230')
# Deliberately disjoint from OS network transaction/installed OS helper.
for path in [Path('/root/dell-network19'),Path('/root/dell-network19/staged')]:
 if path.resolve(strict=False)!=path:raise SystemExit('stage parent symlink')
 path.mkdir(mode=0o700,exist_ok=True)
 if path.stat().st_uid!=0 or path.stat().st_mode&0o022:raise SystemExit('stage parent untrusted')
root.mkdir(mode=0o700,exist_ok=False)
for rel,encoded in values.items():
 if rel.startswith('/') or '..' in Path(rel).parts:raise SystemExit('unsafe stage member')
 target=root/rel;target.parent.mkdir(mode=0o700,parents=True,exist_ok=True);data=base64.b64decode(encoded);fd=os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
 with os.fdopen(fd,'wb') as f:f.write(data)
p=subprocess.run(['python3','-I','-B',str(root/'apply-monitoring.py'),'--bundle',str(root),'--os-contract',str(root/'230.json'),'--inspect'],capture_output=True,text=True,timeout=90)
try:result=json.loads(p.stdout)
except Exception:result={'status':'inspect-failed-no-public-result'}
print(json.dumps({'stage_path':str(root),'stage_file_count':len(values),'inspect_exit_code':p.returncode,'inspect':result,'OS_transaction_path_touched':False,'active_monitoring_or_addresses_changed':False,'services_started_or_restarted':False}));raise SystemExit(p.returncode)
'''
row=next(x for x in json.loads((R/'evidence/implementation/private-guest-access.json').read_text())['roles'] if x['target']['vmid']==230)
r=control.guest(230,'sudo -n python3 -I -B -c '+shlex.quote(P),data=json.dumps(files).encode(),timeout=130,info=row['target'])
try:x=json.loads(r['stdout'])
except Exception:raise SystemExit('standby stage failed; no sensitive output')
(H/'monitoring230-stage-evidence.json').write_text(json.dumps({'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'exit_code':r['exit_code'],'result':x},indent=2)+'\n');print(json.dumps(x));raise SystemExit(r['exit_code'])
