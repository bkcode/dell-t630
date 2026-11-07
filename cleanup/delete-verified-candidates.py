#!/usr/bin/python3
"""PVE-owned exact retired object cleanup, mandatory full-verified archives and fresh dependencies."""
from pathlib import Path
import os,sys,json,re,hashlib,subprocess,datetime
EXPECTED={104:'publish',103:'publish-base-tpl',101:'data-docker-base-tpl',102:'data-docker-tpl2',105:'java-running-base-tpl',106:'windoge-template',9000:'dell-template-inspect',9002:'dell-linux-clone-test',9003:'dell-docker-clone-test',9004:'dell-docker-clone-a',9005:'dell-linux-clone-b',9006:'dell-docker-clone-b',9020:'dell-restore-baseline',231:'java-prod-02',232:'java-prod-03'}
OUT=Path('/mnt/pve/store/dell-artifacts/cleanup-backups-20261107');ROOT=Path('/root/dell-bootstrap/cleanup')
DISK=re.compile(r'(?:scsi|virtio|ide|sata|unused)\d+|efidisk0|tpmstate0')
def run(a):
 p=subprocess.run(a,capture_output=True,text=True,timeout=120)
 if p.returncode:raise RuntimeError('fixed cleanup action failed:'+a[0])
 return p.stdout
def config(v):return run(['qm','config',str(v)])
def parse(s):return {x.split(': ',1)[0]:x.split(': ',1)[1] for x in s.splitlines() if ': ' in x}
def disks(c):return {k:v.split(',',1)[0] for k,v in c.items() if DISK.fullmatch(k) and v.split(',',1)[0]!='none' and 'media=cdrom' not in v}
def save(path,x):
 t=path.with_suffix('.new');t.write_text(json.dumps(x,indent=2)+'\n');t.chmod(0o600);os.replace(t,path)
def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
 return h.hexdigest()
def dependency_guard(v,c):
 mine=list(disks(c).values());refs=[]
 for p in Path('/etc/pve/qemu-server').glob('*.conf'):
  if not p.stem.isdigit() or int(p.stem)==v:continue
  other=parse(p.read_text().split('\n[',1)[0])
  for key,vol in disks(other).items():
   if any(vol==base or vol.startswith(base+'/') for base in mine):refs.append({'vmid':int(p.stem),'slot':key})
 assert not refs,'disk still referenced by another currentVM'
 if v==103:assert not Path('/etc/pve/qemu-server/104.conf').exists(),'dependent104 must be processed first'
 for vol in mine:
  if vol.startswith('local-lvm:'):
   lv=vol.split(':',1)[1];rows=json.loads(run(['lvs','--reportformat','json','-o','lv_name,origin']))['report'][0]['lv']
   assert not any(x.get('origin','').strip()==lv for x in rows),'thin descendants still exist; review before removal'
def main():
 os.umask(0o077);assert os.geteuid()==0 and Path('/etc/pve').exists();execute=sys.argv[1:]==['--execute'];assert execute or not sys.argv[1:]
 manifest=json.loads((OUT/'manifest.json').read_text());byid={x['vmid']:x for x in manifest if x['status']=='verified'};allcfg={};review=[]
 for v,name in EXPECTED.items():
  b=byid[v];assert b['zstd_test'] and b['VMA_full_verify'];archive=Path(b['archive']);assert archive.parent==OUT and not archive.is_symlink() and archive.stat().st_uid==0 and archive.stat().st_mode&0o077==0 and archive.stat().st_size==b['bytes'];assert sha(archive)==b['sha256']
  s=config(v);c=parse(s);assert c['name']==name and not c.get('lock') and c.get('protection','0')=='0';assert run(['qm','status',str(v)]).strip()=='status: stopped';assert hashlib.sha256(s.encode()).hexdigest()==b['source_config_sha256'],'config changed after backup; review drift';allcfg[v]=c
  review.append({'vmid':v,'name':name,'archive':archive.name,'archive_SHA_verified':True,'VMA_full_verify':True,'disk_slots':sorted(disks(c))})
 report={'at':datetime.datetime.now().isoformat(),'scope':'exact15redundantoldtemplates/QA/duplicateJava;NOT Nexus221,active220/coretemplates','review':review,'execute':execute,'deleted':[],'kept_core_templates':[9001,9010,9011],'shared_artifacts_ISO_not_a_delete_target':True}
 save(ROOT/'delete-review.json',report)
 if not execute:print(json.dumps({'mode':'dryrun-backup-and-config-preflight-passed','candidate_vmids':list(EXPECTED),'no_objects_deleted':True}));return
 for v in EXPECTED:
  c=parse(config(v));assert c==allcfg[v] and run(['qm','status',str(v)]).strip()=='status: stopped'
  dependency_guard(v,c)
  run(['qm','destroy',str(v),'--purge','1'])
  assert not Path('/etc/pve/qemu-server/'+str(v)+'.conf').exists();report['deleted'].append(v);save(ROOT/'delete-review.json',report)
 report['status']='exact-candidates-cleaned-backups-retained';report['at_completed']=datetime.datetime.now().isoformat();save(ROOT/'delete-review.json',report);print(json.dumps({'status':report['status'],'deleted_ids':report['deleted'],'backups_PVE_only_verified':True,'221_220_and_kept_templates_untouched':True}))
if __name__=='__main__':main()
