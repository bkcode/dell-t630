#!/usr/bin/env python3
"""Current scope: public IP contract commit only, publisher stays fenced, no publish/E2E."""
import argparse,base64,datetime,json,shlex,sys
from pathlib import Path
sys.dont_write_bytecode=True
H=Path(__file__).resolve().parent;R=H.parents[1];sys.path.insert(0,str(R/'scripts'));import control
P=r'''import sys,json,base64,os,socket,subprocess
from pathlib import Path
v=json.loads(sys.stdin.read());vmid=v['vmid'];role={220:'publish-service',240:'java-test-01'}[vmid]
if os.geteuid()!=0 or socket.gethostname().split('.')[0]!=role or Path('/etc/pve').exists():raise SystemExit('fixed publisher role')
root=Path('/root/dell-network19/staged/services-core-v1')
for name,encoded in v['updates'].items():
 if name not in ['commit-publisher.py','prepared-public-contract.json']:raise SystemExit('stage update whitelist')
 p=root/name
 if p.is_symlink():raise SystemExit('stage symlink')
 p.write_bytes(base64.b64decode(encoded));p.chmod(0o600)
receipt=root/'window-public-IP-fenced.json';receipt.write_text(json.dumps({'migration':'network19','vmid':vmid,'phase':'commit-fenced','parent_window_open':True,'publisher_transactions_frozen':True,'java_apps_deployment_allowed':False}));receipt.chmod(0o600)
p=subprocess.run(['python3','-I','-B',str(root/'commit-publisher.py'),'--vmid',str(vmid),'--contract-dir',str(root),'--mode','commit-fenced','--root-receipt',str(receipt)],capture_output=True,text=True,timeout=100)
try:x=json.loads(p.stdout)
except Exception:x={'status':'no-sanitized-public-contract-result'}
if vmid==240:
 policy=json.loads(Path('/etc/dell-publisher/test240-policy.json').read_text());x['baseline_remains_false']=policy.get('baseline_migrated') is False
 if not x['baseline_remains_false']:p=type('R',(),{'returncode':1})()
x['business_deploy_requests_issued']=0;x['Java_apps_started']=False
print(json.dumps(x));raise SystemExit(p.returncode)
'''
def main():
 a=argparse.ArgumentParser();a.add_argument('--vmid',type=int,choices=[220,240],required=True);v=a.parse_args();targets=json.loads((R/'network19/evidence/migrated-access.json').read_text())['targets'];info=targets[str(v.vmid)];expect={220:'192.168.19.30',240:'192.168.19.45'}[v.vmid]
 if info['ip']!=expect:raise SystemExit('new trusted target required')
 data={'vmid':v.vmid,'updates':{n:base64.b64encode((H/n).read_bytes()).decode() for n in ['commit-publisher.py','prepared-public-contract.json']}}
 r=control.guest(v.vmid,'sudo -n python3 -I -B -c '+shlex.quote(P),data=json.dumps(data).encode(),timeout=140,info=info)
 try:x=json.loads(r['stdout'])
 except Exception:raise SystemExit('no safe receipt, no blind retry')
 (H/('publisher'+str(v.vmid)+'-fenced-evidence.json')).write_text(json.dumps({'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'exit_code':r['exit_code'],'result':x},indent=2)+'\n');print(json.dumps(x));return r['exit_code']
if __name__=='__main__':raise SystemExit(main())
