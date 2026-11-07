#!/usr/bin/env python3
"""PVE-only metadata audit. No disk contents, lifecycle, backup or mutation commands."""
import sys,json,shlex,datetime
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts'));import control
P=r'''
import os,json,pathlib,subprocess,re,datetime
assert os.geteuid()==0 and pathlib.Path('/etc/pve').exists()
D={'captured_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'read_only':True,'guests':[],'failures':[]};volume_ids=set()
def run(args,timeout=35):
 try:r=subprocess.run(args,capture_output=True,text=True,timeout=timeout);return r.returncode,r.stdout
 except subprocess.TimeoutExpired:return -999,''
def api(path,extra=None):
 code,text=run(['pvesh','get',path,* (extra or []),'--output-format','json']);return code,json.loads(text) if code==0 else None
def filter_config(c):
 out={k:c[k] for k in ['name','hostname','memory','cores','sockets','balloon','template','onboot','ostype','agent','parent','lock'] if k in c};disks={}
 for k,v in c.items():
  if re.fullmatch(r'(?:scsi|virtio|sata|ide|efidisk|tpmstate|unused|mp)\d+',k) or k in ['rootfs','vmstate']:
   if not isinstance(v,str):continue
   parts=v.split(',');first=parts[0];vol=first.split('=',1)[1] if first.startswith('volume=') else first
   params={a:b for a,b in [x.split('=',1) for x in parts[1:] if '=' in x] if a in ['size','format','media','backup','readonly','shared','replicate','snapshot','cache','ssd','discard','iothread']}
   disks[k]={'volume':vol,'options':params}
   if vol not in ['none','cdrom'] and (':' in vol or vol.startswith('/dev/')):volume_ids.add(vol)
 out['disks']=disks;return out
code,res=api('/cluster/resources',['--type','vm']);assert code==0
for obj in sorted(res,key=lambda x:(x.get('type',''),x['vmid'])):
 v=obj['vmid'];kind='lxc' if obj.get('type')=='lxc' else 'qemu';base='/nodes/pve/'+kind+'/'+str(v);r={'vmid':v,'kind':kind,'runtime':{k:obj.get(k) for k in ['name','status','template','cpus','maxmem','mem','maxdisk','uptime']}}
 code,c=api(base+'/config',['--current','1'] if kind=='qemu' else None);r['current_config_exit']=code
 if code==0:r['effective_config']=filter_config(c)
 else:D['failures'].append({'vmid':v,'operation':'effective-config','exit':code})
 code,snaps=api(base+'/snapshot');r['snapshot_list_exit']=code;r['snapshots']=[]
 if code==0:
  for s in snaps:
   meta={k:s.get(k) for k in ['name','parent','snaptime','vmstate','running','snapstate'] if k in s}
   if s.get('name')!='current':
    sc,conf=api(base+'/snapshot/'+s['name']+'/config');meta['config_exit']=sc
    if sc==0:meta['config']=filter_config(conf)
   r['snapshots'].append(meta)
 if kind=='qemu':
  code,pending=api(base+'/pending');r['pending_disks']=[]
  if code==0:
   for z in pending:
    key=z.get('key','')
    if re.fullmatch(r'(?:scsi|virtio|sata|ide|efidisk|tpmstate|unused)\d+',key):
     item={'key':key}
     for field in ['value','pending','delete']:
      if field in z:
       if field=='delete':item[field]=z[field]
       elif isinstance(z[field],str):item[field]=filter_config({key:z[field]})['disks'].get(key)
     r['pending_disks'].append(item)
 D['guests'].append(r)
code,s=api('/nodes/pve/storage');assert code==0;D['storages']=[{k:x.get(k) for k in ['storage','type','content','active','enabled','total','used','avail','shared']} for x in s];D['storage_images']=[]
for x in s:
 if not x.get('active'):continue
 code,content=api('/nodes/pve/storage/'+x['storage']+'/content');D['failures']+=([{'operation':'storage-content','storage':x['storage'],'exit':code}] if code else [])
 if code==0:
  for z in content:
   if z.get('content') in ['images','rootdir']:
    m={k:z.get(k) for k in ['volid','content','format','size','vmid','parent','used','ctime','encrypted'] if k in z};m['storage']=x['storage'];D['storage_images'].append(m);volume_ids.add(z['volid'])
D['volume_paths']=[]
for vol in sorted(volume_ids):
 if vol.startswith('/dev/'):
  D['volume_paths'].append({'volid':vol,'exit':0,'path':vol,'realpath':os.path.realpath(vol),'is_block':True});continue
 code,path=run(['pvesm','path',vol]);row={'volid':vol,'exit':code}
 if code==0:
  path=path.strip();row.update(path=path,realpath=os.path.realpath(path),is_block=path.startswith('/dev/'),exists=pathlib.Path(path).exists())
 D['volume_paths'].append(row)
for label,args in {'lvm':['lvs','-a','--reportformat','json','--units','b','--nosuffix','-o','vg_name,lv_name,lv_path,lv_attr,lv_size,origin,pool_lv,segtype,lv_uuid,data_percent,metadata_percent'],'pvs':['pvs','--reportformat','json','--units','b','--nosuffix','-o','pv_name,vg_name,pv_size,pv_free,pv_uuid'],'vgs':['vgs','--reportformat','json','--units','b','--nosuffix','-o','vg_name,vg_size,vg_free,vg_uuid'],'host_filesystems':['findmnt','-J','-t','ext4,xfs,btrfs,zfs','-o','TARGET,SOURCE,UUID,FSTYPE,OPTIONS'],'host_capacity':['df','-B1','--output=source,fstype,size,used,avail,target']}.items():
 code,text=run(args);D[label]={'exit':code}
 if code==0:
  try:D[label]['data']=json.loads(text)
  except ValueError:D[label]['data']=text
D['forbidden_actions_executed']=[];D['guest_files_or_private_material_read']=False;print(json.dumps(D))
'''
j=json.loads(control.pve('python3 -',data=P.encode(),timeout=300));p=ROOT/'cleanup/audit/pve-storage-inventory.json';p.write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'captured_at':j['captured_at'],'guests':len(j['guests']),'storage_images':len(j['storage_images']),'volumes':len(j['volume_paths']),'failures':j['failures'],'storages':j['storages'],'candidates':[{'vmid':x['vmid'],'runtime':x['runtime'],'disk_refs':x.get('effective_config',{}).get('disks'),'snapshots':[s['name'] for s in x.get('snapshots',[])]} for x in j['guests'] if x['vmid'] in [101,104,102,103,105,106,9000,9002,9003,9004,9005,9006,9020,231,232]]},ensure_ascii=False))
