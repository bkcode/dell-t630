#!/usr/bin/env python3
"""Owned guest250 runner; new owner session remains on that guest for read-only checks."""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
import control
control.BASE += ['-o', 'ForwardAgent=no']
row = next(x for x in json.loads((ROOT / 'evidence/implementation/private-guest-access.json').read_text())['roles'] if x['target']['vmid'] == 250)
source = Path(__file__).with_suffix('.mjs').read_text()
guest = r'''
import hashlib, importlib.util, json, subprocess, sys, time
from pathlib import Path
BASE=Path('/opt/dell/penpot')
sys.path.insert(0,str(BASE))
from target_guard import verify_target
verify_target(require_docker_data=True)
spec=importlib.util.spec_from_file_location('target_api',BASE/'application/target-api.py')
api=importlib.util.module_from_spec(spec);spec.loader.exec_module(api)
owner=api.API('owner')
FILE='13a31dab-5204-818d-8008-e7004b9343a1'; PAGE='13a31dab-5204-818d-8008-e7004b9343a2'
ledger=json.loads(Path('/etc/penpot/application-id-map.json').read_text())
ids=[x['target_id'] for x in ledger['files'].values()]
def stats():return {i:owner.call('get-file-stats',{'id':i}) for i in ids}
def hashes():return {p:hashlib.sha256(Path('/etc/penpot',p).read_bytes()).hexdigest() for p in ['new-identities.json','worker-credentials.json','application-id-map.json']}
before_stats=stats();before_hashes=hashes()
def backend(expected):
 started=time.monotonic();last_name=None;count=0
 while time.monotonic()-started<25:
  count+=1
  full=owner.call('get-file',{'id':FILE});data=full['data']
  pages=data.get('pages-index',data.get('pagesIndex'))
  if not isinstance(pages,dict) or PAGE not in pages:raise RuntimeError('Backend acceptance page absent')
  if full['id']!=FILE or full['name']!='Dell dedicated MCP acceptance':raise RuntimeError('Backend context mismatch')
  page=pages[PAGE]
  objects=page['objects']
  if len(objects)!=1 or objects['00000000-0000-0000-0000-000000000000'].get('shapes',[]):raise RuntimeError('Backend dedicated page not empty')
  last_name=page['name']
  if last_name==expected:return {'ok':True,'name':last_name,'revn':full['revn'],'polls':count,'elapsed_ms':round((time.monotonic()-started)*1000),'source':'independent owner get-file API'}
  time.sleep(.5)
 return {'ok':False,'observed_name':last_name,'polls':count,'reason':'25 second persistence deadline exceeded'}
cmd=['docker','compose','--env-file','/etc/penpot/.env','-f',str(BASE/'compose.fresh.yaml'),'exec','-T','-e','DELL_MCP_NAME_ROUNDTRIP=parent-approved-target250-window','penpot-worker','node','--input-type=module','-e',SOURCE]
p=subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,bufsize=1)
receipt=None
for line in p.stdout:
 try:item=json.loads(line)
 except json.JSONDecodeError:continue
 if 'backend_check' in item:
  try:reply=backend(item['expected'])
  except Exception:reply={'ok':False,'reason':'independent backend verifier rejected context or API request'}
  p.stdin.write(json.dumps(reply)+'\n');p.stdin.flush()
 elif 'receipt' in item:receipt=item['receipt']
p.wait(timeout=30)
if receipt is None:raise RuntimeError('MCP roundtrip did not return a receipt')
receipt.update(process_exit_code=p.returncode,migrated_original_stats_unchanged=stats()==before_stats,new_identity_and_idmap_hashes_unchanged=hashes()==before_hashes)
receipt['backend_final']=backend('Page 1')
if not all([receipt['migrated_original_stats_unchanged'],receipt['new_identity_and_idmap_hashes_unchanged'],receipt['backend_final']['ok']]):receipt['status']='failed'
out=BASE/'application/mcp-name-roundtrip-result.json';out.write_text(json.dumps(receipt,indent=2)+'\n');out.chmod(0o644)
print(json.dumps(receipt))
raise SystemExit(0 if receipt['status']=='passed' and p.returncode==0 else 1)
'''.replace('SOURCE', repr(source))
r = control.guest(250, 'sudo python3 -', data=guest.encode(), timeout=360, info=row['target'])
try:
    value = json.loads(r['stdout'])
except json.JSONDecodeError:
    raise SystemExit('Target roundtrip did not return public evidence; inspect target without rerunning a write')
out = ROOT / 'infra/penpot/application/mcp-name-roundtrip-result.json'
out.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')
print(json.dumps(value, ensure_ascii=False))
raise SystemExit(r['exit_code'])
