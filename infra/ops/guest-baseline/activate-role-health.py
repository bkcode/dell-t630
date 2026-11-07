#!/usr/bin/env python3
"""Activate approved local health targets through existing strict guest SSH only."""
import argparse,datetime,hashlib,importlib.util,json,sys
from pathlib import Path
from zoneinfo import ZoneInfo
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
sys.path.insert(0,str(ROOT/'scripts'));import control
spec=importlib.util.spec_from_file_location('baseline',HERE/'install-guest-baseline.py');baseline=importlib.util.module_from_spec(spec);spec.loader.exec_module(baseline)
APPROVED=[200,201,210,221,240,250,260,270]
EVIDENCE=ROOT/'evidence/implementation/guest-role-health-activation.json'
REMOTE=r'''
import json,os,socket,pathlib,stat,subprocess,hashlib,importlib.util,tempfile,datetime
role=ROLE;ip=ADDRESS;profile=PROFILE;apply=APPLY
CONFIG=pathlib.Path('/etc/dell-guest-monitoring/health.json');TEXT=pathlib.Path('/var/lib/prometheus/node-exporter-textfile/dell_guest_health.prom')
def snapshot(services):
 units={}
 for unit in services:
  r=subprocess.run(['systemctl','show',unit,'-p','ActiveState','-p','SubState','-p','MainPID','-p','ExecMainStartTimestampMonotonic'],capture_output=True,text=True,timeout=8);assert r.returncode==0;units[unit]=dict(x.split('=',1) for x in r.stdout.splitlines() if '=' in x)
 containers=[]
 if pathlib.Path('/var/run/docker.sock').exists():
  r=subprocess.run(['docker','ps','--quiet'],capture_output=True,text=True,timeout=10);assert r.returncode==0
  for id in r.stdout.split():
   fmt='{{.Id}} {{.State.Pid}} {{.State.StartedAt}} {{.State.Status}} {{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}';p=subprocess.run(['docker','inspect','--format',fmt,id],capture_output=True,text=True,timeout=10);assert p.returncode==0;id,pid,started,state,health=p.stdout.split();containers.append({'id':id,'pid':int(pid),'started_at':started,'state':state,'health':health})
 return {'units':units,'containers':sorted(containers,key=lambda x:x['id'])}
def atomic(body,mode=0o644):
 fd,name=tempfile.mkstemp(prefix='.health-',suffix='.json',dir=CONFIG.parent)
 try:
  os.fchmod(fd,mode)
  with os.fdopen(fd,'wb') as f:f.write(body);f.flush();os.fsync(f.fileno())
  os.replace(name,CONFIG)
 finally:
  if os.path.exists(name):os.unlink(name)
def sample_present(body,name,tags,value):
 line=name+'{'+','.join(k+'="'+v+'"' for k,v in tags.items())+'} '+str(value)
 return line in body.splitlines()
changed=False;original=None;result={'role':role,'private_ip':ip,'applied':False,'business_services_restarted':False,'response_bodies_or_env_or_logs_emitted':False}
try:
 assert os.geteuid()==0 and socket.gethostname()==role and not pathlib.Path('/etc/pve').exists()
 assert CONFIG.parent.resolve()==CONFIG.parent
 st=CONFIG.lstat();assert stat.S_ISREG(st.st_mode) and st.st_uid==0 and not st.st_mode&0o022
 original=CONFIG.read_bytes();c=json.loads(original);assert c['role']==role and c['private_ip']==ip
 spec=importlib.util.spec_from_file_location('collector','/opt/dell/guest-monitoring/collect-guest-health.py');collector=importlib.util.module_from_spec(spec);spec.loader.exec_module(collector)
 addresses=collector.local_addresses();collector.validate(c,addresses)
 base=['ssh.service','qemu-guest-agent.service','prometheus-node-exporter.service'];assert all(n in c['services'] for n in base)
 for unit in profile['services']:
  present,active,readable=collector.unit_state(unit);assert present==active==1 and readable
 for check in profile['http_checks']:
  assert collector.http_state(check['url'])==(1,200)
 updated=json.loads(original)
 for n in profile['services']:
  if n not in updated['services']:updated['services'].append(n)
 existing={x['name']:x for x in updated['http_checks']}
 for check in profile['http_checks']:
  assert check['name'] not in existing or existing[check['name']]==check
  if check['name'] not in existing:updated['http_checks'].append(check);existing[check['name']]=check
 collector.validate(updated,addresses)
 # Existing ordering and every non-target field must survive exactly.
 assert updated['services'][:len(c['services'])]==c['services'] and updated['http_checks'][:len(c['http_checks'])]==c['http_checks']
 assert {k:v for k,v in updated.items() if k not in ['services','http_checks']}=={k:v for k,v in c.items() if k not in ['services','http_checks']}
 result['before']=snapshot(updated['services']);result['before_sha256']=hashlib.sha256(original).hexdigest();result['before_config']=c;result['target_profile']=profile
 if not apply:result['status']='preflight-passed';print(json.dumps(result));raise SystemExit(0)
 backup_parent=pathlib.Path('/var/backups/dell-guest-monitoring');backup_parent.mkdir(mode=0o700,exist_ok=True);stb=backup_parent.lstat();assert stat.S_ISDIR(stb.st_mode) and stb.st_uid==0 and stat.S_IMODE(stb.st_mode)==0o700 and backup_parent.resolve()==backup_parent
 backup=backup_parent/('health-before-role-activation-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%f')+'.json');fd=os.open(backup,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
 with os.fdopen(fd,'wb') as f:f.write(original);f.flush();os.fsync(f.fileno())
 result['guest_backup_path']=str(backup);body=(json.dumps(updated,indent=2)+'\n').encode();atomic(body);changed=True;result['applied']=True;result['after_sha256']=hashlib.sha256(body).hexdigest()
 r=subprocess.run(['systemctl','start','dell-guest-health.service'],capture_output=True,text=True,timeout=50);result['collector_start_exit_code']=r.returncode;assert r.returncode==0
 collected=TEXT.read_text();metrics=[]
 for n in profile['services']:
  ok=sample_present(collected,'dell_guest_service_active',{'role':role,'service':n},1);assert ok;metrics.append({'kind':'service','name':n,'active':1})
 for check in profile['http_checks']:
  tags={'role':role,'check':check['name']};assert sample_present(collected,'dell_guest_http_up',tags,1) and sample_present(collected,'dell_guest_http_status_code',tags,200);metrics.append({'kind':'http','name':check['name'],'up':1,'status':200})
 assert sample_present(collected,'dell_guest_health_collection_success',{'role':role},1)
 result['after']=snapshot(updated['services']);assert result['after']==result['before'];st=CONFIG.stat();assert st.st_uid==0 and stat.S_IMODE(st.st_mode)==0o644
 result.update(status='passed',after_config=updated,config_uid=st.st_uid,config_gid=st.st_gid,config_mode=oct(st.st_mode&0o777),local_textfile_metrics=metrics,pids_started_at_and_service_state_unchanged=True)
 print(json.dumps(result))
except Exception as error:
 result.update(status='failed',exception_class=type(error).__name__)
 if changed and original is not None:
  atomic(original,stat.S_IMODE(st.st_mode));result['original_config_restored']=True
 print(json.dumps(result));raise SystemExit(1)
'''
def main():
 parser=argparse.ArgumentParser(description=__doc__);who=parser.add_mutually_exclusive_group(required=True);who.add_argument('--role',choices=sorted(baseline.ROLES));who.add_argument('--all-approved',action='store_true');parser.add_argument('--apply',action='store_true');a=parser.parse_args()
 rows=json.loads((HERE/'guest-targets.json').read_text())['roles'];targets={x['target']['vmid']:x['target'] for x in json.loads((ROOT/'evidence/implementation/private-guest-access.json').read_text())['roles']}
 selected=[r for r in rows if r['vmid'] in APPROVED] if a.all_approved else [r for r in rows if r['role']==a.role];assert selected and all(r['vmid'] in APPROVED for r in selected)
 receipt=json.loads(EVIDENCE.read_text()) if EVIDENCE.exists() else {'started_at':datetime.datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),'scope':'8-existing-guests-local-health-config-only','business_or_host_network_mutation':False,'guests':[]}
 for row in selected:
  v=row['vmid'];assert targets[v]['ip']==row['private_ip'];assert not any(x['vmid']==v and x['status']=='passed' for x in receipt['guests']),'refuse repeat activation of passed guest'
  code=REMOTE.replace('ROLE',repr(row['role'])).replace('ADDRESS',repr(row['private_ip'])).replace('PROFILE',repr(baseline.role_health_profile(row))).replace('APPLY',repr(a.apply));r=control.guest(v,'sudo -n python3 -',data=code.encode(),timeout=110,info=targets[v]);result=json.loads(r['stdout']);result.update(vmid=v,transport_exit_code=r['exit_code'],at=datetime.datetime.now(ZoneInfo('Asia/Shanghai')).isoformat());receipt['guests'].append(result);receipt['status']='local-configs-applied-prometheus-verification-pending' if r['exit_code']==0 else 'stopped-on-failure';tmp=EVIDENCE.with_suffix('.tmp');tmp.write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n');tmp.replace(EVIDENCE);print(json.dumps({'vmid':v,'status':result['status'],'applied':result['applied']}),flush=True)
  if r['exit_code']:raise SystemExit(1)
if __name__=='__main__':main()
