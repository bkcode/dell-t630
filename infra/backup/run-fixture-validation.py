#!/usr/bin/env python3
"""Approved A-D: only synthetic200/201 fixture backups, isolated restore, private Mac artifacts."""
import datetime,hashlib,importlib.util,json,os,shlex,subprocess,sys,tarfile,uuid
from pathlib import Path
from zoneinfo import ZoneInfo
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent;E=ROOT/'evidence/implementation'
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
control=load('backup_control',ROOT/'scripts/control.py');deployment=load('backup_data_deployment',ROOT/'infra/data/deploy-guests.py')
def now():return datetime.datetime.now(ZoneInfo('Asia/Shanghai')).isoformat()
def save(path,value):
 tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n');tmp.replace(path)
COPY=r'''import os,sys,socket,ast,json,hashlib
from pathlib import Path
role=ROLE
if os.geteuid()!=0 or socket.gethostname().split('.')[0]!=role or Path('/etc/pve').exists():raise SystemExit('fixture tool target rejected')
p=Path('/tmp/dell-app-backup')
if p.resolve(strict=False)!=p:raise SystemExit('fixture tool path symlink rejected')
p.mkdir(mode=0o700,exist_ok=True);p.chmod(0o700)
data=sys.stdin.buffer.read(131073)
if len(data)>131072:raise SystemExit('fixture tool too large')
ast.parse(data.decode());target=p/'fixture-worker.py'
if target.is_symlink():raise SystemExit('fixture tool file symlink rejected')
fd=os.open(target,os.O_WRONLY|os.O_CREAT|os.O_TRUNC|os.O_NOFOLLOW,0o700)
with os.fdopen(fd,'wb') as out:out.write(data)
print(json.dumps({'public_tool_copied':True,'sha256':hashlib.sha256(data).hexdigest(),'secrets_transferred':False}))'''

def raw_guest_args(target,command):
 proxy=shlex.join(control.BASE+['-W','%h:%p','root@192.168.21.22'])
 return control.BASE+['-o','HostKeyAlias='+target['host_key_alias'],'-o','ProxyCommand='+proxy,'ub@'+target['ip'],command]

def check_archive(path):
 allowed={'manifest.json','mysql-fixture.sql','nacos-filtered-config.sql','redis-fixture.dump','rabbit-fixture-definitions.json'}
 with tarfile.open(path) as t:
  members=t.getmembers()
  if any(not m.isfile() or m.name not in allowed or m.size>1024*1024 for m in members):raise RuntimeError('received synthetic artifact archive scope rejected')
  manifest=json.loads(t.extractfile('manifest.json').read())
  if manifest['kind']!='synthetic-backup-fixtures-only' or manifest['contains_credentials'] or manifest['contains_business_data'] or not manifest['isolated_restore_verified'] or not manifest.get('temporary_containers_removed'):raise RuntimeError('synthetic manifest verification failed')
  if {m.name for m in members}!={'manifest.json',*manifest['files']}:raise RuntimeError('archive file list mismatch')
  for name,digest in manifest['files'].items():
   if hashlib.sha256(t.extractfile(name).read()).hexdigest()!=digest:raise RuntimeError('received synthetic artifact checksum mismatch')
 return {'role':manifest['role'],'coverage':manifest['coverage'],'verification':manifest['verification'],'files':sorted(manifest['files']),'contains_credentials':False,'contains_business_data':False}

def main():
 if sys.argv[1:]!=['--execute-approved-synthetic-only']:raise SystemExit('explicit approved synthetic-only flag required')
 nonce=uuid.uuid4().hex;private=ROOT/'private/backups/app'/nonce
 if private.resolve(strict=False)!=private:raise RuntimeError('private synthetic backup directory symlink rejected')
 private.mkdir(mode=0o700,parents=True,exist_ok=False)
 access=json.loads((E/'private-guest-access.json').read_text())['roles'];rows={x['target']['vmid']:x for x in access}
 data=(HERE/'fixture-worker.py').read_bytes();targets={200:rows[200]['target'],201:rows[201]['target']};created=[]
 report={'started_at':now(),'mode':'approved-pure-synthetic-fixtures-only','work_id':nonce,'vmids':[200,201],'source_business_data_exported':False,'source_credentials_exported':False,'cf_accessed':False,'host_network_changed':False,'real_messages_sent':0,'steps':[],'status':'running'}
 evidence=E/'app-backup-fixture-validation.json'
 snapshots={}
 def step(vmid,name,command,payload=None,timeout=180):
  print(json.dumps({'vmid':vmid,'phase':name}),flush=True)
  r=control.guest(vmid,command,data=payload,timeout=timeout,info=targets[vmid]);report['steps'].append({'vmid':vmid,'name':name,'exit_code':r['exit_code'],'stdout':r['stdout'],'stderr':r['stderr']});save(evidence,report)
  if r['exit_code']:raise RuntimeError('fixture '+name+' failed on '+str(vmid)+'; output retained without secrets')
  return r['stdout']
 def phase(vmid,name,timeout=180):
  return step(vmid,name,shlex.join(['sudo','-n','python3','/tmp/dell-app-backup/fixture-worker.py',name,'--work-id',nonce]),timeout=timeout)
 try:
  for vmid,role in [(200,'prod-db'),(201,'prod-infra')]:
   expected='data-prod-db' if vmid==200 else 'data-prod-infra'
   if rows[vmid]['name']!=expected or rows[vmid]['status']!='ssh-verified' or targets[vmid]['ip']!=('10.63.10.10' if vmid==200 else '10.63.10.11'):raise RuntimeError('backup private guest proof mismatch')
   snapshots[vmid]=json.loads(step(vmid,'source-before', 'sudo -n python3 -',deployment.SNAPSHOT.replace('role=ROLE','role='+repr(role)).encode(),90))
   step(vmid,'copy-public-fixture-tool','sudo -n python3 -c '+shlex.quote(COPY.replace('role=ROLE','role='+repr(expected))),data,90)
   created.append(vmid);phase(vmid,'prepare')
  # 201 creates the Nacos row;200 snapshots only that row from the authoritative external MySQL.
  phase(200,'snapshot');phase(201,'snapshot')
  phase(200,'verify',360);phase(201,'verify',360)
  report['mac_artifacts']=[]
  for vmid in [200,201]:
   dest=private/('vm'+str(vmid)+'-synthetic-fixture.tar');fd=os.open(dest,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
   command=shlex.join(['sudo','-n','python3','/tmp/dell-app-backup/fixture-worker.py','export','--work-id',nonce])
   print(json.dumps({'vmid':vmid,'phase':'stream-verified-pure-synthetic-artifact-to-private-Mac'}),flush=True)
   with os.fdopen(fd,'wb') as file:r=subprocess.run(raw_guest_args(targets[vmid],command),stdout=file,stderr=subprocess.PIPE,timeout=120)
   if r.returncode:raise RuntimeError('synthetic archive transfer failed; no alternate transfer or policy bypass attempted')
   record=check_archive(dest);record.update(vmid=vmid,relative_private_path=str(dest.relative_to(ROOT)),archive_sha256=hashlib.sha256(dest.read_bytes()).hexdigest(),mode=oct(dest.stat().st_mode&0o777));report['mac_artifacts'].append(record);save(evidence,report)
  report['status']='synthetic-backup-isolated-restore-and-private-Mac-archive-verified'
 except Exception as error:
  report.update(status='failed',error=str(error));raise
 finally:
  report['cleanup']=[]
  for vmid in created:
   try:result=phase(vmid,'cleanup');report['cleanup'].append({'vmid':vmid,'status':'source-owned-fixtures-cleaned','result':json.loads(result)})
   except Exception as error:report['cleanup'].append({'vmid':vmid,'status':'cleanup-pending','error':str(error)});report['status']='failed-cleanup-pending'
  report['source_service_identity_unchanged']=True
  for vmid,role in [(200,'prod-db'),(201,'prod-infra')]:
   try:
    after=json.loads(step(vmid,'source-after','sudo -n python3 -',deployment.SNAPSHOT.replace('role=ROLE','role='+repr(role)).encode(),90))
    before={x['service']:(x['container_id'],x['started_at'],x['pid']) for x in snapshots.get(vmid,{}).get('containers',[])}
    current={x['service']:(x['container_id'],x['started_at'],x['pid']) for x in after['containers']}
    if not before or before!=current:report['source_service_identity_unchanged']=False;report['status']='failed-source-state-changed'
   except Exception as error:report['source_service_identity_unchanged']=False;report['status']='failed-source-readback';report['source_readback_error']=str(error)
  report['finished_at']=now();save(evidence,report)
 print(json.dumps({'status':report['status'],'vmids':[200,201],'source_services_unchanged':report['source_service_identity_unchanged'],'private_synthetic_archives':len(report.get('mac_artifacts',[]))}),flush=True)
 return 0 if report['status']=='synthetic-backup-isolated-restore-and-private-Mac-archive-verified' else 1

if __name__=='__main__':raise SystemExit(main())
