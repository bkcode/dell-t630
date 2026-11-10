#!/usr/bin/env python3
"""One-time VM280 FileBrowser retirement; preserve resources, NFS and private state."""
import datetime,hashlib,json,os,re,socket,stat,subprocess,tempfile
from pathlib import Path
from zoneinfo import ZoneInfo

BACKUP=Path('/root/dell-filebrowser-retired-20261110')
HEALTH=Path('/etc/dell-guest-monitoring/health.json')
UNITS=['dell-filebrowser.service','dell-filebrowser-firewall.service']
PROTECTED=['nfs-server.service','nfs-mountd.service','srv-resources.mount','dell-resources-firewall.service','ssh.service','systemd-networkd.service','prometheus-node-exporter.service']
NFS_FILES=['/etc/exports.d/dell-resources.exports','/etc/nfs.conf.d/90-dell-resources.conf','/etc/dell-resources/input.nft','/etc/systemd/system/srv-resources.mount','/etc/systemd/system/nfs-server.service.d/50-dell-resources.conf','/etc/systemd/system/dell-resources-firewall.service']
EXPECTED={'dell-filebrowser.service':'94aec8ba0232171b65b1671b12c4dfa8cc4891c3926a1745cd19d4eb25974ca7','dell-filebrowser-firewall.service':'bd91a8e2c54aabe66177aa269327f4f117a93d06f964f853227bd0636c0ccf84'}

def need(value,code):
 if not value:raise RuntimeError(code)

def run(args,allowed=(0,),timeout=30):
 p=subprocess.run(args,capture_output=True,text=True,timeout=timeout)
 need(p.returncode in allowed,'fixed-native-command-failed')
 return p.stdout.strip()

def atomic(path,raw,mode=0o600):
 fd,tmp=tempfile.mkstemp(prefix='.nfs-only-',dir=path.parent)
 try:
  with os.fdopen(fd,'wb')as stream:os.fchmod(stream.fileno(),mode);stream.write(raw);stream.flush();os.fsync(stream.fileno())
  os.replace(tmp,path)
 finally:
  if os.path.exists(tmp):os.unlink(tmp)

def metadata(path):
 p=Path(path);s=p.lstat();need(not p.is_symlink(),'symlink-refused')
 return {'uid':s.st_uid,'gid':s.st_gid,'mode':stat.S_IMODE(s.st_mode),'device':s.st_dev,'inode':s.st_ino}

def frames():
 return {n:run(['systemctl','show',n,'--property=MainPID,ExecMainStartTimestampMonotonic,ActiveState,SubState'])for n in PROTECTED}

def units():
 return {n:dict(x.split('=',1)for x in run(['systemctl','show',n,'--property=ActiveState,SubState,MainPID,UnitFileState']).splitlines()if'='in x)for n in UNITS}

def main():
 os.umask(0o077)
 need(os.geteuid()==0 and socket.gethostname()=='resource-service'and not Path('/etc/pve').exists(),'VM280-root-only')
 need(not BACKUP.exists(),'retirement-transaction-already-exists-review-before-resume')
 need(json.loads(run(['python3','-I','-B','/opt/dell/resources/guard.py','--role','server']))['mount_guard'],'NFS-guard-required')
 need(metadata('/srv/resources')['mode']==0o2770,'resource-root-mode-required')
 unit_paths={name:Path('/etc/systemd/system')/name for name in UNITS}
 oldunits={name:path.read_bytes()for name,path in unit_paths.items()}
 for name,path in unit_paths.items():
  need(metadata(path)['uid']==0 and hashlib.sha256(oldunits[name]).hexdigest()==EXPECTED[name],'original-unit-drift')
 health_raw=HEALTH.read_bytes();health=json.loads(health_raw)
 expected_services=['ssh.service','qemu-guest-agent.service','prometheus-node-exporter.service','nfs-server.service','dell-resources-firewall.service','dell-filebrowser.service']
 expected_http=[{'name':'filebrowser-http-health','url':'http://192.168.19.80:8080/health'}]
 need(health['role']=='resource-service'and health['private_ip']=='192.168.19.80'and health['services']==expected_services and health['http_checks']==expected_http,'original-resource-health-contract-drift')
 after_health=dict(health,services=expected_services[:-1],http_checks=[])
 before_frames=frames();nfs_before={p:Path(p).read_bytes()for p in NFS_FILES}
 exports_before=run(['exportfs','-v']);versions_before=Path('/proc/fs/nfsd/versions').read_bytes()
 state_before=metadata('/var/lib/dell-filebrowser');root_before=metadata('/srv/resources')
 secret_paths=[Path('/etc/dell-filebrowser/secrets')/n for n in ['jwt-key','admin-password','login.json']]
 secrets_before={str(p):metadata(p)for p in secret_paths}
 need(all(m['uid']==0 and m['mode']==0o600 for m in secrets_before.values()),'original-private-secret-protection-required')
 web_table=run(['nft','list','table','inet','dell_filebrowser_input'])+'\n'
 nfs_table=run(['nft','-s','list','table','inet','dell_resources_input'])
 old_states=units();need(all(x['UnitFileState']=='enabled'and x['ActiveState']=='active'for x in old_states.values()),'original-management-active-required')
 BACKUP.mkdir(mode=0o700);BACKUP.chmod(0o700)
 for name,raw in oldunits.items():atomic(BACKUP/name,raw)
 atomic(BACKUP/'health.json',health_raw);atomic(BACKUP/'filebrowser-input.nft',web_table.encode())
 journal={'phase':'prepared-before-retirement','units':old_states,'secret_or_resource_contents_copied':False}
 atomic(BACKUP/'journal.json',(json.dumps(journal,indent=2)+'\n').encode())
 try:
  # Remove only the retired checks before stopping the component; NFS checks stay live.
  need(HEALTH.read_bytes()==health_raw,'health-CAS-drift')
  atomic(HEALTH,(json.dumps(after_health,indent=2)+'\n').encode(),0o644)
  run(['systemctl','disable','--now',*UNITS],timeout=60)
  need(run(['ss','-H','-lnt','sport = :8080'])=='','retired-web-listener-remains')
  for name,path in unit_paths.items():
   need(path.read_bytes()==oldunits[name],'unit-CAS-drift')
   path.unlink()
  run(['systemctl','daemon-reload']);run(['systemctl','mask',*UNITS])
  run(['nft','delete','table','inet','dell_filebrowser_input'])
  run(['systemctl','start','dell-guest-health.service'])
  need(all(x['UnitFileState']=='masked'and x['ActiveState']=='inactive'for x in units().values()),'management-not-inactive-and-masked')
  need(run(['ss','-H','-lnt','sport = :8080'])=='','web-port-not-closed')
  nft=subprocess.run(['nft','list','table','inet','dell_filebrowser_input'],capture_output=True)
  need(nft.returncode!=0,'retired-web-table-remains')
  need(frames()==before_frames,'protected-service-restarted-or-changed')
  need(all(Path(p).read_bytes()==raw for p,raw in nfs_before.items()),'NFS-config-changed')
  need(run(['exportfs','-v'])==exports_before and Path('/proc/fs/nfsd/versions').read_bytes()==versions_before,'NFS-export-or-version-changed')
  need(run(['nft','-s','list','table','inet','dell_resources_input'])==nfs_table,'NFS-input-policy-changed')
  need(metadata('/srv/resources')==root_before and metadata('/var/lib/dell-filebrowser')==state_before,'resource-or-private-state-identity-changed')
  need(all(metadata(p)==secrets_before[str(p)]for p in secret_paths),'original-private-secret-metadata-changed')
  need(json.loads(run(['python3','-I','-B','/opt/dell/resources/guard.py','--role','server']))['mount_guard'],'final-NFS-guard-failed')
  metrics=Path('/var/lib/prometheus/node-exporter-textfile/dell_guest_health.prom').read_text()
  need('dell-filebrowser'not in metrics and 'filebrowser-http-health'not in metrics,'retired-component-metrics-remain')
  need(all('dell_guest_service_active{role="resource-service",service="'+name+'"} 1'in metrics for name in expected_services[:-1]),'five-NFS-role-service-metrics-not-UP')
 except BaseException:
  # Restore only this transaction if incomplete. Shared data/NFS are never modified here.
  for name,path in unit_paths.items():
   if path.is_symlink()and os.readlink(path)=='/dev/null':path.unlink()
   atomic(path,oldunits[name],0o644)
  atomic(HEALTH,health_raw,0o644)
  table=subprocess.run(['nft','list','table','inet','dell_filebrowser_input'],capture_output=True)
  if table.returncode!=0:run(['nft','-f',str(BACKUP/'filebrowser-input.nft')])
  run(['systemctl','daemon-reload']);run(['systemctl','enable','--now',*UNITS],timeout=60)
  run(['systemctl','start','dell-guest-health.service'])
  journal['phase']='retirement-failed-original-service-restored';atomic(BACKUP/'journal.json',(json.dumps(journal,indent=2)+'\n').encode())
  raise
 journal['phase']='retired-NFS-only-verified';atomic(BACKUP/'journal.json',(json.dumps(journal,indent=2)+'\n').encode())
 result={'at':datetime.datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),'status':'FileBrowser-retired-NFS-only-verified','vmid':280,'retired_units':units(),'web_TCP_8080_listener_absent':True,'FileBrowser_input_table_absent':True,'NFS_guard_passed':True,'NFS_configs_exports_versions_and_input_unchanged':True,'protected_service_identities_unchanged':True,'NFS_or_client_restarts':False,'health_before_services':expected_services,'health_after_services':after_health['services'],'health_before_HTTP_checks':expected_http,'health_after_HTTP_checks':[],'current_health_service_count':5,'current_health_service_metrics_UP':True,'private_state_and_secret_metadata_preserved':True,'resource_root_identity_permissions_preserved':True,'resource_file_or_secret_contents_read_copied_deleted':False,'protected_local_rollback_directory':str(BACKUP),'rollback_directory_mode':'0700','rollback_files_mode':'0600','shared_file_data_migration':False}
 atomic(BACKUP/'result.json',(json.dumps(result,indent=2)+'\n').encode());print(json.dumps(result))

if __name__=='__main__':
 try:main()
 except Exception as error:
  print(json.dumps({'status':'retirement-not-confirmed','error':str(error)if re.fullmatch('[A-Za-z0-9-]{1,100}',str(error))else'withheld','error_type':type(error).__name__}));raise SystemExit(1)
