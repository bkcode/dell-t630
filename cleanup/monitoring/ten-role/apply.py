#!/usr/bin/env python3
"""Future explicit window: only paired catalog/ROLES files; immutable health+collector."""
import argparse,base64,json,shlex,sys,uuid,hashlib
from pathlib import Path
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];sys.path.insert(0,str(ROOT/'scripts'));import control
M=json.loads((HERE/'manifest.json').read_text());T={x['target']['vmid']:x['target'] for x in json.loads((ROOT/'evidence/implementation/private-guest-access.json').read_text())['roles']}
REMOTE=r'''
import os,sys,pathlib,json,socket,subprocess,hashlib,stat,tempfile,time,ast
p=json.load(sys.stdin);assert os.geteuid()==0 and not pathlib.Path('/etc/pve').exists() and socket.gethostname()==p['hostname'];allowed={'/opt/dell/guest-monitoring/guest-targets.json','/opt/dell/guest-monitoring/install-guest-baseline.py'};sha=lambda b:hashlib.sha256(b).hexdigest()
def run(a,timeout=40):
 r=subprocess.run(a,capture_output=True,text=True,timeout=timeout)
 if r.returncode:raise RuntimeError('fixed-readonly-or-timer-command-failed')
 return r.stdout

def state(unit):return dict(x.split('=',1) for x in run(['systemctl','show',unit,'-p','ActiveState','-p','MainPID','-p','ExecMainStartTimestampMonotonic']).splitlines() if '=' in x)
def immutable():
 for path,value in p['unchanged'].items():assert sha(pathlib.Path(path).read_bytes())==value,'health-or-collector-drift; no overwrite'
def write(path,b,st):
 assert str(path) in allowed and not path.is_symlink() and path.parent.resolve()==path.parent;fd,name=tempfile.mkstemp(prefix='.roster10-',dir=path.parent)
 try:
  os.fchmod(fd,st['mode']);os.fchown(fd,st['uid'],st['gid'])
  with os.fdopen(fd,'wb') as f:f.write(b);f.flush();os.fsync(f.fileno())
  os.replace(name,path)
 finally:
  if os.path.exists(name):os.unlink(name)
def check():
 run(['python3','-B','/opt/dell/guest-monitoring/install-guest-baseline.py','--check-private-ip','--role',p['role']]);raw=run(['runuser','--user','prometheus','--','python3','-B','/opt/dell/guest-monitoring/collect-guest-health.py','--check'],timeout=50);result=json.loads(raw);assert result['metrics_written'] is False
 return {'private_IP_ExecCondition_passed':True,'collector_read_access_passed':True,'collector_did_not_write_metrics':True}
immutable();before=state('prometheus-node-exporter.service');assert before['ActiveState']=='active';wasactive=state('dell-guest-health.timer')['ActiveState']=='active';enabled=run(['systemctl','show','dell-guest-health.timer','-p','UnitFileState','--value']).strip();root=pathlib.Path('/root/dell-roster10');root.mkdir(mode=0o700,exist_ok=True);assert root.resolve()==root and stat.S_IMODE(root.stat().st_mode)==0o700;folder=root/p['nonce'];records=[];changed=False;paused=False;out={'vmid':p['vmid'],'nonce':p['nonce'],'health_or_collector_written':False,'business_or_exporter_restart':False,'Nexus_lifecycle_package_or_credentials_touched':False}
try:
 if p['action']=='rollback':
  j=json.loads((folder/'journal.json').read_text());assert j['vmid']==p['vmid'];records=j['records']
  for r in records:assert r['path'] in allowed and sha(pathlib.Path(r['path']).read_bytes()) in [r['old_SHA'],r['new_SHA']]
 else:
  assert p['action']=='apply' and {r['target_path'] for r in p['files']}==allowed and len(p['files'])==2
  statuses=[]
  for r in p['files']:
   f=pathlib.Path(r['target_path']);st=f.stat();assert not f.is_symlink() and st.st_uid==0 and not st.st_mode&0o022;b=f.read_bytes();n=__import__('base64').b64decode(r['body']);assert sha(n)==r['new_SHA256'];statuses.append('old' if sha(b)==r['expected_old_SHA256'] else 'new' if sha(b)==r['new_SHA256'] else 'drift');ast.parse(n) if f.suffix=='.py' else json.loads(n);records.append({'path':str(f),'old_SHA':r['expected_old_SHA256'],'new_SHA':r['new_SHA256'],'mode':stat.S_IMODE(st.st_mode),'uid':st.st_uid,'gid':st.st_gid,'new':n})
  assert statuses in [['old','old'],['new','new']],'mixed/drift pairedstate; inspect journal before retry'
  if statuses==['new','new']:
   out.update(status='already-ten-role-no-write',checks=check());immutable();assert state('prometheus-node-exporter.service')==before;print(json.dumps(out));raise SystemExit(0)
  assert not folder.exists();folder.mkdir(mode=0o700)
  for i,r in enumerate(records):
   backup=folder/(str(i)+'.before');backup.write_bytes(pathlib.Path(r['path']).read_bytes());backup.chmod(0o600);r['backup']=str(backup)
  info={'vmid':p['vmid'],'timer_was_active':wasactive,'records':[{k:v for k,v in r.items() if k!='new'} for r in records]};(folder/'journal.json').write_text(json.dumps(info));(folder/'journal.json').chmod(0o600)
 # Only healthtimer may pause; never invoke install/activate/mask or restart exporter/business.
 run(['systemctl','stop','dell-guest-health.timer']);paused=True;end=time.monotonic()+55
 while state('dell-guest-health.service')['ActiveState'] in ['active','activating','deactivating']:
  if time.monotonic()>end:raise RuntimeError('collectorbusy-no-file-change')
  time.sleep(.5)
 for r in records:write(pathlib.Path(r['path']),pathlib.Path(r['backup']).read_bytes() if p['action']=='rollback' else r['new'],r);changed=True
 out['checks']=check();immutable();assert state('prometheus-node-exporter.service')==before;assert run(['systemctl','show','dell-guest-health.timer','-p','UnitFileState','--value']).strip()==enabled;out['status']='committed-ten-role-pair' if p['action']=='apply' else 'restored-exact-twelve-role-pair';out['exporter_PID_start_state_unchanged']=True
except Exception as e:
 out['status']='failed';out['error_class']=type(e).__name__;errors=[]
 if changed:
  for r in records:
   try:write(pathlib.Path(r['path']),pathlib.Path(r['backup']).read_bytes(),r)
   except Exception as ex:errors.append(type(ex).__name__)
  out['old_pair_restored']=not errors;out['restore_errors']=errors
finally:
 if paused and wasactive:run(['systemctl','start','dell-guest-health.timer'])
 out['timer_activation_unchanged']=state('dell-guest-health.timer')['ActiveState']==('active' if wasactive else 'inactive')
 if folder.exists():f=folder/'result.json';f.write_text(json.dumps(out));f.chmod(0o600)
print(json.dumps(out))
'''
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['plan','apply','rollback']);p.add_argument('--vmid',type=int,choices=M['exporter_ids']);p.add_argument('--nonce');p.add_argument('--execute',action='store_true');a=p.parse_args()
 if a.action=='plan':print(json.dumps({'status':'prepared-only','guests':10,'live_files':20,'health_collector_unchanged':True,'Nexus221_preserved':True,'not_executed':True}));return
 if not a.execute or a.vmid is None:p.error('future mutation requires explicit --execute --vmid; currenttask prepare-only')
 nonce=a.nonce or uuid.uuid4().hex;assert len(nonce)==32 and all(x in '0123456789abcdef' for x in nonce);row=next(x for x in json.loads((HERE/'live-source-inventory.json').read_text())['roles'] if x['vmid']==a.vmid);role=next(x['health_metadata']['role'] for x in row['files'] if x['path'].endswith('/health.json'));files=[]
 for r in M['files']:
  if r['vmid']==a.vmid:
   x=dict(r);x['body']=base64.b64encode((HERE/r['candidate']).read_bytes()).decode();files.append(x)
 payload={'vmid':a.vmid,'hostname':row['hostname'],'role':role,'action':a.action,'nonce':nonce,'unchanged':M['unchanged_guards'][str(a.vmid)],'files':files};r=control.guest(a.vmid,'sudo -n python3 -B -c '+shlex.quote(REMOTE),data=json.dumps(payload).encode(),info=T[a.vmid],timeout=220);assert r['exit_code']==0,'unconfirmed; inspect rootjournal, no blindretry';j=json.loads(r['stdout']);d=HERE/'deployment-evidence';d.mkdir(exist_ok=True);(d/(str(a.vmid)+'-'+nonce+'.json')).write_text(json.dumps(j,indent=2)+'\n');print(json.dumps(j));assert j['status'] in ['committed-ten-role-pair','already-ten-role-no-write','restored-exact-twelve-role-pair']
if __name__=='__main__':main()
