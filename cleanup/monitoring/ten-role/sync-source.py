#!/usr/bin/env python3
"""Future local-source pair sync after owner mainplan becomes12 physical roles."""
import argparse,hashlib,json,os,stat,tempfile,uuid
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];M=json.loads((HERE/'manifest.json').read_text());sha=lambda b:hashlib.sha256(b).hexdigest()
p=argparse.ArgumentParser();p.add_argument('--execute',action='store_true');a=p.parse_args()
if not a.execute:print(json.dumps({'status':'source-ten-role-candidates-only','Nexus_profile_unchanged':True,'source_files_not_written':True}));raise SystemExit(0)
plan=json.loads((ROOT/'plan.json').read_text());assert len(plan['roles'])==12 and {r.get('vmid',r.get('existing_ctid')) for r in plan['roles']}==set(M['exporter_ids'])|{100,190},'owner mainplan12 with221retained required'
for r in M['source_files']:assert sha((ROOT/r['path']).read_bytes())==r['old_SHA256'] and sha((HERE/r['candidate']).read_bytes())==r['new_SHA256']
def put(path,b,mode):
 fd,name=tempfile.mkstemp(prefix='.ten-role-source-',dir=path.parent)
 try:
  os.fchmod(fd,mode)
  with os.fdopen(fd,'wb') as f:f.write(b);f.flush();os.fsync(f.fileno())
  os.replace(name,path)
 finally:
  if os.path.exists(name):os.unlink(name)
backup=HERE/'source-backups'/uuid.uuid4().hex;backup.mkdir(parents=True,mode=0o700);old=[]
try:
 for i,r in enumerate(M['source_files']):
  p=ROOT/r['path'];b=p.read_bytes();mode=stat.S_IMODE(p.stat().st_mode);q=backup/(str(i)+'.before');q.write_bytes(b);q.chmod(0o600);old.append((p,b,mode));put(p,(HERE/r['candidate']).read_bytes(),mode)
except Exception:
 for p,b,mode in old:put(p,b,mode)
 raise
print(json.dumps({'status':'local-source-pair-synced','backup':str(backup),'mainplan_or_guest_written':False}))
