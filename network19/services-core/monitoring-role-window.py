#!/usr/bin/env python3
"""Explicit per-role manager window. Default stage+inspect; apply requires CLI acknowledged role."""
import argparse,base64,datetime,json,shlex,sys
from pathlib import Path
sys.dont_write_bytecode=True
H=Path(__file__).resolve().parent;R=H.parents[1];sys.path.insert(0,str(R/'scripts'));import control
P=r'''import json,sys,base64,os,socket,subprocess,re,time,urllib.request
from pathlib import Path
v=json.loads(sys.stdin.read());vmid=v['vmid'];role=v['role'];new=v['new_ip'];root=Path('/root/dell-network19/staged')/('core-monitoring'+str(vmid))
if os.geteuid()!=0 or socket.gethostname().split('.')[0]!=role or Path('/etc/pve').exists():raise SystemExit('assigned role only')
for p in [Path('/root/dell-network19'),root.parent]:
 if p.resolve(strict=False)!=p:raise SystemExit('stage path symlink')
 p.mkdir(mode=0o700,exist_ok=True)
fresh=not root.exists()
if fresh:root.mkdir(mode=0o700,exist_ok=False)
if root.resolve()!=root or root.stat().st_uid!=0 or root.stat().st_mode&0o022:raise SystemExit('untrusted existing stage')
for rel,encoded in v['files'].items():
 if rel.startswith('/') or '..' in Path(rel).parts:raise SystemExit('stage path unsafe')
 p=root/rel;data=base64.b64decode(encoded)
 if p.exists():
  if p.resolve()!=p or p.stat().st_uid!=0 or p.stat().st_mode&0o022 or p.read_bytes()!=data:raise SystemExit('existing role stage differs; no overwrite')
 else:
  if not fresh:raise SystemExit('partial existing stage requires review')
  p.parent.mkdir(mode=0o700,parents=True,exist_ok=True);fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
  with os.fdopen(fd,'wb') as f:f.write(data)
base=['python3','-I','-B',str(root/'apply-monitoring.py'),'--bundle',str(root),'--os-contract',str(root/(str(vmid)+'.json'))]
def call(args):
 p=subprocess.run(args,capture_output=True,text=True,timeout=180)
 try:x=json.loads(p.stdout)
 except Exception:x={'status':'no-sanitized-result'}
 return p.returncode,x
code,inspected=call(base+['--inspect'])
if code or not v['apply']:print(json.dumps({'stage_path':str(root),'inspect_exit':code,'inspect':inspected,'applied':False,'OS_or_apps_changed':False}));raise SystemExit(code)
receipt=root/(str(vmid)+'-window.json');receipt.write_text(json.dumps({'migration':'network19','vmid':vmid,'phase':'OScommitted-monitoring-window','parent_window_open':True}));receipt.chmod(0o600)
code,applied=call(base+['--root-receipt',str(receipt),'--apply-after-oscommit'])
if code:print(json.dumps({'status':'apply-failed','apply':applied}));raise SystemExit(code)
p=subprocess.run(['systemctl','start','dell-guest-health.service'],capture_output=True,text=True,timeout=30)
text=Path('/var/lib/prometheus/node-exporter-textfile/dell_guest_health.prom').read_text();match=re.search(r'dell_guest_health_collection_timestamp_seconds[^\n]* ([0-9.]+)',text);age=time.time()-float(match[1]) if match else None
with urllib.request.build_opener(urllib.request.ProxyHandler({})).open('http://'+new+':9100/metrics',timeout=5) as r:metrics=r.read(4*1024*1024).decode();http=r.status
units=subprocess.run(['systemctl','list-units','--all','--no-legend','--plain','--state=active','dell-finger-*'],capture_output=True,text=True,timeout=10).stdout.splitlines() if vmid in [230,231,232,240] else []
needle='dell_guest_health_collection_success{role="'+role+'"} 1'
checks={'sample_exit0':p.returncode==0,'fresh_textfile':age is not None and 0<=age<90,'collection_success1':needle in text,'new_exporter200_and_serves_role_textfile':http==200 and needle in metrics,'formal_apps_not_started':not units}
print(json.dumps({'status':'applied-sampled-local-pass' if all(checks.values()) else 'sample-failed','vmid':vmid,'stage_path':str(root),'inspect':inspected,'apply':applied,'sample_checks':checks,'textfile_age_seconds':round(age,3) if age is not None else None,'Ops_remote_targetUP_not_checked':True,'OS_or_business_apps_changed':False}));raise SystemExit(0 if all(checks.values()) else 1)
'''
def main():
 p=argparse.ArgumentParser();p.add_argument('--vmid',type=int,required=True);p.add_argument('--apply-authorized-role',action='store_true');a=p.parse_args();vmid=a.vmid;bundle=H/'prepared/monitoring'/('vm'+str(vmid));model=json.loads((bundle/'role-contract.json').read_text())
 files={str(p.relative_to(bundle)):base64.b64encode(p.read_bytes()).decode() for p in bundle.rglob('*') if p.is_file()};files['apply-monitoring.py']=base64.b64encode((H/'apply-monitoring.py').read_bytes()).decode();files[str(vmid)+'.json']=base64.b64encode((R/'network19/contracts'/(str(vmid)+'.json')).read_bytes()).decode()
 targets=json.loads((R/'network19/evidence/migrated-access.json').read_text())['targets'] if (R/'network19/evidence/migrated-access.json').exists() else {};old={r['target']['vmid']:r['target'] for r in json.loads((R/'evidence/implementation/private-guest-access.json').read_text())['roles']};info=targets.get(str(vmid),old[vmid])
 if a.apply_authorized_role and info['ip']!=model['new_ip']:raise SystemExit('new strict verified target required')
 v={'vmid':vmid,'role':model['role'],'new_ip':model['new_ip'],'apply':a.apply_authorized_role,'files':files};r=control.guest(vmid,'sudo -n python3 -I -B -c '+shlex.quote(P),data=json.dumps(v).encode(),timeout=300,info=info)
 try:out=json.loads(r['stdout'])
 except Exception:raise SystemExit('no sanitized role receipt; no blind retry')
 (H/('monitoring'+str(vmid)+'-window-evidence.json')).write_text(json.dumps({'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'exit_code':r['exit_code'],'new_target':info,'result':out},indent=2)+'\n');print(json.dumps(out));return r['exit_code']
if __name__=='__main__':raise SystemExit(main())
