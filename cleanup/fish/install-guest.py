#!/usr/bin/env python3
"""Explicit authorized guests fish install-only; no chsh/config/plugins or service restart."""
import argparse,datetime,json,os,pwd,re,shutil,stat,subprocess,sys,tempfile,time
from pathlib import Path
ALLOW={190:'network-gateway',200:'data-prod-db',201:'data-prod-infra',210:'data-test',220:'publish-service',221:'artifact-service',230:'java-prod-01',240:'java-test-01',260:'nas-media'}
VERSION='4.0.2-1'
class Refused(RuntimeError):pass

def run(args,timeout=30,env=None):return subprocess.run(args,capture_output=True,text=True,timeout=timeout,env=env)
def shells():return {n:pwd.getpwnam(n).pw_shell for n in ['ub','root']}
def publisher_protection(vmid):
 if vmid!=220:return None
 p=Path('/var/lib/dell-publisher/.ssh/test240_ed25519');st=p.stat();u=pwd.getpwnam('publisher');groups=sorted(os.getgrouplist('publisher',u.pw_gid));docker_group=__import__('grp').getgrnam('docker').gr_gid
 return {'UID':u.pw_uid,'GID':u.pw_gid,'shell':u.pw_shell,'groups':groups,'not_in_docker_group':docker_group not in groups,'private_key_stat_only':{'uid':st.st_uid,'gid':st.st_gid,'mode':stat.S_IMODE(st.st_mode),'inode':st.st_ino,'size':st.st_size,'mtime_ns':st.st_mtime_ns},'key_bytes_not_read':True}

def installed(name):
 p=run(['dpkg-query','--show','--showformat=${db:Status-Status}\t${Version}',name]);parts=p.stdout.strip().split('\t');return (len(parts)==2 and parts[0]=='installed',parts[1] if len(parts)>1 else None)
def memory():return int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))*1024

def core():
 names=['ssh.service','qemu-guest-agent.service','systemd-networkd.service','systemd-resolved.service','docker.service','containerd.service','dnsmasq.service','openmediavault-engined.service','nginx.service','smbd.service']
 p=run(['systemctl','list-units','--type=service','--state=active','--plain','--no-legend'])
 names += [line.split()[0] for line in p.stdout.splitlines() if line.split() and line.split()[0].startswith('dell-') and line.split()[0] not in ['dell-guest-health.service']]
 result={}
 for name in sorted(set(names)):
  p=run(['systemctl','show',name,'--property=LoadState,ActiveState,SubState,MainPID,ExecMainStartTimestampMonotonic'])
  x=dict(l.split('=',1) for l in p.stdout.splitlines() if '=' in l)
  if x.get('LoadState')=='loaded' and x.get('ActiveState')=='active':result[name]=x
 containers={}
 if Path('/var/run/docker.sock').exists() and shutil.which('docker'):
  p=run(['docker','--host','unix:///var/run/docker.sock','ps','-aq'])
  for cid in p.stdout.split():
   fmt='{"name":{{json .Name}},"pid":{{json .State.Pid}},"running":{{json .State.Running}},"started_at":{{json .State.StartedAt}},"health":{{if (index .State "Health")}}{{json .State.Health.Status}}{{else}}null{{end}}}'
   q=run(['docker','--host','unix:///var/run/docker.sock','inspect','--format',fmt,cid]);containers[cid]=json.loads(q.stdout)
 return {'services':result,'containers':containers}

def main():
 p=argparse.ArgumentParser();p.add_argument('--vmid',type=int,choices=ALLOW,required=True);p.add_argument('--apply',action='store_true');a=p.parse_args()
 if os.geteuid()!=0 or Path('/etc/pve').exists() or __import__('socket').gethostname().split('.')[0]!=ALLOW[a.vmid]:raise Refused('explicit-retained-guest-only')
 if 'VERSION_ID="13"' not in Path('/etc/os-release').read_text() and 'VERSION_ID=13' not in Path('/etc/os-release').read_text():raise Refused('Debian13-only')
 before_shell=shells();before_core=core();publisher_before=publisher_protection(a.vmid);free=shutil.disk_usage('/').free
 if a.vmid==221:
  if len(before_core['containers'])!=2 or not all(x['running'] and x['pid']>0 for x in before_core['containers'].values()) or 'docker.service' not in before_core['services']:raise Refused('Nexus221-two-running-containers-active-Docker-precondition')
 if free<1024**3 or memory()<(200 if a.vmid==190 else 256)*1024**2:raise Refused('light-install-resource-gate')
 apt=['apt-get','-o','DPkg::Lock::Timeout=60','-o','Acquire::Retries=0','-o','Acquire::http::Timeout=20','-o','Acquire::https::Timeout=20','--no-install-recommends','--no-upgrade','install','fish='+VERSION,'fish-common='+VERSION]
 simulate=run(apt[:1]+['--simulate','-o','Debug::NoLocking=1','-o','Dir::Cache::pkgcache=','-o','Dir::Cache::srcpkgcache=']+apt[1:],timeout=60)
 if simulate.returncode:raise Refused('apt-simulation-failed-no-install')
 if re.search(r'^Remv ',simulate.stdout,re.M):raise Refused('APT-would-remove-package')
 plans=[]
 for package in re.findall(r'^Inst (\S+)',simulate.stdout,re.M):
  if not re.fullmatch(r'[a-z0-9][a-z0-9+.-]*(?::[a-z0-9]+)?',package):raise Refused('unsupported-package-name')
  present,version=installed(package)
  if present:raise Refused('APT-would-upgrade-or-reinstall-existing-package')
  plans.append(package)
 if not a.apply:print(json.dumps({'status':'simulation-only','vmid':a.vmid,'new_packages':plans,'remove_or_upgrade':False,'shell_change':False,'writes':0}));return
 env=os.environ.copy();env.update(DEBIAN_FRONTEND='noninteractive',NEEDRESTART_MODE='l',APT_LISTCHANGES_FRONTEND='none')
 # Native APT timeout/lock limits bound acquisition; never kill an active dpkg via a short outer timeout.
 process=subprocess.run(apt[:1]+['--yes']+apt[1:],capture_output=True,text=True,env=env)
 if process.returncode:
  categories={k:bool(re.search(pattern,process.stdout+process.stderr,re.I)) for k,pattern in {'fetch_failure':'failed to fetch|404|could not resolve','dpkg_failure':'dpkg.*error|dpkg was interrupted','lock_busy':'could not get lock|unable to acquire'}.items()}
  print(json.dumps({'status':'APT-install-failed','vmid':a.vmid,'exit_code':process.returncode,'failure_categories':categories,'shells_unchanged':shells()==before_shell,'raw_output_withheld':True}));return 1
 package_ok,version=installed('fish');common_ok,common_version=installed('fish-common')
 p=run(['/usr/bin/fish','--version']);binary_version=p.stdout.strip() if p.returncode==0 else None
 ub=pwd.getpwnam('ub')
 with tempfile.TemporaryDirectory(prefix='dell-fish-smoke-') as tmp:
  root=Path(tmp);os.chown(root,ub.pw_uid,ub.pw_gid)
  for name in ['config','data','cache']:
   q=root/name;q.mkdir(mode=0o700);os.chown(q,ub.pw_uid,ub.pw_gid)
  command=['runuser','--user','ub','--','env','XDG_CONFIG_HOME='+str(root/'config'),'XDG_DATA_HOME='+str(root/'data'),'XDG_CACHE_HOME='+str(root/'cache'),'/usr/bin/fish','--no-config','--private','-c','printf fish-smoke-ok']
  smoke=run(command,timeout=15);smoke_ok=smoke.returncode==0 and smoke.stdout=='fish-smoke-ok'
 after_core=core();core_same=before_core==after_core;publisher_after=publisher_protection(a.vmid);checks={'fish_exact_version':package_ok and version==VERSION,'fish_common_exact_version':common_ok and common_version==VERSION,'binary_version_command':p.returncode==0,'ub_nonconfig_private_smoke':smoke_ok,'ub_root_login_shells_unchanged':shells()==before_shell,'core_services_and_containers_PIDs_start_health_unchanged':core_same}
 if a.vmid==221:checks['Nexus221_two_container_ID_PID_start_health_and_Docker_service_unchanged']=before_core==after_core and len(after_core['containers'])==2
 if a.vmid==220:checks['publisher_UID_GID_shell_groups_key_stat_unchanged']=publisher_before==publisher_after and publisher_after['not_in_docker_group']
 result={'status':'installed-verified' if all(checks.values()) else 'installed-needs-review','vmid':a.vmid,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'checks':checks,'before_shells':before_shell,'after_shells':shells(),'fish_binary_version':binary_version,'new_packages':plans,'NEEDRESTART_MODE':'l','no_install_recommends':True,'existing_packages_upgraded_or_removed':False,'apt_update_fullupgrade_autoremove_chsh_or_shellconfig_run':False,'service_restart_requested_by_tool':False,'core_before':before_core,'core_after':after_core,'publisher_before':publisher_before,'publisher_after':publisher_after,'user_config_temporary_smoke_cleaned':True}
 print(json.dumps(result));return 0 if all(checks.values()) else 1
if __name__=='__main__':
 try:sys.exit(main())
 except Exception as e:print(json.dumps({'status':'refused-or-failed','error_category':type(e).__name__,'reason':str(e) if isinstance(e,Refused) else 'details-withheld','chsh_or_excluded_roles_touched':False}));sys.exit(1)
