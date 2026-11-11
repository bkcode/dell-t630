#!/usr/bin/env python3
"""VM250 read-only idle/data/identity snapshot kept locally before narrow supervisor fix."""
import datetime,hashlib,json,os,socket,subprocess,urllib.request
from pathlib import Path
from zoneinfo import ZoneInfo
assert os.geteuid()==0 and socket.gethostname()=='penpot-service';os.umask(0o077)
ROOT=Path('/root/dell-penpot-dns-init-fix-20261111');BASE=Path('/opt/dell/penpot');SUP=BASE/'runtime/health-supervision'
def run(args,timeout=40):return subprocess.check_output(args,stderr=subprocess.PIPE,timeout=timeout).decode().strip()
def sha(p):
 with p.open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()
unit=run(['systemctl','is-active','dell-penpot.service']);assert unit=='active','wait-for-healthy-automatic-recovery-before-change'
net=json.loads(run(['docker','inspect','penpot-penpot-worker-1','--format','{{json .NetworkSettings.Networks}}']));ip=next(x['IPAddress']for x in net.values()if x['IPAddress']);o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with o.open('http://'+ip+':4404/readyz',timeout=5)as r:worker=json.loads(r.read(8192))
assert worker.get('state')in['ready','busy']and worker.get('activeTasks')==0,'MCP-worker-not-idle'
jobdir=Path('/srv/penpot/docker/volumes/penpot_penpot_import_jobs/_data');jobs={}
for p in jobdir.glob('*.json'):
 if p.name.endswith('.tmp'):continue
 state=json.loads(p.read_text()).get('status','unknown');jobs[state]=jobs.get(state,0)+1
assert not any(jobs.get(k,0)for k in ['queued','preparing','downloading','importing','unknown']),'import-job-active'
unit_source=Path('/etc/systemd/system/dell-penpot.service').read_text();files={}
for p in [SUP/'supervisor.py',SUP/'compose.health-supervision.yaml',SUP/'deployment-lock.json']:
 assert p.is_file()and not p.is_symlink()and p.stat().st_uid==0;files[str(p)]={'sha256':sha(p),'bytes':p.read_text(),'mode':p.stat().st_mode&0o777}
assert files[str(SUP/'supervisor.py')]['sha256']=='fdd384bf5470890eb1802cc2eacb49bcc0c0d96013cfe57b257c5021af3b0448'
lock=json.loads((SUP/'deployment-lock.json').read_text());assert lock['guest']['ip']=='192.168.19.50'
compose=['docker','compose','--project-directory',str(BASE),'--env-file','/etc/penpot/.env','-f',str(BASE/'compose.fresh.yaml'),'-f',str(SUP/'compose.health-supervision.yaml')];render=json.loads(run(compose+['config','--format','json']))
containers={}
for name in ['penpot-'+v+'-1'for v in lock['services']]:
 raw=json.loads(run(['docker','inspect',name]))[0];assert raw['State']['Running']and raw['State']['Health']['Status']=='healthy'
 containers[name]={'id':raw['Id'],'image':raw['Image'],'user':raw['Config']['User'],'command':raw['Config']['Cmd'],'hostconfig':{k:raw['HostConfig'].get(k)for k in ['Init','PidsLimit','Memory','NanoCpus','RestartPolicy','CapAdd','CapDrop','SecurityOpt','ReadonlyRootfs','NetworkMode']},'mounts':raw['Mounts'],'networks':sorted(raw['NetworkSettings']['Networks'])}
sql="SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_name IN ('file','file_data_fragment') ORDER BY table_name"
tables=run(['docker','exec','penpot-penpot-postgres-1','psql','-U','penpot','-d','penpot','-At','-c',sql]).splitlines();assert 'file'in tables
hashes={}
for table in tables:
 sql='SELECT COALESCE(json_agg(q),\'[]\'::json) FROM (SELECT id::text AS id,md5(row_to_json(t)::text) AS hash FROM public."'+table+'" t ORDER BY id) q'
 hashes[table]=json.loads(run(['docker','exec','penpot-penpot-postgres-1','psql','-U','penpot','-d','penpot','-At','-c',sql],timeout=90))
assets=Path('/srv/penpot/docker/volumes/penpot_penpot_assets/_data');media={str(p.relative_to(assets)):sha(p)for p in assets.rglob('*')if p.is_file()}
identity={str(p):sha(p)for p in Path('/etc/penpot').glob('*')if p.is_file()};git={'HEAD':run(['git','--no-optional-locks','-C',str(BASE/'source'),'rev-parse','HEAD']),'status':run(['git','--no-optional-locks','-C',str(BASE/'source'),'status','--porcelain'])};assert not git['status']
assert not ROOT.exists();ROOT.mkdir(mode=0o700)
private={'captured_at':datetime.datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),'files':files,'render':render,'containers':containers,'identity_hashes':identity,'design_table_hashes':hashes,'media':media,'Git':git,'unit_source_sha256':hashlib.sha256(unit_source.encode()).hexdigest(),'NRestarts':run(['systemctl','show','dell-penpot.service','-p','NRestarts','--value'])}
p=ROOT/'before-private.json';p.write_text(json.dumps(private));p.chmod(0o600)
print(json.dumps({'at':private['captured_at'],'status':'idle-guards-and-server-local-protection-snapshot-passed','worker_active_tasks':0,'import_job_status_counts':jobs,'running_healthy_containers':len(containers),'design_table_row_counts':{k:len(v)for k,v in hashes.items()},'media_files':len(media),'Git_HEAD':git['HEAD'],'Git_clean':True,'NRestarts_before':private['NRestarts'],'private_data_hashes_config_and_credentials_retained_only_on_VM250':True,'planned_change':'DNS Init true plus strict runtime guard and bounded secret-free failure ledger','images_designs_credentials_and_other_resources_to_change':False}))
