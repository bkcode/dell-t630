#!/usr/bin/env python3
"""Read-only app/storage/identity snapshot on250; only hashes/counts/IDs emitted."""
import hashlib,importlib.util,json,os,socket,subprocess,sys,urllib.request
from pathlib import Path
if os.geteuid()!=0 or socket.gethostname().split('.')[0]!='penpot-service' or Path('/etc/pve').exists():raise SystemExit('assigned250 only')
sys.dont_write_bytecode=True
BASE=Path('/opt/dell/penpot');D=['docker','--host','unix:///var/run/docker.sock']
def run(args):
 p=subprocess.run(args,capture_output=True,text=True,timeout=30)
 if p.returncode:raise RuntimeError('snapshot metadata command failed')
 return p.stdout

def digest(path):
 with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def frame():
 out={}
 for cid in run(D+['ps','-aq']).split():
  fmt='{"name":{{json .Name}},"image":{{json .Image}},"running":{{json .State.Running}},"started_at":{{json .State.StartedAt}},"health":{{if (index .State "Health")}}{{json .State.Health.Status}}{{else}}null{{end}}}'
  out[cid]=json.loads(run(D+['inspect','--format',fmt,cid]))
 return out
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
net=json.loads(run(D+['inspect','--format','{{json .NetworkSettings.Networks}}','penpot-penpot-worker-1']));ip=next(n['IPAddress'] for n in net.values() if n['IPAddress'])
with opener.open('http://'+ip+':4404/readyz',timeout=6) as r:worker=json.load(r)
jobdir=Path('/srv/penpot/docker/volumes/penpot_penpot_import_jobs/_data');jobstates={}
for file in jobdir.glob('*.json'):
 if file.name.endswith('.tmp'):continue
 status=json.loads(file.read_text()).get('status','unknown');jobstates[status]=jobstates.get(status,0)+1
idle=worker.get('state')=='ready' and worker.get('activeTasks')==0 and not any(jobstates.get(k,0) for k in ['preparing','downloading','importing','unknown'])
if not idle:raise RuntimeError('worker or importer not idle; no changes allowed')
sys.path.insert(0,str(BASE));spec=importlib.util.spec_from_file_location('app_snapshot_api',BASE/'application/target-api.py');api=importlib.util.module_from_spec(spec);spec.loader.exec_module(api)
owner=api.API('owner');ledger=json.loads(Path('/etc/penpot/application-id-map.json').read_text());files={}
expected={'13a31dab-5204-818d-8008-e6fe8d7ec046','13a31dab-5204-818d-8008-e6feac0c763c','13a31dab-5204-818d-8008-e6febff84cd7'}
if {x['target_id'] for x in ledger['files'].values()}!=expected:raise RuntimeError('original-three-file-ledger differs')
for identity in sorted(expected):
 stats=owner.call('get-file-stats',{'id':identity});full=owner.call('get-file',{'id':identity})
 if not isinstance(full.get('data'),dict):raise RuntimeError('full original design data unavailable')
 files[identity]={'stats':stats,'revn':full.get('revn'),'vern':full.get('vern'),'data_sha256':hashlib.sha256(json.dumps(full['data'],sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()}
assets=Path('/srv/penpot/docker/volumes/penpot_penpot_assets/_data');asset_hashes={str(p.relative_to(assets)):digest(p) for p in assets.rglob('*') if p.is_file()}
secretfiles=['.env','new-identities.json','worker-credentials.json','worker-credentials.uid1001.json','worker-credentials.uid1000.json','application-id-map.json','automation-ready.json']
identity_hashes={f:digest(Path('/etc/penpot')/f) for f in secretfiles}
unit=Path('/etc/systemd/system/dell-penpot.service')
result={'status':'snapshot-collected','worker_idle':True,'worker_active_tasks':worker['activeTasks'],'import_job_status_counts':jobstates,'containers':frame(),'original_files':files,'media_files':len(asset_hashes),'media_unique_hashes':len(set(asset_hashes.values())),'media_path_to_sha256':asset_hashes,'identity_hashes':identity_hashes,'unit_sha256':digest(unit),'unit_content':unit.read_text(),'Git_HEAD':run(['git','--no-optional-locks','-C',str(BASE/'source'),'rev-parse','HEAD']).strip(),'Git_dirty':run(['git','--no-optional-locks','-C',str(BASE/'source'),'status','--porcelain=v1']).strip(),'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'snapshot_content_or_secret_values_emitted':False}
print(json.dumps(result))
