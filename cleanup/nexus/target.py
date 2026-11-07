#!/usr/bin/env python3
"""Same-instance Nexus220 relocation. Stage allowed now; mount/commit/start require root handover."""
import argparse,hashlib,importlib.util,json,os,platform,re,socket,stat,subprocess,sys,tempfile,time
from pathlib import Path
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('relocation',HERE/'relocate.py');r=importlib.util.module_from_spec(s);s.loader.exec_module(r)
D=['/usr/bin/docker','--host','unix:///var/run/docker.sock'];ENV={'PATH':'/usr/sbin:/usr/bin:/sbin:/bin','LANG':'C','LC_ALL':'C','HOME':'/root'}


def run(args,timeout=30,check=True):
 p=subprocess.run(args,capture_output=True,text=True,env=ENV,timeout=timeout)
 if check and p.returncode:raise RuntimeError('fixed target operation failed; raw details withheld')
 return p


def read(path,limit=2*1024**2):
 p=Path(path);s=p.stat()
 if p.resolve()!=p or not p.is_file() or s.st_nlink!=1 or s.st_size>limit:raise RuntimeError('bounded canonical regular file required')
 return p.read_bytes()


def sha(raw):return hashlib.sha256(raw).hexdigest()


def atomic(path,raw,mode=0o600):
 p=Path(path);assert p.parent.resolve()==p.parent and not p.is_symlink()
 fd,tmp=tempfile.mkstemp(prefix='.nexus-move-',dir=p.parent)
 try:
  with os.fdopen(fd,'wb') as f:os.fchmod(f.fileno(),mode);f.write(raw);f.flush();os.fsync(f.fileno())
  os.replace(tmp,p)
 finally:
  if os.path.exists(tmp):os.unlink(tmp)


def save(path,value):atomic(path,(json.dumps(value,indent=2)+'\n').encode())


def guard(final):
 if os.geteuid()!=0 or socket.gethostname().split('.')[0]!='publish-service' or Path('/etc/pve').exists() or platform.machine()!='x86_64':raise RuntimeError('assigned220 only')
 for p in [HERE,HERE/'target.py',HERE/'relocate.py']:
  if p.resolve()!=p or p.stat().st_uid!=0 or p.stat().st_mode&0o022:raise RuntimeError('trusted root tools required')
 rows=json.loads(run(['/usr/sbin/ip','-j','addr']).stdout);nic=[x for x in rows if x.get('address','').lower()=='bc:24:11:2a:01:ad'];assert len(nic)==1
 ips={a['local'] for a in nic[0].get('addr_info',[]) if a.get('family')=='inet' and a.get('prefixlen')==24}
 assert ips==({'192.168.19.30','192.168.19.31'} if final else {'192.168.19.30'}),'root owns service alias transfer; do not bind it here'
 info=json.loads(run(D+['info','--format','{"name":{{json .Name}},"driver":{{json .Driver}},"root":{{json .DockerRootDir}},"arch":{{json .Architecture}}}']).stdout)
 assert info=={'name':'publish-service','driver':'overlay2','root':'/var/lib/docker','arch':'x86_64'}
 assert 'docker' not in run(['/usr/bin/id','publisher']).stdout
 if final:
  mem=int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemTotal:')))*1024
  assert os.cpu_count()>=6 and mem>=7.5*1024**3,'root6CPU8GiB resource change must precede final start'
  route=json.loads(run(['/usr/sbin/ip','-j','route','get','192.168.19.45']).stdout);assert len(route)==1 and route[0].get('prefsrc',route[0].get('src'))=='192.168.19.30','publisher default egress must remain primary30; never use its key to test this'
 for identity in r.IMAGES.values():
  metadata=json.loads(run(D+['image','inspect','--format','{"id":{{json .Id}},"OS":{{json .Os}},"arch":{{json .Architecture}}}',identity]).stdout)
  assert metadata=={'id':identity,'OS':'linux','arch':'amd64'}


def disk_guard():
 fs=json.loads(run(['/usr/bin/findmnt','--json','--mountpoint','/srv/nexus','--output','TARGET,SOURCE,FSTYPE,UUID']).stdout)['filesystems']
 assert len(fs)==1 and fs[0]['target']=='/srv/nexus' and fs[0]['uuid']==r.DATA_UUID and fs[0]['fstype']=='ext4'
 assert os.stat('/srv/nexus').st_dev!=os.stat('/').st_dev
 data=Path('/srv/nexus/data');assert data.is_dir() and data.stat().st_uid==200 and data.stat().st_gid==200 and any(data.iterdir())
 assert (data/'db').is_dir() and (data/'blobs').is_dir(),'existing database/blob tree required; never initialize fresh'


def stage(folder):
 incoming=folder/'incoming';manifest=json.loads(read(incoming/'private-manifest.json'))['files'];files={}
 for key in r.FILES:
  p=incoming/key.replace('/','__');s=p.stat();assert s.st_uid==0 and stat.S_IMODE(s.st_mode)==0o600
  raw=read(p);assert len(raw)==manifest[key]['size'] and sha(raw)==manifest[key]['sha256'];files[key]=raw
 changed=r.transformed(files);prepared=folder/'prepared';assert not prepared.exists();prepared.mkdir(mode=0o700)
 entries={}
 for key,raw in changed.items():atomic(prepared/key.replace('/','__'),raw);entries[key]={'sha256':sha(raw),'source_unchanged':raw==files[key]}
 assert all(entries[key]['source_unchanged'] for key in r.FILES if key.startswith(('secret/','env/')))
 save(folder/'relocation.json',{'phase':'prepared-no-active-install','entries':entries,'identity_source':'same owned active221 instance','expected_source221_off_before_start':True,'source_filesystem_uuid':r.DATA_UUID,'target_primary':'192.168.19.30','service_alias':'192.168.19.31','target_hostname':'publish-service'})


def mount_existing(folder):
 source=Path('/dev/disk/by-uuid')/r.DATA_UUID;assert source.exists(),'root must reassign original disk first'
 p=Path('/srv/nexus')
 if not p.exists():p.mkdir(mode=0o755)
 mounted=run(['/usr/bin/mountpoint','-q',str(p)],check=False).returncode==0
 if mounted:disk_guard();return
 assert not any(p.iterdir()),'do not shadow a nonempty rootfs directory'
 fstab=Path('/etc/fstab');old=read(fstab)
 active=[x for x in old.decode().splitlines() if x.strip() and not x.lstrip().startswith('#')]
 assert not any('/srv/nexus' in x or r.DATA_UUID in x for x in active),'existing fstab ownership must be reviewed'
 atomic(folder/'fstab.before',old)
 line='UUID='+r.DATA_UUID+' /srv/nexus ext4 defaults,nofail,x-systemd.device-timeout=10s 0 2\n'
 atomic(fstab,old+(b'' if old.endswith(b'\n') else b'\n')+line.encode(),0o644)
 run(['/usr/bin/systemctl','daemon-reload']);run(['/usr/bin/mount','/srv/nexus']);disk_guard()


def commit(folder):
 disk_guard();j=json.loads(read(folder/'relocation.json'));assert j['phase']=='prepared-no-active-install'
 assert not Path('/opt/dell/nexus').exists() and not Path('/root/dell-nexus-secrets').exists() and not Path('/etc/nexus.env').exists() and not Path('/etc/systemd/system/dell-nexus.service').exists(),'do not overwrite another installation'
 assert run(D+['ps','-aq']).stdout.strip()==''
 entries=j['entries']
 for key in r.FILES:assert sha(read(folder/'prepared'/key.replace('/','__')))==entries[key]['sha256']
 # Preflight complete before any active destination write. Service is installed last, not started.
 for key,target in r.FILES.items():
  path=Path(target);path.parent.mkdir(parents=True,mode=0o700,exist_ok=True)
  private=key.startswith(('secret/','env/')) or key=='package/fresh-instance.json'
  atomic(path,read(folder/'prepared'/key.replace('/','__')),0o600 if private else 0o644)
 run(['/usr/bin/python3','/opt/dell/nexus/manage.py','check','--env-file','/etc/nexus.env'],timeout=90)
 run(['/usr/bin/systemd-analyze','verify','/etc/systemd/system/dell-nexus.service'],timeout=60)
 run(['/usr/bin/systemctl','daemon-reload']);run(['/usr/bin/systemctl','enable','dell-nexus.service'])
 j['phase']='installed-no-start';save(folder/'relocation.json',j)


def frame():
 fmt='{"name":{{json .Name}},"id":{{json .Id}},"image":{{json .Image}},"running":{{json .State.Running}},"health":{{if .State.Health}}{{json .State.Health.Status}}{{else}}null{{end}}}'
 values=[]
 for name in ['nexus-nexus-1','nexus-gateway-1']:
  p=run(D+['inspect','--format',fmt,name],check=False)
  if p.returncode:return []
  values.append(json.loads(p.stdout))
 return values


def start(folder):
 disk_guard();j=json.loads(read(folder/'relocation.json'));assert j['phase']=='installed-no-start'
 run(['/usr/bin/systemctl','start','--no-block','dell-nexus.service']);deadline=time.monotonic()+600
 while time.monotonic()<deadline:
  rows=frame();unit=run(['/usr/bin/systemctl','show','dell-nexus.service','--property=ActiveState,SubState']).stdout
  if len(rows)==2 and all(x['running'] and x['health']=='healthy' for x in rows) and 'ActiveState=active\n' in unit and 'SubState=running\n' in unit:
   assert {x['image'] for x in rows}==set(r.IMAGES.values())
   for key,target in r.FILES.items():
    if key.startswith('secret/'):assert sha(read(target))==j['entries'][key]['sha256']
   j['phase']='running-final-data-and-publisher-verification-required';save(folder/'relocation.json',j);return rows
  time.sleep(3)
 raise RuntimeError('bounded Nexus health startup remains unconfirmed')


def main():
 os.umask(0o077);p=argparse.ArgumentParser();p.add_argument('action',choices=['stage','mount','commit','start']);p.add_argument('--nonce',required=True);p.add_argument('--root-source221-off-and-disk-handover-complete',action='store_true');a=p.parse_args();assert re.fullmatch('[a-f0-9]{32}',a.nonce)
 final=a.action!='stage';guard(final)
 if final and not a.root_source221_off_and_disk_handover_complete:raise RuntimeError('explicit root coldbackup/disk/IP ownership handover confirmation required')
 folder=Path('/root/dell-nexus-merge')/a.nonce;assert folder.resolve()==folder and folder.stat().st_uid==0 and stat.S_IMODE(folder.stat().st_mode)==0o700
 if a.action=='stage':stage(folder)
 elif a.action=='mount':mount_existing(folder)
 elif a.action=='commit':commit(folder)
 else:start(folder)
 print(json.dumps({'role':220,'status':'Nexus-relocation-'+a.action+'-completed','service_alias':'192.168.19.31','hostname':'publish-service','secret_values_or_private_hashes_emitted':False}))

if __name__=='__main__':
 try:main()
 except Exception:
  print(json.dumps({'role':220,'status':'Nexus-relocation-rejected-or-unconfirmed','private_stage_retained':True}));raise SystemExit(1)
