#!/usr/bin/env python3
"""Explicit future execution only: minimal file transaction, no generic installer modes."""
import argparse,base64,hashlib,json,shlex,sys,uuid
from pathlib import Path
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];sys.path.insert(0,str(ROOT/'scripts'));import control
M=json.loads((HERE/'manifest.json').read_text());T={x['target']['vmid']:x['target'] for x in json.loads((ROOT/'evidence/implementation/private-guest-access.json').read_text())['roles']}
REMOTE=r'''
import json,sys,pathlib,socket,os,hashlib,stat,subprocess,tempfile,time,importlib.util,urllib.request,re,base64,ast
p=json.load(sys.stdin);v=p['vmid'];role={220:'publish-service',270:'ops-service'}[v];primary={220:'192.168.19.30',270:'192.168.19.70'}[v];mac={220:'bc:24:11:2a:01:ad',270:'bc:24:11:ce:8c:67'}[v];assert os.geteuid()==0 and socket.gethostname()==role and not pathlib.Path('/etc/pve').exists()
def run(a,timeout=35):
 r=subprocess.run(a,capture_output=True,text=True,timeout=timeout)
 if r.returncode:raise RuntimeError('fixed-command-failed:'+a[0])
 return r.stdout
def digest(b):return hashlib.sha256(b).hexdigest()
def state(unit):return dict(x.split('=',1) for x in run(['systemctl','show',unit,'-p','ActiveState','-p','SubState','-p','MainPID','-p','ExecMainStartTimestampMonotonic']).splitlines() if '=' in x)
def addresses():
 x=json.loads(run(['ip','-j','addr']));iface=next(i for i in x if i.get('address','').lower()==mac);actual={a['local'] for a in iface.get('addr_info',[]) if a['family']=='inet'};assert primary in actual;return (actual&({primary,'192.168.19.31'} if v==220 else {primary}))|{'127.0.0.1','::1'}
def module(path,name):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def snapshot():
 units=['ssh.service','qemu-guest-agent.service','prometheus-node-exporter.service','docker.service']+(['dell-nexus.service'] if v==220 else ['dell-ops.service','dell-lark-notify.service']);out={'units':{u:state(u) for u in units},'containers':[]}
 for id in run(['docker','ps','--quiet']).split():
  f='{{.Id}} {{.State.Pid}} {{.State.StartedAt}} {{.State.Status}} {{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}';out['containers'].append(run(['docker','inspect','--format',f,id]).strip())
 out['containers'].sort();return out
def atomic(path,b,mode,uid,gid):
 assert path.is_absolute() and path.parent.resolve()==path.parent and not path.is_symlink();fd,tmp=tempfile.mkstemp(prefix='.monitor-cleanup-',dir=path.parent)
 try:
  os.fchmod(fd,mode);os.fchown(fd,uid,gid)
  with os.fdopen(fd,'wb') as f:f.write(b);f.flush();os.fsync(f.fileno())
  os.replace(tmp,path)
 finally:
  if os.path.exists(tmp):os.unlink(tmp)
def native_prom():
 id=run(['docker','ps','--quiet','--filter','label=com.docker.compose.service=prometheus']).split();assert len(id)==1
 run(['docker','exec',id[0],'/bin/promtool','check','config','/etc/prometheus/prometheus.yml'])
 raw=run(['docker','exec',id[0],'/bin/promtool','check','service-discovery','--timeout=1s','/etc/prometheus/prometheus.yml','guest-node']);assert len(json.loads(raw))==9
 return {'config_exit0':True,'actual_fileSD_discovered_groups':9}
def prom_ready():
 op=urllib.request.build_opener(urllib.request.ProxyHandler({}));end=time.monotonic()+90
 while True:
  with op.open('http://192.168.19.70:9090/api/v1/targets',timeout=8) as r:ts=json.loads(r.read(2000000))['data']['activeTargets']
  nodes=[x for x in ts if x.get('labels',{}).get('job')=='guest-node'];others=[x for x in ts if x.get('labels',{}).get('job')!='guest-node'];expected=set(p['expected_node_addresses']);actual={x['labels']['instance'] for x in nodes}
  if len(ts)==14 and len(nodes)==9 and len(others)==5 and actual==expected and all(x['health']=='up' for x in ts):return {'total':14,'guest_nodes':9,'unchanged_own_targets':5,'allUP':True}
  if time.monotonic()>end:raise RuntimeError('actual-fileSD14-target-health-not-settled')
  time.sleep(2)
assert digest(pathlib.Path('/opt/dell/guest-monitoring/collect-guest-health.py').read_bytes())==p['collector_SHA'],'collector changed since readonly capture';collector=module('/opt/dell/guest-monitoring/collect-guest-health.py','collector');allowed=addresses();root=pathlib.Path('/root/dell-monitor-cleanup');root.mkdir(mode=0o700,exist_ok=True);assert root.resolve()==root and stat.S_IMODE(root.stat().st_mode)==0o700
journal=root/p['nonce'];assert journal.parent==root
allowed_paths={'/opt/dell/guest-monitoring/guest-targets.json','/opt/dell/guest-monitoring/install-guest-baseline.py'}|({'/etc/dell-guest-monitoring/health.json'} if v==220 else {'/opt/dell/ops/config/prometheus/targets/guest-node.json'})
result={'vmid':v,'nonce':p['nonce'],'status':'not-applied','business_or_exporter_restart':False,'generic_installer_install_activate_invoked':False,'mask_or_network_or_auth_operation':False};before=snapshot();assert len(before['containers'])==(2 if v==220 else 4) and all(x.endswith(' running healthy') for x in before['containers']),'existing containers not stablyhealthy; no config write';wasactive=state('dell-guest-health.timer')['ActiveState']=='active';records=[];changed=False
try:
 if p['action']=='rollback':
  info=json.loads((journal/'journal.json').read_text());assert info['vmid']==v;records=info['records']
  for r in records:
   path=pathlib.Path(r['path']);assert str(path) in allowed_paths;assert digest(path.read_bytes()) in [r['old_SHA'],r['new_SHA']],'concurrent file changed; refusing rollback overwrite'
 else:
  assert p['action']=='apply' and not journal.exists();assert len(p['files'])==3 and {r['target_path'] for r in p['files']}==allowed_paths
  if v==220:
   assert state('dell-nexus.service')['ActiveState']=='active','Nexus target not yet active; no config write'
   health=json.loads(base64.b64decode(next(r['body_b64'] for r in p['files'] if r['target_path']=='/etc/dell-guest-monitoring/health.json')));collector.validate(health,allowed)
   if p['profile']=='full':
    assert '192.168.19.31' in allowed,'approved alias31 absent from original MAC'
    with urllib.request.build_opener(urllib.request.ProxyHandler({})).open('http://192.168.19.31:8081/service/rest/v1/status',timeout=5) as r:assert r.status==200;r.read(1024)
  else:
   assert digest(pathlib.Path('/opt/dell/ops/config/prometheus/prometheus.yml').read_bytes())==p['prom_SHA'] and digest(pathlib.Path('/opt/dell/ops/config/prometheus/rules/infra.yml').read_bytes())==p['rules_SHA']
  for r in p['files']:
   path=pathlib.Path(r['target_path']);assert path.is_file() and not path.is_symlink();st=path.stat();old=path.read_bytes();assert digest(old)==r['expected_old_SHA256'] and st.st_uid==0 and not st.st_mode&0o022,'baseline drift';new=base64.b64decode(r['body_b64']);assert digest(new)==r['new_SHA256'];ast.parse(new.decode()) if path.suffix=='.py' else json.loads(new);records.append({'path':str(path),'old_SHA':digest(old),'new_SHA':digest(new),'mode':stat.S_IMODE(st.st_mode),'uid':st.st_uid,'gid':st.st_gid,'new':new})
  journal.mkdir(mode=0o700)
  for index,r in enumerate(records):
   backup=journal/(str(index)+'.before');backup.write_bytes(pathlib.Path(r['path']).read_bytes());backup.chmod(0o600);r['backup']=str(backup)
  persisted={k:v for k,v in {'vmid':v,'timer_was_active':wasactive,'records':[{k:v for k,v in r.items() if k!='new'} for r in records],'phase':'backed-up'}.items()};(journal/'journal.json').write_text(json.dumps(persisted));(journal/'journal.json').chmod(0o600)
 # Pause only the collector timer, never exporter/Docker/business. Drain any existingoneshot first.
 run(['systemctl','stop','dell-guest-health.timer']);end=time.monotonic()+50
 while state('dell-guest-health.service')['ActiveState'] in ['active','activating','deactivating']:
  if time.monotonic()>end:raise RuntimeError('collector-busy-no-config-written')
  time.sleep(.5)
 for r in records:
  body=pathlib.Path(r['backup']).read_bytes() if p['action']=='rollback' else r['new'];atomic(pathlib.Path(r['path']),body,r['mode'],r['uid'],r['gid']);changed=True
 # Exact read-only ExecCondition and unchangedcollector, no general installer mode.
 run(['python3','-B','/opt/dell/guest-monitoring/install-guest-baseline.py','--check-private-ip','--role',role]);run(['runuser','--user','prometheus','--','python3','-B','/opt/dell/guest-monitoring/collect-guest-health.py','--check'],timeout=45);run(['systemctl','start','dell-guest-health.service'],timeout=50)
 if p['action']=='apply':
  text=pathlib.Path('/var/lib/prometheus/node-exporter-textfile/dell_guest_health.prom').read_text();assert 'dell_guest_health_collection_success{role="'+role+'"} 1' in text
  if v==220:
   assert 'dell_guest_service_active{role="publish-service",service="dell-nexus.service"} 1' in text
   if p['profile']=='full':assert 'dell_guest_http_up{role="publish-service",check="nexus-status"} 1' in text and 'dell_guest_http_status_code{role="publish-service",check="nexus-status"} 200' in text
  else:result['native']=native_prom();result['actual_targets']=prom_ready()
 assert snapshot()==before,'business/exporter/container identity changed during window';result['status']='committed' if p['action']=='apply' else 'rolled-back';result['snapshot_unchanged']=True
except Exception as e:
 result['status']='failed';result['error_class']=type(e).__name__;result['error_category']=str(e) if str(e) in ['baseline drift','collector-busy-no-config-written','actual-fileSD14-target-health-not-settled'] else 'fixed-monitoring-check-failed';errors=[]
 if changed:
  for r in records:
   try:atomic(pathlib.Path(r['path']),pathlib.Path(r['backup']).read_bytes(),r['mode'],r['uid'],r['gid'])
   except Exception as ex:errors.append(type(ex).__name__)
  result['original_files_restored']=not errors;result['restore_error_classes']=errors
finally:
 if wasactive:run(['systemctl','start','dell-guest-health.timer'])
 result['timer_original_active_restored']=state('dell-guest-health.timer')['ActiveState']==('active' if wasactive else 'inactive')
 if journal.exists():(journal/'result.json').write_text(json.dumps(result));(journal/'result.json').chmod(0o600)
print(json.dumps(result))
'''
def payload(vmid,profile):
 rows=[dict(r) for r in M['files'] if r['vmid']==vmid]
 if vmid==220:
  h=dict(M['health220']);h.update(h.pop('profiles')[profile]);rows.append(h)
 for r in rows:r['body_b64']=base64.b64encode((HERE/r['candidate']).read_bytes()).decode()
 return rows
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['plan','apply','rollback']);p.add_argument('--vmid',type=int,choices=[220,270]);p.add_argument('--profile',choices=['unit-only','full'],default='full');p.add_argument('--nonce');p.add_argument('--execute',action='store_true');a=p.parse_args()
 if a.action=='plan':print(json.dumps({'status':'prepared-only','manifest':str(HERE/'manifest.json'),'future_targets':14,'readiness_at_capture':M['readiness'],'no_guest_writes':True}));return
 if not a.execute or a.vmid is None:p.error('mutating future action requires explicit --execute and --vmid; current task is prepare-only')
 nonce=a.nonce or uuid.uuid4().hex;assert len(nonce)==32 and all(x in '0123456789abcdef' for x in nonce)
 if a.action=='apply' and (a.vmid==270 or a.profile=='full'):
  inventory=json.loads(control.pve('pvesh get /cluster/resources --type vm --output-format json',timeout=30));states={x['vmid']:x.get('status') for x in inventory};assert all(states.get(v,'absent') in ['stopped','absent'] for v in [221,231,232]),'retiring221/231/232mustbestoppedorabsent before compact/fullNexus monitoring; no guest write'
 if a.vmid==270 and a.action=='apply':
  # Parent-only deployment gate: do not remove221scrape before healthy merged service exists on220.
  code="import json,subprocess,pathlib,urllib.request; import socket; assert socket.gethostname()=='publish-service'; x=json.loads(subprocess.run(['ip','-j','addr'],capture_output=True,text=True,check=True).stdout); i=next(r for r in x if r.get('address','').lower()=='bc:24:11:2a:01:ad'); assert any(a.get('local')=='192.168.19.31' for a in i.get('addr_info',[])); assert subprocess.run(['systemctl','is-active','--quiet','dell-nexus.service']).returncode==0; r=urllib.request.build_opener(urllib.request.ProxyHandler({})).open('http://192.168.19.31:8081/service/rest/v1/status',timeout=5); assert r.status==200; print(json.dumps({'mergedNexus220ready':True}))"
  check=control.guest(220,'sudo -n python3 -B -c '+shlex.quote(code),info=T[220],timeout=25);assert check['exit_code']==0,'merge precondition not ready; no270write'
 data={'vmid':a.vmid,'action':a.action,'profile':a.profile,'nonce':nonce,'collector_SHA':M['unchanged_collector_SHA256'],'prom_SHA':M['prometheus_config_SHA256'],'rules_SHA':M['rules_SHA256'],'expected_node_addresses':[x['targets'][0] for x in json.loads((HERE/'candidates/ops/guest-node.json').read_text())],'files':payload(a.vmid,a.profile) if a.action=='apply' else []}
 r=control.guest(a.vmid,'sudo -n python3 -B -c '+shlex.quote(REMOTE),data=json.dumps(data).encode(),info=T[a.vmid],timeout=240);assert r['exit_code']==0,'bounded transaction transport failed; inspect rootjournal, do not blindlyrepeat';result=json.loads(r['stdout']);folder=HERE/'deployment-evidence';folder.mkdir(exist_ok=True);(folder/(str(a.vmid)+'-'+nonce+'.json')).write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result));assert result['status'] in ['committed','rolled-back']
if __name__=='__main__':main()
