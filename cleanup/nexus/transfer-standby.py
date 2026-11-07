#!/usr/bin/env python3
"""Approved221->220 minimal standby stream, no local secret archive and no runtime data copy."""
import importlib.util,json,shlex,subprocess,sys,uuid
from pathlib import Path
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
spec=importlib.util.spec_from_file_location('contract',HERE/'relocate.py');contract=importlib.util.module_from_spec(spec);spec.loader.exec_module(contract)
sys.path.insert(0,str(ROOT/'scripts'));import control
control.BASE+=['-o','ForwardAgent=no'];targets=json.loads((ROOT/'network19/evidence/migrated-access.json').read_text())['targets'];nonce=uuid.uuid4().hex
(HERE/'standby-window.json').write_text(json.dumps({'nonce':nonce,'source_vmid':221,'target_vmid':220,'source':'192.168.19.31','target_primary':'192.168.19.30','scope':'minimal code/env/new-owned-Nexus secrets only; no publisher or SSH identities/runtime data'},indent=2)+'\n')
SOURCE=r'''
import hashlib,io,json,os,socket,stat,sys,tarfile
from pathlib import Path
assert os.geteuid()==0 and socket.gethostname().split('.')[0]=='artifact-service' and not Path('/etc/pve').exists()
FILES=FILE_MAP
values={}
for name,path in FILES.items():
 p=Path(path);s=p.stat();assert p.resolve()==p and s.st_uid==0 and s.st_nlink==1 and s.st_size<=1024*1024 and not(s.st_mode&0o022)
 if name.startswith(('secret/','env/')) or name=='package/fresh-instance.json':assert stat.S_IMODE(s.st_mode)==0o600
 values[name]=p.read_bytes()
manifest={name:{'sha256':hashlib.sha256(data).hexdigest(),'size':len(data)} for name,data in values.items()}
raw=(json.dumps({'files':manifest,'runtime_data_or_SSH_identities':False})+'\n').encode()
with tarfile.open(fileobj=sys.stdout.buffer,mode='w|',format=tarfile.USTAR_FORMAT) as archive:
 for name,data in [('bundle-manifest.json',raw)]+sorted(values.items()):
  info=tarfile.TarInfo(name);info.size=len(data);info.mode=0o600;info.uid=0;info.gid=0;archive.addfile(info,io.BytesIO(data))
'''.replace('FILE_MAP',repr(contract.FILES))
TARGET=r'''
import hashlib,json,os,socket,stat,sys,tarfile
from pathlib import Path
assert os.geteuid()==0 and socket.gethostname().split('.')[0]=='publish-service' and not Path('/etc/pve').exists()
os.umask(0o077)
assert not Path('/opt/dell/nexus').exists(),'standby must not overwrite existing service'
FILES=FILE_MAP;folder=Path('/root/dell-nexus-merge')/NONCE/'incoming';assert not folder.exists()
folder.mkdir(parents=True,mode=0o700)
for p in [folder.parent.parent,folder.parent,folder]:assert p.resolve()==p and p.stat().st_uid==0 and stat.S_IMODE(p.stat().st_mode)==0o700
manifest=None;seen=set();total=0
with tarfile.open(fileobj=sys.stdin.buffer,mode='r|') as archive:
 for item in archive:
  assert item.isreg() and not item.pax_headers and item.size<=1024*1024
  data=archive.extractfile(item).read(item.size+1);assert len(data)==item.size
  if manifest is None:
   assert item.name=='bundle-manifest.json';manifest=json.loads(data);assert set(manifest['files'])==set(FILES);continue
  assert item.name in FILES and item.name not in seen;seen.add(item.name);total+=len(data);assert total<=8*1024*1024
  expected=manifest['files'][item.name];assert len(data)==expected['size'] and hashlib.sha256(data).hexdigest()==expected['sha256']
  p=folder/item.name.replace('/','__');fd=os.open(p,os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_NOFOLLOW,0o600)
  with os.fdopen(fd,'wb') as f:f.write(data);f.flush();os.fsync(f.fileno())
assert seen==set(FILES)
p=folder/'private-manifest.json';p.write_text(json.dumps(manifest,indent=2)+'\n');p.chmod(0o600)
assert all(p.is_file() and p.stat().st_uid==0 and stat.S_IMODE(p.stat().st_mode)==0o600 for p in folder.iterdir())
print(json.dumps({'role':220,'status':'minimal-Nexus-standby-package-received','nonce':NONCE,'files':len(seen),'secret_and_marker_files_root600':True,'runtime_data_copied':False,'publisher_key_or_SSH_identity_included':False,'Nexus_started_or_service_alias_bound':False,'credential_values_or_private_hashes_emitted':False}))
'''.replace('FILE_MAP',repr(contract.FILES)).replace('NONCE',repr(nonce))

def argv(info,body):
 proxy=shlex.join(control.BASE+['-W','%h:%p','root@192.168.21.22'])
 return control.BASE+['-o','HostKeyAlias='+info['host_key_alias'],'-o','ProxyCommand='+proxy,'ub@'+info['ip'],'sudo /usr/bin/python3 -I -B -c '+shlex.quote(body)]
# Source stdout goes directly to target stdin; secret bytes never become a local file or tool output.
source=subprocess.Popen(argv(targets['221'],SOURCE),stdout=subprocess.PIPE,stderr=subprocess.PIPE)
target=subprocess.Popen(argv(targets['220'],TARGET),stdin=source.stdout,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
source.stdout.close();output,error=target.communicate(timeout=240);source.wait(timeout=40)
if source.returncode or target.returncode:raise SystemExit('Controlled standby stream unconfirmed; raw secret/archive output withheld')
value=json.loads(output);(HERE/'standby-transfer-result.json').write_text(json.dumps(value,indent=2)+'\n');print(json.dumps({'role':220,'status':value['status']}))
