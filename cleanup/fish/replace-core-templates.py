#!/usr/bin/python3
"""Replace only stopped generic core templates with fully verified fish candidate archives."""
from pathlib import Path
import sys,json,subprocess,hashlib,datetime,os,re
OUT=Path('/mnt/pve/store/dell-artifacts/cleanup-backups-20261107');ROOT=Path('/root/dell-bootstrap/cleanup')
JOBS=[(9010,9040,'tpl-linux-base','local-lvm','dell-linux-default-user.yaml'),(9001,9041,'tpl-docker-base','local-lvm','dell-docker-default-user.yaml'),(9011,9042,'tpl-java-acceptance','store','dell-linux-default-user.yaml')]
def run(a,timeout=180):
 p=subprocess.run(a,capture_output=True,text=True,timeout=timeout)
 if p.returncode:raise RuntimeError('fixed coretemplate action failed:'+a[1])
 return p.stdout
def cfg(v):return run(['qm','config',str(v)])
def parse(s):return {l.partition(': ')[0]:l.partition(': ')[2] for l in s.splitlines() if ': 'in l}
def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for x in iter(lambda:f.read(4*1024*1024),b''):h.update(x)
 return h.hexdigest()
def dependencies(v,c):
 vols=[val.split(',',1)[0] for k,val in c.items() if re.fullmatch(r'(?:scsi|virtio|sata|unused)\d+|efidisk0|tpmstate0',k)]
 for p in Path('/etc/pve/qemu-server').glob('*.conf'):
  if not p.stem.isdigit() or int(p.stem)==v:continue
  o=parse(p.read_text().split('\n[',1)[0])
  for k,val in o.items():
   if re.fullmatch(r'(?:scsi|virtio|sata|unused)\d+|efidisk0|tpmstate0',k):
    ref=val.split(',',1)[0];assert not any(ref==base or ref.startswith(base+'/') for base in vols),'retainedVMstillreferencesoldtemplate'
 rows=json.loads(run(['lvs','--reportformat','json','-o','lv_name,origin']))['report'][0]['lv']
 for vol in vols:
  if vol.startswith('local-lvm:'):assert not any(x.get('origin','').strip()==vol.split(':',1)[1] for x in rows),'thin descendants prevent replacement'
def save(x):
 p=ROOT/'core-template-replacement.json';t=p.with_suffix('.new');t.write_text(json.dumps(x,indent=2)+'\n');t.chmod(0o600);os.replace(t,p)
def main():
 os.umask(0o077);assert Path('/etc/pve').exists() and os.geteuid()==0;assert sys.argv[1:] in [[],['--execute']];execute=bool(sys.argv[1:]);m={r['vmid']:r for r in json.loads((OUT/'manifest.json').read_text()) if r['status']=='verified'};review=[]
 for core,candidate,name,storage,user in JOBS:
  c=parse(cfg(core));assert c['name']==name and c['template']=='1' and c.get('protection','0')=='0' and not c.get('lock');assert run(['qm','status',str(core)]).strip()=='status: stopped';dependencies(core,c)
  assert hashlib.sha256(cfg(core).encode()).hexdigest()==m[core]['source_config_sha256']
  for v in [core,candidate]:
   b=m[v];p=Path(b['archive']);assert p.parent==OUT and not p.is_symlink() and p.stat().st_uid==0 and p.stat().st_mode&0o077==0 and b['zstd_test'] and b['VMA_full_verify'] and p.stat().st_size==b['bytes'] and digest(p)==b['sha256']
  review.append({'core_vmid':core,'candidate_vmid':candidate,'name':name,'old_archive':m[core]['archive'],'new_archive':m[candidate]['archive'],'storage':storage,'source_dependencies_clear':True,'both_archives_full_verified':True})
 result={'at':datetime.datetime.now().isoformat(),'mode':'execute' if execute else 'dryrun','review':review,'replaced':[],'runtime_business_VMs_touched':False,'old_archives_retained_PVE_only':True};save(result)
 if not execute:print(json.dumps({'status':'3core-backups-candidate-archives-and-current-dependencies-reviewed','execute':False}));return
 for core,candidate,name,storage,user in JOBS:
  c=parse(cfg(core));dependencies(core,c);assert c['template']=='1' and run(['qm','status',str(core)]).strip()=='status: stopped'
  run(['qm','destroy',str(core),'--purge','1'])
  try:
   run(['qmrestore',m[candidate]['archive'],str(core),'--storage',storage,'--unique','1'],timeout=600)
   run(['qm','set',str(core),'--name',name,'--memory','2048','--cores','2','--balloon','0','--net0','virtio,bridge=vmbr19,firewall=0','--ipconfig0','ip=dhcp','--nameserver','192.168.19.1','--cicustom','user=store:snippets/'+user,'--onboot','0','--description','Accepted generic '+name+' with fish4.0.2;bashdefault;independent candidate QA passed;no business data/credentials'])
   c=parse(cfg(core))
   if c.get('template')!='1':run(['qm','template',str(core)])
   c=parse(cfg(core));assert c['template']=='1' and c['name']==name and c['ipconfig0']=='ip=dhcp' and c['onboot']=='0' and 'bridge=vmbr19' in c['net0'] and c['cicustom']=='user=store:snippets/'+user;assert run(['qm','status',str(core)]).strip()=='status: stopped'
   result['replaced'].append({'vmid':core,'name':name,'template_stopped':True,'generic_CI_DHCP':True,'candidate_archive_SHA256':m[candidate]['sha256'],'old_rollback_archive':m[core]['archive'],'net0':c['net0'],'source_candidate':candidate});save(result)
  except Exception as e:
   result.update(status='replacement-unconfirmed-stop-before-next-core',failed_vmid=core,error_category=type(e).__name__,rollback_archive=m[core]['archive']);save(result);raise
 result['status']='3core-fish-templates-replaced-metadata-verified';save(result);print(json.dumps({'status':result['status'],'replaced':[v['vmid'] for v in result['replaced']],'stopped':True,'runtime_business_VMs_touched':False}))
if __name__=='__main__':main()
