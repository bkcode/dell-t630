#!/usr/bin/env python3
"""Update tool defaults via Git and change only private artifact repository mapping, not passwords."""
import json,os,re,sqlite3,subprocess,sys,time
from pathlib import Path
assert os.geteuid()==0 and __import__('socket').gethostname()=='publish-service'
ROOT=Path('/opt/deploy-public');CFG=ROOT/'config.local.yaml';STATE=Path('/root/dell-nexus-local-config-keep-extra-20261111');EXPECTED=sys.argv[1]
assert json.loads((STATE/'result.json').read_text())['repository_or_artifact_DELETE_calls']==0

def run(args,**kwargs):return subprocess.run(list(map(str,args)),check=True,capture_output=True,**kwargs).stdout.decode().strip()
def user(args,**kwargs):return run(['runuser','-u','ub','--',*args],**kwargs)
assert user(['git','-C',ROOT,'branch','--show-current'])=='main'and not user(['git','-C',ROOT,'status','--porcelain'])
oldhead=user(['git','-C',ROOT,'rev-parse','HEAD']);original=CFG.read_bytes();meta=CFG.stat();assert meta.st_uid==1000 and meta.st_mode&0o777==0o600
with sqlite3.connect('file:/srv/dell-build/deploy-public/mcp-state/jobs.sqlite?mode=ro',uri=True)as db:assert all(json.loads(x[0])['status']not in('running','queued')for x in db.execute('SELECT payload FROM jobs'))
pids={u:run(['systemctl','show',u,'-p','MainPID','--value'])for u in ['dell-nexus.service','dell-service-directory.service']}
worker=r'''
import copy,json,os,subprocess,sys,uuid
from pathlib import Path
sys.path.insert(0,'/opt/deploy-public')
import yaml
from config_loader import load_config
path=Path('/opt/deploy-public/config.local.yaml');beforebytes=path.read_bytes();before=load_config(path);before.require_artifacts();after=copy.deepcopy(before.raw)
after['artifacts']['read_repository']='maven-public';after['artifacts']['publish_repositories']={'dev':'imnull-snapshots','prod':'imnull-releases'}
old_unchanged=copy.deepcopy(before.raw);new_unchanged=copy.deepcopy(after)
for value in [old_unchanged,new_unchanged]:
 value['artifacts'].pop('read_repository');value['artifacts'].pop('publish_repositories')
assert old_unchanged==new_unchanged
backup=path.with_name(path.name+'.before-local-repository-alignment-20261111');assert not backup.exists()
fd=os.open(backup,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
with os.fdopen(fd,'wb')as f:f.write(beforebytes)
tmp=path.with_name(path.name+'.'+uuid.uuid4().hex);fd=os.open(tmp,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
with os.fdopen(fd,'w')as f:yaml.safe_dump(after,f,sort_keys=False,allow_unicode=True)
verified=load_config(tmp).require_artifacts();assert verified.artifacts['credentials']==before.artifacts['credentials']and verified.mcp==before.mcp and verified.targets==before.targets and verified.paths==before.paths
assert verified.mcp['environment']=='dev'and verified.mcp['jobs']['deploy-services']['enabled']is False
assert path.read_bytes()==beforebytes;os.replace(tmp,path);final=load_config(path).require_artifacts();passwords=[x['password']for x in final.artifacts['credentials'].values()]
summary={}
for action in ['show','check']:
 p=subprocess.run([sys.executable,'/opt/deploy-public/artifact_exec.py',action],capture_output=True,text=True,check=True,timeout=30);assert all(s not in p.stdout+p.stderr for s in passwords);summary[action]=json.loads(p.stdout)
p=subprocess.run([sys.executable,'/opt/deploy-public/artifact_exec.py','exec','--env','dev','--access','reader','--','ls'],capture_output=True,text=True,check=True,timeout=30);assert all(s not in p.stdout+p.stderr for s in passwords)and'puyu-common-lib'in p.stdout
print(json.dumps({'private_repository_mapping':final.artifact_urls(),'only_read_and_publish_repository_names_changed':True,'passwords_MCP_key_and_all_other_configuration_preserved':True,'private_YAML_owner':'ub','private_YAML_mode':'0600','private_YAML_ignored':subprocess.run(['git','-C','/opt/deploy-public','check-ignore','-q','config.local.yaml']).returncode==0,'offline_adapter':summary,'fixed_build_script_ls_only_passed':True,'Gradle_or_Java_Go_build_or_publish_executed':False,'credential_values_output':False}))
'''
run(['systemctl','stop','puyu-deploy-mcp.service'],timeout=90)
try:
 user(['git','-C',ROOT,'pull','--ff-only','origin','main'],timeout=120);head=user(['git','-C',ROOT,'rev-parse','HEAD']);assert head==EXPECTED
 log=STATE/'Linux-tests.log'
 with log.open('wb')as stream:
  log.chmod(0o600);p=subprocess.run(['runuser','-u','ub','--',str(ROOT/'.venv/bin/python'),'-m','unittest','discover','-s','tests','-v'],cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT,timeout=180)
 text=log.read_text(errors='replace');match=re.search(r'Ran 75 tests in ([0-9.]+)s',text);assert p.returncode==0 and match and re.search(r'(?m)^OK$',text)
 update=json.loads(user([ROOT/'.venv/bin/python','-I','-B','-c',worker],timeout=60))
 run(['systemctl','start','puyu-deploy-mcp.service'],timeout=45)
 for _ in range(30):
  state=subprocess.run(['systemctl','is-active','puyu-deploy-mcp.service'],capture_output=True,text=True).stdout.strip()
  if state=='active'and'127.0.0.1:18765'in run(['ss','-H','-lnt','sport','=',':18765']):break
  time.sleep(.2)
 else:raise RuntimeError('MCP-start-unconfirmed')
 assert all(run(['systemctl','show',u,'-p','MainPID','--value'])==v for u,v in pids.items())
except Exception:
 CFG.write_bytes(original);os.chown(CFG,meta.st_uid,meta.st_gid);CFG.chmod(0o600);run(['systemctl','start','puyu-deploy-mcp.service'],timeout=45);raise
result={'status':'publisher-local-repository-mapping-updated','old_source_HEAD':oldhead,'source_HEAD':head,'Linux_tests':75,'Linux_tests_seconds':float(match.group(1)),'Linux_tests_passed':True,'configuration_update':update,'MCP_active_loopback_only':True,'MCP_only_dev_and_business_deploy_disabled':True,'Nexus_and_navigation_service_PIDs_preserved':True,'repository_or_artifact_delete_performed':False,'historical_data_imported':False}
p=STATE/'publisher-result.json';p.write_text(json.dumps(result,indent=2)+'\n');p.chmod(0o600);print(json.dumps(result))
