#!/usr/bin/env python3
"""Manager runner: transfer public code only; return sanitized metadata, never snapshots."""
import argparse,base64,datetime,importlib.util,json,shlex,sys
from pathlib import Path
sys.dont_write_bytecode=True
BASE=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('full_restore_control',BASE/'scripts/control.py');control=importlib.util.module_from_spec(s);s.loader.exec_module(control)
STAGE='''import os,socket,sys,json,base64,ast
from pathlib import Path
expected=EXPECTED
if os.geteuid()!=0 or socket.gethostname().split('.')[0]!=expected or Path('/etc/pve').exists():raise SystemExit('assigned data guest only')
p=Path('/opt/dell/full-snapshot-restore')
if p.resolve(strict=False)!=p:raise SystemExit('symlink stage rejected')
p.mkdir(mode=0o700,exist_ok=True);p.chmod(0o700)
values=json.loads(sys.stdin.read(100000))
if set(values)!={'worker.py','sql_snapshot.py'}:raise SystemExit('public source file set invalid')
for name,value in values.items():
 data=base64.b64decode(value);ast.parse(data.decode());path=p/name
 fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_TRUNC|os.O_NOFOLLOW,0o700)
 with os.fdopen(fd,'wb') as out:out.write(data)
print(json.dumps({'public_code_staged':True,'private_data_transferred':False}))'''
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def main():
 p=argparse.ArgumentParser();p.add_argument('component',choices=['nacos','redis','rabbit-topology']);p.add_argument('--execute-approved-local-restore',action='store_true');a=p.parse_args()
 vmid=200 if a.component=='nacos' else 201;name='data-prod-db' if vmid==200 else 'data-prod-infra';ip='10.63.10.10' if vmid==200 else '10.63.10.11'
 rows=json.loads((BASE/'evidence/implementation/private-guest-access.json').read_text())['roles'];row=next(x for x in rows if x['target']['vmid']==vmid)
 if row['name']!=name or row['target']['ip']!=ip or row['status']!='ssh-verified':raise RuntimeError('strict existing target proof mismatch')
 payload={name:base64.b64encode((HERE/name).read_bytes()).decode() for name in ['worker.py','sql_snapshot.py']}
 r=control.guest(vmid,'sudo -n python3 -c '+shlex.quote(STAGE.replace('expected=EXPECTED','expected='+repr(name))),data=json.dumps(payload).encode(),timeout=60,info=row['target'])
 if r['exit_code']:raise RuntimeError('public stage failed; no snapshot transferred')
 action='--execute-approved-local-restore' if a.execute_approved_local_restore else '--check-only'
 result=control.guest(vmid,shlex.join(['sudo','-n','python3','-I','/opt/dell/full-snapshot-restore/worker.py',a.component,action]),timeout=900 if a.execute_approved_local_restore else 120,info=row['target'])
 # Worker deliberately prints only metadata. No SQL/RDB/definitions or raw container logs returned.
 evidence=BASE/'evidence/implementation'/('full-snapshot-'+a.component+('-restore' if a.execute_approved_local_restore else '-preflight')+'.json')
 if evidence.exists():
  history=evidence.with_name(evidence.stem+'-previous-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%f')+'.json');history.write_bytes(evidence.read_bytes())
 record={'collected_at':now(),'vmid':vmid,'component':a.component,'exit_code':result['exit_code'],'stdout':result['stdout'],'stderr':result['stderr'],'snapshot_content_exported':False,'CF_accessed':False};evidence.write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record))
 return result['exit_code']
if __name__=='__main__':raise SystemExit(main())
