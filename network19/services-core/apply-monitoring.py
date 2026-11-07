#!/usr/bin/env python3
"""Single role helper. Default inspect; apply requires exact staged bundle + root600 OScommit receipt."""
import argparse,datetime,fcntl,hashlib,importlib.util,json,os,platform,shutil,socket,stat,subprocess,sys,tempfile,time
from pathlib import Path
class Refused(RuntimeError):pass

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def run(args,check=True,timeout=30):
 p=subprocess.run(args,capture_output=True,text=True,timeout=timeout)
 if check and p.returncode:raise Refused('fixed-monitoring-operation-failed:'+args[0])
 return p
def owned(path):
 if path.resolve()!=path or not path.is_file():raise Refused('canonical-file-required')
 st=path.stat()
 if st.st_uid!=0 or st.st_mode&0o022:raise Refused('root-owned-no-group-world-write-required')
 return st

def os_committed(contract,addresses):
 # Require the original NIC MAC and exact new address/prefix, and no old address on any NIC.
 new=contract['new_ip'];old=contract['old_ip'];MAC=contract['MAC'].lower()
 matched=[r for r in addresses if r.get('address','').lower()==MAC and 'UP' in r.get('flags',[])]
 if len(matched)!=1 or not any(a.get('local')==new and a.get('prefixlen')==24 and a.get('scope')=='global' for a in matched[0].get('addr_info',[])):raise Refused('new-IP24-not-UP-on-original-MAC')
 if any(a.get('local')==old for r in addresses for a in r.get('addr_info',[])):raise Refused('old-address-still-present-not-committed')
 return matched[0]['ifname']

def load_module(path):
 spec=importlib.util.spec_from_file_location('readonly_monitor_candidate',path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def candidate_contract(bundle,model):
 role=model['role'];old=model['old_ip'];new=model['new_ip'];rows={r['target_path']:r for r in model['files']};required={'/etc/default/prometheus-node-exporter','/etc/systemd/system/prometheus-node-exporter.service.d/10-private-only.conf','/etc/dell-guest-monitoring/health.json','/opt/dell/guest-monitoring/guest-targets.json','/opt/dell/guest-monitoring/install-guest-baseline.py','/opt/dell/guest-monitoring/collect-guest-health.py'}
 if set(rows)!=required:raise Refused('exact-six-monitoring-files-required')
 for path,row in rows.items():
  local=bundle/path.lstrip('/');owned(local)
  if digest(local)!=row['new_SHA256']:raise Refused('staged-monitoring-SHA-differs')
 health=json.loads((bundle/'etc/dell-guest-monitoring/health.json').read_text());catalog=json.loads((bundle/'opt/dell/guest-monitoring/guest-targets.json').read_text())
 if health['role']!=role or health['private_ip']!=new or len(catalog['roles'])!=12:raise Refused('staged-health-catalog-mismatch')
 selected=next(r for r in catalog['roles'] if r['role']==role)
 if selected['private_ip']!=new:raise Refused('paired-catalog-new-IP-missing')
 drop=(bundle/'etc/systemd/system/prometheus-node-exporter.service.d/10-private-only.conf').read_text()
 if drop.count('--web.listen-address='+new+':9100')!=1 or '--web.listen-address='+old+':9100' in drop:raise Refused('staged-exact-new-listen-required')
 # Executes only pure validation function against staged public config, never collector main or metrics writes.
 collector=load_module(bundle/'opt/dell/guest-monitoring/collect-guest-health.py');collector.validate(health,{new,'127.0.0.1','::1'})
 return rows,health

def atomic(target,data,uid,gid,mode):
 fd,path=tempfile.mkstemp(prefix='.network19-monitor-',dir=target.parent)
 try:
  with os.fdopen(fd,'wb') as f:f.write(data);f.flush();os.fsync(f.fileno())
  os.chown(path,uid,gid);os.chmod(path,mode);os.replace(path,target)
 finally:
  if Path(path).exists():Path(path).unlink()

def listener_contract(text,new):
 entries=[]
 for line in text.splitlines():
  parts=line.split()
  if len(parts)>3 and parts[3].rsplit(':',1)[-1]=='9100':entries.append(parts[3])
 if not entries or set(entries)!={new+':9100'}:raise Refused('node-exporter-not-only-exact-new-IP9100')
 return entries

def wait_listener(new,query=None,clock=time.monotonic,sleeper=time.sleep):
 query=query or (lambda:run(['ss','-H','-ltn','sport = :9100']).stdout)
 deadline=clock()+15
 while True:
  text=query()
  try:return listener_contract(text,new)
  except Refused:
   if clock()>=deadline:raise Refused('exact-new-listener-not-ready-within15s')
   sleeper(.25)

def main():
 p=argparse.ArgumentParser();p.add_argument('--bundle',type=Path,required=True);p.add_argument('--os-contract',type=Path,required=True);p.add_argument('--inspect',action='store_true');p.add_argument('--apply-after-oscommit',action='store_true');p.add_argument('--root-receipt',type=Path);a=p.parse_args()
 sys.dont_write_bytecode=True
 if os.geteuid()!=0 or platform.system()!='Linux' or Path('/etc/pve').exists():raise Refused('assigned-Linux-guest-root-only')
 owned(a.os_contract);bundle=a.bundle
 if bundle.resolve()!=bundle or bundle.stat().st_uid!=0 or bundle.stat().st_mode&0o022:raise Refused('trusted-stage-directory-required')
 rc=bundle/'role-contract.json';owned(rc);model=json.loads(rc.read_text());oscontract=json.loads(a.os_contract.read_text())
 if model['vmid']!=oscontract['vmid'] or model['role']!=oscontract['hostname'] or model['new_ip']!=oscontract['new_ip'] or model['old_ip']!=oscontract['old_ip'] or socket.gethostname().split('.')[0]!=model['role']:raise Refused('role-OS-stage-identity-mismatch')
 rows,health=candidate_contract(bundle,model)
 originals={}
 for path,row in rows.items():
  target=Path(path);st=owned(target)
  if digest(target)!=row['expected_old_SHA256']:raise Refused('active-old-monitoring-SHA-changed-reinventory')
  originals[path]=(target.read_bytes(),st.st_uid,st.st_gid,stat.S_IMODE(st.st_mode))
 if not a.apply_after_oscommit:
  print(json.dumps({'status':'stage-inspected-no-write','vmid':model['vmid'],'role':model['role'],'files':6,'old_and_staged_SHAs_match':True,'paired_new_map_valid':True,'services_changed':False}));return
 if a.root_receipt is None:raise Refused('root600-OScommit-receipt-required')
 st=owned(a.root_receipt)
 if st.st_mode&0o077:raise Refused('receipt-root600-required')
 receipt=json.loads(a.root_receipt.read_text())
 if receipt.get('migration')!='network19' or receipt.get('vmid')!=model['vmid'] or receipt.get('phase')!='OScommitted-monitoring-window' or receipt.get('parent_window_open') is not True:raise Refused('OScommit-window-not-approved')
 if oscontract.get('gateway')!='192.168.19.1' or oscontract.get('DNS')!='192.168.19.1':raise Refused('GW-DNS-contract-mismatch')
 iface=os_committed(oscontract,json.loads(run(['ip','-j','addr']).stdout))
 route=json.loads(run(['ip','-j','route','show','default']).stdout)
 if not any(x.get('gateway')=='192.168.19.1' and x.get('dev')==iface for x in route):raise Refused('new-default-route-not-committed')
 # DNS actual link state is checked without printing unrelated resolvectl fields.
 dns=run(['resolvectl','dns',iface]).stdout
 if dns.strip().split(':',1)[-1].split()!=['192.168.19.1']:raise Refused('new-per-link-DNS-not-committed')
 lock=os.open('/run/lock/dell-network19-monitoring.lock',os.O_WRONLY|os.O_CREAT|os.O_NOFOLLOW,0o600);fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 backup=Path('/root/dell-network19/monitoring')/str(model['vmid']);backup.mkdir(mode=0o700,parents=True,exist_ok=False)
 timer='dell-guest-health.timer';was_active=run(['systemctl','is-active',timer],check=False).stdout.strip()=='active';was_enabled=run(['systemctl','is-enabled',timer],check=False).stdout.strip();written=[]
 try:
  run(['systemctl','stop',timer])
  run(['systemctl','stop','dell-guest-health.service'],check=False)
  for path,(data,uid,gid,mode) in originals.items():
   dest=backup/path.lstrip('/');dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data);dest.chmod(0o600)
  (backup/'original-metadata.json').write_text(json.dumps({'files':{p:{'uid':v[1],'gid':v[2],'mode':v[3]} for p,v in originals.items()},'timer_was_active':was_active,'timer_enable_state':was_enabled}));(backup/'original-metadata.json').chmod(0o600)
  order=['/opt/dell/guest-monitoring/guest-targets.json','/opt/dell/guest-monitoring/install-guest-baseline.py','/opt/dell/guest-monitoring/collect-guest-health.py','/etc/dell-guest-monitoring/health.json','/etc/default/prometheus-node-exporter','/etc/systemd/system/prometheus-node-exporter.service.d/10-private-only.conf']
  for path in order:
   data=(bundle/path.lstrip('/')).read_bytes();_,uid,gid,mode=originals[path];atomic(Path(path),data,uid,gid,mode);written.append(path)
  run(['systemctl','daemon-reload'])
  run(['python3','-B','/opt/dell/guest-monitoring/install-guest-baseline.py','--check-private-ip','--role',model['role']])
  run(['systemctl','restart','prometheus-node-exporter.service'])
  listen=wait_listener(model['new_ip'])
  # Native collector --check does no textfile write and doesn't sign off HTTP2xx itself.
  run(['runuser','--user','prometheus','--','python3','-B','/opt/dell/guest-monitoring/collect-guest-health.py','--check'])
  if was_active:run(['systemctl','start',timer])
  if run(['systemctl','is-enabled',timer],check=False).stdout.strip()!=was_enabled:raise Refused('timer-enable-state-changed')
  proof={'status':'applied-and-local-monitoring-verified','vmid':model['vmid'],'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'listener':listen,'timer_original_activation_restored':True,'collector_access_checked_no_notification':True,'apps_started_or_restarted':False,'prometheus_targetUP_and_textfile_freshness':'root coordinator must verify after scheduled collection','old_files_backup':str(backup),'OS_not_changed_by_helper':True}
  (backup/'result.json').write_text(json.dumps(proof,indent=2));(backup/'result.json').chmod(0o600);print(json.dumps(proof))
 except Exception as error:
  # Reverting monitoring alone on new-only OS would expose stale address; park exporter/timer instead.
  run(['systemctl','stop','prometheus-node-exporter.service'],check=False);run(['systemctl','stop',timer],check=False)
  (backup/'failure.json').write_text(json.dumps({'status':'monitoring-failed-parked','written_paths':written,'restore_only_with_corresponding_OS_oldIP_rollback':True,'error_category':type(error).__name__}));(backup/'failure.json').chmod(0o600)
  raise
 finally:os.close(lock)
if __name__=='__main__':
 try:main()
 except Exception as e:print(json.dumps({'status':'refused-or-failed','error_category':type(e).__name__,'reason':str(e) if isinstance(e,Refused) else 'details-withheld'}));sys.exit(1)
