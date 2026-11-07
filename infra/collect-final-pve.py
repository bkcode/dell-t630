#!/usr/bin/env python3
"""Read-only non-secret host/storage/assigned VM final inventory."""
from pathlib import Path
import sys,json,datetime,shlex
BASE=Path(__file__).resolve().parents[1];sys.path.insert(0,str(BASE/'scripts'));import control
vmids=[200,201,210,220,221,230,231,232,240,250,260,270]
code='''import json,subprocess,datetime
from pathlib import Path
assert Path('/etc/pve').exists()
def run(a):
 p=subprocess.run(a,capture_output=True,text=True,timeout=30);assert p.returncode==0,a[0];return p.stdout
r={'at':datetime.datetime.now().isoformat(),'host':run(['hostname']).strip(),'pve_version':run(['pveversion']).strip(),'storage':json.loads(run(['pvesh','get','/nodes/pve/storage','--output-format','json'])),'lvm':json.loads(run(['lvs','--reportformat','json','--units','b','--nosuffix','-o','lv_name,vg_name,lv_size,lv_attr,data_percent,metadata_percent,pool_lv,origin'])),'vm_resources':json.loads(run(['pvesh','get','/cluster/resources','--type','vm','--output-format','json'])),'mounts':{},'assigned_vm_configs':{}}
for mount in ['/','/mnt/pve/store']:r['mounts'][mount]=json.loads(run(['findmnt','-J','-T',mount,'-o','TARGET,SOURCE,FSTYPE,UUID']))
for vmid in [200,201,210,220,221,230,231,232,240,250,260,270]:
 allowed={'name','memory','cores','onboot','scsi0','scsi1','net0','boot','ostype'}
 r['assigned_vm_configs'][str(vmid)]={k:v.strip() for k,v in (line.split(':',1) for line in run(['qm','config',str(vmid)]).splitlines() if ':' in line) if k in allowed}
print(json.dumps(r))
'''
r=json.loads(control.pve('python3 -c '+shlex.quote(code),timeout=150));r['source_command_policy']='read-only whitelist; no sshkeys/password/token/config secrets collected'
(BASE/'evidence/implementation/pve-final-inventory.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps({'host':r['host'],'version':r['pve_version'],'assigned_vms':len(r['assigned_vm_configs']),'storage':[{'name':s['storage'],'free_fraction':s.get('avail',0)/s.get('total',1) if s.get('total') else None} for s in r['storage']]}))
