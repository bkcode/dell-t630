#!/usr/bin/env python3
"""PREPARED ONLY. Guest-local application-file cutover; never changes a NIC/router/PVE."""
import argparse
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import re
import socket
import stat
import subprocess
import tempfile
import time

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('media_patches',HERE/'patches.py');patch=importlib.util.module_from_spec(spec);spec.loader.exec_module(patch)
D=['/usr/bin/docker','--host','unix:///var/run/docker.sock']
ENV={'PATH':'/usr/sbin:/usr/bin:/sbin:/bin','LANG':'C','LC_ALL':'C'}
NASM='/srv/dev-disk-by-uuid-5b19837c-128c-498a-b79d-563db810c34a'
ROLES={
 250:dict(driver='overlay2',host='penpot-service',old_gateway='10.63.30.1',docker_root='/srv/penpot/docker',old='10.63.30.30',new='192.168.19.50',mac='bc:24:11:78:e9:84',mount='/srv/penpot',uuid='ccccda03-bffd-4054-afd3-e0e22f0c607e',unit='dell-penpot.service',names=['penpot-penpot-'+s+'-1' for s in ['frontend','backend','admin-console','exporter','dns','mcp','worker','import','postgres','valkey','mailpit']],files=['/opt/dell/penpot/assignment.json','/etc/penpot/.env','/opt/dell/penpot/compose.fresh.yaml','/opt/dell/penpot/application/target-api.py','/opt/dell/penpot/runtime/health-supervision/supervisor.py','/opt/dell/penpot/runtime/health-supervision/node-health.mjs','/opt/dell/penpot/runtime/health-supervision/deployment-lock.json'],protected=['/etc/penpot/'+s for s in ['new-identities.json','worker-credentials.json','worker-credentials.uid1001.json','worker-credentials.uid1000.json','application-id-map.json','automation-ready.json','fresh-instance.json']]),
 221:dict(driver='overlay2',host='artifact-service',old_gateway='10.63.30.1',docker_root='/var/lib/docker',old='10.63.30.20',new='192.168.19.31',mac='bc:24:11:ec:e1:6f',mount='/srv/nexus',uuid='239dc45a-b1f3-408b-a8ef-7afa77b52204',unit='dell-nexus.service',names=['nexus-nexus-1','nexus-gateway-1'],files=['/opt/dell/nexus/assignment.json','/opt/dell/nexus/fresh-instance.json','/etc/nexus.env','/opt/dell/nexus/application-import.py'],protected=['/root/dell-nexus-secrets/'+s+'-password' for s in ['admin','reader','publisher']]),
 260:dict(driver='overlayfs',host='nas-media',old_gateway='10.63.40.1',docker_root='/var/lib/docker',old='10.63.40.10',new='192.168.19.60',mac='bc:24:11:a7:3b:73',mount=NASM,uuid='5b19837c-128c-498a-b79d-563db810c34a',unit='dell-nas-jellyfin.service',names=['dell-nas-jellyfin-1'],files=['/opt/dell/nas/.env',patch.NAS_NETWORK],protected=['/etc/shadow','/home/ub/.ssh/authorized_keys','/usr/local/libexec/dell-nas-check-data'])}


def command(args,timeout=30,check=True):
 p=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=timeout,env=ENV)
 if check and p.returncode:raise patch.Rejected('fixed command failed; raw details withheld')
 return p


def read(path):
 p=Path(path)
 if not p.is_absolute() or p.resolve()!=p or not p.is_file() or p.stat().st_size>4*1024**2 or p.stat().st_nlink!=1:raise patch.Rejected('canonical bounded regular file required')
 return p.read_bytes()


def atomic(path,raw,mode=0o600,uid=0,gid=0):
 p=Path(path)
 if p.parent.resolve()!=p.parent or p.is_symlink():raise patch.Rejected('atomic destination path rejected')
 fd,name=tempfile.mkstemp(prefix='.dell19-',dir=p.parent)
 try:
  os.fchmod(fd,mode);os.fchown(fd,uid,gid)
  with os.fdopen(fd,'wb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
  os.replace(name,p)
 finally:
  if os.path.exists(name):os.unlink(name)


def save(path,value):atomic(path,(json.dumps(value,indent=2)+'\n').encode())


def matches_address(nics,r,phase):
 allowed={r['old']} if phase=='old' else {r['new']} if phase=='new' else {r['old'],r['new']}
 selected=[x for x in nics if x.get('address','').lower()==r['mac']]
 return len(selected)==1 and bool(allowed&{a.get('local') for a in selected[0].get('addr_info',[]) if a.get('prefixlen')==24})


def guard(role,phase):
 r=ROLES[role]
 if os.geteuid()!=0 or platform.system()!='Linux' or platform.machine() not in ('x86_64','amd64') or Path('/etc/pve').exists() or socket.gethostname().split('.')[0]!=r['host']:raise patch.Rejected('assigned AMD64 root guest only')
 if HERE!=Path('/opt/dell/network19/services-media'):raise patch.Rejected('reviewed guest package installation path required')
 for path in [Path('/opt'),Path('/opt/dell'),Path('/opt/dell/network19'),HERE,HERE/'guest_transaction.py',HERE/'patches.py']:
  if path.resolve()!=path or path.stat().st_uid!=0 or path.stat().st_mode&0o022:raise patch.Rejected('trusted package ownership required')
 rows=json.loads(command(['/usr/sbin/ip','-j','address','show']).stdout)
 if not matches_address(rows,r,phase):raise patch.Rejected('MAC-addressed old/new transition guard rejected')
 iface=next(x['ifname'] for x in rows if x.get('address','').lower()==r['mac'])
 gateways={r['old_gateway']} if phase=='old' else {'192.168.19.1'} if phase=='new' else {r['old_gateway'],'192.168.19.1'}
 routes=json.loads(command(['/usr/sbin/ip','-j','route','show','default']).stdout)
 if not any(x.get('dev')==iface and x.get('gateway') in gateways for x in routes):raise patch.Rejected('phase-specific MAC interface default gateway required')
 fs=json.loads(command(['/usr/bin/findmnt','--json','--mountpoint',r['mount'],'--output','TARGET,SOURCE,FSTYPE,UUID']).stdout)['filesystems']
 if len(fs)!=1 or fs[0]['target']!=r['mount'] or fs[0]['uuid']!=r['uuid'] or fs[0]['fstype']!='ext4' or os.stat(r['mount']).st_dev==os.stat('/').st_dev:raise patch.Rejected('same dedicated data UUID required')
 info=json.loads(command(D+['info','--format','{"name":{{json .Name}},"os":{{json .OSType}},"arch":{{json .Architecture}},"driver":{{json .Driver}},"root_dir":{{json .DockerRootDir}}}']).stdout)
 if info!={'name':r['host'],'os':'linux','arch':'x86_64','driver':r['driver'],'root_dir':r['docker_root']}:raise patch.Rejected('same local classic Docker daemon required')
 return r


def state(r):
 result=[]
 fmt='{"name":{{json .Name}},"id":{{json .Id}},"image":{{json .Image}},"running":{{json .State.Running}},"health":{{if .State.Health}}{{json .State.Health.Status}}{{else}}null{{end}}}'
 for name in r['names']:
  value=json.loads(command(D+['inspect','--type','container','--format',fmt,name]).stdout)
  if value['name'].lstrip('/')!=name:raise patch.Rejected('exact owned production container required')
  result.append(value)
 return result


def require_stopped(r):
 if any(x['running'] for x in state(r)):raise patch.Rejected('owned role containers must be stopped before file transaction')


def protected(r):return {p:patch.sha(read(p)) for p in r['protected']}


def prove_protected(r,j):
 if protected(r)!=j['protected_hashes']:raise patch.Rejected('identity/key/protected bytes changed; do not overwrite')


def pen_snapshot():
 # Existing read-only helper checks worker ready/activeTasks=0 and import jobs idle.
 p='/opt/dell/penpot/runtime/health-supervision/snapshot.py'
 s=Path(p).stat()
 if s.st_uid!=0 or s.st_mode&0o022:raise patch.Rejected('existing snapshot helper ownership required')
 return json.loads(command(['/usr/bin/python3','-I','-B',p],timeout=180).stdout)


def current_env_proof(role,raw):
 keys={250:{'PENPOT_PUBLIC_URI'},221:{'NEXUS_BIND_ADDRESS'},260:{'NAS_BIND_IP','JELLYFIN_PUBLIC_URL'}}[role]
 return patch.sha(b''.join(line for line in raw.splitlines(keepends=True) if line.split(b'=',1)[0].decode('utf8','replace') not in keys))


def stage(role,r,folder):
 if folder.exists():raise patch.Rejected('transaction nonce already exists; inspect journal rather than overwrite')
 files={p:read(p) for p in r['files']}
 if role==250:
  lock=json.loads(files['/opt/dell/penpot/runtime/health-supervision/deployment-lock.json'])
  for group,prefix in [('package_file_sha256','/opt/dell/penpot/'),('supervision_file_sha256','/opt/dell/penpot/runtime/health-supervision/')]:
   for key in lock[group]:
    if key.startswith('/') or '..' in key.split('/'):raise patch.Rejected('public lock relative path rejected')
    files[prefix+key]=read(prefix+key)
 changes,proof=patch.TRANSFORMS[role](files)
 before=state(r)
 if not all(x['running'] and x['health']=='healthy' for x in before):raise patch.Rejected('healthy role baseline required')
 baseline=pen_snapshot() if role==250 else None
 # Persistent transaction backups never leave this guest. Public output has no hashes.
 for directory in [Path('/root/dell-network19-media'),folder.parent]:
  directory.mkdir(mode=0o700,exist_ok=True)
  if directory.resolve()!=directory or directory.stat().st_uid!=0 or stat.S_IMODE(directory.stat().st_mode)!=0o700:raise patch.Rejected('private transaction directory ownership/mode rejected')
 folder.mkdir(mode=0o700)
 journal={'role':role,'phase':'staged','created_at':time.time(),'protected_hashes':protected(r),'before_containers':before,'files':[],'proof':proof,'penpot_baseline':baseline}
 for i,(path,new) in enumerate(changes.items()):
  old=files[path];s=Path(path).stat()
  if path.endswith('.env') and (s.st_uid!=0 or stat.S_IMODE(s.st_mode)!=0o600):raise patch.Rejected('private env mode600/root required')
  atomic(folder/(str(i)+'.old'),old);atomic(folder/(str(i)+'.new'),new)
  journal['files'].append({'path':path,'old_sha':patch.sha(old),'new_sha':patch.sha(new),'index':i,'mode':stat.S_IMODE(s.st_mode),'uid':s.st_uid,'gid':s.st_gid})
 save(folder/'journal.json',journal)


def validate_all(folder,j,target):
 # Full preflight before any target overwrite, including automatic rollback.
 for item in j['files']:
  old=read(folder/(str(item['index'])+'.old'));new=read(folder/(str(item['index'])+'.new'))
  if patch.sha(old)!=item['old_sha'] or patch.sha(new)!=item['new_sha']:raise patch.Rejected('backup/stage SHA mismatch')
  actual=patch.sha(read(item['path']))
  if actual not in ({item['old_sha']} if target=='commit' else {item['old_sha'],item['new_sha']}):raise patch.Rejected('third-party or interrupted file change; refuse overwrite')


def install_files(folder,j,new):
 validate_all(folder,j,'commit' if new else 'rollback')
 for item in j['files']:
  raw=read(folder/(str(item['index'])+('.new' if new else '.old')))
  atomic(item['path'],raw,item['mode'],item['uid'],item['gid'])
  j.setdefault('written',[]).append(item['path']);save(folder/'journal.json',j)


def validate_after_apply(role):
 if role==250:
  command(['/usr/bin/python3','-I','-B','/opt/dell/penpot/runtime/health-supervision/supervisor.py','check'],timeout=180)
  compose=D+['compose','--env-file','/etc/penpot/.env','-f','/opt/dell/penpot/compose.fresh.yaml','-f','/opt/dell/penpot/runtime/health-supervision/compose.health-supervision.yaml']
 elif role==221:
  command(['/usr/bin/python3','/opt/dell/nexus/manage.py','check','--env-file','/etc/nexus.env'],timeout=120)
  compose=D+['compose','--env-file','/etc/nexus.env','-f','/opt/dell/nexus/compose.yaml','-f','/opt/dell/nexus/compose.mount-gated.yaml']
 else:
  command(['/usr/local/libexec/dell-nas-check-data','--mountpoint',NASM,'--uuid',ROLES[260]['uuid']])
  compose=D+['compose','--env-file','/opt/dell/nas/.env','-f','/opt/dell/nas/compose.yaml']
 command(compose+['config','--quiet'])
 # Metadata-only reference check before a supervisor can start; no pull/build.
 for image in command(compose+['config','--images']).stdout.decode().split():
  command(D+['image','inspect','--format','{{.Id}}',image])


def start_wait(r,j,rollback):
 command(['/usr/bin/systemctl','start','--no-block',r['unit']])
 deadline=time.monotonic()+600
 while time.monotonic()<deadline:
  try:rows=state(r)
  except patch.Rejected:rows=[]  # Compose may briefly remove an owned name while recreating its binding.
  u=command(['/usr/bin/systemctl','show',r['unit'],'--property=ActiveState,SubState']).stdout.decode()
  if len(rows)==len(r['names']) and 'ActiveState=active\n' in u and 'SubState=running\n' in u and all(x['running'] and x['health']=='healthy' for x in rows):
   if {x['name']:x['image'] for x in rows}!={x['name']:x['image'] for x in j['before_containers']}:raise patch.Rejected('runtime image IDs changed')
   return
  time.sleep(3)
 raise patch.Rejected('bounded systemd readiness failed; do not rewrite state as healthy')


def rollback_permitted(phase):
 return phase in ['quiesced','applying','interrupted-needs-reviewed-rollback','applied-await-start','runtime-ready-final-app-verification-pending','rolled-back-files-await-old-network']


def main():
 os.umask(0o077)
 p=argparse.ArgumentParser();p.add_argument('action',choices=['preflight','stage','quiesce','commit-files','start','rollback-files','rollback-start']);p.add_argument('--role',type=int,choices=list(ROLES),required=True);p.add_argument('--window',default='')
 a=p.parse_args();phase='old' if a.action in ['preflight','stage','quiesce','rollback-start'] else 'new' if a.action in ['commit-files','start'] else 'transition';r=guard(a.role,phase)
 if a.action=='preflight':print(json.dumps({'status':'read-only-preflight','role':a.role}));return
 if not re.fullmatch('[a-f0-9]{32}',a.window):raise patch.Rejected('explicit root-reviewed role-window nonce required')
 folder=Path('/root/dell-network19-media')/str(a.role)/a.window
 if a.action=='stage':stage(a.role,r,folder)
 else:
  for directory in [folder.parent.parent,folder.parent,folder]:
   if directory.resolve()!=directory or directory.stat().st_uid!=0 or stat.S_IMODE(directory.stat().st_mode)!=0o700:raise patch.Rejected('private transaction ancestry rejected')
  if stat.S_IMODE((folder/'journal.json').stat().st_mode)!=0o600:raise patch.Rejected('private journal mode600 required')
  j=json.loads(read(folder/'journal.json'));prove_protected(r,j)
  if j['role']!=a.role:raise patch.Rejected('journal role differs')
  if a.action=='quiesce':
   if j['phase']!='staged':raise patch.Rejected('stage phase required')
   if a.role==250:pen_snapshot()
   command(['/usr/bin/systemctl','stop',r['unit']],timeout=240);require_stopped(r);j['phase']='quiesced';save(folder/'journal.json',j)
  elif a.action=='commit-files':
   if j['phase']!='quiesced':raise patch.Rejected('quiesced phase required')
   require_stopped(r);j['phase']='applying';save(folder/'journal.json',j)
   try:
    install_files(folder,j,True)
    env=next(x['path'] for x in j['files'] if x['path'].endswith('.env'))
    if current_env_proof(a.role,read(env))!=j['proof']['protected_env_bytes_sha256']:raise patch.Rejected('protected env bytes differ')
    prove_protected(r,j);validate_after_apply(a.role)
   except Exception:
    try:install_files(folder,j,False);j['phase']='rolled-back-files-await-old-network';save(folder/'journal.json',j)
    except Exception:j['phase']='interrupted-needs-reviewed-rollback';save(folder/'journal.json',j)
    raise patch.Rejected('file transaction failed; inspect private journal') from None
   j['phase']='applied-await-start';save(folder/'journal.json',j)
  elif a.action=='start':
   if j['phase']!='applied-await-start':raise patch.Rejected('applied transaction phase required')
   start_wait(r,j,False);prove_protected(r,j)
   if a.role==250:
    post=pen_snapshot();before=j['penpot_baseline']
    for key in ['original_files','media_path_to_sha256','Git_HEAD','Git_dirty']:
     if post[key]!=before[key]:raise patch.Rejected('original Penpot/Git/media changed; retain stopped/review option')
   j['phase']='runtime-ready-final-app-verification-pending';save(folder/'journal.json',j)
  elif a.action=='rollback-files':
   if not rollback_permitted(j['phase']):raise patch.Rejected('no committed or interrupted transaction to rollback')
   command(['/usr/bin/systemctl','stop',r['unit']],timeout=240);require_stopped(r);install_files(folder,j,False);prove_protected(r,j);j['phase']='rolled-back-files-await-old-network';save(folder/'journal.json',j)
  elif a.action=='rollback-start':
   if j['phase']!='rolled-back-files-await-old-network':raise patch.Rejected('rollback files and root old network first')
   start_wait(r,j,True);prove_protected(r,j);j['phase']='old-runtime-restored-final-verification-pending';save(folder/'journal.json',j)
 print(json.dumps({'status':'prepared-transaction-action-completed','role':a.role,'action':a.action,'secret_values_or_hashes_emitted':False,'network_or_identity_mutation':False}))


if __name__=='__main__':
 try:main()
 except Exception:
  print(json.dumps({'status':'rejected-or-unconfirmed','details_withheld':True,'inspect':'guest-private transaction journal if already staged'}));raise SystemExit(1)
