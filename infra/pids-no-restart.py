#!/usr/bin/env python3
"""Approved fixed-scope pids-limit persistence and NAS dependency metadata update."""
from pathlib import Path
import sys,json,datetime,hashlib,re,importlib.util,shlex,os
sys.dont_write_bytecode=True
BASE=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('control',BASE/'scripts/control.py');control=importlib.util.module_from_spec(spec);spec.loader.exec_module(control)
PRE=json.loads((BASE/'evidence/implementation/docker-pids-dependency-preaudit.json').read_text());OLD={x['vmid']:x for x in PRE['guests']};ROLES={x['target']['vmid']:x for x in json.loads((BASE/'evidence/implementation/private-guest-access.json').read_text())['roles']}
ASSIGNED=[(200,'data-prod-db','prod-db','/opt/dell/data/prod-db/compose.yaml'),(201,'data-prod-infra','prod-infra','/opt/dell/data/prod-infra/compose.yaml'),(210,'data-test','test-data','/opt/dell/data/test-data/compose.yaml'),(270,'ops-service','ops','/opt/dell/ops/compose.yaml')]
FILES=['infra/data/compose.prod-db.yaml','infra/data/compose.prod-infra.yaml','infra/data/compose.test-data.yaml','infra/ops/compose.yaml','private/data/bundles/prod-db/compose.yaml','private/data/bundles/prod-infra/compose.yaml','private/data/bundles/test-data/compose.yaml','private/ops/bundle/compose.yaml']
OUT=BASE/'evidence/implementation/docker-pids-dependency-remediation.json';assert not OUT.exists(),'Retain previous attempt; no blind repeat'
RUN=datetime.datetime.now().strftime('%Y%m%dT%H%M%S');BACKUPS=BASE/'private/audit-backups'/('pids-'+RUN);BACKUPS.mkdir(parents=True,mode=0o700)
def now():return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat()
def save():
 tmp=OUT.with_suffix('.json.tmp');tmp.write_text(json.dumps(REPORT,ensure_ascii=False,indent=2)+'\n');tmp.chmod(0o600);tmp.replace(OUT)

def strip_pids(text):return ''.join(l for l in text.splitlines(keepends=True) if not re.match(r'^    pids_limit:',l))
def patch(text):
 lines=text.splitlines(keepends=True);inside=False;result=[];services=[]
 for l in lines:
  if l.rstrip('\r\n')=='services:':inside=True;result.append(l);continue
  if inside and l.strip() and not l.startswith((' ','#')):inside=False
  if inside and re.match(r'^    pids_limit:',l):continue
  result.append(l)
  m=re.match(r'^  ([A-Za-z0-9_-]+):(?:\s*#.*)?\s*$',l.rstrip('\r\n')) if inside else None
  if m:services.append(m.group(1));result.append('    pids_limit: 1024\n')
 changed=''.join(result);assert services and strip_pids(text)==strip_pids(changed)
 return changed,services

REMOTE_COMMON=r'''
from pathlib import Path
import os,socket,json,subprocess,re,hashlib,datetime,shlex
PIDS_LIMIT=1024
docker=['docker','--host','unix:///var/run/docker.sock']
def stamp():return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat()
def capture():
 ids=subprocess.check_output(docker+['ps','--all','--quiet','--no-trunc'],text=True).split();assert ids
 fmt='{"id":{{json .Id}},"name":{{json .Name}},"pid":{{json .State.Pid}},"started_at":{{json .State.StartedAt}},"state":{{json .State.Status}},"health":{{if .State.Health}}{{json .State.Health.Status}}{{else}}null{{end}},"pids_limit":{{json .HostConfig.PidsLimit}},"image_id":{{json .Image}},"nano_cpus":{{json .HostConfig.NanoCpus}},"cpu_quota":{{json .HostConfig.CpuQuota}},"cpu_period":{{json .HostConfig.CpuPeriod}},"memory":{{json .HostConfig.Memory}},"memory_swap":{{json .HostConfig.MemorySwap}},"port_bindings":{{json .HostConfig.PortBindings}},"service":{{json (index .Config.Labels "com.docker.compose.service")}},"compose_files":{{json (index .Config.Labels "com.docker.compose.project.config_files")}}}'
 rows=[json.loads(l) for l in subprocess.check_output(docker+['container','inspect','--format',fmt]+ids,text=True).splitlines()]
 for row in rows:
  row['cgroup_pids']={}
  if row['pid']:
   line=next(x for x in Path('/proc/'+str(row['pid'])+'/cgroup').read_text().splitlines() if x.startswith('0::'));relative=Path(line.split(':',2)[2].lstrip('/'));assert '..'not in relative.parts;cg=Path('/sys/fs/cgroup')/relative
   for key in ['pids.current','pids.max','pids.peak']:
    p=cg/key
    if p.exists():row['cgroup_pids'][key]=p.read_text().strip()
 return rows
def immutable(row):return {k:v for k,v in row.items() if k not in ['pids_limit','cgroup_pids']}
def same(before,after):return {r['id']:immutable(r) for r in before}=={r['id']:immutable(r) for r in after}
def strip_pids(text):return ''.join(l for l in text.splitlines(keepends=True) if not re.match(r'^    pids_limit:',l))
def patch(text):
 result=[];inside=False;services=[]
 for l in text.splitlines(keepends=True):
  if l.rstrip('\r\n')=='services:':inside=True;result.append(l);continue
  if inside and l.strip() and not l.startswith((' ','#')):inside=False
  if inside and re.match(r'^    pids_limit:',l):continue
  result.append(l);m=re.match(r'^  ([A-Za-z0-9_-]+):(?:\s*#.*)?\s*$',l.rstrip('\r\n')) if inside else None
  if m:services.append(m.group(1));result.append('    pids_limit: 1024\n')
 new=''.join(result);assert services and strip_pids(text)==strip_pids(new);return new,services
def atomic_file(path,data,mode,uid,gid):
 temp=path.with_name('.'+path.name+'.pids-audit-tmp');assert not temp.is_symlink();temp.write_text(data);temp.chmod(mode);os.chown(temp,uid,gid);os.replace(temp,path)
'''
READ=r'''
role=ROLE
assert os.geteuid()==0 and socket.gethostname()==role and not Path('/etc/pve').exists()
print(json.dumps({'role':role,'at':stamp(),'containers':capture(),'environment_read':False,'health_logs_read':False,'mutation_performed':False}))
'''
APPLY=r'''
role=ROLE;expected=EXPECTED;path=Path(COMPOSE);run=RUN
assert os.geteuid()==0 and socket.gethostname()==role and not Path('/etc/pve').exists()
record={'role':role,'started_at':stamp(),'status':'in-progress','environment_read':False,'health_logs_read':False,'container_recreate_or_restart_invoked':False,'operations':[]}
try:
 before=capture();assert same(expected,before),'Unexpected immutable container drift before apply'
 for r in before:assert r['state']=='running' and r['health']=='healthy' and max(int(r['cgroup_pids'].get('pids.current','0')),int(r['cgroup_pids'].get('pids.peak','0')))<512
 assert path.is_file() and not path.is_symlink() and path.resolve()==path
 cfg=docker+['compose','--env-file',str(path.parent/'.env'),'-f',str(path),'config','--quiet']
 result=subprocess.run(cfg,capture_output=True);record['native_config_before']={'exit_code':result.returncode,'stdout_bytes':len(result.stdout),'stderr_bytes':len(result.stderr),'rendered_output_saved':False};assert result.returncode==0
 old=path.read_text();new,services=patch(old);assert set(services)=={r['service'] for r in before}
 folder=Path('/root/dell-docker-audit-backups')/run;folder.mkdir(parents=True,mode=0o700);backup=folder/'compose.yaml.before';assert not backup.exists();backup.write_text(old);backup.chmod(0o600)
 st=path.stat();atomic_file(path,new,st.st_mode&0o777,st.st_uid,st.st_gid)
 result=subprocess.run(cfg,capture_output=True);record['native_config_after']={'exit_code':result.returncode,'stdout_bytes':len(result.stdout),'stderr_bytes':len(result.stderr),'rendered_output_saved':False};assert result.returncode==0
 record['compose']={'path':str(path),'backup':str(backup),'before_sha256':hashlib.sha256(old.encode()).hexdigest(),'after_sha256':hashlib.sha256(new.encode()).hexdigest(),'stripped_before_sha256':hashlib.sha256(strip_pids(old).encode()).hexdigest(),'stripped_after_sha256':hashlib.sha256(strip_pids(new).encode()).hexdigest(),'non_pids_text_unchanged':True,'services':services}
 for row in before:
  p=subprocess.run(docker+['update','--pids-limit','1024',row['id']],capture_output=True,text=True,timeout=30);record['operations'].append({'container_id':row['id'],'action':'docker update --pids-limit1024','exit_code':p.returncode});assert p.returncode==0,'Runtime pids update failed; no automatic broad rollback'
  current=capture();assert same(before,current),'Unexpected immutable runtime change'
 after=capture();assert same(before,after)
 assert all(r['pids_limit']==1024 and r['cgroup_pids'].get('pids.max')=='1024' for r in after)
 record.update(status='passed-no-restart-pids-only',before=before,after=after,completed_at=stamp(),immutable_metadata_unchanged=True)
except Exception as e:record.update(status='failed-stopped',error_type=type(e).__name__,completed_at=stamp())
print(json.dumps(record))
'''
REPORT={'schema_version':1,'started_at':now(),'scope':'approved12-containers-pids-only-and-NAS-dependency-metadata','status':'in-progress','preaudit':'evidence/implementation/docker-pids-dependency-preaudit.json','local_files':[],'guests':[],'container_Config_Env_inspected':False,'secret_payload_files_read_by_verifier':False,'native_compose_existing_env_resolution_internal_only':True,'health_logs_read':False,'pve_original_repo_knownhosts_touched':False}
save()
try:
 # Complete the fresh read-only admission check before changing any public/private file.
 for vmid,role,_,_ in ASSIGNED:
  assert ROLES[vmid]['name']==role
  code=(REMOTE_COMMON+READ).replace('ROLE',repr(role));r=control.guest(vmid,'sudo -n python3 -',data=code.encode(),timeout=50,info=ROLES[vmid]['target']);assert r['exit_code']==0;fresh=json.loads(r['stdout'])
  def imm(row):return {k:v for k,v in row.items() if k not in ['pids_limit','cgroup_pids']}
  assert {x['id']:imm(x) for x in fresh['containers']}=={x['id']:imm(x) for x in OLD[vmid]['containers']},'Container drift during approval window'
  assert all(x['health']=='healthy' and max(int(x['cgroup_pids'].get('pids.current','0')),int(x['cgroup_pids'].get('pids.peak','0')))<512 for x in fresh['containers'])
 for relative in FILES:
  path=BASE/relative;assert path.resolve()==path and path.is_file();old=path.read_text();new,services=patch(old);backup=BACKUPS/relative;backup.parent.mkdir(mode=0o700,parents=True,exist_ok=True);backup.write_text(old);backup.chmod(0o600);mode=path.stat().st_mode&0o777;temp=path.with_name('.'+path.name+'.pids-audit-tmp');assert not temp.is_symlink();temp.write_text(new);temp.chmod(mode);temp.replace(path)
  REPORT['local_files'].append({'path':relative,'backup':str(backup),'before_sha256':hashlib.sha256(old.encode()).hexdigest(),'after_sha256':hashlib.sha256(new.encode()).hexdigest(),'stripped_before_sha256':hashlib.sha256(strip_pids(old).encode()).hexdigest(),'stripped_after_sha256':hashlib.sha256(strip_pids(new).encode()).hexdigest(),'services':services,'non_pids_text_unchanged':True});save()
 for vmid,role,_,path in ASSIGNED:
  print('APPLY_ROLE '+role+' '+now(),flush=True)
  code=(REMOTE_COMMON+APPLY).replace('ROLE',repr(role)).replace('EXPECTED',repr(OLD[vmid]['containers'])).replace('COMPOSE',repr(path)).replace('RUN',repr(RUN));r=control.guest(vmid,'sudo -n python3 -',data=code.encode(),timeout=180,info=ROLES[vmid]['target']);assert r['exit_code']==0;result=json.loads(r['stdout']);result['vmid']=vmid;REPORT['guests'].append(result);save();assert result['status']=='passed-no-restart-pids-only','Target update failed; stop'
  print('ROLE_VERIFIED '+role+' '+now(),flush=True)
 # NAS: only dependency metadata; no unit content/env inspection and no restart.
 nas_code=REMOTE_COMMON+r'''
assert os.geteuid()==0 and socket.gethostname()=='nas-media' and not Path('/etc/pve').exists()
def unit(name):
 text=subprocess.check_output(['systemctl','show',name,'-p','BindsTo','-p','Requires','-p','After','-p','ActiveState','-p','SubState','-p','MainPID','-p','ExecMainStartTimestampMonotonic'],text=True);return dict(l.split('=',1) for l in text.splitlines() if '='in l)
before=unit('dell-nas-jellyfin.service');dbefore=unit('docker.service');containers_before=capture();assert before['ActiveState']=='active' and before['MainPID']=='1110' and dbefore['ActiveState']=='active' and dbefore['MainPID']=='840';assert len(containers_before)==1 and containers_before[0]['pids_limit']==256
path=Path('/etc/systemd/system/dell-nas-jellyfin.service.d/20-docker-binds.conf');assert not path.exists();path.parent.mkdir(mode=0o755,exist_ok=True);content='[Unit]\nBindsTo=docker.service\n';path.write_text(content);path.chmod(0o644)
p=subprocess.run(['systemctl','daemon-reload'],capture_output=True);assert p.returncode==0
after=unit('dell-nas-jellyfin.service');dafter=unit('docker.service');containers_after=capture();old_bind=set(shlex.split(before['BindsTo']));new_bind=set(shlex.split(after['BindsTo']));assert new_bind-old_bind=={'docker.service'} and old_bind<=new_bind
for key in ['ActiveState','SubState','MainPID','ExecMainStartTimestampMonotonic']:assert before[key]==after[key] and dbefore[key]==dafter[key]
assert set(shlex.split(before['Requires']))==set(shlex.split(after['Requires'])) and set(shlex.split(before['After']))==set(shlex.split(after['After']))
assert same(containers_before,containers_after) and all(x['pids_limit']==256 for x in containers_after)
print(json.dumps({'status':'passed-dependency-only-no-restart','at':stamp(),'dropin':str(path),'dropin_sha256':hashlib.sha256(content.encode()).hexdigest(),'before':before,'after':after,'docker_before':dbefore,'docker_after':dafter,'containers_before':containers_before,'containers_after':containers_after,'mount_dependency_preserved':True,'pids256_preserved':True,'environment_or_unit_file_contents_read':False,'daemon_reload_exit_code':p.returncode,'restart_invoked':False}))
'''
 r=control.guest(260,'sudo -n python3 -',data=nas_code.encode(),timeout=80,info=ROLES[260]['target']);assert r['exit_code']==0;REPORT['nas']=json.loads(r['stdout']);save()
 generator=BASE/'infra/nas/deploy-jellyfin.sh';old=generator.read_text();needle='BindsTo=$MOUNT_UNIT';assert old.count(needle)==1;new=old.replace(needle,'BindsTo=docker.service $MOUNT_UNIT');assert old.replace(needle,'')==new.replace('BindsTo=docker.service $MOUNT_UNIT','');backup=BACKUPS/'infra/nas/deploy-jellyfin.sh';backup.parent.mkdir(parents=True,exist_ok=True,mode=0o700);backup.write_text(old);backup.chmod(0o600);generator.write_text(new)
 REPORT['nas_generator']={'path':'infra/nas/deploy-jellyfin.sh','before_sha256':hashlib.sha256(old.encode()).hexdigest(),'after_sha256':hashlib.sha256(new.encode()).hexdigest(),'only_BindsTo_line_changed':True,'backup':str(backup)}
 REPORT['status']='passed-no-restart-pids-and-dependency-only';REPORT['completed_at']=now();save();print('ALL_APPROVED_REMEDIATION_PASSED '+now(),flush=True)
except Exception as e:
 REPORT['status']='failed-stopped-no-scope-expansion';REPORT['error_type']=type(e).__name__;REPORT['error_summary']='Unexpected drift or operation failure; stop without recreation, restart, secret reads or broader rollback';REPORT['failed_at']=now();save();raise
