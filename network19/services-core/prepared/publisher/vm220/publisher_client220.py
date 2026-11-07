#!/usr/bin/python3 -I
"""Dedicated publisher220 client. Key stays220; immutable archive stdin only."""
import argparse,hashlib,importlib.util,json,os,pwd,socket,stat,subprocess,sys,tempfile
from pathlib import Path
PROFILE=Path('/etc/dell-publisher/client-test240.json')
KEY=Path('/var/lib/dell-publisher/.ssh/test240_ed25519')
KNOWN=Path('/etc/dell-publisher/known_hosts')

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['status','stage','activate','rollback']);p.add_argument('--release-id');p.add_argument('--bundle',type=Path);args=p.parse_args()
 if socket.gethostname().split('.')[0]!='publish-service' or Path('/etc/pve').exists() or os.geteuid()!=pwd.getpwnam('publisher').pw_uid:raise RuntimeError('dedicated publisher220 account required')
 private=KEY.lstat()
 if not stat.S_ISREG(private.st_mode) or private.st_uid!=os.geteuid() or private.st_mode&0o777!=0o600:raise RuntimeError('publisher private key permissions invalid')
 for path in [PROFILE,KNOWN]:
  if path.is_symlink() or path.stat().st_uid!=0 or path.stat().st_mode&0o022:raise RuntimeError('root-trusted client profile/host key required')
 profile=json.loads(PROFILE.read_text())
 if profile!={'target_host':'192.168.19.45','target_user':'deployer','host_key_alias':'dell-test240-publisher','source_ip':'192.168.19.30'}:raise RuntimeError('client target profile differs')
 interfaces=json.loads(subprocess.run(['ip','-j','addr'],capture_output=True,text=True,check=True).stdout)
 if not any(a.get('local')=='192.168.19.30' for n in interfaces for a in n.get('addr_info',[])):raise RuntimeError('publisher private source IP missing')
 import re,datetime
 if args.action!='status':
  if not args.release_id or not re.fullmatch('[0-9]{8}T[0-9]{6}',args.release_id):raise RuntimeError('release id required')
  datetime.datetime.strptime(args.release_id,'%Y%m%dT%H%M%S')
 command='dell-publish-v1 '+args.action
 data=None
 if args.action=='stage':
  if not args.bundle or not args.bundle.is_dir() or args.bundle.is_symlink():raise RuntimeError('immutable release directory required')
  code=Path('/usr/local/libexec/dell-publisher/publisher_protocol.py')
  if code.is_symlink() or code.stat().st_uid!=0 or code.stat().st_mode&0o022:raise RuntimeError('trusted canonical packager required')
  spec=importlib.util.spec_from_file_location('client_protocol',code);protocol=importlib.util.module_from_spec(spec);spec.loader.exec_module(protocol)
  outgoing=Path('/var/lib/dell-publisher/outgoing')
  if outgoing.resolve(strict=False)!=outgoing:raise RuntimeError('outgoing path symlink rejected')
  outgoing.mkdir(mode=0o700,exist_ok=True)
  folder=Path(tempfile.mkdtemp(prefix=args.release_id+'-',dir=outgoing))
  archive=protocol.build_canonical_archive(args.bundle.resolve(),folder/'bundle.tar',args.release_id)
  size=archive.stat().st_size
  with archive.open('rb') as file:digest=hashlib.file_digest(file,'sha256').hexdigest()
  command+=' '+args.release_id+' '+digest+' '+str(size);data=archive.open('rb')
 elif args.action!='status':command+=' '+args.release_id
 elif args.bundle or args.release_id:raise RuntimeError('status accepts no release/archive')
 ssh=['/usr/bin/ssh','-F','/dev/null','-i',str(KEY),'-o','IdentitiesOnly=yes','-o','IdentityAgent=none','-o','ForwardAgent=no','-o','RequestTTY=no','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','UserKnownHostsFile='+str(KNOWN),'-o','HostKeyAlias='+profile['host_key_alias'],'-o','ClearAllForwardings=yes','-o','PermitLocalCommand=no','-o','ControlMaster=no','-o','ControlPath=none','-o','ConnectTimeout=8','-o','ServerAliveInterval=15','-o','ServerAliveCountMax=3','deployer@192.168.19.45',command]
 try:result=subprocess.run(ssh,stdin=data if data else subprocess.DEVNULL,capture_output=True,timeout=1600)
 finally:
  if data:data.close()
 # A single structured server frame; do not append a second error that masks its category.
 try:response=json.loads(result.stdout)
 except (ValueError,UnicodeError):response=None
 if isinstance(response,dict) and type(response.get('ok')) is bool:
  print(json.dumps(response));return result.returncode
 print(json.dumps({'ok':False,'message':'restricted publisher SSH/RPC failed; unstructured output withheld'}));return result.returncode or 1

if __name__=='__main__':
 try:sys.exit(main())
 except Exception:print(json.dumps({'ok':False,'message':'publisher client rejected local input or target access'}));sys.exit(1)
