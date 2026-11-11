#!/usr/bin/env python3
"""One controlled VM250 maintenance: DNS init only, strict guard and bounded failure evidence."""
import copy,hashlib,importlib.util,json,os,socket,subprocess,sys,time,urllib.request
from pathlib import Path
assert os.geteuid()==0 and socket.gethostname()=='penpot-service';os.umask(0o077)
ROOT=Path('/root/dell-penpot-dns-init-fix-20261111');BASE=Path('/opt/dell/penpot');SUP=BASE/'runtime/health-supervision';before=json.loads((ROOT/'before-private.json').read_text());payload=json.load(sys.stdin)
source=payload['supervisor_source'];assert hashlib.sha256(source.encode()).hexdigest()==payload['supervisor_SHA']=='4aeadb7af39ef450ee5cdc940a9d9d2fce1a8be1a2c7b753d46bedca72cdced6';compile(source,'candidate-supervisor','exec')
def run(args,timeout=45):return subprocess.check_output(list(map(str,args)),stderr=subprocess.PIPE,timeout=timeout).decode().strip()
def sha(p):
 with p.open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()
for name,spec in before['files'].items():assert sha(Path(name))==spec['sha256']and Path(name).stat().st_uid==0 and not Path(name).is_symlink(),'reviewed-file-CAS-drift'
assert not(ROOT/'apply-result.json').exists()
assert run(['systemctl','is-active','dell-penpot.service'])=='active'
net=json.loads(run(['docker','inspect','penpot-penpot-worker-1','--format','{{json .NetworkSettings.Networks}}']));ip=next(v['IPAddress']for v in net.values()if v['IPAddress']);o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with o.open('http://'+ip+':4404/readyz',timeout=5)as r:worker=json.loads(r.read(8192))
assert worker['state']=='ready'and worker['activeTasks']==0,'wait-for-idle-worker'
jobdir=Path('/srv/penpot/docker/volumes/penpot_penpot_import_jobs/_data')
for p in jobdir.glob('*.json'):
 if not p.name.endswith('.tmp'):assert json.loads(p.read_text()).get('status')not in['queued','preparing','downloading','importing','unknown']
old_overlay=before['files'][str(SUP/'compose.health-supervision.yaml')]['bytes'];needle='  penpot-dns:\n';assert old_overlay.count(needle)==1;new_overlay=old_overlay.replace(needle,needle+'    init: true\n',1)
old_lock=json.loads(before['files'][str(SUP/'deployment-lock.json')]['bytes']);new_lock=copy.deepcopy(old_lock);assert new_lock['supervision_file_sha256']['supervisor.py']==before['files'][str(SUP/'supervisor.py')]['sha256'];assert 'deployment-lock.json'not in new_lock['supervision_file_sha256']
new_lock['services']['penpot-dns']['require_init']=True;new_lock['supervision_file_sha256']['supervisor.py']=payload['supervisor_SHA'];new_lock['supervision_file_sha256']['compose.health-supervision.yaml']=hashlib.sha256(new_overlay.encode()).hexdigest()
changes={str(SUP/'supervisor.py'):source,str(SUP/'compose.health-supervision.yaml'):new_overlay,str(SUP/'deployment-lock.json'):json.dumps(new_lock,indent=2)+'\n'}
compose=['docker','compose','--project-directory',str(BASE),'--env-file','/etc/penpot/.env','-f',str(BASE/'compose.fresh.yaml'),'-f',str(SUP/'compose.health-supervision.yaml')]
run(['systemctl','stop','dell-penpot.service'],timeout=240)
# is-active returns3 when inactive; collect directly without treating expected state as command failure.
assert subprocess.run(['systemctl','is-active','dell-penpot.service'],capture_output=True,text=True).stdout.strip()=='inactive'
assert not run(['docker','ps','-q','--filter','label=com.docker.compose.project=penpot'])
try:
 for name,text in changes.items():
  p=Path(name);p.write_text(text);p.chmod(before['files'][name]['mode'])
 rendered=json.loads(run(compose+['config','--format','json']));expected_render=copy.deepcopy(before['render']);expected_render['services']['penpot-dns']['init']=True;assert rendered==expected_render,'only-DNS-init-may-change-in-compose'
 run(['python3','-I','-B',SUP/'supervisor.py','check'],timeout=120)
 run(['systemctl','start','--no-block','dell-penpot.service'])
 deadline=time.monotonic()+600;containers={}
 while time.monotonic()<deadline:
  unit=run(['systemctl','show','dell-penpot.service','-p','ActiveState','-p','SubState']);ids=run(['docker','ps','-aq','--filter','label=com.docker.compose.project=penpot']).split()
  rows=json.loads(run(['docker','inspect',*ids]))if ids else[]
  if len(rows)==11 and all(v['State']['Running']and v['State'].get('Health',{}).get('Status')=='healthy'for v in rows)and'ActiveState=active\n'in unit+'\n'and'SubState=running'in unit:
   containers={v['Name'].lstrip('/'):v for v in rows};break
  time.sleep(2)
 else:raise RuntimeError('supervised-readiness-timeout')
 for name,old in before['containers'].items():
  actual=containers[name];assert actual['Image']==old['image']and actual['Config']['User']==old['user']and actual['Config']['Cmd']==old['command']and actual['Mounts']==old['mounts']and sorted(actual['NetworkSettings']['Networks'])==old['networks']
  for key,value in old['hostconfig'].items():
   if key!='Init':assert actual['HostConfig'].get(key)==value,'resource-or-security-contract-drift'
  if name=='penpot-penpot-dns-1':assert actual['HostConfig'].get('Init')is True and actual['Id']!=old['id']
  else:assert actual['Id']==old['id']and actual['HostConfig'].get('Init')==old['hostconfig']['Init'],'other-container-recreated'
 assert run(['git','--no-optional-locks','-C',BASE/'source','rev-parse','HEAD'])==before['Git']['HEAD']and not run(['git','--no-optional-locks','-C',BASE/'source','status','--porcelain'])
 assert all(sha(Path(p))==digest for p,digest in before['identity_hashes'].items())
except Exception:
 subprocess.run(['systemctl','stop','dell-penpot.service'],capture_output=True,timeout=240)
 for name,spec in before['files'].items():p=Path(name);p.write_text(spec['bytes']);p.chmod(spec['mode'])
 subprocess.run(['systemctl','start','--no-block','dell-penpot.service'],capture_output=True)
 p=ROOT/'rollback-status.json';p.write_text(json.dumps({'status':'candidate-failed-original-files-restored-start-requested','design_or_credentials_modified':False}));p.chmod(0o600);raise
value={'status':'DNS-init-and-strict-supervision-failure-evidence-applied','DNS_only_container_recreated':True,'other_ten_container_IDs_preserved':True,'all_eleven_running_healthy':True,'DNS_Init':True,'DNS_PID_limit':containers['penpot-penpot-dns-1']['HostConfig']['PidsLimit'],'images_users_commands_mounts_networks_caps_readonly_resources_restart_policies_preserved':True,'Git_HEAD':before['Git']['HEAD'],'Git_clean':True,'identity_credentials_and_base_systemd_unit_preserved':True,'supervisor_public_SHA256':payload['supervisor_SHA'],'new_NRestarts_baseline':run(['systemctl','show','dell-penpot.service','-p','NRestarts','--value']),'no_pulls_builds_design_writes_volume_deletes_or_data_migration':True,'private_snapshot_retained_VM250_only':True}
assert sha(Path('/etc/systemd/system/dell-penpot.service'))==before['unit_source_sha256']
p=ROOT/'apply-result.json';p.write_text(json.dumps(value,indent=2)+'\n');p.chmod(0o600);print(json.dumps(value))
