#!/usr/bin/python3
"""190 owned DNS files only; no nft/address/sysctl mutation or non-DNS restart."""
import base64,datetime,fcntl,hashlib,importlib.util,json,os,signal,socket,stat,struct,subprocess,sys,tempfile,time,uuid
from pathlib import Path
ETC=Path('/etc/dell-gateway19');CFG=ETC/'config.json';DNSCONF=ETC/'dnsmasq.conf';STATE=Path('/var/lib/dell-gateway19');DNS='dell-gateway19-dnsmasq.service'
NON_DNS=['dell-gateway19-firewall.service','dell-gateway19-ready.service','systemd-networkd.service','ssh.service','systemd-resolved.service']
KEEP={('artifact-service','192.168.19.31'),('publish-service','192.168.19.30')}
REMOVALS={('data-docker-base-tpl','192.168.19.101'),('publish-legacy','192.168.19.104'),('java-prod-02','192.168.19.41'),('java-prod-03','192.168.19.42'),('dell-template-inspect','192.168.19.190'),('dell-linux-clone-test','192.168.19.191'),('dell-docker-clone-test','192.168.19.192'),('dell-docker-clone-a','192.168.19.193'),('dell-linux-clone-b','192.168.19.194'),('dell-docker-clone-b','192.168.19.195'),('dell-restore-baseline','192.168.19.196')}
def run(args,timeout=30):
 r=subprocess.run(args,capture_output=True,text=True,timeout=timeout)
 if r.returncode:raise RuntimeError('fixed DNS action failed; raw output withheld')
 return r.stdout

def load():
 path=Path('/usr/local/libexec/dell-gateway19/manage.py')
 if path.is_symlink() or path.stat().st_uid!=0 or path.stat().st_mode&0o022:raise RuntimeError('trusted gateway code required')
 s=importlib.util.spec_from_file_location('existing_gateway_runtime',path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);m.guard_identity();return m

def safe(path):
 if path.is_symlink() or path.resolve(strict=False)!=path:raise RuntimeError('symlink path rejected')
 return path

def put(path,data,mode):
 safe(path);fd,temp=tempfile.mkstemp(prefix='.'+path.name+'-',dir=path.parent)
 try:
  with os.fdopen(fd,'wb') as out:out.write(data);out.flush();os.fsync(out.fileno())
  os.chown(temp,0,0);os.chmod(temp,mode);os.replace(temp,path)
 finally:Path(temp).unlink(missing_ok=True)

def normalize(value):
 if isinstance(value,list):return [normalize(x) for x in value]
 if isinstance(value,dict):return {k:({} if k=='counter' else normalize(v)) for k,v in value.items() if k not in ('handle','metainfo')}
 return value

def snapshot(m):
 cfg=m.read_config();interfaces=m.guard(cfg,True);rules=json.loads(run(['nft','-j','list','ruleset']));filtered=[x for x in rules['nftables'] if 'metainfo'not in x]
 times={name:run(['systemctl','show',name,'-p','MainPID','-p','ExecMainStartTimestampMonotonic','-p','ActiveState','-p','SubState']).splitlines() for name in NON_DNS}
 addresses=json.loads(run(['ip','-j','addr']));macs={role:{'name':name,'mac':next(x['address'] for x in addresses if x['ifname']==name),'v4':[a['local']+'/'+str(a['prefixlen']) for x in addresses if x['ifname']==name for a in x.get('addr_info',[]) if a.get('family')=='inet']} for role,name in interfaces.items()}
 lease=Path('/var/lib/misc/dnsmasq.leases').stat();ssh=run(['sshd','-T']);auth={x.split()[0]:x.split()[1] for x in ssh.splitlines() if x.split()[0] in ('pubkeyauthentication','passwordauthentication','kbdinteractiveauthentication')}
 return {'persistent_nonDNS_services':times,'normalized_nft_sha256':hashlib.sha256(json.dumps(normalize(filtered),sort_keys=True).encode()).hexdigest(),'routes':json.loads(run(['ip','-j','route'])),'MAC_IPs':macs,'forwarding_all_WAN_LAN':m.forwarding_values(interfaces),'ip_forward':Path('/proc/sys/net/ipv4/ip_forward').read_text().strip(),'lease_metadata':{'uid':lease.st_uid,'gid':lease.st_gid,'mode':oct(lease.st_mode&0o777)},'DNS_uid_caps':run(['systemctl','show',DNS,'-p','User','-p','Group','-p','AmbientCapabilities','-p','CapabilityBoundingSet','-p','NoNewPrivileges','-p','ProtectSystem','-p','ReadWritePaths']).splitlines(),'SSH_auth':auth,'WireGuard_client_access':cfg.get('WireGuard_client_access')}

def dns_query(name,proto):
 identifier=0x1907;question=struct.pack('!HHHHHH',identifier,0x100,1,0,0,0)+b''.join(bytes([len(x)])+x.encode() for x in name.split('.'))+b'\0'+struct.pack('!HH',1,1)
 with socket.socket(socket.AF_INET,socket.SOCK_DGRAM if proto=='UDP' else socket.SOCK_STREAM) as sock:
  sock.settimeout(3)
  if proto=='UDP':sock.sendto(question,('192.168.19.1',53));body=sock.recv(4096)
  else:
   sock.connect(('192.168.19.1',53));sock.sendall(struct.pack('!H',len(question))+question);head=sock.recv(2)
   if len(head)!=2:raise RuntimeError('DNS TCP response truncated')
   size=struct.unpack('!H',head)[0];body=b''
   while len(body)<size:
    part=sock.recv(size-len(body))
    if not part:raise RuntimeError('DNS body truncated')
    body+=part
 ident,flags,questions,count,_,_=struct.unpack('!HHHHHH',body[:12])
 if ident!=identifier:raise RuntimeError('DNS ID mismatch')
 def skip(pos):
  for _ in range(128):
   value=body[pos]
   if value&0xc0==0xc0:return pos+2
   pos+=1
   if not value:return pos
   pos+=value
  raise RuntimeError('DNS name bound')
 pos=12
 for _ in range(questions):pos=skip(pos)+4
 records=[]
 for _ in range(count):
  pos=skip(pos);kind,cls,ttl,length=struct.unpack('!HHIH',body[pos:pos+10]);pos+=10
  if kind==1 and cls==1 and length==4:records.append(socket.inet_ntoa(body[pos:pos+length]))
  pos+=length
 return {'rcode':flags&15,'A':records}

def assert_delta(old,new,p,interfaces):
 p.validate_config(old);p.validate_config(new);keys={'hosts','migration_plan_sha256'}
 if {k:v for k,v in old.items() if k not in keys}!={k:v for k,v in new.items() if k not in keys}:raise RuntimeError('only DNS hosts/provenance delta permitted')
 pairs=lambda c:{(x['role'],x['address']) for x in c['hosts']};before,after=pairs(old),pairs(new)
 if not KEEP.issubset(before) or not KEEP.issubset(after) or after-before or before-after!=before.intersection(REMOVALS):raise RuntimeError('only approved present retired hosts removable, Nexus31 retained')
 if p.nft(old,interfaces)!=p.nft(new,interfaces):raise RuntimeError('DNS cleanup cannot alter expected nft bytes')
 return sorted(before-after)

def main():
 if sys.argv[1:]!=['--reviewed-190-DNS-only']:raise RuntimeError('explicit root DNS-only window required')
 m=load();signal.signal(signal.SIGHUP,signal.SIG_IGN);lock=os.open(STATE/'transaction.lock',os.O_RDWR|os.O_NOFOLLOW);fcntl.flock(lock,fcntl.LOCK_EX)
 if (STATE/'pending.json').exists():raise RuntimeError('another gateway transaction pending')
 raw=sys.stdin.buffer.read(131073)
 if len(raw)>131072:raise RuntimeError('bounded public input')
 request=json.loads(raw)
 if set(request)!={'new_config','expected_old_config_sha256','expected_old_dns_sha256'}:raise RuntimeError('fixed request schema')
 for path in [CFG,DNSCONF]:
  safe(path);st=path.stat()
  if st.st_uid!=0 or st.st_mode&0o022:raise RuntimeError('root-trusted config files required')
 old_cfg=CFG.read_bytes();old_dns=DNSCONF.read_bytes()
 if hashlib.sha256(old_cfg).hexdigest()!=request['expected_old_config_sha256'] or hashlib.sha256(old_dns).hexdigest()!=request['expected_old_dns_sha256']:raise RuntimeError('CAS failed; current DNS/config drift')
 old=m.read_config();new=request['new_config'];p=m.load_policy();interfaces=m.guard(old,True);removed=assert_delta(old,new,p,interfaces);before=snapshot(m);lease_before=Path('/var/lib/misc/dnsmasq.leases').stat().st_size
 root=STATE/'dns-cleanup';root.mkdir(mode=0o700,exist_ok=True);root.chmod(0o700);backup=root/uuid.uuid4().hex;backup.mkdir(mode=0o700);put(backup/'config.before.json',old_cfg,0o600);put(backup/'dnsmasq.before.conf',old_dns,0o600)
 stage=Path(tempfile.mkdtemp(prefix='dell-dns-only-',dir='/run'));stage.chmod(0o755);candidate=stage/'dnsmasq.conf';new_dns=p.dnsmasq(new,interfaces).encode();candidate.write_bytes(new_dns);candidate.chmod(0o644)
 syntax=run(['runuser','--user','dnsmasq','--','/usr/sbin/dnsmasq','--test','--conf-file='+str(candidate)])
 result={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'190-owned-DNS-files-and-DNS-unit-only','status':'pending','backup_directory_190_private':str(backup),'approved_removed':removed,'retained_aliases':sorted(KEEP),'native_dnsmasq_test_exit':0,'lease_contents_read_or_overwritten_by_tool':False,'lease_bytes_before':lease_before,'before':before,'DNS_PID_before':run(['systemctl','show',DNS,'-p','MainPID']).strip()}
 try:
  put(CFG,(json.dumps(new,indent=2)+'\n').encode(),0o600);put(DNSCONF,new_dns,0o644);run(['systemctl','restart',DNS]);m.check()
  queries={}
  for row in new['hosts']:
   name=row['role']+'.dell.home.arpa';values={proto:dns_query(name,proto) for proto in ['UDP','TCP']};queries[name]=values
   if any(x['rcode']!=0 or x['A']!=[row['address']] for x in values.values()):raise RuntimeError('retained DNS A mismatch')
  retired={}
  for name,address in removed:
   domain=name+'.dell.home.arpa';values={proto:dns_query(domain,proto) for proto in ['UDP','TCP']};retired[domain]=values
   if any(x['rcode']!=3 or x['A'] for x in values.values()):raise RuntimeError('retired DNS must be NXDOMAIN')
  after=snapshot(m)
  if before!=after:raise RuntimeError('DNS-only invariant changed; rollback only files/DNS unit')
  result.update(status='DNS-only-cleanup-applied-verified',after=after,nonDNS_invariants_unchanged=True,retained_A_queries=queries,retired_NXDOMAIN_queries=retired,DNS_PID_after=run(['systemctl','show',DNS,'-p','MainPID']).strip(),lease_bytes_after=Path('/var/lib/misc/dnsmasq.leases').stat().st_size)
 except BaseException:
  put(CFG,old_cfg,0o600);put(DNSCONF,old_dns,0o644);run(['systemctl','restart',DNS]);m.check();result.update(status='failed-original-DNS-files-restored',rollback_nonDNS_invariants_unchanged=snapshot(m)==before);put(backup/'receipt.json',(json.dumps(result,indent=2)+'\n').encode(),0o600);print(json.dumps(result));return 1
 finally:
  candidate.unlink(missing_ok=True);stage.rmdir()
 put(backup/'receipt.json',(json.dumps(result,indent=2)+'\n').encode(),0o600);print(json.dumps(result));return 0
if __name__=='__main__':
 try:sys.exit(main())
 except Exception:print(json.dumps({'status':'failed','message':'fixed DNS-only action rejected/failed; no policy broadening attempted'}));sys.exit(1)
