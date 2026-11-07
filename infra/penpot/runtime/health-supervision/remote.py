"""Strict existing guest250 SSH only; no host-key mutations or private export."""
import datetime,json,sys
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT/'scripts'));import control
HERE=Path(__file__).resolve().parent

def guest(code,timeout=180,payload=None,phase='read'):
 row=next(r for r in json.loads((ROOT/'evidence/implementation/private-guest-access.json').read_text())['roles'] if r['target']['vmid']==250)
 if row['name']!='penpot-service' or row['target']['ip']!='10.63.30.30':raise RuntimeError('fixed250 trust mapping differs')
 import shlex
 command='sudo -n python3 -I -B -' if payload is None else 'sudo -n python3 -I -B -c '+shlex.quote(code)
 r=control.guest(250,command,data=code.encode() if payload is None else payload,timeout=timeout,info=row['target'])
 try:result=json.loads(r['stdout'])
 except Exception:raise RuntimeError('target phase did not return sanitized metadata; no raw output emitted') from None
 record={'collected_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'phase':phase,'exit_code':r['exit_code'],'result':result}
 folder=HERE/'evidence';folder.mkdir(exist_ok=True);p=folder/(phase+'.json')
 if p.exists():p.with_name(p.stem+'-previous-'+datetime.datetime.now().strftime('%H%M%S%f')+'.json').write_bytes(p.read_bytes())
 p.write_text(json.dumps(record,indent=2)+'\n')
 summary={k:v for k,v in result.items() if k not in ('media_path_to_sha256','original_files','unit_content','identity_hashes','containers','expected_media_sha256')}
 summary.update(phase=phase,exit_code=r['exit_code'])
 if 'containers' in result:summary['container_count']=len(result['containers'])
 if 'original_files' in result:summary['original_file_count']=len(result['original_files'])
 print(json.dumps(summary),flush=True)
 if r['exit_code']:raise RuntimeError('target phase '+phase+' failed; sanitized evidence retained')
 return result
