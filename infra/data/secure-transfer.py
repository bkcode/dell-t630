#!/usr/bin/env python3
"""Private data bundle transfer via in-memory tar/SSH STDIN; no secret argv/stdout."""
import hashlib,io,json,os,tarfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
ROLES={'prod-db':{'vmid':200,'guest_role':'data-prod-db','ip':'10.63.10.10'},'prod-infra':{'vmid':201,'guest_role':'data-prod-infra','ip':'10.63.10.11'},'test-data':{'vmid':210,'guest_role':'data-test','ip':'10.63.20.10'}}
PUBLIC_FILES={'.env','bundle.json','compose.yaml','images.lock.json','config/mysql.cnf','config/rabbitmq.conf','vendor/nacos-mysql-schema-2.4.3.sql','vendor/nacos-application-2.4.3.properties','scripts/manage.py','scripts/mysql-health.sh','scripts/nacos-entrypoint.sh','scripts/redis-entrypoint.sh','scripts/redis-health.sh','scripts/acceptance.py'}
SECRET_NAMES={'mysql-root-password','nacos-db-password','redis-password','rabbit-admin-password','rabbit-app-password','nacos-admin-password','nacos-client-password','nacos-identity-value','nacos-auth-token','rabbit-definitions.json'}

def envelope(role,product_uuid):
    if role not in ROLES:raise ValueError('role outside assigned data guest scope')
    bundle=ROOT/'private/data/bundles'/role
    meta=json.loads((bundle/'bundle.json').read_text())
    if meta['role']!=role or meta['service_ip']!=ROLES[role]['ip'] or not meta['data_filesystem_uuid']:raise ValueError('bundle role/address/filesystem identity incomplete')
    entries={}
    for path in bundle.rglob('*'):
        if path.is_symlink():raise ValueError('bundle symlink rejected')
        if not path.is_file():continue
        name=path.relative_to(bundle).as_posix()
        if name not in PUBLIC_FILES and not (name.startswith('secrets/') and name.split('/',1)[1] in SECRET_NAMES):
            raise ValueError('unexpected private bundle file; inspect before transmission')
        if name.startswith('secrets/') and path.stat().st_mode&0o777!=0o600:raise ValueError('secret file mode must be600')
        entries[name]=path.read_bytes()
    if role=='prod-db' and {x for x in entries if x.startswith('secrets/')}!={'secrets/mysql-root-password','secrets/nacos-db-password'}:raise ValueError('prod-db secret scope exceeded')
    header={'role':role,**ROLES[role],'product_uuid':product_uuid.lower(),'install_dir':meta['install_dir'],'data_mountpoint':meta['data_mountpoint'],'data_fs_uuid':meta['data_filesystem_uuid'],'files':{n:hashlib.sha256(b).hexdigest() for n,b in entries.items()}}
    out=io.BytesIO()
    with tarfile.open(fileobj=out,mode='w') as archive:
        for name,data in entries.items():
            item=tarfile.TarInfo(name);item.size=len(data);item.mode=0o755 if name.startswith('scripts/') else 0o600;archive.addfile(item,io.BytesIO(data))
    return json.dumps(header).encode()+b'\n'+out.getvalue()

REMOTE=r'''import sys,json,io,tarfile,hashlib,os,socket,subprocess
from pathlib import Path,PurePosixPath
expected={'prod-db':(200,'data-prod-db','10.63.10.10'),'prod-infra':(201,'data-prod-infra','10.63.10.11'),'test-data':(210,'data-test','10.63.20.10')}
raw=sys.stdin.buffer
head=raw.readline(65537)
if len(head)>65536:raise SystemExit('invalid transfer envelope header')
h=json.loads(head);role=h['role']
if role not in expected or (h['vmid'],h['guest_role'],h['ip'])!=expected[role]:raise SystemExit('target outside data scope')
if os.geteuid()!=0 or Path('/etc/pve').exists() or socket.gethostname().split('.')[0]!=h['guest_role']:raise SystemExit('target guest identity rejected')
if Path('/sys/class/dmi/id/product_uuid').read_text().strip().lower()!=h['product_uuid']:raise SystemExit('target VM UUID mismatch')
def run(args):
 p=subprocess.run(args,capture_output=True,text=True,timeout=30)
 if p.returncode:raise SystemExit('target prerequisite read failed')
 return p.stdout
ips=json.loads(run(['ip','-j','address','show']))
if not any(h['ip']==x.get('local') for a in ips for x in a.get('addr_info',[])):raise SystemExit('target private IP not active')
mount=Path(h['data_mountpoint'])
if str(mount)!='/srv/dell-data' or mount.resolve()!=mount:raise SystemExit('data mountpoint contract mismatch')
fs=json.loads(run(['findmnt','--json','--mountpoint',str(mount),'--output','TARGET,UUID,FSTYPE,OPTIONS']))['filesystems']
if len(fs)!=1 or fs[0].get('target')!=str(mount) or fs[0].get('uuid')!=h['data_fs_uuid'] or fs[0].get('fstype')!='ext4' or 'rw' not in fs[0].get('options','').split(','):raise SystemExit('data filesystem identity mismatch')
base=Path('/opt/dell/data')/role
if h['install_dir']!=str(base) or base.resolve(strict=False)!=base:raise SystemExit('install path mismatch or symlink')
blob=raw.read(2097153)
if len(blob)>2097152:raise SystemExit('bundle exceeds transfer limit')
with tarfile.open(fileobj=io.BytesIO(blob),mode='r:') as archive:
 members=archive.getmembers()
 if len(members)!=len(h['files']) or {m.name for m in members}!=set(h['files']) or any(not m.isfile() or PurePosixPath(m.name).is_absolute() or '..' in PurePosixPath(m.name).parts for m in members):raise SystemExit('bundle paths rejected')
 data={m.name:archive.extractfile(m).read() for m in members}
 if any(hashlib.sha256(b).hexdigest()!=h['files'][name] for name,b in data.items()):raise SystemExit('bundle integrity mismatch')
 metadata=json.loads(data['bundle.json'])
 env=dict(x.split('=',1) for x in data['.env'].decode().splitlines() if x)
 if metadata['role']!=role or env['ROLE']!=role or env['SERVICE_IP']!=h['ip'] or env['DATA_FS_UUID']!=h['data_fs_uuid'] or env['INSTALL_DIR']!=str(base):raise SystemExit('bundle internal identity mismatch')
 # Never silently replace a secret already installed on target.
 for name,b in data.items():
  target=base/name
  if target.is_symlink() or target.parent.resolve(strict=False)!=target.parent:raise SystemExit('existing target path symlink rejected')
  if name.startswith('secrets/') and target.exists() and target.read_bytes()!=b:raise SystemExit('target secret differs; explicit credential reconciliation required')
 active=subprocess.run(['systemctl','is-active','--quiet','dell-data-'+role+'.service'],capture_output=True)
 changed=any(not (base/name).exists() or (base/name).read_bytes()!=b for name,b in data.items())
 if active.returncode==0 and changed:raise SystemExit('refusing to overwrite active managed role; stop it deliberately first')
 if changed:
  base.mkdir(parents=True,exist_ok=True,mode=0o700);base.chmod(0o700)
  for name,b in data.items():
   target=base/name;target.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
   fd=os.open(target,os.O_WRONLY|os.O_CREAT|os.O_TRUNC|os.O_NOFOLLOW,0o755 if name.startswith('scripts/') else 0o600)
   with os.fdopen(fd,'wb') as out:out.write(b)
   target.chmod(0o755 if name.startswith('scripts/') else 0o600)
print(json.dumps({'role':role,'vmid':h['vmid'],'private_ip':h['ip'],'files':len(data),'mode':'secure-stdin-bundle','secrets_values_emitted':False,'source_business_data_included':False,'status':'copied' if changed else 'unchanged'}))
'''
