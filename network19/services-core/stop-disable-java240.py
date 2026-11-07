#!/usr/bin/env python3
"""User scope change: only stop/disable existing240 five apps and fence publisher; no deploy."""
import datetime,json,os,shlex,sys
from pathlib import Path
sys.dont_write_bytecode=True
H=Path(__file__).resolve().parent;R=H.parents[1];sys.path.insert(0,str(R/'scripts'));import control
P=r'''import os,json,socket,subprocess,fcntl,hashlib,tempfile
from pathlib import Path
if os.geteuid()!=0 or socket.gethostname().split('.')[0]!='java-test-01' or Path('/etc/pve').exists():raise SystemExit('240 only')
lock=os.open('/run/lock/dell-publish-test240.lock',os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW,0o600);fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
policy=Path('/etc/dell-publisher/test240-policy.json');st=policy.stat()
if policy.resolve()!=policy or st.st_uid!=0 or st.st_mode&0o077:raise SystemExit('root600 policy required')
backup=Path('/root/dell-network19/java-hold');backup.mkdir(mode=0o700,parents=True,exist_ok=True)
p=backup/'publisher-policy-before-hold.json'
if not p.exists():p.write_bytes(policy.read_bytes());p.chmod(0o600)
x=json.loads(policy.read_text());x['baseline_migrated']=False
fd,tmp=tempfile.mkstemp(prefix='.publisher-fence-',dir=policy.parent)
with os.fdopen(fd,'w') as f:json.dump(x,f)
os.chmod(tmp,0o600);os.replace(tmp,policy)
services=['finger-gateway-mobile','finger-bff-system','finger-auth','finger-service-coms','finger-service-system'];units=['dell-finger-'+n+'.service' for n in services]
current=Path('/opt/finger/current-test').resolve();manifest=current/'manifest.json';before_sha=hashlib.sha256(manifest.read_bytes()).hexdigest()
p=subprocess.run(['systemctl','stop',*units],capture_output=True,text=True,timeout=240)
if p.returncode:print(json.dumps({'status':'app-stop-failed-publisher-fenced','stop_exit':p.returncode}));raise SystemExit(1)
p=subprocess.run(['systemctl','disable',*units],capture_output=True,text=True,timeout=30)
if p.returncode:print(json.dumps({'status':'app-disable-failed-publisher-fenced','disable_exit':p.returncode}));raise SystemExit(1)
proof=[]
for unit in units:
 p=subprocess.run(['systemctl','show',unit,'--property=ActiveState,SubState,MainPID,UnitFileState,ControlGroup'],capture_output=True,text=True,timeout=10);row=dict(l.split('=',1) for l in p.stdout.splitlines() if '=' in l);group=row.get('ControlGroup','');procs=Path('/sys/fs/cgroup')/group.lstrip('/')/'cgroup.procs' if group else None;empty=procs is None or not procs.exists() or not procs.read_text().strip();proof.append({'unit':unit,'active':row.get('ActiveState'),'mainPID0':row.get('MainPID')=='0','enabled':row.get('UnitFileState'),'cgroup_empty':empty})
checked=all(r['active']=='inactive' and r['mainPID0'] and r['enabled']=='disabled' and r['cgroup_empty'] for r in proof)
result={'status':'stopped-disabled-publisher-fenced' if checked else 'stop-disable-verification-failed','app_count':5,'unit_checks':proof,'active_immutable_release_manifest_unchanged':hashlib.sha256(manifest.read_bytes()).hexdigest()==before_sha,'existing_root600_configs_preserved':all((current/n/'application.yaml').stat().st_mode&0o777==0o600 for n in services),'fresh_Nacos_dataIds_published':False,'release_activated':False,'business_E2E_or_restarts_performed':False,'credentials_or_policy_values_emitted':False}
p=backup/'hold-proof.json';p.write_text(json.dumps(result,indent=2));p.chmod(0o600);print(json.dumps(result));os.close(lock);raise SystemExit(0 if checked else 1)
'''
old=next(r['target'] for r in json.loads((R/'evidence/implementation/private-guest-access.json').read_text())['roles'] if r['target']['vmid']==240);mapped=json.loads((R/'network19/evidence/migrated-access.json').read_text())['targets'];info=mapped.get('240',old)
r=control.guest(240,'sudo -n python3 -I -B -c '+shlex.quote(P),timeout=300,info=info)
try:x=json.loads(r['stdout'])
except Exception:raise SystemExit('hold no safe receipt; no blind app action')
(H/'java240-stop-disable-hold-evidence.json').write_text(json.dumps({'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'exit_code':r['exit_code'],'result':x},indent=2)+'\n');print(json.dumps(x));raise SystemExit(r['exit_code'])
