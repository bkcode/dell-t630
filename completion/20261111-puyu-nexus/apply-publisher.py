#!/usr/bin/env python3
"""Git-update only publisher tool and merge scoped artifact settings into its private YAML."""
import json,os,re,sqlite3,subprocess,sys,time
from pathlib import Path
ROOT=Path('/opt/deploy-public');CFG=ROOT/'config.local.yaml';STATE=Path('/root/dell-puyu-nexus-20261111');EXPECTED=sys.argv[1]
assert os.geteuid()==0 and __import__('socket').gethostname()=='publish-service'and STATE.is_dir()
def run(args,**kw):return subprocess.run(list(map(str,args)),capture_output=True,check=True,**kw).stdout.decode().strip()
def user(args,**kw):return run(['runuser','-u','ub','--',*args],**kw)
assert user(['git','-C',ROOT,'branch','--show-current'])=='main'and not user(['git','-C',ROOT,'status','--porcelain'])
oldhead=user(['git','-C',ROOT,'rev-parse','HEAD']);original=CFG.read_bytes();metadata=CFG.stat();assert metadata.st_uid==1000 and metadata.st_mode&0o777==0o600
with sqlite3.connect('file:/srv/dell-build/deploy-public/mcp-state/jobs.sqlite?mode=ro',uri=True)as db:assert all(json.loads(x[0])['status']not in('running','queued')for x in db.execute('SELECT payload FROM jobs'))
nexus_pid=run(['systemctl','show','dell-nexus.service','-p','MainPID','--value']);nav_pid=run(['systemctl','show','dell-service-directory.service','-p','MainPID','--value'])
worker=r'''
import copy,json,os,sys,uuid
from pathlib import Path
sys.path.insert(0,'/opt/deploy-public')
import yaml
from config_loader import load_config
path=Path('/opt/deploy-public/config.local.yaml');beforebytes=path.read_bytes();before=load_config(path);payload=json.load(sys.stdin);assert set(payload)=={'artifacts'}and 'artifacts'not in before.raw
old=copy.deepcopy(before.raw);after=copy.deepcopy(old);after['artifacts']=payload['artifacts'];backup=path.with_name(path.name+'.before-puyu-artifacts-20261111');assert not backup.exists()
fd=os.open(backup,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
with os.fdopen(fd,'wb')as f:f.write(beforebytes)
temp=path.with_name(path.name+'.'+uuid.uuid4().hex);fd=os.open(temp,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
with os.fdopen(fd,'w')as f:yaml.safe_dump(after,f,sort_keys=False,allow_unicode=True)
checked=load_config(temp).require_artifacts();actual=copy.deepcopy(checked.raw);actual.pop('artifacts');assert actual==old
assert checked.mcp==before.mcp and checked.mcp['environment']=='dev'and checked.mcp['jobs']['deploy-services']['enabled']is False
assert path.read_bytes()==beforebytes;os.replace(temp,path);verified=load_config(path).require_artifacts()
print(json.dumps({'artifact_configuration_added':True,'MCP_key_and_all_previous_configuration_values_preserved':True,'configuration_mode':'0600','configuration_owner':'ub','MCP_environment':'dev','business_deploy_enabled':False,'artifact_URLs':verified.artifact_urls(),'credentials_output':False}))
'''
run(['systemctl','stop','puyu-deploy-mcp.service'],timeout=90)
try:
 user(['git','-C',ROOT,'pull','--ff-only','origin','main'],timeout=120);head=user(['git','-C',ROOT,'rev-parse','HEAD']);assert head==EXPECTED
 log=STATE/'Linux-tests.log'
 with log.open('wb')as out:
  log.chmod(0o600);p=subprocess.run(['runuser','-u','ub','--',str(ROOT/'.venv/bin/python'),'-m','unittest','discover','-s','tests','-v'],cwd=ROOT,stdout=out,stderr=subprocess.STDOUT,timeout=180)
 data=log.read_text(errors='replace');match=re.search(r'Ran 75 tests in ([0-9.]+)s',data);assert p.returncode==0 and match and re.search(r'(?m)^OK$',data),'Linux-tests-failed'
 creds={role:{'username':'puyu-'+role,'password':(Path('/root/dell-nexus-secrets')/('puyu-'+role+'-password')).read_text().strip()}for role in ['reader','publisher']}
 artifacts={'base_url':'http://192.168.19.31:8081','read_repository':'puyu-public','publish_repositories':{'dev':'puyu-snapshots','prod':'puyu-releases'},'credentials':creds}
 update=json.loads(user([ROOT/'.venv/bin/python','-I','-B','-c',worker],input=json.dumps({'artifacts':artifacts}).encode(),timeout=40))
 summaries={}
 for action in ['show','check']:
  raw=user([ROOT/'.venv/bin/python',ROOT/'artifact_exec.py',action],cwd=ROOT,timeout=30);assert all(v['password']not in raw for v in creds.values());summaries[action]=json.loads(raw)
 raw=user([ROOT/'.venv/bin/python',ROOT/'artifact_exec.py','exec','--env','dev','--access','reader','--','ls'],cwd=ROOT,timeout=30);assert all(v['password']not in raw for v in creds.values())and'puyu-common-lib'in raw
 assert user(['git','-C',ROOT,'check-ignore','config.local.yaml'])=='config.local.yaml'
 run(['systemctl','start','puyu-deploy-mcp.service'],timeout=45)
 for _ in range(30):
  if run(['systemctl','is-active','puyu-deploy-mcp.service'])=='active'and'127.0.0.1:18765'in run(['ss','-H','-lnt','sport','=',':18765']):break
  time.sleep(0.2)
 else:raise RuntimeError('MCP-start-unconfirmed')
 assert run(['systemctl','show','dell-nexus.service','-p','MainPID','--value'])==nexus_pid and run(['systemctl','show','dell-service-directory.service','-p','MainPID','--value'])==nav_pid
except Exception:
 CFG.write_bytes(original);os.chown(CFG,metadata.st_uid,metadata.st_gid);CFG.chmod(0o600);run(['systemctl','start','puyu-deploy-mcp.service'],timeout=45);raise
result={'status':'publisher-Git-updated-and-scoped-Nexus-YAML-connected','old_source_HEAD':oldhead,'source_HEAD':head,'Linux_tests':75,'Linux_tests_seconds':float(match.group(1)),'Linux_tests_passed':True,'config_update':update,'adapter_offline_checks':summaries,'real_adapter_fixed_build_ls_only_passed':True,'Gradle_or_Java_Go_build_or_publish_executed':False,'private_config_Git_ignored':True,'MCP_active_loopback_only':True,'Nexus_and_navigation_service_PIDs_unchanged':True,'Nexus_restarted':False,'private_credentials_exported_to_Mac_or_logs':False}
p=STATE/'publisher-applied.json';p.write_text(json.dumps(result,indent=2)+'\n');p.chmod(0o600);print(json.dumps(result))
