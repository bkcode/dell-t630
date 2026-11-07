#!/usr/bin/env python3
"""Fixed260 manager runner; commands contain only public source and nonce, no secrets."""
import argparse,datetime,hashlib,json,shlex,sys,uuid
from pathlib import Path
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];sys.path.insert(0,str(ROOT/'scripts'));import control

REQUIRED_PRECHECKS={'exact_QA_project','exact_one_service','exact_zero_publish_mappings','only_exact_QA_bind_sources','internal_network','CPU025','memory512','pids128'}
def guarded_phase_call(phase,nonce,callback,precheck=None):
 if phase!='cleanup':
  check=precheck if precheck is not None else json.loads((HERE/'native-merged-v2-normalized.json').read_text())
  if check.get('nonce')!=nonce or check.get('status')!='passed' or check.get('native_command_exit_code')!=0 or set(check.get('checks',{}))!=REQUIRED_PRECHECKS or not all(check['checks'].values()):raise RuntimeError('failclosed-native-precheck-gate; no target phase invoked')
 return callback()

def main():
 p=argparse.ArgumentParser();p.add_argument('phase',choices=['prepare','b1','b2','restore','resume-c','cleanup']);p.add_argument('--nonce');a=p.parse_args()
 nonce=a.nonce or (uuid.uuid4().hex if a.phase=='prepare' else None)
 if not nonce:raise RuntimeError('existing nonce required for non-prepare action')
 rows=json.loads((ROOT/'evidence/implementation/private-guest-access.json').read_text())['roles'];row=next(x for x in rows if x['target']['vmid']==260)
 if row['name']!='nas-media' or row['target']['ip']!='10.63.40.10':raise RuntimeError('260 trust mapping mismatch')
 folder=HERE/'evidence'/nonce;folder.mkdir(parents=True,exist_ok=True)
 source=(HERE/'worker.py').read_text();request={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'phase':a.phase,'nonce':nonce,'worker_sha256':hashlib.sha256(source.encode()).hexdigest(),'target':260}
 (folder/(a.phase+'-request.json')).write_text(json.dumps(request,indent=2)+'\n')
 command=shlex.join(['sudo','-n','python3','-I','-B','-c',source,a.phase,'--nonce',nonce])
 r=guarded_phase_call(a.phase,nonce,lambda:control.guest(260,command,timeout=300 if a.phase in ['prepare','restore','resume-c'] else 180,info=row['target']))
 try:value=json.loads(r['stdout'])
 except Exception:raise RuntimeError('QA phase failed to emit sanitized metadata; never rerun prepare blindly') from None
 receipt={'collected_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'exit_code':r['exit_code'],'result':value}
 path=folder/(a.phase+'.json')
 if path.exists():path.with_name(path.stem+'-previous-'+datetime.datetime.now().strftime('%H%M%S%f')+'.json').write_bytes(path.read_bytes())
 path.write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt));return r['exit_code']
if __name__=='__main__':raise SystemExit(main())
