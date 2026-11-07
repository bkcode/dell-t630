#!/usr/bin/env python3
"""No guest writes/API mutations: filtered current core config and installed code metadata."""
import concurrent.futures,datetime,hashlib,json,shlex,sys,base64
from pathlib import Path
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];sys.path.insert(0,str(ROOT/'scripts'));import control
if (HERE/'inventory.json').exists():raise SystemExit('Initial snapshot already exists; preserve old evidence and request a separately versioned collection')
GUEST=r'''import sys
sys.dont_write_bytecode=True
import os,json,socket,subprocess,re,hashlib,base64
from pathlib import Path
spec=json.loads(sys.stdin.read());vmid=spec['vmid'];role=spec['role'];old=spec['old_ip']
if os.geteuid()!=0 or Path('/etc/pve').exists() or socket.gethostname().split('.')[0]!=role:raise SystemExit('assigned guest only')
def run(a):
 p=subprocess.run(a,capture_output=True,text=True,timeout=30)
 if p.returncode:raise RuntimeError('readonly command failed; values withheld')
 return p.stdout
ips=[a.get('local') for n in json.loads(run(['ip','-j','addr'])) for a in n.get('addr_info',[]) if a.get('family')=='inet']
if old not in ips:raise SystemExit('assigned old address absent; stop inventory')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def env(p):
 x={}
 if p.exists():
  for line in p.read_text().splitlines():
   if line and not line.startswith('#') and '=' in line:
    k,v=line.split('=',1);x[k]=v.strip().strip("'\"")
 return x
result={'vmid':vmid,'hostname':role,'IP_addresses':ips,'files':{},'public_sources':{},'env_safe':{},'selected_JSON':{},'units':{},'no_mutations':True,'secret_values_returned':False}
public=[];paths=[]
if vmid in [200,201,210]:
 data_role={200:'prod-db',201:'prod-infra',210:'test-data'}[vmid];bundle=Path('/opt/dell/data')/data_role;paths+=[bundle/'.env',bundle/'compose.yaml',bundle/'scripts/manage.py',bundle/'scripts/acceptance.py',bundle/'config/rabbitmq.conf']
 values=env(bundle/'.env');safe={'ROLE','ENVIRONMENT','SERVICE_IP','INSTALL_DIR','DATA_MOUNTPOINT','DATA_ROOT','DATA_FS_UUID','MYSQL_HOST','MYSQL_PORT','NACOS_MYSQL_HOST','NACOS_DB_NAME','NACOS_DB_USER','NACOS_CLIENT_USER','NACOS_CLIENT_ROLE','NACOS_GROUP','RABBIT_VHOST'}
 result['env_safe']={k:v for k,v in values.items() if k in safe};result['env_key_names']=sorted(values)
 if 'NACOS_NAMESPACE_ID' in values:result['namespace_preservation_sha256']=hashlib.sha256(values['NACOS_NAMESPACE_ID'].encode()).hexdigest()
 public+=[bundle/'scripts/manage.py',bundle/'scripts/acceptance.py',bundle/'compose.yaml']
if vmid==220:
 public+=[Path('/usr/local/bin/dell-publish')];paths+=public+[Path('/etc/dell-publisher/client-test240.json')]
 p=Path('/etc/dell-publisher/client-test240.json')
 if p.exists():result['selected_JSON'][str(p)]={k:v for k,v in json.loads(p.read_text()).items() if k in ['target_host','target_user','host_key_alias','source_ip']}
 for p in [Path('/var/lib/dell-publisher/.ssh/test240_ed25519'),Path('/etc/dell-publisher/known_hosts')]:
  if p.exists():s=p.stat();result['files'][str(p)]={'exists':True,'uid':s.st_uid,'mode':oct(s.st_mode&0o777),'contents_not_read':True}
if vmid==240:
 public+=[Path('/usr/local/libexec/dell-publish-test240'),Path('/usr/local/libexec/dell-publisher-dispatch'),Path('/usr/local/libexec/dell-publisher/publisher_protocol.py'),Path('/usr/local/libexec/dell/deploy-test-chain.py')]
 paths+=public+[Path('/etc/dell-publisher/test240-policy.json'),Path('/root/dell-java-test-readiness.json')]
 for p in [Path('/etc/dell-publisher/test240-policy.json'),Path('/root/dell-java-test-readiness.json')]:
  if p.exists():
   x=json.loads(p.read_text());allowed={'target_hostname','target_ip','baseline_migrated','fixed_deployer_sha256','database_schemas_ready','nacos_configs_ready','network_policy_ready','issuer_candidate_acknowledged'}
   result['selected_JSON'][str(p)]={k:v for k,v in x.items() if k in allowed};result['selected_JSON_keys']={**result.get('selected_JSON_keys',{}),str(p):sorted(x)}
 current=Path('/opt/finger/current-test');result['current_release']=str(current.resolve()) if current.is_symlink() else None
 result['managed_release_ids']=[p.name for p in Path('/opt/finger/releases/test').iterdir() if p.is_dir()] if Path('/opt/finger/releases/test').exists() else []
 if current.is_symlink():
  manifest=json.loads((current/'manifest.json').read_text());result['release_manifest']={k:v for k,v in manifest.items() if k in ['schema_version','release_id','target_hostname','target_ip','data_ip','profile','issuer','services']}
  result['release_files']={}
  for name in ['finger-gateway-mobile','finger-auth','finger-service-system','finger-service-coms','finger-bff-system']:
   folder=current/name
   for n in ['application.yaml','app.jar','unit.service']:
    p=folder/n;s=p.stat();result['release_files'][str(p)]={'sha256':sha(p),'uid':s.st_uid,'gid':s.st_gid,'mode':oct(s.st_mode&0o777)}
   try:
    import yaml
    y=yaml.safe_load((folder/'application.yaml').read_text());sp=y.get('spring',{});nacos=sp.get('cloud',{}).get('nacos',{});row={'server':{k:v for k,v in y.get('server',{}).items() if k in ['address','port']},'application_name':sp.get('application',{}).get('name'),'profile':sp.get('profiles',{}).get('active'),'imports':sp.get('config',{}).get('import'),'Nacos_server':nacos.get('server-addr'),'Nacos_discovery_ip':nacos.get('discovery',{}).get('ip'),'datasource_url':sp.get('datasource',{}).get('url'),'datasource_username':sp.get('datasource',{}).get('username'),'issuer':y.get('finger',{}).get('auth',{}).get('bootstrap',{}).get('issuer'),'COMS_upload':{k:v for k,v in y.get('file',{}).get('upload',{}).items() if k in ['domain','path']},'redis_host':sp.get('data',{}).get('redis',{}).get('host'),'rabbit_host':sp.get('rabbitmq',{}).get('host'),'rabbit_vhost':sp.get('rabbitmq',{}).get('virtual-host')}
    result.setdefault('application_safe',{})[name]=row
   except ImportError:result['YAML_parser_available']=False
 for p in [Path('/etc/ssh/sshd_config.d/60-dell-publisher.conf'),Path('/etc/sudoers.d/dell-publisher'),Path('/etc/ssh/authorized_keys/deployer')]:
  paths.append(p)
  if p.exists():
   text=p.read_text();result.setdefault('SSH_contract',{})[str(p)]={'ip_literals':sorted(set(re.findall(r'(?<![0-9])(?:[0-9]{1,3}\.){3}[0-9]{1,3}(?![0-9])',text))),'forced_command_present':'dell-publisher-dispatch' in text,'private_key_not_read':True}
if vmid==270:
 bundle=Path('/opt/dell/ops');values=env(bundle/'.env');result['env_safe']={k:v for k,v in values.items() if k in ['ROLE','SERVICE_IP','INSTALL_DIR','DATA_MOUNTPOINT','DATA_ROOT','DATA_FS_UUID']};result['env_key_names']=sorted(values)
 paths += [bundle/'.env',bundle/'compose.yaml',bundle/'scripts/manage.py',bundle/'config/prometheus/prometheus.yml',bundle/'config/alertmanager/alertmanager.yml',bundle/'lark-notify-state.json',Path('/etc/dell-lark-notify/policy.json'),Path('/etc/systemd/system/dell-lark-notify.service')]
 public += [bundle/'scripts/manage.py',Path('/usr/local/libexec/dell-lark-notify/bridge.py'),Path('/usr/local/libexec/dell-lark-notify/configuration.py')]
 for p in (bundle/'config/prometheus/targets').glob('*.json'):
  paths.append(p);result['selected_JSON'][str(p)]=json.loads(p.read_text())
 for p in [bundle/'lark-notify-state.json',Path('/etc/dell-lark-notify/policy.json')]:
  if p.exists():x=json.loads(p.read_text());result['selected_JSON'][str(p)]={k:v for k,v in x.items() if k in ['mode','schema_version','active','bind','port','allowed_source','source_ip']};result.setdefault('JSON_key_names',{})[str(p)]=sorted(x)
 for p in [Path('/usr/local/libexec/dell-lark-notify/bridge.py'),Path('/usr/local/libexec/dell-lark-notify/configuration.py')]:paths.append(p)
 # Whitelist selected no-secret AM routing config scalars; never return auth/secret fields.
 p=bundle/'config/alertmanager/alertmanager.yml'
 if p.exists():
  text=p.read_text();result['AM_no_send_metadata']={'sha256':sha(p),'bridge_URL_present':'http://172.18.0.1:19093/v1/alertmanager' in text,'outbound_config_not_called':True}
for p in [Path('/etc/dell-guest-monitoring/health.json'),Path('/opt/dell/guest-monitoring/collect-guest-health.py'),Path('/etc/systemd/system/prometheus-node-exporter.service.d/10-private-only.conf')]:
 paths.append(p)
 if p.name=='health.json' and p.exists():
  x=json.loads(p.read_text());result['selected_JSON'][str(p)]={k:v for k,v in x.items() if k in ['role','ip','private_ip','expected_ip','services','http','checks','listen_address','urls']};result.setdefault('JSON_key_names',{})[str(p)]=sorted(x)
for p in dict.fromkeys(paths):
 if p.is_file():
  s=p.stat();result['files'][str(p)]={'exists':True,'sha256':sha(p),'uid':s.st_uid,'gid':s.st_gid,'mode':oct(s.st_mode&0o777),'IP_literals':sorted(set(re.findall(r'(?<![0-9])(?:[0-9]{1,3}\.){3}[0-9]{1,3}(?![0-9])',p.read_text(errors='replace')))) if p.suffix not in ('.jar',) else []}
 else:result['files'][str(p)]={'exists':False}
for p in dict.fromkeys(public):
 if p.is_file():result['public_sources'][str(p)]=base64.b64encode(p.read_bytes()).decode()
units=['prometheus-node-exporter.service','dell-guest-health.service']
if vmid in [230,231,232,240]:units+=['dell-finger-'+n+'.service' for n in ['finger-gateway-mobile','finger-auth','finger-service-system','finger-service-coms','finger-bff-system']]
if vmid==270:units+=['dell-ops.service','dell-lark-notify.service']
for name in units:
 p=subprocess.run(['systemctl','show',name,'--property=LoadState,ActiveState,SubState,LoadCredential,FragmentPath'],capture_output=True,text=True,timeout=15);result['units'][name]=dict(l.split('=',1) for l in p.stdout.splitlines() if '=' in l)
print(json.dumps(result))
'''
def collect(role,access):
 vmid=role['vmid'];payload=json.dumps(role).encode();r=control.guest(vmid,'sudo -n python3 -I -B -c '+shlex.quote(GUEST),data=payload,timeout=150,info=access['target'])
 if r['exit_code']:return {'vmid':vmid,'status':'read-failed','error':'details-withheld'}
 value=json.loads(r['stdout']);folder=HERE/'baselines'/('vm'+str(vmid));folder.mkdir(parents=True,exist_ok=True)
 sources=value.pop('public_sources',{})
 for index,(path,encoded) in enumerate(sources.items()):
  p=folder/(str(index)+'-'+Path(path).name);p.write_bytes(base64.b64decode(encoded));value['files'].setdefault(path,{})['captured_public_source']=str(p.relative_to(HERE))
 return value

def main():
 contract=json.loads((HERE/'contract.json').read_text());access={r['target']['vmid']:r for r in json.loads((ROOT/'evidence/implementation/private-guest-access.json').read_text())['roles']};roles=contract['roles']
 with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:results=list(pool.map(lambda r:collect(r,access[r['vmid']]),roles))
 out={'collected_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'current installed runtime only; no PVE/OW/mutations/notifications','roles':results};(HERE/'inventory.json').write_text(json.dumps(out,indent=2)+'\n')
 for r in results:print(json.dumps({'vmid':r['vmid'],'hostname':r.get('hostname'),'status':r.get('status','collected'),'files':len(r.get('files',{})),'active_release':r.get('current_release')}))
if __name__=='__main__':main()
