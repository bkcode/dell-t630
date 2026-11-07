#!/usr/bin/python3
"""PVE-only non-destructive stopped candidate backups. Never backup100/220 or deleteVMs."""
from pathlib import Path
import os,sys,json,subprocess,hashlib,datetime
ROOT=Path('/root/dell-bootstrap/cleanup');OUT=Path('/mnt/pve/store/dell-artifacts/cleanup-backups-20261107')
ALLOWED={101,102,103,104,105,106,231,232,9000,9002,9003,9004,9005,9006,9020,221,9001,9010,9011,9040,9041,9042}
def run(args,out=None):
 p=subprocess.run(args,stdout=out if out else subprocess.PIPE,stderr=subprocess.STDOUT if out else subprocess.PIPE)
 if p.returncode:raise RuntimeError('fixed backup/verification action failed:'+args[0])
 return '' if out else p.stdout.decode()
def save(p,x):
 t=p.with_suffix('.new');t.write_text(json.dumps(x,indent=2)+'\n');t.chmod(0o600);os.replace(t,p)
def main():
 os.umask(0o077);assert os.geteuid()==0 and Path('/etc/pve').exists();ids=[int(v) for v in sys.argv[1:]];assert ids and len(ids)==len(set(ids)) and set(ids)<=ALLOWED and not {100,220}&set(ids)
 for p in [ROOT,OUT]:
  assert not p.is_symlink();p.mkdir(mode=0o700,parents=True,exist_ok=True);p.chmod(0o700)
 ledger=OUT/'manifest.json';rows=json.loads(ledger.read_text()) if ledger.exists() else []
 for vmid in ids:
  if any(x['vmid']==vmid and x['status']=='verified' for x in rows):continue
  assert run(['qm','status',str(vmid)]).strip()=='status: stopped','Source must be stopped first'
  cfg=run(['qm','config',str(vmid)]);backupcfg=OUT/('vm'+str(vmid)+'-config.conf');backupcfg.write_text(cfg);backupcfg.chmod(0o600)
  before=set(OUT.glob('vzdump-qemu-'+str(vmid)+'-*.vma.zst'));log=OUT/('vm'+str(vmid)+'-backup-verify.log')
  state={'vmid':vmid,'started_at':datetime.datetime.now().isoformat(),'status':'backing-up','data_exported_from_PVE':False};save(ROOT/'backup-current.json',state)
  try:
   with log.open('ab') as f:
    run(['vzdump',str(vmid),'--dumpdir',str(OUT),'--mode','stop','--compress','zstd'],out=f)
    new=set(OUT.glob('vzdump-qemu-'+str(vmid)+'-*.vma.zst'))-before;assert len(new)==1;archive=new.pop();archive.chmod(0o600)
    state.update(status='verifying',archive=str(archive));save(ROOT/'backup-current.json',state)
    run(['zstd','--test',str(archive)],out=f)
    temporary=OUT/('.verify-vm'+str(vmid)+'.vma');assert not temporary.exists()
    with temporary.open('xb') as raw:
     decompressor=subprocess.run(['zstd','-dc',str(archive)],stdout=raw,stderr=f)
     if decompressor.returncode:raise RuntimeError('zstd-decompression-failed')
    temporary.chmod(0o600)
    run(['vma','verify',str(temporary)],out=f);temporary.unlink()
   h=hashlib.sha256()
   with archive.open('rb') as source:
    for chunk in iter(lambda:source.read(4*1024*1024),b''):h.update(chunk)
   state.update(status='verified',finished_at=datetime.datetime.now().isoformat(),bytes=archive.stat().st_size,sha256=h.hexdigest(),zstd_test=True,VMA_full_verify=True,source_config_sha256=hashlib.sha256(cfg.encode()).hexdigest(),archive_mode=oct(archive.stat().st_mode&0o777),directory_mode=oct(OUT.stat().st_mode&0o777),source_still_stopped=run(['qm','status',str(vmid)]).strip()=='status: stopped')
   assert state['source_still_stopped'];rows.append(state);save(ledger,rows);save(ROOT/'backup-current.json',state)
   for p in OUT.glob('vzdump-qemu-'+str(vmid)+'-*'):p.chmod(0o600)
  except Exception as e:state.update(status='failed-no-delete-permitted',error_category=type(e).__name__);save(ROOT/'backup-current.json',state);raise
 save(ROOT/'backup-job-complete.json',{'finished_at':datetime.datetime.now().isoformat(),'requested_ids':ids,'verified_ids':[r['vmid'] for r in rows if r['status']=='verified'],'VMs_or_data_deleted':False})
if __name__=='__main__':main()
