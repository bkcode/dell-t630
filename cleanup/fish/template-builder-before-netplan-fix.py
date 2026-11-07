#!/usr/bin/env python3
"""Exact root-created builder only; check is read-only, install/seal require phase window."""
import argparse,contextlib,datetime,glob,hashlib,importlib.util,io,json,os,pwd,re,socket,stat,subprocess,sys
from pathlib import Path
sys.dont_write_bytecode=True
ROLES={9040:(9010,'fish-build-linux','192.168.19.197'),9041:(9001,'fish-build-docker','192.168.19.198'),9042:(9011,'fish-build-java','192.168.19.199')}
VERSION='4.0.2-1'
class Refused(RuntimeError):pass

def require(value,reason):
 if not value:raise Refused(reason)
def run(args,check=True):
 p=subprocess.run(args,capture_output=True,text=True,timeout=90)
 if check:require(p.returncode==0,'fixed-command-failed-'+Path(args[0]).name)
 return p
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def secure(path):
 p=Path(path);s=p.lstat();require(stat.S_ISREG(s.st_mode) and s.st_uid==0 and stat.S_IMODE(s.st_mode)==0o600,'root600-regular-file-required');return p

def validate_contract(c):
 require(c.get('schema_version')==1 and c.get('vmid') in ROLES,'explicit-builder-only')
 source,name,ip=ROLES[c['vmid']]
 require((c.get('source_template'),c.get('hostname'),c.get('ip'))==(source,name,ip),'exact-template-hostname-IP-required')
 require(bool(re.fullmatch(r'bc:24:11:(?:[0-9a-f]{2}:){2}[0-9a-f]{2}',c.get('mac',''))),'root-assigned-PVE-MAC-required')
 require(c.get('fish_version')==VERSION and c.get('no_chsh') is True,'install-only-version-contract')
 return c

def guard(c):
 require(os.geteuid()==0 and not Path('/etc/pve').exists(),'root-guest-only')
 require(socket.gethostname().split('.')[0]==c['hostname'],'exact-builder-hostname')
 osrelease=Path('/etc/os-release').read_text();require(bool(re.search(r'^ID=debian$',osrelease,re.M)) and bool(re.search(r'^VERSION_ID="?13"?$',osrelease,re.M)),'Debian13-only')
 require(run(['uname','-m']).stdout.strip()=='x86_64','AMD64-only')
 links=json.loads(run(['ip','-j','addr']).stdout);real=[x for x in links if x['ifname']!='lo' and x.get('link_type')=='ether' and not x['ifname'].startswith(('docker','br-','veth'))]
 require(len(real)==1 and real[0].get('address','').lower()==c['mac'],'exact-primary-MAC-only')
 ipv4=[a.get('local')+'/'+str(a.get('prefixlen')) for a in real[0].get('addr_info',[]) if a.get('family')=='inet']
 require(ipv4==[c['ip']+'/24'],'exact-primary-IP24-only')
 require(os.cpu_count()==2 and 1536*1024<=int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemTotal:')))<=2200*1024,'2CPU-2GiB-builder-only')
 cloud=run(['cloud-init','status','--format=json']);cloud=json.loads(cloud.stdout);require(cloud.get('status')=='done' and not cloud.get('errors'),'cloudinit-done-required')
 forbidden=['/opt/finger','/etc/nacos','/var/lib/mysql','/opt/dell/ops','/etc/penpot','/etc/nexus.env','/var/lib/dell-gateway19','/var/lib/dell-publisher']
 require(not any(Path(x).exists() for x in forbidden),'business-role-state-present')
 for home in [Path('/root'),Path('/home/ub')]:
  require(not any((home/'.ssh').glob('id_*')),'unexpected-client-key-material-stop-root-review')
 require(not Path('/root/.docker/config.json').exists(),'Docker-client-config-stop-root-review')
 return real[0]['ifname']

def window(c,phase,path):
 w=json.loads(secure(path).read_text());require(w.get('vmid')==c['vmid'] and w.get('allowed_phase')==phase and w.get('contract_sha256')==hashlib.sha256(json.dumps(c,sort_keys=True,separators=(',',':')).encode()).hexdigest(),'exact-phase-window-required')
 expiry=datetime.datetime.fromisoformat(w['expires_at']);require(expiry.tzinfo is not None and datetime.datetime.now(datetime.timezone.utc)<expiry,'window-expired')

def docker_baseline():
 prefix=['docker','--host','unix:///var/run/docker.sock'];info=json.loads(run(prefix+['info','--format','{{json .}}']).stdout)
 require(info['DockerRootDir']=='/var/lib/docker' and info['Driver']=='overlay2' and not info.get('LiveRestoreEnabled'),'classic-root-Docker-profile-required')
 require(info['Containers']==0 and not run(prefix+['ps','-aq']).stdout.strip(),'zero-containers-required')
 require(not run(prefix+['volume','ls','-q']).stdout.strip(),'zero-volumes-required')
 require(not run(prefix+['image','ls','-q']).stdout.strip(),'zero-images-required-no-unreviewed-cache-purge')
 require(sorted(run(prefix+['network','ls','--format','{{.Name}}']).stdout.split())==['bridge','host','none'],'default-networks-only')
 require(info.get('Swarm',{}).get('LocalNodeState')=='inactive','no-swarm-state')
 root=Path('/var/lib/docker');require(not root.is_symlink() and root.resolve()==root,'Docker-root-no-symlink')
 engine=root/'engine-id';require(engine.is_file() and not engine.is_symlink() and engine.read_text()==info['ID'],'observed-engine-id-equals-Docker-ID')
 require(not Path('/etc/docker/key.json').exists(),'unexpected-legacy-engine-key-stop-review')
 mount=json.loads(run(['findmnt','--json','--list','--output','TARGET']).stdout)
 require(not any(x['target'].startswith('/var/lib/docker/') for x in mount.get('filesystems',[])),'no-Docker-submounts')
 daemon=Path('/etc/docker/daemon.json');settings=json.loads(daemon.read_text());require(settings.get('features',{}).get('containerd-snapshotter') is False and settings.get('live-restore') is False,'explicit-classic-config-required')
 return {'engine_id_sha256':hashlib.sha256(info['ID'].encode()).hexdigest(),'daemon_sha256':sha(daemon),'version':info['ServerVersion'],'zero_containers_volumes_images':True,'default_networks_only':True}

def protected(c):
 result={'shells':{n:pwd.getpwnam(n).pw_shell for n in ['root','ub']},'files':{}}
 if c['vmid']==9041:result['docker']=docker_baseline();result['files']['/etc/docker/daemon.json']=sha('/etc/docker/daemon.json')
 if c['vmid']==9042:
  verify='/usr/local/libexec/dell-java-acceptance/verify.py';u=pwd.getpwnam('java');require(u.pw_uid==999 and u.pw_shell in ('/usr/sbin/nologin','/bin/false'),'java999-nonlogin-required')
  smoke=json.loads(run(['runuser','--user','java','--','python3',verify,'--smoke']).stdout);require(smoke['status']=='java21-clean-nonroot-acceptance-passed','Java21-smoke-required')
  result['java']={'uid':u.pw_uid,'gid':u.pw_gid,'shell':u.pw_shell,'home':u.pw_dir,'java_realpath':str(Path('/usr/bin/java').resolve()),'javac_realpath':str(Path('/usr/bin/javac').resolve())};result['files'][verify]=sha(verify)
 return result

def check_preserved(before,c):
 require(before['shells']=={n:pwd.getpwnam(n).pw_shell for n in ['root','ub']},'login-shells-changed')
 require(all(sha(p)==s for p,s in before['files'].items()),'protected-file-SHA-changed')
 if c['vmid']==9042:
  u=pwd.getpwnam('java');require(before['java']=={'uid':u.pw_uid,'gid':u.pw_gid,'shell':u.pw_shell,'home':u.pw_dir,'java_realpath':str(Path('/usr/bin/java').resolve()),'javac_realpath':str(Path('/usr/bin/javac').resolve())},'Java-identity-or-JDK-changed')

def seal(c,before):
 # All fallible hygiene/precondition checks precede first stop/identity deletion.
 check_preserved(before,c)
 for name in ['fish','fish-common']:require(run(['dpkg-query','-W','-f=${Version}',name]).stdout==VERSION,'exact-fish-installed-required')
 helptext=run(['cloud-init','clean','--help']).stdout;require(all(x in helptext for x in ['--logs','--machine-id','--seed','--configs','network']),'cloudinit-clean-options-required')
 network=[]
 for folder in ['/etc/netplan','/etc/systemd/network','/etc/network/interfaces.d']:
  for p in Path(folder).glob('*'):
   if p.is_file() and c['ip'] in p.read_text(errors='replace'):
    # Only actual cloud-init-generated networking; arbitrary static files are never deleted.
    content=p.read_text(errors='replace');require('cloud-init' in content.lower() and ('generated' in content.lower() or p.name=='10-cloud-init-eth0.network'),'unexpected-static-network-stop-review');network.append(p)
 if c['vmid']==9041:
  now=docker_baseline();require(now==before['docker'],'Docker-baseline-changed-before-seal')
  run(['systemctl','stop','docker.socket','docker.service','containerd.service'])
  for unit in ['docker.socket','docker.service','containerd.service']:require(run(['systemctl','is-active','--quiet',unit],False).returncode!=0,'Docker-stop-not-confirmed')
  # Never recursively remove Docker/containerd data. Default network DB is empty of workloads.
  for p in [Path('/var/lib/docker/engine-id'),Path('/var/lib/docker/network/files/local-kv.db')]:
   if p.exists():require(p.is_file() and not p.is_symlink(),'unexpected-Docker-identity-object');p.unlink()
  require(sha('/etc/docker/daemon.json')==before['files']['/etc/docker/daemon.json'],'daemon-config-changed')
 identity=Path('/etc/cloud/cloud.cfg.d/91-fish-template-identity.cfg');identity.write_text('ssh_deletekeys: true\nssh_genkeytypes: [ed25519, rsa]\nssh_pwauth: false\npreserve_hostname: false\n');identity.chmod(0o644)
 run(['cloud-init','clean','--logs','--machine-id','--seed','--configs','network'])
 for p in network:
  if p.exists():p.unlink()
 Path('/etc/hostname').write_text('localhost\n');hosts=Path('/etc/hosts')
 if hosts.exists():hosts.write_text('\n'.join(line.replace(c['hostname'],'localhost') for line in hosts.read_text().splitlines() if c['ip'] not in line)+'\n')
 for pat in ['/etc/ssh/ssh_host_*','/var/lib/dhcp/*.leases','/var/lib/dhcp/*.leases~','/var/lib/NetworkManager/*.lease']:
  for raw in glob.glob(pat):
   p=Path(raw);require(not p.is_dir(),'unexpected-hygiene-object');p.unlink()
 for home in [Path('/root'),Path('/home/ub')]:
  for relative in ['.ssh/authorized_keys','.bash_history','.zsh_history','.python_history']:
   p=home/relative
   if p.exists() or p.is_symlink():require(not p.is_dir(),'unexpected-hygiene-object');p.unlink()
 dbus=Path('/var/lib/dbus/machine-id')
 if dbus.exists() and not dbus.is_symlink():dbus.unlink();dbus.symlink_to('/etc/machine-id')
 require(Path('/etc/machine-id').read_text().strip() in ('','uninitialized'),'machine-id-not-reset')
 require(not list(Path('/etc/ssh').glob('ssh_host_*')),'hostkeys-remain')
 for folder in ['/var/lib/cloud/seed','/var/lib/cloud/instances']:
  require(not Path(folder).exists() or not any(Path(folder).iterdir()),'cloudinit-instance-remains')
 require(not any(c['ip'] in p.read_text(errors='replace') for folder in ['/etc/netplan','/etc/systemd/network','/etc/network/interfaces.d'] for p in Path(folder).glob('*') if p.is_file()),'stale-IP-remains')
 check_preserved(before,c);run(['apt-get','clean']);run(['sync'])
 return {'sealed':True,'runtime_network_left_until_root_shutdown':True,'next_clone_generic_userdata_required':True,'machine_id_reset':True,'hostkeys_authorized_keys_instances_removed':True,'Docker_engine_id_reset':c['vmid']==9041,'no_power_or_PVE_action':True}

def main():
 p=argparse.ArgumentParser();p.add_argument('--contract',required=True);p.add_argument('--phase',choices=['check','install','seal'],required=True);p.add_argument('--window');a=p.parse_args()
 c=validate_contract(json.loads(secure(a.contract).read_text()));guard(c);path=Path('/root/dell-fish-builder-'+str(c['vmid'])+'.json')
 if a.phase!='check':window(c,a.phase,a.window)
 if a.phase=='check':result={'protected':protected(c),'machine_id_sha256':sha('/etc/machine-id'),'hostkey_fingerprint':run(['ssh-keygen','-lf','/etc/ssh/ssh_host_ed25519_key.pub']).stdout.split()[1],'persistent_configuration_writes':False,'temporary_java_smoke_cleaned':c['vmid']==9042}
 elif a.phase=='install':
  require(not path.exists(),'existing-builder-receipt-stop-review');before=protected(c)
  sidecar=Path(__file__).with_name('install-guest.py');s=sidecar.lstat();require(stat.S_ISREG(s.st_mode) and s.st_uid==0 and not s.st_mode&0o022,'root-owned-installer-required')
  spec=importlib.util.spec_from_file_location('fish_installer',sidecar);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);m.ALLOW={i:v[1] for i,v in ROLES.items()};sys.argv=[str(sidecar),'--vmid',str(c['vmid']),'--apply'];capture=io.StringIO()
  with contextlib.redirect_stdout(capture):code=m.main()
  install_result=json.loads(capture.getvalue());require(code in (None,0) and install_result.get('status')=='installed-verified','fish-install-not-verified');check_preserved(before,c)
  result={'before':before,'install':install_result,'machine_id_sha256':sha('/etc/machine-id'),'hostkey_fingerprint':run(['ssh-keygen','-lf','/etc/ssh/ssh_host_ed25519_key.pub']).stdout.split()[1]};fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
  with os.fdopen(fd,'w') as f:json.dump(result,f)
 elif a.phase=='seal':
  before=json.loads(secure(path).read_text());stage=Path(__file__).parent;require(str(stage)=='/root/dell-fish-template-stage-'+str(c['vmid']) and not stage.is_symlink(),'exact-ephemeral-stage-required');allowed={'template-builder.py','install-guest.py','contract.json','install-window.json','seal-window.json'};require(all(x.name in allowed and x.is_file() and not x.is_symlink() for x in stage.iterdir()),'unknown-stage-files-stop-before-seal');result=seal(c,before['before']);path.unlink()
  for file in stage.iterdir():file.unlink()
  stage.rmdir();result['own_ephemeral_stage_removed']=True
 print(json.dumps({'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'vmid':c['vmid'],'phase':a.phase,'status':'passed','result':result}))
if __name__=='__main__':
 try:main()
 except Exception as e:print(json.dumps({'status':'refused-or-failed','category':type(e).__name__,'reason':str(e) if isinstance(e,Refused) else 'details-withheld','no_PVE_operations':True}));sys.exit(1)
