#!/usr/bin/env python3
"""Opened root window: sequential exactpair apply with independent service readbacks."""
import sys,json,shlex,subprocess,datetime,hashlib
from pathlib import Path
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];sys.path.insert(0,str(ROOT/'scripts'));import control
M=json.loads((HERE/'manifest.json').read_text());T={x['target']['vmid']:x['target'] for x in json.loads((ROOT/'evidence/implementation/private-guest-access.json').read_text())['roles']};OUT=HERE/'execution-window.json'
assert not OUT.exists(),'inspect existing window, no blindreplay'
APPS={200:['dell-data-prod-db.service'],201:['dell-data-prod-infra.service'],210:['dell-data-test-data.service'],220:['dell-nexus.service'],221:['dell-nexus.service'],230:[],240:['dell-finger-'+n+'.service' for n in ['finger-service-system','finger-service-coms','finger-auth','finger-bff-system','finger-gateway-mobile']],250:['dell-penpot.service'],260:['nginx.service','openmediavault-engined.service','smbd.service','dell-nas-jellyfin.service'],270:['dell-ops.service','dell-lark-notify.service']}
CODE=r'''
import json,pathlib,subprocess,hashlib,socket,sys
p=json.load(sys.stdin);assert not pathlib.Path('/etc/pve').exists();out={'hostname':socket.gethostname(),'units':{},'containers':[],'files':{}}
for unit in p['units']:
 r=subprocess.run(['systemctl','show',unit,'-p','LoadState','-p','ActiveState','-p','SubState','-p','MainPID','-p','ExecMainStartTimestampMonotonic'],capture_output=True,text=True,check=True);out['units'][unit]=dict(x.split('=',1) for x in r.stdout.splitlines() if '=' in x)
for name in ['guest-targets.json','install-guest-baseline.py','collect-guest-health.py']:
 out['files']['/opt/dell/guest-monitoring/'+name]=hashlib.sha256(pathlib.Path('/opt/dell/guest-monitoring',name).read_bytes()).hexdigest()
out['files']['/etc/dell-guest-monitoring/health.json']=hashlib.sha256(pathlib.Path('/etc/dell-guest-monitoring/health.json').read_bytes()).hexdigest()
r=subprocess.run(['systemctl','show','dell-guest-health.timer','-p','ActiveState','-p','UnitFileState'],capture_output=True,text=True,check=True);out['timer']=dict(x.split('=',1) for x in r.stdout.splitlines() if '=' in x)
if pathlib.Path('/var/run/docker.sock').exists():
 ids=subprocess.run(['docker','ps','--quiet'],capture_output=True,text=True,check=True).stdout.split()
 for i in ids:
  f='{{.Id}} {{.State.Pid}} {{.State.StartedAt}} {{.State.Status}} {{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}';out['containers'].append(subprocess.run(['docker','inspect','--format',f,i],capture_output=True,text=True,check=True).stdout.strip())
out['containers'].sort();print(json.dumps(out))
'''
def now():return datetime.datetime.now().astimezone().isoformat()
def save():OUT.write_text(json.dumps(D,indent=2)+'\n')
def read(v):
 units=['ssh.service','qemu-guest-agent.service','prometheus-node-exporter.service','docker.service']+APPS[v];r=control.guest(v,'sudo -n python3 -B -c '+shlex.quote(CODE),data=json.dumps({'units':units}).encode(),info=T[v],timeout=40);assert r['exit_code']==0,('independent readonlybeforeafterfailed',v,r['exit_code']);return json.loads(r['stdout'])
D={'started_at':now(),'authorization':'explicitparent10guestpairwindow','status':'running','roles':[],'mainplan_modified':False,'Nexus_lifecycle_or_profile_migration':False};save()
for v in M['exporter_ids']:
 row={'vmid':v,'started_at':now(),'before':read(v),'status':'preflight'};D['roles'].append(row);save()
 r=subprocess.run([sys.executable,str(HERE/'apply.py'),'apply','--vmid',str(v),'--execute'],capture_output=True,text=True,timeout=260);row['apply_exit']=r.returncode
 if r.returncode:
  row['status']='failed-stopped-no-blindretry';row['stderr_present']=bool(r.stderr);row['stdout_metadata']=r.stdout[-1800:];D['status']='stopped-on-first-failure';save();print(json.dumps({'vmid':v,'status':row['status']}));raise SystemExit(1)
 row['receipt']=json.loads(r.stdout);row['after']=read(v);a,b=row['before'],row['after'];assert a['units']==b['units'] and a['containers']==b['containers'] and a['timer']==b['timer'],'service/Exporter/container/timer drift after update'
 for path,val in M['unchanged_guards'][str(v)].items():assert a['files'][path]==b['files'][path]==val
 for file in [x for x in M['files'] if x['vmid']==v]:assert b['files'][file['target_path']]==file['new_SHA256']
 row.update(status='passed',completed_at=now(),services_Exporter_containers_timer_unchanged=True,health_collector_unchanged=True);save();print(json.dumps({'vmid':v,'status':'passed','receipt_nonce':row['receipt']['nonce']}),flush=True)
D['status']='ten-guests-complete-source-sync-pending';D['completed_at']=now();save();print(json.dumps({'status':D['status'],'roles':len(D['roles'])}))
