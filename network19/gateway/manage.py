#!/usr/bin/python3
"""Dedicated190-only routing transaction. Never used on PVE or another guest."""
import argparse,base64,contextlib,datetime,fcntl,hashlib,importlib.util,json,os,platform,pwd,grp,secrets,shutil,socket,subprocess,sys,tempfile,time,uuid
from pathlib import Path
HERE=Path(__file__).resolve().parent;ETC=Path('/etc/dell-gateway19');STATE=Path('/var/lib/dell-gateway19');CODE=Path('/usr/local/libexec/dell-gateway19');CONFIG=ETC/'config.json';PENDING=STATE/'pending.json';FIREWALL='dell-gateway19-firewall.service';READY='dell-gateway19-ready.service';DNS='dell-gateway19-dnsmasq.service';TIMER='dell-gateway19-rollback.timer'
FILES=['/etc/cloud/cloud.cfg.d/99-dell-gateway19-network.cfg','/etc/systemd/network/05-dell-gateway19-wan.network','/etc/systemd/network/05-dell-gateway19-lan.network','/etc/systemd/system/systemd-networkd.service.d/90-dell-gateway19.conf','/etc/sysctl.d/99-dell-gateway19.conf','/etc/ssh/sshd_config.d/70-dell-gateway19.conf',str(CONFIG),str(ETC/'dnsmasq.conf')]+['/etc/systemd/system/'+x for x in [FIREWALL,READY,DNS,'dell-gateway19-apply.service','dell-gateway19-rollback.service',TIMER]]
SERVICES=[FIREWALL,READY,DNS,TIMER,'systemd-networkd.service','systemd-networkd-wait-online.service']
def run(args,check=True,timeout=90):
 r=subprocess.run(args,capture_output=True,timeout=timeout)
 if check and r.returncode:raise RuntimeError('fixed gateway action failed: '+args[0])
 return r

def load_policy():
 file=CODE/'policy.py'
 if not file.exists():file=HERE/'policy.py'
 if file.is_symlink() or file.stat().st_uid!=0 or file.stat().st_mode&0o022:raise RuntimeError('trusted root policy code required')
 s=importlib.util.spec_from_file_location('gateway19_policy',file);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def owned(path):
 if path.is_symlink() or path.resolve(strict=False)!=path:raise RuntimeError('symlink path rejected')
 return path

def put(path,data,mode=0o600):
 owned(path);path.parent.mkdir(parents=True,exist_ok=True)
 fd,temp=tempfile.mkstemp(prefix='.'+path.name+'-',dir=path.parent)
 try:
  with os.fdopen(fd,'wb') as out:out.write(data);out.flush();os.fsync(out.fileno())
  os.chown(temp,0,0);os.chmod(temp,mode);os.replace(temp,path)
 finally:Path(temp).unlink(missing_ok=True)

def read_config():
 owned(CONFIG)
 if CONFIG.stat().st_uid!=0 or CONFIG.stat().st_mode&0o077:raise RuntimeError('root600 policy required')
 return load_policy().validate_config(json.loads(CONFIG.read_text()))

def guard_identity():
 if os.geteuid()!=0 or Path('/etc/pve').exists() or socket.gethostname().split('.')[0]!='network-gateway' or platform.system()!='Linux' or platform.machine() not in ('x86_64','amd64'):raise RuntimeError('assigned gateway190 only')
 rows=json.loads(run(['ip','-j','link']).stdout)
 for mac in ['02:63:19:01:90:00','02:63:19:01:90:01']:
  if sum(r.get('address','').lower()==mac for r in rows)!=1:raise RuntimeError('fixed190 hardware MACs required before any write')

def guard(config,require_bootstrap=False):
 if os.geteuid()!=0 or Path('/etc/pve').exists() or socket.gethostname().split('.')[0]!='network-gateway' or platform.system()!='Linux' or platform.machine() not in ('x86_64','amd64'):raise RuntimeError('assigned gateway190 only')
 fields=dict(x.split('=',1) for x in Path('/etc/os-release').read_text().splitlines() if '='in x)
 if fields.get('ID','').strip('"')!='debian' or fields.get('VERSION_ID','').strip('"')!='13':raise RuntimeError('Debian13 only')
 p=load_policy();p.validate_config(config);rows=json.loads(run(['ip','-j','addr']).stdout);interfaces={}
 for role in ['WAN','LAN']:
  matches=[r for r in rows if r.get('address','').lower()==config[role+'_MAC']]
  if len(matches)!=1:raise RuntimeError('reviewed MAC does not uniquely identify NIC')
  row=matches[0];interfaces[role]=p.iface(row['ifname'])
  if require_bootstrap:
   expected='192.168.21.23' if role=='WAN' else '192.168.19.1'
   found=[a for a in row.get('addr_info',[]) if a.get('family')=='inet']
   if len(found)!=1 or found[0]['local']!=expected or found[0]['prefixlen']!=24:raise RuntimeError('reviewed bootstrap dual addresses required')
 if interfaces['WAN']==interfaces['LAN']:raise RuntimeError('distinct NICs required')
 if not Path('/proc/sys/net/ipv6/conf/lo/disable_ipv6').exists():raise RuntimeError('kernel-wide IPv6 disable prevents required loopback; stop for review')
 return interfaces

def nft_state():
 data=json.loads(run(['nft','-j','list','ruleset']).stdout);tables=[x['table'] for x in data.get('nftables',[]) if 'table'in x]
 if any(t.get('family')!='inet' or t.get('name')!='dell_gateway19' for t in tables):raise RuntimeError('foreign nft table; do not flush or replace it')
 return bool(tables)

def native_checks(config,interfaces,folder):
 p=load_policy();folder.mkdir(mode=0o700,parents=True,exist_ok=True);rules=p.nft(config,interfaces);exists=nft_state();transaction=('delete table inet dell_gateway19\n' if exists else '')+rules
 put(folder/'candidate.nft',transaction.encode());put(folder/'dnsmasq.conf',p.dnsmasq(config,interfaces).encode(),0o644)
 run(['nft','--check','--file',str(folder/'candidate.nft')]);run(['dnsmasq','--test','--conf-file='+str(folder/'dnsmasq.conf')]);return transaction

def sysctl(key,value):run(['sysctl','-q','-w',key+'='+str(value)])
def forwarding_values(interfaces):
 keys={'all':'net.ipv4.conf.all.forwarding',**{role:'net/ipv4/conf/'+name+'/forwarding' for role,name in interfaces.items()}}
 return {role:run(['sysctl','-n',key]).stdout.decode().strip() for role,key in keys.items()}

def set_forwarding(interfaces,enabled):
 value=int(enabled);sysctl('net.ipv4.ip_forward',value);sysctl('net.ipv4.conf.all.forwarding',value)
 # Unknown/new NICs must not silently become forwarding interfaces.
 sysctl('net.ipv4.conf.default.forwarding',0)
 for name in interfaces.values():sysctl('net/ipv4/conf/'+name+'/forwarding',value)
 if set(forwarding_values(interfaces).values())!={str(value)}:raise RuntimeError('all/WAN/LAN forwarding readback differs')

def security_flags(interfaces):
 # Never write all.disable_ipv6: per-NIC disable and loopback enable are intentional.
 for key,value in [('net.ipv6.conf.default.disable_ipv6',1),('net.ipv6.conf.lo.disable_ipv6',0),('net.ipv4.conf.all.accept_redirects',0),('net.ipv4.conf.default.accept_redirects',0),('net.ipv4.conf.all.send_redirects',0),('net.ipv4.conf.default.send_redirects',0),('net.ipv4.conf.all.accept_source_route',0),('net.ipv4.conf.default.accept_source_route',0)]:sysctl(key,value)
 for name in interfaces.values():
  for key,value in [('disable_ipv6',1),('accept_ra',0),('forwarding',0)]:sysctl('net/ipv6/conf/'+name+'/'+key,value)
  for key,value in [('accept_redirects',0),('send_redirects',0),('accept_source_route',0),('rp_filter',1)]:sysctl('net/ipv4/conf/'+name+'/'+key,value)
 run(['ip','-6','address','replace','::1/128','dev','lo'])

def harden(interfaces,forwarding_enabled=False):
 set_forwarding(interfaces,False);security_flags(interfaces)
 if forwarding_enabled:
  try:
   set_forwarding(interfaces,True)
   # Linux ip_forward changes router defaults; reapply hardening afterwards.
   security_flags(interfaces)
  except BaseException:
   set_forwarding(interfaces,False);raise
 return forwarding_values(interfaces)

def boot_firewall():
 config=read_config();interfaces=guard(config);set_forwarding(interfaces,False);folder=STATE/'native-check';transaction=native_checks(config,interfaces,folder);run(['nft','--file',str(folder/'candidate.nft')]);harden(interfaces);put(ETC/'dnsmasq.conf',load_policy().dnsmasq(config,interfaces).encode(),0o644)
 return {'status':'filter-loaded-forwarding-still-disabled','MAC_interfaces':interfaces,'rules_sha256':hashlib.sha256(transaction.encode()).hexdigest()}

def ready():
 config=read_config();interfaces=guard(config,True);default=json.loads(run(['ip','-j','route','show','default']).stdout)
 if len(default)!=1 or default[0].get('gateway')!='192.168.21.1' or default[0].get('dev')!=interfaces['WAN']:raise RuntimeError('exact WAN default route required')
 if not nft_state():raise RuntimeError('own firewall missing')
 data=json.loads(run(['nft','-j','list','table','inet','dell_gateway19']).stdout);chains={x['chain']['name']:x['chain'].get('policy') for x in data['nftables'] if 'chain'in x}
 if chains!={'input':'drop','forward':'drop','output':'accept'}:raise RuntimeError('deny-by-default chain policies required')
 harden(interfaces,False)
 for name in interfaces.values():
  if Path('/proc/sys/net/ipv6/conf',name,'disable_ipv6').read_text().strip()!='1':raise RuntimeError('physical IPv6 not disabled')
 if Path('/proc/sys/net/ipv6/conf/lo/disable_ipv6').read_text().strip()!='0':raise RuntimeError('loopback IPv6 not retained')
 values=harden(interfaces,True)
 return {'status':'gateway-config-ready-forward-enabled','MAC_interfaces':interfaces,'NAT':'none','IPv6':'WAN/LAN disabled,lo retained','forwarding_all_WAN_LAN':values,'packet_path_and_LAN_DHCP_tests':'pending-external-client-verification'}

def snapshot(config):
 old={};states={}
 for text in FILES:
  file=Path(text);owned(file)
  if file.exists():
   st=file.stat()
   if st.st_uid!=0 or st.st_mode&0o022:raise RuntimeError('existing config not root trusted')
   old[text]={'data':base64.b64encode(file.read_bytes()).decode(),'mode':st.st_mode&0o777}
  else:old[text]=None
 for name in SERVICES:states[name]={'enabled':run(['systemctl','is-enabled',name],False).stdout.decode().strip(),'active':run(['systemctl','is-active','--quiet',name],False).returncode==0}
 exists=nft_state();nf=run(['nft','list','table','inet','dell_gateway19']).stdout.decode() if exists else None
 interfaces=guard(config,True);keys=['net.ipv4.ip_forward','net.ipv4.conf.all.forwarding','net.ipv4.conf.default.forwarding','net.ipv6.conf.default.disable_ipv6','net.ipv6.conf.lo.disable_ipv6']
 for group in ['all','default']:
  keys+=['net.ipv4.conf.'+group+'.'+key for key in ['accept_redirects','send_redirects','accept_source_route']]
 for name in interfaces.values():
  keys+=['net/ipv6/conf/'+name+'/'+key for key in ['disable_ipv6','accept_ra','forwarding']]
  keys+=['net/ipv4/conf/'+name+'/'+key for key in ['accept_redirects','send_redirects','accept_source_route','rp_filter','forwarding']]
 values={key:run(['sysctl','-n',key]).stdout.decode().strip() for key in keys}
 return {'files':old,'service_states':states,'old_own_nft':nf,'sysctls':values,'interfaces':interfaces,'config':config}

def restore_sysctls(values):
 # Global router defaults first, then every saved per-scope value after the reset.
 priority=['net.ipv4.ip_forward','net.ipv4.conf.all.forwarding','net.ipv4.conf.default.forwarding']
 for key in priority+[k for k in values if k not in priority]:
  if key in values:sysctl(key,values[key])
 for key,value in values.items():
  if run(['sysctl','-n',key]).stdout.decode().strip()!=str(value):raise RuntimeError('rollback sysctl readback differs')

def units(deadline):
 common='[Unit]\nDescription=Dell dedicated gateway19 '
 fw=common+'filter before networking\nDefaultDependencies=no\nAfter=local-fs.target systemd-udev-trigger.service systemd-sysctl.service\nWants=network-pre.target\nBefore=network-pre.target systemd-networkd.service\n[Service]\nType=oneshot\nRemainAfterExit=yes\nExecStart=/usr/bin/python3 '+str(CODE/'manage.py')+' boot-firewall\nExecStop=/usr/bin/python3 '+str(CODE/'manage.py')+' quiesce\n[Install]\nWantedBy=multi-user.target\n'
 rd=common+'readiness and forwarding\nRequires='+FIREWALL+' systemd-networkd.service\nAfter='+FIREWALL+' systemd-networkd.service network-online.target\nWants=network-online.target\n[Service]\nType=oneshot\nRemainAfterExit=yes\nExecStart=/usr/bin/python3 '+str(CODE/'manage.py')+' ready\nExecStop=/usr/bin/python3 '+str(CODE/'manage.py')+' quiesce\n[Install]\nWantedBy=multi-user.target\n'
 dns=common+'LAN DNS/DHCP\nRequires='+READY+'\nAfter='+READY+'\nPartOf='+READY+'\n[Service]\nType=simple\nUser=dnsmasq\nGroup=nogroup\nAmbientCapabilities=CAP_NET_ADMIN CAP_NET_RAW CAP_NET_BIND_SERVICE\nExecStartPre=/usr/sbin/dnsmasq --test --conf-file='+str(ETC/'dnsmasq.conf')+'\nExecStart=/usr/sbin/dnsmasq --keep-in-foreground --conf-file='+str(ETC/'dnsmasq.conf')+'\nRestart=on-failure\nRestartSec=5\nNoNewPrivileges=yes\nProtectSystem=strict\nProtectHome=yes\nPrivateTmp=yes\nReadWritePaths=/var/lib/misc/dnsmasq.leases\nCapabilityBoundingSet=CAP_NET_ADMIN CAP_NET_RAW CAP_NET_BIND_SERVICE\nMemoryMax=64M\nTasksMax=32\n[Install]\nWantedBy=multi-user.target\n'
 apply=common+'independent apply transaction\nAfter=local-fs.target\n[Service]\nType=oneshot\nExecStart=/usr/bin/python3 '+str(CODE/'manage.py')+' activate\nTimeoutStartSec=120\n'
 rollback=common+'rollback watchdog\nAfter=local-fs.target\n[Service]\nType=oneshot\nExecStart=/usr/bin/python3 '+str(CODE/'manage.py')+' rollback\nTimeoutStartSec=120\n'
 timer='[Unit]\nDescription=Dell gateway19 unconfirmed rollback\n[Timer]\nOnActiveSec=180s\nOnCalendar='+deadline+'\nPersistent=true\nAccuracySec=1s\nUnit=dell-gateway19-rollback.service\n[Install]\nWantedBy=timers.target\n'
 return {FIREWALL:fw,READY:rd,DNS:dns,'dell-gateway19-apply.service':apply,'dell-gateway19-rollback.service':rollback,TIMER:timer}

def prepare_leasefile():
 # dnsmasq opens the file as root before dropping uid; pre-create its sole writable file.
 directory=owned(Path('/var/lib/misc'));st=directory.stat()
 if not directory.is_dir() or st.st_uid!=0 or st.st_mode&0o022:raise RuntimeError('OS misc directory must retain trusted original ownership/mode')
 file=owned(directory/'dnsmasq.leases');account=pwd.getpwnam('dnsmasq')
 if grp.getgrgid(account.pw_gid).gr_name!='nogroup':raise RuntimeError('measured Debian dnsmasq primary group differs; stop for review')
 if file.exists():
  st=file.stat()
  if not file.is_file() or st.st_nlink!=1 or st.st_size!=0 or st.st_uid!=account.pw_uid or st.st_gid!=account.pw_gid or st.st_mode&0o777!=0o600:raise RuntimeError('existing lease data/owner must not be overwritten')
 else:
  fd=os.open(file,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
  try:os.fchown(fd,account.pw_uid,account.pw_gid);os.fchmod(fd,0o600)
  finally:os.close(fd)
 # Test DAC under the exact unprivileged identity without truncating the file.
 probe="import os; f=os.open('/var/lib/misc/dnsmasq.leases',os.O_RDWR|os.O_NOFOLLOW); os.close(f)"
 run(['runuser','--user','dnsmasq','--','/usr/bin/python3','-c',probe])

def stage(bundle):
 if PENDING.exists():raise RuntimeError('pending transaction exists; inspect/rollback, do not overwrite')
 p=load_policy();config=p.validate_config(json.loads((bundle/'config.json').read_text()));interfaces=guard(config,True)
 if run(['systemctl','is-active','--quiet','systemd-networkd.service'],False).returncode!=0 or run(['systemctl','is-active','--quiet','networking.service'],False).returncode==0 or run(['systemctl','is-active','--quiet','NetworkManager.service'],False).returncode==0:raise RuntimeError('measured networkd-only backend required; do not migrate an unknown renderer')
 native_checks(config,interfaces,STATE/'stage-check');original=snapshot(config);
 if CONFIG.exists() is False and set(forwarding_values(interfaces).values())!={'0'}:raise RuntimeError('initial bootstrap must have all/WAN/LAN forwarding zero')
 nonce=uuid.uuid4().hex;backup=STATE/('before-'+nonce);backup.mkdir(mode=0o700);put(backup/'snapshot.json',(json.dumps(original,indent=2)+'\n').encode());deadline=datetime.datetime.now(datetime.timezone.utc)+datetime.timedelta(seconds=180)
 # Boot/sysctl restores lo after any earlier inherited all-disable without toggling all.
 sysctls='net.ipv4.ip_forward=0\nnet.ipv4.conf.all.forwarding=0\nnet.ipv4.conf.default.forwarding=0\nnet.ipv6.conf.default.disable_ipv6=1\nnet.ipv6.conf.lo.disable_ipv6=0\n'
 contents={FILES[0]:b'network: {config: disabled}\n',FILES[1]:p.network(config,'WAN').encode(),FILES[2]:p.network(config,'LAN').encode(),FILES[3]:('[Unit]\nRequires='+FIREWALL+'\nAfter='+FIREWALL+'\n').encode(),FILES[4]:sysctls.encode(),FILES[5]:b'PasswordAuthentication no\nKbdInteractiveAuthentication no\nPubkeyAuthentication yes\n',str(CONFIG):(json.dumps(config,indent=2)+'\n').encode(),str(ETC/'dnsmasq.conf'):p.dnsmasq(config,interfaces).encode()}
 for name,text in units(deadline.strftime('%Y-%m-%d %H:%M:%S UTC')).items():contents['/etc/systemd/system/'+name]=text.encode()
 pending={'nonce':nonce,'backup':str(backup),'deadline_utc':deadline.isoformat(),'status':'staged-not-activated','config':config};put(PENDING,(json.dumps(pending,indent=2)+'\n').encode())
 try:
  for text,data in contents.items():put(Path(text),data,0o600 if text==str(CONFIG) else 0o644)
  prepare_leasefile()
  run(['sshd','-t']);run(['systemctl','daemon-reload']);run(['systemd-analyze','verify',*['/etc/systemd/system/'+name for name in units(deadline.strftime('%Y-%m-%d %H:%M:%S UTC'))]])
  run(['systemctl','enable','--now',TIMER]);run(['systemctl','start','--no-block','dell-gateway19-apply.service'])
 except BaseException:rollback();raise
 return {'status':'activation-scheduled-requires-new-strict-SSH-confirm','nonce':nonce,'deadline_utc':pending['deadline_utc'],'rollback_armed':True,'packet_validation':'not-yet-proved'}

def service_fingerprints():
 names=[FIREWALL,READY,DNS,'systemd-networkd.service','ssh.service','systemd-resolved.service']
 return {name:run(['systemctl','show',name,'-p','MainPID','-p','ExecMainStartTimestampMonotonic','-p','ActiveState','-p','SubState']).stdout.decode().splitlines() for name in names}

def validate_hot_delta(old,new):
 p=load_policy();p.validate_config(old);p.validate_config(new)
 if new.get('WireGuard_client_access')==p.WG_FULL and old.get('WireGuard_client_access')!=p.WG_FULL:
  if old.get('WireGuard_client_access')!=p.WG_NARROW:raise RuntimeError('full trust hot scope requires currently confirmed exact narrow contract')
  omit={'migration_plan_sha256','WireGuard_client_access'}
  if {k:v for k,v in old.items() if k not in omit}!={k:v for k,v in new.items() if k not in omit}:raise RuntimeError('full trust upgrade may not change any other contract')
  return
 features={'OW_fake_IP_proxy','CF_fake_IP_proxy','WireGuard_client_access'};added={key for key in features if key in new and key not in old}
 if len(added)!=1:raise RuntimeError('only one exact approved compatibility addition permitted per transaction')
 omit={'migration_plan_sha256',*added}
 if {k:v for k,v in old.items() if k not in omit}!={k:v for k,v in new.items() if k not in omit}:raise RuntimeError('hot update cannot change any other gateway contract')

def queue_hot_apply():
 # The caller still holds the transaction lock; waiting for a oneshot here deadlocks its child.
 run(['systemd-run','--no-block','--unit=dell-gateway19-hot-apply','--collect','--property=Type=oneshot','--property=TimeoutStartSec=90','/usr/bin/python3',str(CODE/'manage.py'),'hot-activate'])

def hot_stage(bundle):
 if PENDING.exists():raise RuntimeError('pending transaction exists')
 p=load_policy();old=read_config();new=p.validate_config(json.loads((bundle/'config.json').read_text()));validate_hot_delta(old,new);interfaces=guard(old,True);check();native_checks(new,interfaces,STATE/'hot-check')
 nonce=uuid.uuid4().hex;backup=STATE/('before-hot-'+nonce);backup.mkdir(mode=0o700);original=snapshot(old)
 if new.get('WireGuard_client_access')==p.WG_FULL:
  # Keep exact old raw rules for audit, but revoke mark5 INPUT trials on rollback.
  original['hot_rollback_nft']=p.nft(old,interfaces)
  rollback_check=('delete table inet dell_gateway19\n' if nft_state() else '')+original['hot_rollback_nft']
  put(backup/'rollback-check.nft',rollback_check.encode());run(['nft','--check','--file',str(backup/'rollback-check.nft')])
 put(backup/'snapshot.json',(json.dumps(original,indent=2)+'\n').encode());deadline=datetime.datetime.now(datetime.timezone.utc)+datetime.timedelta(seconds=180)
 pending={'nonce':nonce,'kind':'hot-policy-only','backup':str(backup),'deadline_utc':deadline.isoformat(),'status':'staged-not-activated','config':new,'service_fingerprints':service_fingerprints()};put(PENDING,(json.dumps(pending,indent=2)+'\n').encode())
 try:
  text=units(deadline.strftime('%Y-%m-%d %H:%M:%S UTC'))[TIMER];put(Path('/etc/systemd/system')/TIMER,text.encode(),0o644);run(['systemctl','daemon-reload']);run(['systemctl','enable','--now',TIMER]);run(['systemctl','is-active','--quiet',TIMER])
  queue_hot_apply()
 except BaseException:hot_rollback(pending,original);raise
 return {'status':'hot-policy-activation-scheduled','nonce':nonce,'deadline_utc':pending['deadline_utc'],'rollback_armed':True,'no_service_or_address_or_sysctl_restart':True}

def hot_activate():
 pending=json.loads(PENDING.read_text())
 if pending.get('kind')!='hot-policy-only':raise RuntimeError('exact hot transaction required')
 original=json.loads((Path(pending['backup'])/'snapshot.json').read_text());new=pending['config'];interfaces=guard(new,True)
 try:
  native_checks(new,interfaces,STATE/'hot-apply');run(['nft','--file',str(STATE/'hot-apply/candidate.nft')]);put(CONFIG,(json.dumps(new,indent=2)+'\n').encode());result=check()
  if service_fingerprints()!=pending['service_fingerprints']:raise RuntimeError('hot policy changed persistent service identities')
  pending['status']='activated-awaiting-confirm';put(PENDING,(json.dumps(pending,indent=2)+'\n').encode());put(STATE/'hot-activation-result.json',(json.dumps(result,indent=2)+'\n').encode());return dict(result,kind='hot-policy-only',persistent_service_PIDs_unchanged=True)
 except BaseException:hot_rollback(pending,original);raise

def hot_rollback(pending,original):
 # Fake-IP flows use mark2; the saved old rules accept only mark1, revoking trial flows.
 own=run(['nft','list','table','inet','dell_gateway19'],False).returncode==0;body=('delete table inet dell_gateway19\n' if own else '')+(original.get('hot_rollback_nft',original['old_own_nft']) or '')
 if body:put(STATE/'hot-rollback.nft',body.encode());run(['nft','--check','--file',str(STATE/'hot-rollback.nft')]);run(['nft','--file',str(STATE/'hot-rollback.nft')])
 old=original['files'][str(CONFIG)]
 if old is None:raise RuntimeError('hot update must have prior active config')
 put(CONFIG,base64.b64decode(old['data']),old['mode']);run(['systemctl','disable','--now',TIMER])
 old_timer=original['files']['/etc/systemd/system/'+TIMER]
 if old_timer:put(Path('/etc/systemd/system')/TIMER,base64.b64decode(old_timer['data']),old_timer['mode'])
 run(['systemctl','daemon-reload'])
 pending['status']='hot-rolled-back-original-policy-services-unchanged';put(STATE/'last-transaction.json',(json.dumps(pending,indent=2)+'\n').encode());PENDING.unlink(missing_ok=True);return {'status':pending['status'],'persistent_service_PIDs_unchanged':service_fingerprints()==pending['service_fingerprints']}

def activate():
 pending=json.loads(PENDING.read_text());guard(pending['config'],True)
 try:
  run(['systemctl','restart',FIREWALL]);run(['systemctl','restart','systemd-networkd.service']);run(['systemctl','enable',FIREWALL,READY,DNS]);run(['systemctl','start',READY]);run(['systemctl','start',DNS]);run(['systemctl','reload','ssh.service']);result=check();pending['status']='activated-awaiting-confirm';put(PENDING,(json.dumps(pending,indent=2)+'\n').encode());put(STATE/'activation-result.json',(json.dumps(result,indent=2)+'\n').encode());return result
 except BaseException:
  # Independent unit owns the mutation; SSH disconnect cannot cancel the watchdog.
  rollback();raise

def dns_sockets_ready():
 end=time.monotonic()+10
 while time.monotonic()<end:
  text=run(['ss','-H','-lntup']).stdout.decode();entries=[row.split() for row in text.splitlines()];dns=[row for row in entries if len(row)>4 and row[4].rsplit(':',1)[-1]=='53' and 'dnsmasq' in ' '.join(row)]
  dhcp=[row for row in entries if len(row)>4 and row[4].rsplit(':',1)[-1]=='67' and 'dnsmasq' in ' '.join(row)]
  if len(dns)==2 and {row[0] for row in dns}=={'tcp','udp'} and all(row[4].rsplit(':',1)[0].split('%')[0]=='192.168.19.1' for row in dns) and dhcp:return {'DNS':'v4 TCP/UDP19.1 only','DHCP_socket_present':True,'DHCP_WAN_negative_packet_test':'pending'}
  time.sleep(.25)
 raise RuntimeError('actual DNS/DHCP sockets not ready or DNS bound outside LAN')

def check():
 config=read_config();interfaces=guard(config,True);result={'status':'configuration-and-services-only','MAC_interfaces':interfaces,'forward':Path('/proc/sys/net/ipv4/ip_forward').read_text().strip(),'forwarding_all_WAN_LAN':forwarding_values(interfaces),'NAT':'none','DHCP_pool':'192.168.19.200-239','packet_tests':'external positive/negative checks still required','units':{name:run(['systemctl','is-active',name],False).stdout.decode().strip() for name in [FIREWALL,READY,DNS]},'IPv6':{role:Path('/proc/sys/net/ipv6/conf',name,'disable_ipv6').read_text().strip() for role,name in interfaces.items()},'lo_IPv6_disable':Path('/proc/sys/net/ipv6/conf/lo/disable_ipv6').read_text().strip()}
 if result['forward']!='1' or set(result['forwarding_all_WAN_LAN'].values())!={'1'} or any(value!='active' for value in result['units'].values()) or any(x!='1' for x in result['IPv6'].values()) or result['lo_IPv6_disable']!='0' or not nft_state():raise RuntimeError('configuration/service readiness incomplete')
 result['listeners']=dns_sockets_ready()
 result['OW_fake_IP_proxy']=config.get('OW_fake_IP_proxy');result['CF_fake_IP_proxy']=config.get('CF_fake_IP_proxy')
 result['WireGuard_client_access']=config.get('WireGuard_client_access')
 if config.get('WireGuard_client_access'):
  p=load_policy();full=config['WireGuard_client_access']==p.WG_FULL;raw=json.loads(run(['nft','-j','list','table','inet','dell_gateway19']).stdout);prefix={'prefix':{'addr':'10.66.66.0','len':24}};found={'input':[],'forward':[]}
  for entry in raw['nftables']:
   if 'rule' not in entry or entry['rule']['chain'] not in found:continue
   expr=entry['rule']['expr']
   if any(x.get('match',{}).get('right')==prefix for x in expr):found[entry['rule']['chain']].append(expr)
  if len(found['input'])!=(1 if full else 0) or len(found['forward'])!=1:raise RuntimeError('WG actual INPUT/FORWARD scope count differs')
  for chain,expressions in found.items():
   if not expressions:continue
   expr=expressions[0];matches=[x['match'] for x in expr if 'match'in x];right=[x['right'] for x in matches];mark_value=0x19000005 if full else 0x19000004
   mark=any(x.get('mangle',{}).get('key')=={'ct':{'key':'mark'}} and x['mangle'].get('value')==mark_value for x in expr)
   if interfaces['WAN'] not in right or not mark:raise RuntimeError('WG WAN or conntrack mark differs')
   if chain=='input':
    if not any(isinstance(x,dict) and set(x.get('set',[]))=={'192.168.21.23','192.168.19.1'} for x in right):raise RuntimeError('WG exact gateway-local addresses differ')
   elif interfaces['LAN'] not in right or ({'prefix':{'addr':'192.168.19.0','len':24}} if full else '192.168.19.50') not in right:raise RuntimeError('WG actual routed destination differs')
   ports=[x for x in matches if isinstance(x.get('left'),dict) and x['left'].get('payload',{}).get('field') in ('dport','sport')]
   if full and ports:raise RuntimeError('full authorized WG access must not carry hidden port restrictions')
   if not full and not any(x.get('left')=={'payload':{'protocol':'tcp','field':'dport'}} and x.get('right')==9001 for x in matches):raise RuntimeError('WG narrow port differs')
  mark5_guard=any(x.get('match',{}).get('left')=={'ct':{'key':'mark'}} and x['match'].get('op')=='!=' and x['match'].get('right')==0x19000005 for row in raw['nftables'] if 'rule'in row and row['rule']['chain']=='input' for x in row['rule']['expr'])
  if full and not mark5_guard:raise RuntimeError('generic INPUT established must not swallow full-trust trial mark5')
  result['WG_actual_rules']='trusted VPN /24 full19 /24 + exact gateway addresses mark5' if full else 'only Penpot TCP9001 forward mark4'
 expected=(3 if config.get('OW_fake_IP_proxy') else 0)+(2 if config.get('CF_fake_IP_proxy') else 0)
 if expected:
  text=run(['nft','list','table','inet','dell_gateway19']).stdout.decode()
  if sum('ip daddr 198.18.0.0/15' in line for line in text.splitlines())!=expected:raise RuntimeError('exact approved fake-IP rule branches missing')
 return result

def confirm(nonce):
 pending=json.loads(PENDING.read_text())
 if pending['nonce']!=nonce or pending['status']!='activated-awaiting-confirm':raise RuntimeError('matching activated transaction nonce required')
 result=check()
 if pending.get('kind')=='hot-policy-only' and service_fingerprints()!=pending['service_fingerprints']:raise RuntimeError('persistent services changed during hot transaction')
 result['transaction_kind']=pending.get('kind','full-initial-apply')
 result['persistent_service_PIDs_unchanged']=True if pending.get('kind')=='hot-policy-only' else None
 run(['systemctl','disable','--now',TIMER]);pending.update(status='confirmed-after-independent-SSH',confirmed_at=datetime.datetime.now(datetime.timezone.utc).isoformat());put(STATE/'last-transaction.json',(json.dumps(pending,indent=2)+'\n').encode());PENDING.unlink();return dict(result,status=pending['status'],nonce=nonce)

def rollback():
 if not PENDING.exists():return {'status':'no-pending-transaction-no-action'}
 pending=json.loads(PENDING.read_text());config=pending['config'];interfaces=guard(config);snapshot=json.loads((Path(pending['backup'])/'snapshot.json').read_text())
 if pending.get('kind')=='hot-policy-only':return hot_rollback(pending,snapshot)
 set_forwarding(interfaces,False)
 for name in [DNS,READY,FIREWALL]:run(['systemctl','stop',name],False)
 for name in [DNS,READY,FIREWALL,TIMER]:run(['systemctl','disable',name],False)
 # No flush ruleset: replace/delete this owned table only.
 own=run(['nft','list','table','inet','dell_gateway19'],False).returncode==0
 old=snapshot['old_own_nft'];body=('delete table inet dell_gateway19\n' if own else '')+(old or '')
 if body:put(STATE/'rollback.nft',body.encode());run(['nft','--file',str(STATE/'rollback.nft')])
 for text,value in snapshot['files'].items():
  file=Path(text)
  if value is None:file.unlink(missing_ok=True)
  else:put(file,base64.b64decode(value['data']),value['mode'])
 run(['systemctl','daemon-reload']);run(['systemctl','restart','systemd-networkd.service'])
 # Initial snapshot was required to be this exact bootstrap topology.
 for role,address in [('WAN','192.168.21.23/24'),('LAN','192.168.19.1/24')]:run(['ip','address','replace',address,'dev',interfaces[role]]);run(['ip','link','set','dev',interfaces[role],'up'])
 run(['ip','route','replace','default','via','192.168.21.1','dev',interfaces['WAN']]);run(['sshd','-t']);run(['systemctl','reload','ssh.service'])
 for name in [FIREWALL,READY,DNS]:
  previous=snapshot['service_states'][name]
  if previous['enabled'] in ('enabled','enabled-runtime'):run(['systemctl','enable',name])
  if previous['active']:run(['systemctl','start',name])
 restore_sysctls(snapshot['sysctls'])
 pending['status']='rolled-back-bootstrap-network-restored';put(STATE/'last-transaction.json',(json.dumps(pending,indent=2)+'\n').encode());PENDING.unlink();return {'status':pending['status'],'forward_restored':Path('/proc/sys/net/ipv4/ip_forward').read_text().strip(),'SSH_bootstrap':'192.168.21.23; strict key unchanged','packages_and_public_recovery_code':'retained; default dnsmasq/nft services remain masked'}

def main():
 p=argparse.ArgumentParser();p.add_argument('action',choices=['stage','boot-firewall','ready','activate','check','confirm','rollback','quiesce','hot-stage','hot-activate']);p.add_argument('--bundle',type=Path);p.add_argument('--nonce');p.add_argument('--reviewed-190-apply-window',action='store_true');args=p.parse_args();guard_identity();STATE.mkdir(mode=0o700,exist_ok=True);owned(STATE);STATE.chmod(0o700)
 lock=None
 if args.action in ('stage','activate','confirm','rollback','hot-stage','hot-activate'):
  lock=os.open(STATE/'transaction.lock',os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW,0o600);fcntl.flock(lock,fcntl.LOCK_EX)
 if args.action in ('stage','hot-stage'):
  if not args.reviewed_190_apply_window or not args.bundle:raise RuntimeError('explicit reviewed190 apply window required')
  result=stage(args.bundle) if args.action=='stage' else hot_stage(args.bundle)
 elif args.action=='boot-firewall':result=boot_firewall()
 elif args.action=='ready':result=ready()
 elif args.action=='activate':result=activate()
 elif args.action=='hot-activate':result=hot_activate()
 elif args.action=='check':result=check()
 elif args.action=='quiesce':
  interfaces=guard(read_config());set_forwarding(interfaces,False);result={'status':'quiesced','forwarding_all_WAN_LAN':forwarding_values(interfaces)}
 elif args.action=='confirm':result=confirm(args.nonce)
 else:result=rollback()
 print(json.dumps(result))
if __name__=='__main__':
 try:main()
 except Exception:print(json.dumps({'status':'failed','message':'fixed gateway190 action failed; inspect root-private transaction and QGA, no blind retry'}));sys.exit(1)
