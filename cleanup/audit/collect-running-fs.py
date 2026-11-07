#!/usr/bin/env python3
"""QGA filesystem UUID/mount metadata only; no content or service/lifecycle actions."""
import sys,json,shlex
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts'));import control
j=json.loads((ROOT/'cleanup/audit/pve-storage-inventory.json').read_text());ids=[x['vmid'] for x in j['guests'] if x['kind']=='qemu' and x['runtime']['status']=='running']
P=r'''
import json,pathlib,subprocess,datetime,sys
assert pathlib.Path('/etc/pve').exists();ids=json.load(sys.stdin);out=[]
code="import json,subprocess,socket; p=subprocess.run(['findmnt','-J','-t','ext4,xfs,btrfs','-o','TARGET,SOURCE,UUID,FSTYPE'],capture_output=True,text=True,timeout=10); print(json.dumps({'hostname':socket.gethostname(),'findmnt_exit':p.returncode,'filesystems':json.loads(p.stdout)['filesystems'] if p.returncode==0 else []}))"
for v in ids:
 r=subprocess.run(['qm','guest','exec',str(v),'--timeout','15','--','/usr/bin/python3','-c',code],capture_output=True,text=True,timeout=25);row={'vmid':v,'host_exit':r.returncode}
 if r.returncode==0:
  q=json.loads(r.stdout);row['guest_exit']=q.get('exitcode')
  if q.get('exitcode')==0:row['metadata']=json.loads(q['out-data'])
 out.append(row)
print(json.dumps({'captured_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'running-QEMU filesystem mount/UUID metadata only','rows':out,'CF100_not_execed':True,'stopped_guests_not_started':True,'guest_data_files_read':False}))
'''
r=json.loads(control.pve('python3 -c '+shlex.quote(P),data=json.dumps(ids).encode(),timeout=200));(ROOT/'cleanup/audit/running-filesystems.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'running_QEMU_count':len(r['rows']),'metadata_read_ok':sum(x.get('guest_exit')==0 for x in r['rows']),'CF100_not_execed':True}))
