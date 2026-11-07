#!/usr/bin/env python3
"""Read qemu image headers in approved PVE image directories, never guest files."""
import json,sys,shlex
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts'));import control
meta=json.loads((ROOT/'cleanup/audit/pve-storage-inventory.json').read_text())
P=r'''
import json,sys,pathlib,subprocess,os,re,datetime
assert pathlib.Path('/etc/pve').exists();metadata=json.load(sys.stdin);seeds=[];image_roots=set();excluded=[]
for row in metadata['volume_paths']:
 path=row.get('path','')
 if row.get('is_block') or not path or not row.get('exists'):continue
 p=pathlib.Path(path)
 if p.suffix.lower() not in ['.qcow2','.raw','.img','.vmdk','.qed']:continue
 if p.parent.name.isdigit() and p.parent.parent.name=='images':image_roots.add(str(p.parent.parent));seeds.append(str(p))
# Also cover orphan/unattached managed-directory image files missed by storage API naming.
for root in image_roots:
 assert root.startswith(('/mnt/pve/','/var/lib/vz/'))
 for folder,dirs,files in os.walk(root,followlinks=False):
  dirs[:]=[x for x in dirs if not pathlib.Path(folder,x).is_symlink()]
  for f in files:
   p=pathlib.Path(folder,f)
   if p.suffix.lower() in ['.qcow2','.raw','.img','.vmdk','.qed'] and not p.is_symlink():seeds.append(str(p))
D={'captured_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'command':'qemu-img info -U --output=json (metadata; manually follows only approved local backing paths)','images':[],'image_roots':sorted(image_roots),'errors':[]};seen=set();queue=sorted(set(seeds))
while queue:
 path=queue.pop(0);p=pathlib.Path(path);real=os.path.realpath(path)
 if real in seen:continue
 seen.add(real)
 if not any(real==r or real.startswith(r+'/') for r in image_roots):D['errors'].append({'path_class':'outside-approved-image-root-redacted','operation':'backing-follow-refused'});continue
 r=subprocess.run(['qemu-img','info','-U','--output=json',path],capture_output=True,text=True,timeout=30)
 row={'path':path,'realpath':real,'exit':r.returncode,'input_registered_in_PVE':any(x.get('path')==path for x in metadata['volume_paths'])}
 if r.returncode:row['error_category']='qemu-img-info-failed-no-raw-stderr';D['errors'].append({'path':path,'operation':'qemu-img-info','exit':r.returncode});D['images'].append(row);continue
 q=json.loads(r.stdout);row.update({k:q[k] for k in ['format','virtual-size','actual-size','cluster-size','encrypted','dirty-flag'] if k in q});row['internal_snapshots']=[{k:s[k] for k in ['id','name','vm-state-size','date-sec','vm-clock-sec'] if k in s} for s in q.get('snapshots',[])]
 backing=q.get('full-backing-filename',q.get('backing-filename'))
 if backing:
  if not isinstance(backing,str) or (not backing.startswith('/') and re.match(r'^[A-Za-z0-9+.-]+:',backing)):
   row['backing_reference']='nonlocal-redacted';D['errors'].append({'path':path,'operation':'nonlocal-backing-refused'})
  else:
   resolved=os.path.realpath(backing if backing.startswith('/') else str(p.parent/backing));row['backing_path']=resolved;row['backing_format']=q.get('backing-filename-format');queue.append(resolved)
 specific=q.get('format-specific',{}).get('data',{})
 datafile=specific.get('data-file')
 if datafile:
  resolved=os.path.realpath(datafile if datafile.startswith('/') else str(p.parent/datafile));row['external_data_file_path']=resolved
 D['images'].append(row)
D['forbidden_actions_executed']=[];D['raw_LVM_or_CF_disks_probed']=False;D['running_image_header_shared_read_limitation']='-U header read is observational; recheck DAG immediately before any authorized deletion.';print(json.dumps(D))
'''
j=json.loads(control.pve('python3 -c '+shlex.quote(P),data=json.dumps(meta).encode(),timeout=180));(ROOT/'cleanup/audit/qemu-image-headers.json').write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'images':len(j['images']),'errors':j['errors'],'backing_edges':[{'child':x['path'],'parent':x['backing_path']} for x in j['images'] if x.get('backing_path')],'internal_snapshots':sum(len(x.get('internal_snapshots',[])) for x in j['images']),'orphan_header_count':sum(not x['input_registered_in_PVE'] for x in j['images'])},ensure_ascii=False))
