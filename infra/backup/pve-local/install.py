#!/usr/bin/python3
"""Install only a new private backup namespace and disabled native PVE job."""
import os,socket,json,subprocess,stat,hashlib,datetime,re
from pathlib import Path
p=json.load(__import__('sys').stdin);policy=p['policy'];hook=p['hook'];assert os.geteuid()==0 and socket.gethostname()=='pve' and Path('/etc/pve').is_dir()
assert policy['allowed_vmids']==[100,190,200,201,210,221,230,240,250,260,270] and policy['excluded_vmids']==[220]
assert policy['storage_id']=='dell-local-backup' and policy['job_id']=='dell-local-nightly' and policy['backup_root']=='/mnt/pve/store/dell-artifacts/scheduled-backups'
def run(*a):return subprocess.run(list(a),capture_output=True,text=True,timeout=40,check=True).stdout
def obj(*a):return json.loads(run(*a,'--output-format','json'))
assert not any(v['storage']==policy['storage_id'] for v in obj('pvesh','get','/storage'))
assert not any(v.get('id')==policy['job_id'] for v in obj('pvesh','get','/cluster/backup'))
assert run('timedatectl','show','--property=Timezone','--value').strip()=='Asia/Shanghai'
fs=json.loads(run('findmnt','-J','-T',policy['mountpoint'],'-o','TARGET,FSTYPE,UUID'))['filesystems'];assert len(fs)==1 and fs[0]['uuid']==policy['filesystem_uuid'] and fs[0]['target']==policy['mountpoint']
import shutil;assert shutil.disk_usage(policy['mountpoint']).free>policy['minimum_free_bytes']
rows=obj('pvesh','get','/cluster/resources','--type','vm');assert {v['vmid'] for v in rows if v['status']=='running'}==set(policy['allowed_vmids'])|{220}
assert all(not l.strip().startswith('mailto:') for l in Path('/etc/vzdump.conf').read_text().splitlines() if not l.lstrip().startswith('#'))
base=Path('/root/dell-bootstrap/completion-20261109/pve-local-backup');base.mkdir(parents=True,exist_ok=False);base.chmod(0o700)
files={Path('/usr/local/libexec/dell-local-backup/hook.py'):(hook.encode(),0o755),Path('/etc/dell-local-backup/policy.json'):((json.dumps(policy,indent=2)+'\n').encode(),0o600)}
assert all(not f.exists() and not f.is_symlink() for f in files)
created_dirs=[];created_files=[];storage_created=False;job_created=False
try:
 for dirname in [policy['backup_root'],policy['dumpdir'],policy['state_dir'],policy['tmpdir'],'/usr/local/libexec/dell-local-backup','/etc/dell-local-backup']:
  d=Path(dirname);assert not d.exists() and not d.is_symlink();assert d.resolve(strict=False)==d;mode=0o711 if dirname==policy['tmpdir'] else 0o700;d.mkdir(mode=mode,parents=True,exist_ok=False);d.chmod(mode);created_dirs.append(d)
 for f,(b,mode) in files.items():
  fd=os.open(f,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,mode)
  with os.fdopen(fd,'wb') as out:out.write(b)
  f.chmod(mode);created_files.append(f)
 compile(hook,str(next(iter(files))),'exec')
 run('pvesh','create','/storage','--storage',policy['storage_id'],'--type','dir','--path',policy['backup_root'],'--content','backup','--nodes','pve','--is_mountpoint',policy['mountpoint'],'--create-base-path','0','--create-subdirs','0','--prune-backups',policy['retention']);storage_created=True
 run('pvesh','create','/cluster/backup','--id',policy['job_id'],'--node','pve','--vmid',','.join(map(str,policy['allowed_vmids'])),'--storage',policy['storage_id'],'--mode','snapshot','--compress','zstd','--zstd',str(policy['zstd_threads']),'--bwlimit',str(policy['bwlimit_KiB_per_second']),'--ionice','7','--tmpdir',policy['tmpdir'],'--performance','max-workers=1','--lockwait','0','--script','/usr/local/libexec/dell-local-backup/hook.py','--schedule',policy['schedule'],'--repeat-missed','0','--enabled','0','--prune-backups',policy['retention'],'--notification-mode','legacy-sendmail','--mailto','','--comment','PVE local recovery points only; VM220 excluded; no off-host export');job_created=True
 storage=obj('pvesh','get','/storage/'+policy['storage_id']);job=obj('pvesh','get','/cluster/backup/'+policy['job_id'])
 assert storage['path']==policy['backup_root'] and storage['content']=='backup' and storage['is_mountpoint']==policy['mountpoint']
 assert set(map(int,re.split(r'[,\s]+',job['vmid'].strip())))==set(policy['allowed_vmids']) and not job['enabled'] and job['mode']=='snapshot' and job['notification-mode']=='legacy-sendmail' and not job.get('mailto')
 for d in [Path(policy['backup_root']),Path(policy['dumpdir']),Path(policy['state_dir'])]:assert stat.S_IMODE(d.stat().st_mode)==0o700
except Exception as e:
 errors=[]
 if job_created:
  try:run('pvesh','delete','/cluster/backup/'+policy['job_id'])
  except Exception:errors.append('remove-new-job')
 if storage_created:
  try:run('pvesh','delete','/storage/'+policy['storage_id'])
  except Exception:errors.append('remove-new-storage-config')
 for f in created_files:
  try:f.unlink()
  except OSError:errors.append('remove-new-public-file')
 for d in reversed(created_dirs):
  try:d.rmdir()
  except OSError:errors.append('new-directory-not-empty-retained')
 failure={'status':'install-failed-rollback-attempted','error_type':type(e).__name__,'rollback_errors':errors};q=base/'failure.json';q.write_text(json.dumps(failure));q.chmod(0o600);raise RuntimeError('Backup install failed; inspect protected receipt') from None
result={'at':datetime.datetime.now().astimezone().isoformat(),'status':'private-backup-storage-and-disabled-job-installed','storage':storage,'job':job,'public_file_SHA':{str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in files},'backup_started':False,'migration_performed':False,'guest_configuration_changed':False,'old_archives_touched':False};q=base/'install-receipt.json';q.write_text(json.dumps(result,indent=2)+'\n');q.chmod(0o600);print(json.dumps(result))
