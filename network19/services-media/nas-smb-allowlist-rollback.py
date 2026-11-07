#!/usr/bin/env python3
"""PREPARED ONLY: reviewed NAS network rollback adjunct, before root restores old OS network."""
import importlib.util,json,sys
from pathlib import Path
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('smb_network',HERE/'nas-smb-allowlist-apply.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

def main():
 if sys.argv[1:]!=['--root-reviewed-rollback--SMB-clients-drained']:raise RuntimeError('explicit root rollback/drained confirmation required')
 tx=m.tx;r=tx.guard(260,'new');tx.require_stopped(r)
 folder=Path('/root/dell-network19-media/260/1c97ce46e0e8494aa67f95768a818753');app=json.loads(tx.read(folder/'journal.json'));tx.prove_protected(r,app)
 path=folder/'smb-network-policy.json';record=json.loads(tx.read(path));assert record['phase']=='applied-verified'
 current=m.read_objects()
 for name,obj in current.items():
  expected=record['new_parameters'][name]
  assert {k:obj[k] for k in expected}==expected,'policy or permission drift; no overwrite'
 for name in m.SHARES:m.rpc(record['old_parameters'][name])
 tx.command(['/usr/sbin/omv-salt','deploy','run','samba'],timeout=240)
 assert m.effective()==record['effective_before'];tx.prove_protected(r,app)
 record['phase']='explicit-old-network-allowlist-restored';tx.save(path,record)
 print(json.dumps({'role':260,'status':'old-SMB-network-allowlists-restored-no-account-change'}))

if __name__=='__main__':
 try:main()
 except Exception:
  print(json.dumps({'role':260,'status':'SMB-policy-rollback-rejected-or-unconfirmed','private_backup_retained':True}));raise SystemExit(1)
