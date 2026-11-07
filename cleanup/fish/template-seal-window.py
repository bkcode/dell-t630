#!/usr/bin/env python3
"""Root-reviewed builder seal phase; no lifecycle operations."""
import argparse,datetime,hashlib,json,shlex,sys
from pathlib import Path
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];sys.path.insert(0,str(ROOT/'scripts'));import control
REMOTE=r'''import json,os,subprocess,sys
from pathlib import Path
v=json.load(sys.stdin);c=v['contract'];stage=Path('/root/dell-fish-template-stage-'+str(c['vmid']));assert stage.is_dir() and not stage.is_symlink()
assert json.loads((stage/'contract.json').read_text())==c
window=stage/'seal-window.json'
if not window.exists():
 fd=os.open(window,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
 with os.fdopen(fd,'w') as f:json.dump(v['window'],f)
else:
 old=json.loads(window.read_text());assert all(old[k]==v['window'][k] for k in ['vmid','allowed_phase','contract_sha256'])
p=subprocess.run(['python3','-I','-B',str(stage/'template-builder.py'),'--contract',str(stage/'contract.json'),'--phase','seal','--window',str(window)],capture_output=True,text=True)
try:value=json.loads(p.stdout)
except Exception:value={'status':'unparseable-receipt','raw_output_withheld':True}
print(json.dumps({'exit_code':p.returncode,'receipt':value}));raise SystemExit(p.returncode)'''
def main():
 p=argparse.ArgumentParser();p.add_argument('--vmid',type=int,choices=[9040,9041,9042],required=True);a=p.parse_args();install_path=HERE/'evidence'/('builder'+str(a.vmid)+'-install.json')
 if a.vmid==9041:install_path=HERE/'evidence/builder9041-install-retry-profile.json'
 e=json.loads(install_path.read_text());assert e['exit_code']==0 and e['new_strict_SSH_exit']==0;contract=e['contract'];window={'vmid':a.vmid,'allowed_phase':'seal','expires_at':(datetime.datetime.now(datetime.timezone.utc)+datetime.timedelta(hours=1)).isoformat(),'contract_sha256':hashlib.sha256(json.dumps(contract,sort_keys=True,separators=(',',':')).encode()).hexdigest()}
 path=HERE/'evidence'/('builder'+str(a.vmid)+'-seal.json')
 if path.exists():path=path.with_name(path.stem+'-retry-netplan.json')
 assert not path.exists()
 r=control.guest(a.vmid,'sudo -n python3 -I -B -c '+shlex.quote(REMOTE),data=json.dumps({'contract':contract,'window':window}).encode(),timeout=180,info=e['target'])
 try:value=json.loads(r['stdout'])
 except Exception:value={'status':'unparseable-remote-receipt','raw_output_withheld':True}
 result={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'vmid':a.vmid,'phase':'seal-only-explicit-root-window','exit_code':r['exit_code'],'result':value,'no_power_or_PVE_action':True};path.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result));return r['exit_code']
if __name__=='__main__':raise SystemExit(main())
