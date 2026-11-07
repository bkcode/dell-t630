import concurrent.futures,json,sys,shlex,base64,datetime
from pathlib import Path
sys.dont_write_bytecode=True
H=Path(__file__).resolve().parent;R=H.parents[1];sys.path.insert(0,str(R/'scripts'));import control
if (H/'monitoring-inventory.json').exists():raise SystemExit('Initial snapshot already exists; preserve old evidence and request a separately versioned collection')
M=json.loads((R/'network19/migration-plan.json').read_text());MAP={x['vmid']:x for x in M['guest_addresses']};ids=[200,201,210,220,221,230,231,232,240,250,260,270]
P=r'''import json,hashlib,base64,sys,subprocess,socket,os
from pathlib import Path
v=json.loads(sys.stdin.read())
if os.geteuid()!=0 or Path('/etc/pve').exists() or socket.gethostname().split('.')[0]!=v['name']:raise SystemExit('fixed guest baseline scope only')
files=['/etc/default/prometheus-node-exporter','/etc/systemd/system/prometheus-node-exporter.service.d/10-private-only.conf','/etc/dell-guest-monitoring/health.json','/opt/dell/guest-monitoring/guest-targets.json','/opt/dell/guest-monitoring/install-guest-baseline.py','/opt/dell/guest-monitoring/collect-guest-health.py'];out={'vmid':v['vmid'],'role':v['name'],'files':{}}
for path in files:
 p=Path(path)
 if p.is_file():
  data=p.read_bytes();st=p.stat();out['files'][path]={'exists':True,'sha256':hashlib.sha256(data).hexdigest(),'uid':st.st_uid,'mode':oct(st.st_mode&0o777),'public_data':base64.b64encode(data).decode()}
 else:out['files'][path]={'exists':False}
p=subprocess.run(['systemctl','show','prometheus-node-exporter.service','dell-guest-health.timer','--property=Id,LoadState,ActiveState,SubState,UnitFileState'],capture_output=True,text=True,timeout=15);out['unit_state']=p.stdout
print(json.dumps(out))'''
access={r['target']['vmid']:r['target'] for r in json.loads((R/'evidence/implementation/private-guest-access.json').read_text())['roles']}
def one(vmid):
 r=control.guest(vmid,'sudo -n python3 -I -B -c '+shlex.quote(P),data=json.dumps(MAP[vmid]).encode(),timeout=60,info=access[vmid])
 if r['exit_code']:return {'vmid':vmid,'status':'read-failed'}
 x=json.loads(r['stdout']);folder=H/'monitoring-baselines'/('vm'+str(vmid));folder.mkdir(parents=True,exist_ok=True)
 for i,(path,meta) in enumerate(x['files'].items()):
  if meta.get('exists'):
   p=folder/(str(i)+'-'+Path(path).name);p.write_bytes(base64.b64decode(meta.pop('public_data')));meta['captured_file']=str(p.relative_to(H))
 return x
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as p:rows=list(p.map(one,ids))
(H/'monitoring-inventory.json').write_text(json.dumps({'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'12 guest baseline monitoring files only; no media apps or secrets','roles':rows},indent=2)+'\n')
for x in rows:print(json.dumps({'vmid':x['vmid'],'status':x.get('status','collected'),'files':len(x.get('files',{}))}))
