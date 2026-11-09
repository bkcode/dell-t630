#!/usr/bin/python3
"""Verify the fixed first run, then optionally enable its existing native schedule.
No archive contents, CF digests, notification credentials or publisher keys leave PVE.
"""
import argparse,datetime as dt,hashlib,json,os,re,socket,stat,subprocess
from pathlib import Path
EXPECTED=[100,190,200,201,210,221,230,240,250,260,270]
STATE=Path('/var/lib/dell-local-backup')
POLICY=Path('/etc/dell-local-backup/policy.json')
HOOK=Path('/usr/local/libexec/dell-local-backup/hook.py')
POLICY_SHA='d3e7615137c1456ef450e74a3f5f5ba0e62bbd04912b1070c64669e0df95ad25'
HOOK_SHA='c366ee6a583421efcfe21df312aabe1cec6d0fd8a94c8670f0aae16f6201bf30'

def run(args):
 p=subprocess.run(args,capture_output=True,text=True,timeout=40)
 if p.returncode:raise RuntimeError('fixed native metadata operation failed; raw output withheld')
 return p.stdout

def api(path,*args):return json.loads(run(['pvesh','get',path,*args,'--output-format','json']))
def stamp(s):return dt.datetime.fromisoformat(s).timestamp()
def private(path,mode):
 assert path.resolve()==path and not path.is_symlink()
 s=path.stat();assert s.st_uid==0 and stat.S_IMODE(s.st_mode)==mode

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--enable-reviewed-schedule',action='store_true');a=ap.parse_args()
 assert os.geteuid()==0 and socket.gethostname()=='pve' and Path('/etc/pve').is_dir()
 private(POLICY,0o600);private(STATE,0o700)
 assert hashlib.sha256(POLICY.read_bytes()).hexdigest()==POLICY_SHA
 assert hashlib.sha256(HOOK.read_bytes()).hexdigest()==HOOK_SHA
 p=json.loads(POLICY.read_text());assert p['allowed_vmids']==EXPECTED and p['excluded_vmids']==[220]
 fs=api('/storage/'+p['storage_id']);assert fs['path']==p['backup_root'] and fs['content']=='backup' and fs['is_mountpoint']==p['mountpoint']
 mount=json.loads(run(['findmnt','-J','-T',p['mountpoint'],'-o','TARGET,UUID']))['filesystems']
 assert len(mount)==1 and mount[0]['target']==p['mountpoint'] and mount[0]['uuid']==p['filesystem_uuid']
 for name in ['backup_root','dumpdir']:private(Path(p[name]),0o700)
 for file in ['current.json','last-success.json']:private(STATE/file,0o600)
 ledger=json.loads((STATE/'current.json').read_text());last=json.loads((STATE/'last-success.json').read_text())
 assert ledger==last and ledger['status']=='verified' and ledger['allowed_vmids']==EXPECTED
 assert set(ledger['results'])==set(map(str,EXPECTED)) and not ledger.get('log_permission_error')
 start,end=stamp(ledger['started_at']),stamp(ledger['finished_at']);assert end>=start and 0<=dt.datetime.now(dt.timezone.utc).timestamp()-end<21600
 props=dict(l.split('=',1) for l in run(['systemctl','show','dell-local-backup-first-retry.service','--property=ActiveState,SubState,Result,ExecMainStatus']).splitlines() if '='in l)
 assert props['ActiveState']=='inactive' and props['SubState']=='dead' and props['Result']=='success' and props['ExecMainStatus']=='0'
 assert not api('/nodes/pve/tasks','--source','active','--typefilter','vzdump')
 candidates=[r for r in api('/nodes/pve/tasks','--source','archive','--typefilter','vzdump','--limit','50') if abs(r['starttime']-start)<10]
 assert len(candidates)==1 and candidates[0]['status']=='OK' and candidates[0].get('endtime',0)>=end-3
 task=candidates[0];status=api('/nodes/pve/tasks/'+task['upid']+'/status');assert status['status']=='stopped' and status['exitstatus']=='OK'
 proof=[]
 for vmid in EXPECTED:
  r=ledger['results'][str(vmid)];assert r['status']=='verified' and r['zstd_verified'] is True and r['native_archive_verified'] is True and re.fullmatch('[0-9a-f]{64}',r['sha256'])
  f=Path(p['dumpdir'])/r['archive'];assert f.parent==Path(p['dumpdir']) and re.fullmatch(r'vzdump-(?:lxc|qemu)-'+str(vmid)+r'-[0-9_\-]+\.(?:tar|vma)\.zst',f.name)
  private(f,0o600);s=f.stat();assert stat.S_ISREG(s.st_mode) and s.st_nlink==1 and s.st_size==r['bytes']>0
  proof.append({'vmid':vmid,'bytes':s.st_size,'archive_mode':'0600','zstd_verified':True,'native_archive_verified':True,'private_SHA256_present':True})
 job=api('/cluster/backup/'+p['job_id'])
 expected={'vmid':','.join(map(str,EXPECTED)),'storage':p['storage_id'],'mode':'snapshot','schedule':'03:30','compress':'zstd','zstd':2,'bwlimit':0,'ionice':7,'lockwait':0,'repeat-missed':0,'script':str(HOOK),'tmpdir':p['tmpdir'],'notification-mode':'legacy-sendmail'}
 for k,v in expected.items():assert job.get(k)==v,(k,'native schedule drift; re-review')
 expected.update({'id':p['job_id'],'node':'pve','type':'vzdump','enabled':0,'comment':'PVE local recovery points only; VM220 excluded; no off-host export','prune-backups':{'keep-last':'3','keep-daily':'7','keep-weekly':'4'},'performance':{'max-workers':'1'}})
 assert job==expected,'exact reviewed native job changed; no extra selectors allowed'
 assert not job.get('mailto') and job.get('prune-backups')=={'keep-last':'3','keep-daily':'7','keep-weekly':'4'} and job.get('performance')=={'max-workers':'1'}
 assert job['enabled']==0,'already enabled; inspect receipt instead of rerunning'
 receipt={'at':dt.datetime.now().astimezone().isoformat(),'status':'first-eleven-verified-native-task-OK','run_id':ledger['run_id'],'started_at':ledger['started_at'],'finished_at':ledger['finished_at'],'native_task':{k:task.get(k) for k in ['upid','starttime','endtime','status']},'unit':props,'archives':proof,'total_archive_bytes':sum(r['bytes'] for r in proof),'CF_archive_or_digest_exported':False,'publisher220_included':False,'restore_performed':False,'independent_disaster_recovery':False,'native_prune_before_custom_verification':True,'schedule_enabled':False}
 if a.enable_reviewed_schedule:
  out=STATE/'first-run-enabled-receipt.json';assert not out.exists() and not out.is_symlink(),'existing receipt; inspect instead of rerunning'
  tmp=STATE/('first-run-enabled-receipt.'+ledger['run_id']+'.tmp');assert not tmp.exists() and not tmp.is_symlink()
  try:
   run(['pvesh','set','/cluster/backup/'+p['job_id'],'--enabled','1'])
   after=api('/cluster/backup/'+p['job_id']);assert after=={**job,'enabled':1}
   # Clear only this attempt's stale unit flag; logs and native task history remain.
   old=dict(l.split('=',1) for l in run(['systemctl','show','dell-local-backup-first.service','--property=ActiveState,SubState']).splitlines() if '='in l)
   if old.get('ActiveState')=='failed':run(['systemctl','reset-failed','dell-local-backup-first.service'])
   receipt.update(schedule_enabled=True,native_job=after,old_failed_attempt_unit_flag_cleared=old.get('ActiveState')=='failed',failure_logs_and_native_tasks_preserved=True)
   fd=os.open(tmp,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
   with os.fdopen(fd,'w') as f:json.dump(receipt,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
   os.replace(tmp,out)
  except Exception:
   run(['pvesh','set','/cluster/backup/'+p['job_id'],'--enabled','0'])
   assert api('/cluster/backup/'+p['job_id'])['enabled']==0
   raise RuntimeError('enable window failed; native schedule verified disabled; history preserved') from None
 print(json.dumps(receipt))
if __name__=='__main__':main()
