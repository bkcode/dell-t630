#!/usr/bin/env python3
"""Read-only content/identity/runtime comparison after DNS init fix; private hashes stay VM250."""
import datetime,hashlib,importlib.util,json,os,socket,subprocess,urllib.request
from pathlib import Path
from zoneinfo import ZoneInfo
assert os.geteuid()==0 and socket.gethostname()=='penpot-service';ROOT=Path('/root/dell-penpot-dns-init-fix-20261111');BASE=Path('/opt/dell/penpot');SUP=BASE/'runtime/health-supervision';before=json.loads((ROOT/'before-private.json').read_text())
def run(args,timeout=45):return subprocess.check_output(list(map(str,args)),stderr=subprocess.PIPE,timeout=timeout).decode().strip()
def sha(p):
 with p.open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()
assert run(['systemctl','is-active','dell-penpot.service'])=='active';assert run(['systemctl','is-enabled','dell-penpot.service'])=='enabled'
s=importlib.util.spec_from_file_location('fixed_supervisor',SUP/'supervisor.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);lock=m.load_lock();m.guest_guard();m.storage_guard(lock);m.verify_files_and_images(lock);m.check_config(lock);frame=m.scan();assert m.validate_frame(frame,lock)
containers={}
for name,old in before['containers'].items():
 v=json.loads(run(['docker','inspect',name]))[0];assert v['State']['Running']and v['State']['Health']['Status']=='healthy';assert v['Image']==old['image']and v['Config']['User']==old['user']and v['Config']['Cmd']==old['command']and v['Mounts']==old['mounts']and sorted(v['NetworkSettings']['Networks'])==old['networks']
 for key,value in old['hostconfig'].items():
  if key!='Init':assert v['HostConfig'].get(key)==value
 if name=='penpot-penpot-dns-1':assert v['HostConfig'].get('Init')is True and v['Id']!=old['id']
 else:assert v['Id']==old['id']and v['HostConfig'].get('Init')==old['hostconfig']['Init']
 containers[name]={'id':v['Id'],'image':v['Image'],'healthy':True,'init':v['HostConfig'].get('Init')}
for table,rows in before['design_table_hashes'].items():
 sql='SELECT COALESCE(json_agg(q),\'[]\'::json) FROM (SELECT id::text AS id,md5(row_to_json(t)::text) AS hash FROM public."'+table+'" t ORDER BY id) q'
 actual=json.loads(run(['docker','exec','penpot-penpot-postgres-1','psql','-U','penpot','-d','penpot','-At','-c',sql],timeout=90));assert actual==rows,'design-table-changed-review-before-signoff'
assets=Path('/srv/penpot/docker/volumes/penpot_penpot_assets/_data');actual={str(p.relative_to(assets)):sha(p)for p in assets.rglob('*')if p.is_file()};assert actual==before['media'],'media-content-or-path-changed'
assert all(sha(Path(p))==digest for p,digest in before['identity_hashes'].items())
assert sha(Path('/etc/systemd/system/dell-penpot.service'))==before['unit_source_sha256']
head=run(['git','--no-optional-locks','-C',BASE/'source','rev-parse','HEAD']);assert head==before['Git']['HEAD']and not run(['git','--no-optional-locks','-C',BASE/'source','status','--porcelain'])
network=json.loads(run(['docker','inspect','penpot-penpot-worker-1','--format','{{json .NetworkSettings.Networks}}']));ip=next(v['IPAddress']for v in network.values()if v['IPAddress']);o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with o.open('http://'+ip+':4404/readyz',timeout=5)as r:worker=json.loads(r.read(8192));assert r.status==200 and worker['state']in['ready','busy']
DNS=json.loads(run(['docker','inspect','penpot-penpot-dns-1']))[0];pid=DNS['State']['Pid'];comm=Path('/proc/'+str(pid)+'/comm').read_text().strip();assert comm in['docker-init','tini']
parents={pid};processes=run(['ps','-eo','pid,ppid,stat,comm']).splitlines()[1:];rows=[]
for line in processes:
 f=line.split()
 if len(f)>=4:rows.append((int(f[0]),int(f[1]),f[2],f[3]))
for v in rows:
 if v[1]==pid:parents.add(v[0])
zombies=[v for v in rows if v[1]in parents and v[2].startswith('Z')];assert not zombies
cg=Path('/sys/fs/cgroup')/Path('/proc/'+str(pid)+'/cgroup').read_text().strip().split(':',2)[-1].lstrip('/');counts={k:(cg/k).read_text().strip()for k in ['pids.current','pids.max','pids.events']};assert counts['pids.max']=='128'
value={'at':datetime.datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),'status':'fixed-init-runtime-guards-and-all-design-media-identity-protection-verified','running_healthy_services':11,'design_table_rows_preserved':{k:len(v)for k,v in before['design_table_hashes'].items()},'all_design_row_hashes_equal':True,'media_file_paths_and_every_byte_SHA_equal':True,'media_files':len(actual),'all_original_identity_credentials_env_bytes_preserved':True,'Git_HEAD':head,'Git_clean':True,'DNS_only_recreated':True,'other_ten_container_IDs_preserved':True,'all_images_users_caps_mounts_networks_readonly_CPU_memory_PIDlimits_restart_policy_preserved':True,'DNS_Init':True,'DNS_PID1':comm,'DNS_current_zombies':0,'DNS_cgroup_PID_counters':counts,'NRestarts':run(['systemctl','show','dell-penpot.service','-p','NRestarts','--value']),'supervisor_public_SHA':sha(SUP/'supervisor.py'),'base_unit_bytes_preserved':True,'worker_ready':True,'worker_active_tasks':worker.get('activeTasks'),'design_writes_or_data_migration':False,'private_content_and_hashes_exported':False}
p=ROOT/'postcheck-result.json';p.write_text(json.dumps(value,indent=2)+'\n');p.chmod(0o600);print(json.dumps(value))
