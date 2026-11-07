#!/usr/bin/env python3
"""Manager-only offline NIC/CloudInit metadata migration; no boot, disk/identity edits."""
from pathlib import Path
import sys,json,shlex
BASE=Path(__file__).resolve().parents[1];sys.path.insert(0,str(BASE/'scripts'));import control
code='''import json,subprocess,re,datetime
from pathlib import Path
assert Path('/etc/pve').exists()
ids=[101,102,103,104,105,106,9000,9001,9002,9003,9004,9005,9006,9010,9020]
static={101:'192.168.19.101',104:'192.168.19.104',9000:'192.168.19.190',9002:'192.168.19.191',9003:'192.168.19.192',9004:'192.168.19.193',9005:'192.168.19.194',9006:'192.168.19.195',9020:'192.168.19.196'}
root=Path('/root/dell-bootstrap/network19/dormant-before');root.mkdir(mode=0o700,exist_ok=True)
def run(a):return subprocess.check_output(a,text=True,stderr=subprocess.DEVNULL)
results=[]
for v in ids:
 assert run(['qm','status',str(v)]).strip()=='status: stopped'
 f=Path('/etc/pve/qemu-server')/(str(v)+'.conf');backup=root/f.name
 if backup.exists():original=backup.read_bytes()
 else:original=f.read_bytes();backup.write_bytes(original);backup.chmod(0o600)
 old={k:x.strip() for k,x in (l.split(':',1) for l in original.decode().splitlines() if ':' in l)}
 netkeys=[k for k in old if re.fullmatch('net[0-9]+',k)];assert netkeys
 for k in netkeys:
  network=re.sub(r'bridge=[^,]+','bridge=vmbr19',old[k]);assert 'bridge=vmbr19' in network
  run(['qm','set',str(v),'--'+k,network])
 args=['qm','set',str(v),'--nameserver','192.168.19.1']
 if old.get('template')=='1':args+=['--ipconfig0','ip=dhcp']
 else:args+=['--ipconfig0','ip='+static[v]+'/24,gw=192.168.19.1']
 run(args)
 new={k:x.strip() for k,x in (l.split(':',1) for l in f.read_text().splitlines() if ':' in l)}
 assert all('bridge=vmbr19' in new[k] for k in netkeys)
 for k in old:
  if k not in set(netkeys)|{'ipconfig0','nameserver','digest'}:assert new.get(k)==old[k],'Unexpected non-network field drift'
 results.append({'vmid':v,'name':new['name'],'template':new.get('template')=='1','before_network':{k:old[k] for k in netkeys+['ipconfig0','nameserver'] if k in old},'after_network':{k:new[k] for k in netkeys+['ipconfig0','nameserver'] if k in new},'still_stopped':run(['qm','status',str(v)]).strip()=='status: stopped','OS_runtime_validation':'dormant;not-assumed-from-CloudInit-metadata','disk_identity_fields_unchanged':True})
print(json.dumps({'at':datetime.datetime.now().isoformat(),'status':'15-dormant-guest-template-NICs-server19-only','objects':results,'no_guest_started':True,'no_disk_or_key_changes':True,'actual_backups_PVE_only':str(root)}))
'''
r=control.pve('python3 -c '+shlex.quote(code),timeout=180);(BASE/'network19/evidence/dormant-nics-moved.json').write_bytes(r);m=json.loads(r);print(json.dumps({'status':m['status'],'count':len(m['objects']),'disks_keys_unchanged':True,'OSIPs_not_yet_claimed':True}))
