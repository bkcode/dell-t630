#!/usr/bin/env python3
"""CAS only the reviewed public builder tool/profile contract; no PVE/lifecycle."""
import argparse,datetime,hashlib,importlib.util,json,shlex,sys
from pathlib import Path
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('window',HERE/'template-window.py');w=importlib.util.module_from_spec(spec);spec.loader.exec_module(w)
CODE=r'''import hashlib,json,os,socket,sys
from pathlib import Path
v=json.load(sys.stdin);c=v['contract'];stage=Path('/root/dell-fish-template-stage-'+str(c['vmid']));assert os.geteuid()==0 and not Path('/etc/pve').exists() and socket.gethostname().split('.')[0]==c['hostname'];assert not stage.is_symlink()
p=stage/'template-builder.py';assert not p.is_symlink() and hashlib.sha256(p.read_bytes()).hexdigest()==v['old_sha256'];old=json.loads((stage/'contract.json').read_text());assert all(old[k]==c[k] for k in ['vmid','source_template','hostname','ip','mac','fish_version','no_chsh'])
fd=os.open(stage/'reviewed-tool.tmp',os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
with os.fdopen(fd,'w') as f:f.write(v['source'])
os.replace(stage/'reviewed-tool.tmp',p)
if v.get('install_window'):
 for name,data in [('contract.json',c),('install-window.json',v['install_window'])]:
  target=stage/name;assert not target.is_symlink() and target.stat().st_uid==0
  fd=os.open(stage/(name+'.tmp'),os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
  with os.fdopen(fd,'w') as f:json.dump(data,f)
  os.replace(stage/(name+'.tmp'),target)
print(json.dumps({'vmid':c['vmid'],'status':'reviewed-public-tool-CAS-refreshed','before_sha256':v['old_sha256'],'after_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'contract_profile_refreshed':bool(v.get('install_window')),'no_network_identity_service_changes':True}))'''
def main():
 p=argparse.ArgumentParser();p.add_argument('--vmid',type=int,choices=[9040,9041,9042],required=True);a=p.parse_args();original=json.loads((HERE/'evidence'/('builder'+str(a.vmid)+'-install.json')).read_text());c=original['contract'];info=original['target'];window=None
 if a.vmid==9041:
  c['docker_profile']={'driver':'overlayfs','live_restore':True,'containerd_snapshotter':'default-enabled'};c['docker_daemon_sha256']=json.loads((HERE/'evidence/builder9041-daemon-original-sha.json').read_text())['daemon_sha256'];window={'vmid':a.vmid,'allowed_phase':'install','expires_at':(datetime.datetime.now(datetime.timezone.utc)+datetime.timedelta(hours=1)).isoformat(),'contract_sha256':hashlib.sha256(json.dumps(c,sort_keys=True,separators=(',',':')).encode()).hexdigest()}
 value={'contract':c,'old_sha256':hashlib.sha256((HERE/'template-builder-before-netplan-fix.py').read_bytes()).hexdigest(),'source':(HERE/'template-builder.py').read_text(),'install_window':window}
 path=HERE/'evidence'/('builder'+str(a.vmid)+'-tool-refresh.json');assert not path.exists()
 r=w.control.guest(a.vmid,'sudo -n python3 -I -B -c '+shlex.quote(CODE),data=json.dumps(value).encode(),info=info,timeout=45)
 try:result=json.loads(r['stdout'])
 except Exception:result={'status':'unparseable-output-withheld'}
 path.write_text(json.dumps({'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'exit_code':r['exit_code'],'contract':c,'result':result},indent=2)+'\n');print(json.dumps(result));return r['exit_code']
if __name__=='__main__':raise SystemExit(main())
