from pathlib import Path
import sys,json,shlex,importlib.util,datetime
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'scripts'));import control
collect=r'''from pathlib import Path
import re,json,datetime
rows=[]
for kind,folder in [('vm',Path('/etc/pve/qemu-server')),('lxc',Path('/etc/pve/lxc'))]:
 for p in sorted(folder.glob('*.conf')):
  if not p.stem.isdigit():continue
  c={x.split(': ',1)[0]:x.split(': ',1)[1] for x in p.read_text().split('\n[',1)[0].splitlines() if ': ' in x};nics={k:dict(part.split('=',1) for part in v.split(',') if '=' in part) for k,v in c.items() if re.fullmatch('net[0-9]+',k)}
  rows.append({'vmid':int(p.stem),'kind':kind,'template':c.get('template')=='1','nics':nics})
print(json.dumps({'captured_at':datetime.datetime.now().isoformat(),'guests':rows}))'''
inventory=json.loads(control.pve('python3 -',data=collect.encode()));(R/'network19/audit/nic-registry-current.json').write_text(json.dumps(inventory,indent=2)+'\n')
p=R/'network19/audit/render-bridge-acl.py';spec=importlib.util.spec_from_file_location('render19',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
rules,notes=m.render(json.loads((R/'network19/migration-plan.json').read_text()),inventory);(R/'network19/audit/bridge19-current.nft').write_text(rules);(R/'network19/audit/bridge19-current.json').write_text(json.dumps(notes,indent=2)+'\n')
apply=r'''from pathlib import Path
import json,subprocess,sys,os,datetime,hashlib
x=json.load(sys.stdin);new=x['rules'].encode();assert new.count(b'table bridge dell19_acl {')==1 and b'table inet' not in new and len(new)<100000
p=Path('/etc/dell-network19/bridge19.nft');assert p.stat().st_uid==0 and p.stat().st_mode&0o077==0 and not p.is_symlink();old=p.read_bytes()
transaction=b'delete table bridge dell19_acl\n'+new
subprocess.run(['nft','-c','-f','-'],input=transaction,check=True,capture_output=True)
f=Path('/root/dell-bootstrap/network19/acl')/('refresh-before-'+datetime.datetime.now().strftime('%Y%m%dT%H%M%S')+'.nft');f.write_bytes(old);f.chmod(0o600)
def put(data):
 t=p.with_suffix('.candidate');t.write_bytes(data);t.chmod(0o600);os.replace(t,p)
put(new)
try:subprocess.run(['/usr/local/sbin/dell-apply-network19-bridge'],check=True,capture_output=True,timeout=25)
except Exception:
 put(old);subprocess.run(['/usr/local/sbin/dell-apply-network19-bridge'],check=True,capture_output=True,timeout=25);raise
print(json.dumps({'status':'owned-bridge-ACL-refreshed-native-check-atomic-persisted','old_SHA':hashlib.sha256(old).hexdigest(),'new_SHA':hashlib.sha256(new).hexdigest(),'backup_PVE_only':True,'other_tables_addresses_L3_forwarding_unchanged':True}))'''
x=json.loads(control.pve('python3 -c '+shlex.quote(apply),data=json.dumps({'rules':rules}).encode()));x['at']=datetime.datetime.now().isoformat();x['nic_identities']=len(notes['rows']);dest=R/'network19/evidence/ACL-refresh-history.json';values=json.loads(dest.read_text()) if dest.exists() else [];values.append(x);dest.write_text(json.dumps(values,indent=2)+'\n');print(json.dumps(x))
