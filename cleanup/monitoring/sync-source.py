#!/usr/bin/env python3
"""Explicit local source-sync only after owner updates mainplan to final11 VMIDs."""
import argparse,hashlib,json,os,stat,tempfile,uuid
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
def sha(b):return hashlib.sha256(b).hexdigest()
def atomic(path,b,mode):
 fd,name=tempfile.mkstemp(prefix='.cleanup-monitoring-',dir=path.parent)
 try:
  os.fchmod(fd,mode)
  with os.fdopen(fd,'wb') as f:f.write(b);f.flush();os.fsync(f.fileno())
  os.replace(name,path)
 finally:
  if os.path.exists(name):os.unlink(name)
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--execute',action='store_true');a=p.parse_args();M=json.loads((HERE/'manifest.json').read_text());rows=M['source_sync']
if not a.execute:print(json.dumps({'status':'source-candidates-only','files':rows,'current_source_written':False}));raise SystemExit(0)
plan=json.loads((ROOT/'plan.json').read_text());ids={r.get('vmid',r.get('existing_ctid')) for r in plan['roles']};assert len(plan['roles'])==11 and ids==set(M['exporter_VMIDs'])|{100,190},'parent mainplan must first reflect final11; no plan write is performed'
for r in rows:
 target=ROOT/r['path'];assert not target.is_symlink() and sha(target.read_bytes())==r['expected_old_SHA256'];assert sha((HERE/r['candidate']).read_bytes())==r['new_SHA256']
backup=HERE/'source-backups'/uuid.uuid4().hex;backup.mkdir(parents=True,mode=0o700);old=[]
try:
 for index,r in enumerate(rows):
  path=ROOT/r['path'];body=path.read_bytes();mode=stat.S_IMODE(path.stat().st_mode);b=backup/(str(index)+'.before');b.write_bytes(body);b.chmod(0o600);old.append((path,body,mode));atomic(path,(HERE/r['candidate']).read_bytes(),mode)
except Exception:
 for path,body,mode in old:atomic(path,body,mode)
 raise
(backup/'manifest.json').write_text(json.dumps(rows,indent=2)+'\n');(backup/'manifest.json').chmod(0o600);print(json.dumps({'status':'local-source-synced','backup':str(backup),'mainplan_modified':False,'host_or_guest_writes':False}))
