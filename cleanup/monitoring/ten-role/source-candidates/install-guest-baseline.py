#!/usr/bin/env python3
"""Guest-only Debian 13 node exporter baseline; install-only parks every monitor."""
import argparse,contextlib,datetime,fcntl,grp,ipaddress,json,os,platform,pwd,re,shutil,socket,stat,subprocess,time,uuid
from pathlib import Path
HERE=Path(__file__).resolve().parent
INSTALL=Path('/opt/dell/guest-monitoring')
CONFIG_DIR=Path('/etc/dell-guest-monitoring')
TEXTFILE=Path('/var/lib/prometheus/node-exporter-textfile')
EXPORTER='prometheus-node-exporter.service'
SOCKET='prometheus-node-exporter.socket'
COLLECTOR='dell-guest-health.service'
TIMER='dell-guest-health.timer'
POLICY=Path('/usr/sbin/policy-rc.d')
SELF_LOCK=Path('/run/lock/dell-guest-monitoring.lock')
APT_LOCKS=[Path(x) for x in ['/var/lib/dpkg/lock-frontend','/var/lib/dpkg/lock','/var/lib/apt/lists/lock','/var/cache/apt/archives/lock']]
ROLES={'artifact-service','data-prod-db','data-prod-infra','data-test','java-prod-01','java-test-01','nas-media','ops-service','penpot-service','publish-service'}

def command(args,label,check=True,timeout=180):
    p=subprocess.run(args,capture_output=True,text=True,timeout=timeout)
    if check and p.returncode:raise RuntimeError(label+' failed; raw command output suppressed')
    return p

@contextlib.contextmanager
def management_lock():
    SELF_LOCK.parent.mkdir(parents=True,exist_ok=True)
    fd=os.open(SELF_LOCK,os.O_RDWR|os.O_CREAT,0o600)
    try:
        try:fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise RuntimeError('another guest baseline operation owns the lock') from None
        yield
    finally:os.close(fd)

def wait_apt_idle(timeout=120):
    deadline=time.monotonic()+timeout
    while True:
        opened=[];busy=False
        try:
            for path in APT_LOCKS:
                if path.is_symlink():raise RuntimeError('unexpected APT lock symlink')
                if not path.exists():continue
                file=path.open('r+');opened.append(file)
                try:fcntl.lockf(file.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
                except BlockingIOError:busy=True;break
        finally:
            for file in opened:file.close()
        if not busy:return
        if time.monotonic()>=deadline:raise RuntimeError('APT/DPKG locks busy; no locks deleted and no process killed')
        time.sleep(1)

@contextlib.contextmanager
def deny_daemon_starts():
    # Isolated whitelisted guest only; preserve original inode/symlink and mode.
    parent=POLICY.parent
    if parent.resolve()!=parent:raise RuntimeError('policy parent symlink rejected')
    marker=parent/'.policy-rc.d.dell-active.json'
    if marker.exists() or marker.is_symlink() or list(parent.glob('.policy-rc.d.dell-backup-*')):
        raise RuntimeError('unfinished guest policy recovery record exists; inspect before retry')
    backup=parent/('.policy-rc.d.dell-backup-'+uuid.uuid4().hex)
    existed=POLICY.exists() or POLICY.is_symlink()
    if existed:
        kind=POLICY.lstat().st_mode
        if not (stat.S_ISREG(kind) or stat.S_ISLNK(kind)):raise RuntimeError('unsupported existing policy-rc.d type')
    fd=os.open(marker,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'w') as out:json.dump({'original_existed':existed,'backup_name':backup.name,'scope':'isolated guest package window'},out)
    installed=None;moved=False
    try:
        if existed:os.replace(POLICY,backup);moved=True
        fd=os.open(POLICY,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o755)
        st=os.fstat(fd);installed=(st.st_dev,st.st_ino)
        with os.fdopen(fd,'w') as out:out.write('#!/bin/sh\n# Temporary Dell guest baseline: deny package daemon starts.\nexit 101\n')
        POLICY.chmod(0o755)
        yield
    finally:
        if installed is not None:
            try:current=POLICY.lstat()
            except FileNotFoundError:current=None
            if current is None or (current.st_dev,current.st_ino)!=installed:
                raise RuntimeError('policy changed concurrently; preserved backup requires manual recovery: '+str(backup))
            if existed:os.replace(backup,POLICY)
            else:POLICY.unlink()
        elif moved:
            if not POLICY.exists() and not POLICY.is_symlink():os.replace(backup,POLICY)
            else:raise RuntimeError('policy installation failed; original backup retained for recovery: '+str(backup))
        marker.unlink()

def target_for(role,hostname=None):
    short=(hostname or socket.gethostname()).split('.')[0]
    if role not in ROLES or short!=role:raise RuntimeError('hostname is not the assigned guest role')
    catalog=json.loads((HERE/'guest-targets.json').read_text())
    if len(catalog['roles'])!=len(ROLES) or {x['role'] for x in catalog['roles']}!=ROLES:raise RuntimeError('guest target whitelist mismatch')
    row=next(x for x in catalog['roles'] if x['role']==role)
    if row['hostname']!=role:raise RuntimeError('catalog hostname mismatch')
    ip=ipaddress.IPv4Address(row['private_ip'])
    if ip not in ipaddress.ip_network('192.168.19.0/24') or row['prefixlen']!=24:raise RuntimeError('invalid assigned private subnet')
    return row

def guest_gate(role,require_root=True):
    if require_root and os.geteuid()!=0:raise RuntimeError('run on the assigned guest as root')
    if Path('/etc/pve').exists():raise RuntimeError('PVE host is excluded')
    if platform.system()!='Linux' or platform.machine() not in ('x86_64','amd64'):raise RuntimeError('Linux AMD64 guest required')
    values={}
    for line in Path('/etc/os-release').read_text().splitlines():
        if '=' in line:
            k,v=line.split('=',1);values[k]=v.strip('"')
    if values.get('ID')!='debian' or values.get('VERSION_ID')!='13':raise RuntimeError('Debian 13 guest required')
    row=target_for(role)
    virt=command(['systemd-detect-virt','--vm'],'read virtualization type',False,10)
    if virt.returncode or virt.stdout.strip() not in ('kvm','qemu'):raise RuntimeError('only assigned KVM/QEMU guests are allowed; no host/LXC')
    return row

def private_address_present(row,addresses):
    return any('UP' in item.get('flags',[]) and item.get('ifname')!='lo' and any(x.get('family')=='inet' and x.get('local')==row['private_ip'] and x.get('prefixlen')==row['prefixlen'] and x.get('scope')=='global' for x in item.get('addr_info',[])) for item in addresses)

def require_private_ip(row):
    p=command(['ip','-j','address','show'],'read local addresses',timeout=10)
    if not private_address_present(row,json.loads(p.stdout)):raise RuntimeError('assigned network19 private IP is not configured on an UP guest interface')

def listeners(output,port=9100):
    return sorted({token for line in output.splitlines() for token in line.split() if ':' in token and token.rsplit(':',1)[-1]==str(port)})

def port9100():
    return listeners(command(['ss','--listening','--numeric','--tcp','--udp','--no-header'],'read local listener metadata',timeout=10).stdout)

def state(unit,kind):
    p=command(['systemctl',kind,unit],'read unit state',False,15)
    return p.stdout.strip() or 'unknown'

def park_collectors():
    if Path('/etc/systemd/system',TIMER).exists():command(['systemctl','disable','--now',TIMER],'park guest collector timer')
    if Path('/etc/systemd/system',COLLECTOR).exists():command(['systemctl','stop',COLLECTOR],'park guest collector service')

def enabled_links(unit):
    root=Path('/etc/systemd/system')
    return [str(p) for p in root.glob('**/'+unit) if p.is_symlink() and p.parent.name.endswith(('.wants','.requires'))]

def mask_exporter():
    command(['systemctl','mask','--now',EXPORTER,SOCKET],'mask node exporter before installation')
    command(['systemctl','disable',EXPORTER,SOCKET],'remove monitor enablement links',False)
    park_collectors()
    if port9100():raise RuntimeError('port 9100 is still listening; refusing to install or claim parked state')
    if state(EXPORTER,'is-enabled')!='masked':raise RuntimeError('exporter is not persistently masked')
    if enabled_links(EXPORTER) or enabled_links(SOCKET):raise RuntimeError('exporter enablement links remain behind mask')

def role_health_profile(row):
    """Approved deployed-role checks; activating them remains an explicit action."""
    role=row['role'];ip=row['private_ip']
    names=['finger-service-system','finger-service-coms','finger-auth','finger-bff-system','finger-gateway-mobile']
    units={
      'data-prod-db':['dell-data-prod-db.service'],
      'data-prod-infra':['dell-data-prod-infra.service'],
      'data-test':['dell-data-test-data.service'],
      'artifact-service':['dell-nexus.service'],
      'penpot-service':['dell-penpot.service'],
      'nas-media':['openmediavault-engined.service','nginx.service','smbd.service','dell-nas-jellyfin.service'],
      'ops-service':['dell-ops.service','dell-lark-notify.service']}
    endpoints={
      'data-prod-infra':[(8848,'/nacos/v1/console/health/readiness','nacos-readiness')],
      'data-test':[(8848,'/nacos/v1/console/health/readiness','nacos-readiness')],
      'artifact-service':[(8081,'/service/rest/v1/status','nexus-status')],
      'penpot-service':[(9001,'/','penpot-frontend')],
      'nas-media':[(80,'/','omv-web'),(8096,'/health','jellyfin-health')],
      'ops-service':[(9090,'/-/ready','prometheus-readiness'),(9093,'/-/ready','alertmanager-readiness'),(3000,'/api/health','grafana-health')]}
    return {'services':units.get(role,[]),'http_checks':[{'name':name,'url':'http://'+ip+':'+str(port)+path} for port,path,name in endpoints.get(role,[])]}


def candidates(row):
    role=row['role'];profile=role_health_profile(row)
    docker_roles={'data-prod-db','data-prod-infra','data-test','artifact-service','penpot-service','nas-media','ops-service'}
    candidate_units=(['docker.service'] if role in docker_roles else [])+profile['services']
    return {'role':role,'private_ip':row['private_ip'],'textfile_directory':str(TEXTFILE),'services':['ssh.service','qemu-guest-agent.service',EXPORTER],'http_checks':[],'candidate_service_units':candidate_units,'candidate_http_checks':profile['http_checks'],'notes':'Install-only retains base units and no active HTTP. Approved role candidates require explicit activation after real unit/URL preflight; no credentials, headers or business paths.'}


def write(path,body,mode=0o644):
    if path.parent.resolve(strict=False)!=path.parent:raise RuntimeError('config parent symlink rejected')
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.is_symlink():raise RuntimeError('refusing target config symlink')
    path.write_text(body);path.chmod(mode)

def unit_text(row,user,group):
    role=row['role'];check='/usr/bin/python3 '+str(INSTALL/'install-guest-baseline.py')+' --check-private-ip --role '+role
    drop='[Service]\nUser='+user+'\nGroup='+group+'\nExecCondition='+check+'\nExecStart=\nExecStart=/usr/bin/prometheus-node-exporter --web.listen-address='+row['private_ip']+':9100 --collector.textfile.directory='+str(TEXTFILE)+'\nNoNewPrivileges=yes\nMemoryMax=128M\nCPUQuota=20%\n'
    service='[Unit]\nDescription=Read-only local guest service and HTTP health textfile\nAfter=network-online.target\nWants=network-online.target\n\n[Service]\nType=oneshot\nUser='+user+'\nGroup='+group+'\nExecCondition='+check+'\nExecStart=/usr/bin/python3 '+str(INSTALL/'collect-guest-health.py')+'\nNoNewPrivileges=yes\nProtectSystem=strict\nProtectHome=yes\nPrivateTmp=yes\nReadWritePaths='+str(TEXTFILE)+'\nCapabilityBoundingSet=\nMemoryMax=64M\nCPUQuota=10%\nTasksMax=32\nTimeoutStartSec=45\n'
    timer='[Unit]\nDescription=Periodic local guest health textfile (disabled until explicit activation)\n\n[Timer]\nOnBootSec=2min\nOnUnitActiveSec=60s\nRandomizedDelaySec=10s\nUnit='+COLLECTOR+'\n\n[Install]\nWantedBy=timers.target\n'
    return drop,service,timer

def install_files(row):
    user=pwd.getpwnam('prometheus');group=grp.getgrgid(user.pw_gid).gr_name
    if any(path.resolve(strict=False)!=path for path in (INSTALL,CONFIG_DIR,TEXTFILE)):raise RuntimeError('installation path symlink rejected')
    INSTALL.mkdir(parents=True,exist_ok=True,mode=0o755)
    for name in ['install-guest-baseline.py','collect-guest-health.py','guest-targets.json']:
        source=HERE/name;target=INSTALL/name
        if source.resolve()!=target.resolve():shutil.copyfile(source,target)
        target.chmod(0o755 if name.endswith('.py') else 0o644)
    CONFIG_DIR.mkdir(parents=True,exist_ok=True,mode=0o755)
    config=CONFIG_DIR/'health.json'
    if config.exists():
        if config.is_symlink() or config.stat().st_uid!=0 or config.stat().st_mode&0o022:raise RuntimeError('existing health config ownership/permissions invalid')
        existing=json.loads(config.read_text())
        if existing.get('role')!=row['role'] or existing.get('private_ip')!=row['private_ip']:raise RuntimeError('existing collector config belongs to another guest')
    else:write(config,json.dumps(candidates(row),indent=2)+'\n')
    TEXTFILE.mkdir(parents=True,exist_ok=True,mode=0o755)
    if TEXTFILE.resolve()!=TEXTFILE:raise RuntimeError('textfile path has symlink components')
    os.chown(TEXTFILE,user.pw_uid,user.pw_gid);TEXTFILE.chmod(0o755)
    drop,service,timer=unit_text(row,user.pw_name,group)
    write(Path('/etc/systemd/system')/(EXPORTER+'.d')/'10-private-only.conf',drop)
    write(Path('/etc/systemd/system')/COLLECTOR,service)
    write(Path('/etc/systemd/system')/TIMER,timer)
    command(['systemctl','daemon-reload'],'reload installed disabled guest units')
    command(['systemctl','disable','--now',TIMER],'leave collector timer disabled')
    command(['systemctl','stop',COLLECTOR],'leave collector service inactive')


def receipt(row,action):
    result={'timestamp':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),'mode':action,'role':row['role'],'vmid':row['vmid'],'expected_private_ip':row['private_ip'],'exporter_enabled':state(EXPORTER,'is-enabled'),'exporter_active':state(EXPORTER,'is-active'),'exporter_socket_enabled':state(SOCKET,'is-enabled'),'collector_timer_enabled':state(TIMER,'is-enabled'),'collector_timer_active':state(TIMER,'is-active'),'collector_active':state(COLLECTOR,'is-active'),'listeners_9100':port9100(),'exporter_enablement_links':enabled_links(EXPORTER),'socket_enablement_links':enabled_links(SOCKET),'notifications_sent':False,'pve_or_ct_targeted':False}
    version=command(['dpkg-query','--show','--showformat=${Version}','prometheus-node-exporter'],'read installed exporter version',timeout=10)
    result['package_version']=version.stdout.strip()
    if action=='install-only':
        if result['exporter_enablement_links'] or result['socket_enablement_links'] or result['exporter_enabled']!='masked' or result['exporter_socket_enabled']!='masked' or result['exporter_active'] not in ('inactive','failed','unknown') or result['listeners_9100'] or result['collector_timer_enabled'] not in ('disabled','masked') or result['collector_timer_active'] not in ('inactive','failed','unknown') or result['collector_active'] not in ('inactive','failed','unknown'):
            raise RuntimeError('install-only parked-state verification failed')
    write(Path('/var/lib/dell-guest-monitoring/state.json'),json.dumps(result,indent=2)+'\n',0o600)
    print(json.dumps(result))

def run_action(args,row):
    if args.install_only:
        if not shutil.which('ss'):raise RuntimeError('ss is required before installation to verify no listener')
        mask_exporter()
        env=dict(os.environ,DEBIAN_FRONTEND='noninteractive')
        wait_apt_idle()
        with deny_daemon_starts():
            try:
                # policy-rc.d exit101 also covers maintainer-script starts/unmask attempts.
                for argv,label in [(['apt-get','-o','DPkg::Lock::Timeout=120','update'],'refresh signed Debian package lists'),(['apt-get','-o','DPkg::Lock::Timeout=120','install','--yes','--no-install-recommends','--no-upgrade','prometheus-node-exporter'],'install parked exporter only')]:
                    p=subprocess.run(argv,env=env,capture_output=True,text=True,timeout=600)
                    if p.returncode:raise RuntimeError(label+' failed; raw APT output suppressed')
            finally:
                # Keep deny policy in force until the post-install stop+mask finishes.
                command(['systemctl','stop',EXPORTER],'stop exporter again after APT',False)
                mask_exporter()
        install_files(row)
        receipt(row,'install-only');return
    # No unmask, start or enable happens before exact private-address validation.
    require_private_ip(row)
    if not (INSTALL/'collect-guest-health.py').is_file() or not Path('/etc/systemd/system',EXPORTER+'.d','10-private-only.conf').is_file():raise RuntimeError('install-only baseline is missing')
    if args.enable_collector:
        command(['runuser','--user','prometheus','--','/usr/bin/python3',str(INSTALL/'collect-guest-health.py'),'--check'],'verify unprivileged local read-only collector access',timeout=45)
    try:
        command(['systemctl','unmask',EXPORTER],'unmask private-bound exporter')
        command(['systemctl','enable','--now',EXPORTER],'activate private-bound exporter')
        expected=[row['private_ip']+':9100']
        for _ in range(20):
            observed=port9100()
            if observed==expected:break
            if observed:raise RuntimeError('unexpected listener; refusing temporary LAN exposure')
            time.sleep(0.5)
        else:raise RuntimeError('exporter did not bind the assigned private address')
        if args.enable_collector:command(['systemctl','enable','--now',TIMER],'activate explicitly requested collector timer')
    except Exception:
        mask_exporter();raise
    receipt(row,'activate')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--install-only',action='store_true');mode.add_argument('--activate',action='store_true');mode.add_argument('--check-private-ip',action='store_true')
    parser.add_argument('--role',default=socket.gethostname().split('.')[0])
    parser.add_argument('--enable-collector',action='store_true')
    args=parser.parse_args()
    if args.enable_collector and not args.activate:parser.error('--enable-collector requires explicit --activate')
    row=guest_gate(args.role,require_root=not args.check_private_ip)
    if args.check_private_ip:
        require_private_ip(row);return
    with management_lock():run_action(args,row)

if __name__=='__main__':
    try:main()
    except (RuntimeError,ValueError,OSError,KeyError,subprocess.TimeoutExpired) as error:raise SystemExit('GUEST BASELINE ERROR: '+str(error))
