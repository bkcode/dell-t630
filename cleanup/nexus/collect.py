#!/usr/bin/env python3
"""Readonly220/221 consolidation inventory. Never reads key/password contents or full Env/Cmd."""
import concurrent.futures,json,sys
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts'));import control
control.BASE+=['-o','ForwardAgent=no']
targets=json.loads((ROOT/'network19/evidence/migrated-access.json').read_text())['targets']
SCRIPT=r'''
import datetime,hashlib,json,os,re,shutil,socket,stat,subprocess
from pathlib import Path
ROLE=ROLE_ID
assert os.geteuid()==0 and socket.gethostname().split('.')[0]=={220:'publish-service',221:'artifact-service'}[ROLE] and not Path('/etc/pve').exists()
ENV={'PATH':'/usr/sbin:/usr/bin:/sbin:/bin','LANG':'C','LC_ALL':'C'}
def run(args,ok=True):
 p=subprocess.run(args,capture_output=True,text=True,env=ENV,timeout=30)
 if ok and p.returncode:raise RuntimeError('readonly command failed; raw output withheld')
 return p

def mount(path):
 p=run(['/usr/bin/findmnt','--json','--mountpoint',path,'--output','TARGET,SOURCE,FSTYPE,UUID'],False)
 if p.returncode:return {'mounted':False}
 v=json.loads(p.stdout);s=os.statvfs(path);return {'mounted':True,**v,'capacity_bytes':s.f_blocks*s.f_frsize,'available_bytes':s.f_bavail*s.f_frsize}

def filemeta(path):
 p=Path(path)
 if not p.exists():return {'exists':False}
 s=p.stat();return {'exists':True,'uid':s.st_uid,'gid':s.st_gid,'mode':oct(stat.S_IMODE(s.st_mode)),'size_bytes':s.st_size,'symlink':p.is_symlink()}

osrelease={}
for line in Path('/etc/os-release').read_text().splitlines():
 if '=' in line:
  k,v=line.split('=',1)
  if k in ['ID','VERSION_ID','PRETTY_NAME']:osrelease[k]=v.strip('"')
mem={line.split(':',1)[0]:int(line.split()[1])*1024 for line in Path('/proc/meminfo').read_text().splitlines() if line.split(':',1)[0] in ['MemTotal','MemAvailable','SwapTotal','SwapFree']}
interfaces=json.loads(run(['/usr/sbin/ip','-j','addr','show']).stdout);nics=[{'name':x['ifname'],'MAC':x.get('address'),'ipv4':[{'ip':a['local'],'prefix':a['prefixlen']} for a in x.get('addr_info',[]) if a['family']=='inet']} for x in interfaces if x['ifname'] not in ['lo','docker0'] and not x['ifname'].startswith(('br-','veth'))]
mountpath='/srv/dell-build' if ROLE==220 else '/srv/nexus'
rootstat=os.statvfs('/')
out={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'vmid':ROLE,'hostname':socket.gethostname(),'OS':osrelease,'arch':run(['/usr/bin/uname','-m']).stdout.strip(),'CPU_count':os.cpu_count(),'memory':mem,'load_average':os.getloadavg(),'physical_interfaces':nics,'root_disk':{'capacity_bytes':rootstat.f_blocks*rootstat.f_frsize,'available_bytes':rootstat.f_bavail*rootstat.f_frsize},'role_data_mount':mount(mountpath),'docker_binary':shutil.which('docker'),'private_key_or_secret_contents_read':False,'mutations':False}
for user in ['ub','publisher','finger']:
 p=run(['/usr/bin/id',user],False)
 if p.returncode==0:out.setdefault('user_groups',{})[user]=p.stdout.strip()
packages={}
for pkg in ['docker-ce','docker-ce-cli','containerd.io','docker-compose-plugin','openjdk-21-jdk-headless']:
 p=run(['/usr/bin/dpkg-query','-W','-f=${db:Status-Abbrev} ${Version}',pkg],False);packages[pkg]=p.stdout.strip() if p.returncode==0 else 'not-installed'
out['packages']=packages
unitprops='--property=FragmentPath,DropInPaths,Type,ActiveState,SubState,UnitFileState,Restart,RequiresMountsFor,BindsTo,MainPID'
out['units']={u:dict(x.split('=',1) for x in run(['/usr/bin/systemctl','show',u,unitprops],False).stdout.splitlines() if '='in x) for u in (['docker.service','dell-nexus.service'] if ROLE==221 else ['docker.service','prometheus-node-exporter.service','dell-guest-health.service'])}
if ROLE==220:
 out['publisher_key_metadata_only']=filemeta('/var/lib/dell-publisher/.ssh/test240_ed25519')
 out['publisher_client']=filemeta('/usr/local/bin/dell-publish')
 if Path('/usr/local/bin/dell-publish').exists():
  raw=Path('/usr/local/bin/dell-publish').read_bytes();out['publisher_client']['sha256']=hashlib.sha256(raw).hexdigest();out['publisher_client_public_literals']={'contains19_45':b'192.168.19.45'in raw,'contains19_31':b'192.168.19.31'in raw,'contains_old10_63':b'10.63.'in raw}
 out['busy_build_process_counts']={}
 ps=run(['/bin/ps','-eo','comm=']).stdout.splitlines()
 for name in ['java','node','gradle','pnpm']:out['busy_build_process_counts'][name]=sum(x.strip()==name for x in ps)
 out['nexus_paths_already_exist']={p:Path(p).exists() for p in ['/opt/dell/nexus','/etc/nexus.env','/srv/nexus','/root/dell-nexus-secrets']}
else:
 out['data_ownership']=filemeta('/srv/nexus/data');out['data_bytes']=int(run(['/usr/bin/du','-sx','-B1','/srv/nexus/data']).stdout.split()[0]);out['docker_storage_bytes']=int(run(['/usr/bin/du','-sx','-B1','/var/lib/docker']).stdout.split()[0])
 out['nexus_secret_metadata_only']={name:filemeta('/root/dell-nexus-secrets/'+name+'-password') for name in ['admin','reader','publisher']}
 out['assignment']=json.loads(Path('/opt/dell/nexus/assignment.json').read_text())
 marker=json.loads(Path('/opt/dell/nexus/fresh-instance.json').read_text());out['fresh_marker_nonsecret']={k:marker[k] for k in ['mode','expected_guest_ip','expected_hostname','data_path','filesystem_uuid','old_h2_or_credentials_imported']}
 env={}
 for line in Path('/etc/nexus.env').read_text().splitlines():
  if '=' in line:
   k,v=line.split('=',1)
   if k in ['NEXUS_DATA_DIR','NEXUS_BIND_ADDRESS']:env[k]=v.strip("'\"")
 out['public_nexus_env_keys']=env
 files=['assignment.json','target_guard.py','manage.py','compose.yaml','compose.mount-gated.yaml','application-import.py','config/nginx.conf']
 out['public_runtime_files']={}
 for rel in files:
  p=Path('/opt/dell/nexus')/rel;raw=p.read_bytes();out['public_runtime_files'][rel]={'sha256':hashlib.sha256(raw).hexdigest(),'uid':p.stat().st_uid,'mode':oct(p.stat().st_mode&0o777)}
 unit=Path('/etc/systemd/system/dell-nexus.service').read_text();out['nexus_unit_public_source']=unit
 for f in ['target_guard.py','manage.py','application-import.py']:
  text=(Path('/opt/dell/nexus')/f).read_text();out['public_runtime_files'][f]['address_hostname_guard_lines']=[line.strip() for line in text.splitlines() if any(x in line for x in ['expected_guest_ip','expected_hostname',"ORIGIN =",'socket.gethostname','DockerRootDir'])]
if shutil.which('docker'):
 D=['/usr/bin/docker','--host','unix:///var/run/docker.sock']
 p=run(D+['info','--format','{"name":{{json .Name}},"version":{{json .ServerVersion}},"driver":{{json .Driver}},"root":{{json .DockerRootDir}},"arch":{{json .Architecture}}}'],False)
 out['docker']=json.loads(p.stdout) if p.returncode==0 else {'running':False}
 if ROLE==221:
  fmt='{"name":{{json .Name}},"id":{{json .Id}},"image_id":{{json .Image}},"image_ref":{{json .Config.Image}},"health":{{if .State.Health}}{{json .State.Health.Status}}{{else}}null{{end}},"running":{{json .State.Running}},"CPU_cap":{{json .HostConfig.NanoCpus}},"memory_cap":{{json .HostConfig.Memory}},"pids_cap":{{json .HostConfig.PidsLimit}},"ports":{{json .NetworkSettings.Ports}}}'
  out['containers']=[json.loads(run(D+['inspect','--format',fmt,name]).stdout) for name in ['nexus-nexus-1','nexus-gateway-1']]
  out['current_container_stats']=run(D+['stats','--no-stream','--format','{"name":{{json .Name}},"memory":{{json .MemUsage}},"CPU":{{json .CPUPerc}},"PIDs":{{json .PIDs}}}','nexus-nexus-1','nexus-gateway-1']).stdout.splitlines()
print(json.dumps(out))
'''
def one(role):
 r=control.guest(role,'sudo python3 -',data=SCRIPT.replace('ROLE_ID',str(role)).encode(),timeout=150,info=targets[str(role)])
 if r['exit_code']:return {'vmid':role,'status':'readonly-inventory-unconfirmed','raw_details_withheld':True}
 return json.loads(r['stdout'])
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:values=list(pool.map(one,[220,221]))
Path(__file__).with_name('live-inventory.json').write_text(json.dumps(values,indent=2)+'\n')
for v in values:print(json.dumps({k:v.get(k) for k in ['vmid','hostname','OS','CPU_count','memory','docker_binary','data_bytes','root_disk','role_data_mount','busy_build_process_counts']},ensure_ascii=False))
