#!/usr/bin/python3 -I
"""Prepared manager-only240 transport install. Does NOT alter A units/owner or restart apps."""
import argparse,base64,hashlib,json,os,pwd,shutil,socket,struct,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
FILES={'publisher_root.py':Path('/usr/local/libexec/dell-publish-test240'),'publisher_dispatch.py':Path('/usr/local/libexec/dell-publisher-dispatch'),'publisher_protocol.py':Path('/usr/local/libexec/dell-publisher/publisher_protocol.py'),'fixed-deploy-test-chain.py':Path('/usr/local/libexec/dell/deploy-test-chain.py'),'adopt-baseline240.py':Path('/usr/local/libexec/dell-publisher/adopt-baseline240.py')}
SSH='''Match User deployer
    AuthorizedKeysFile /etc/ssh/authorized_keys/deployer
    AuthenticationMethods publickey
    PubkeyAuthentication yes
    PasswordAuthentication no
    KbdInteractiveAuthentication no
    ForceCommand /usr/local/libexec/dell-publisher-dispatch
    DisableForwarding yes
    AllowAgentForwarding no
    AllowTcpForwarding no
    X11Forwarding no
    PermitTTY no
    PermitUserRC no
Match all
'''
SUDO='''Defaults:deployer env_reset
# Empty argument string means this one fixed command accepts NO argv.
deployer ALL=(root) NOPASSWD: /usr/local/libexec/dell-publish-test240 ""
'''

def run(args):
 p=subprocess.run(args,capture_output=True,text=True,timeout=30)
 if p.returncode:raise RuntimeError('manager transport prerequisite/validation failed; output suppressed')
 return p.stdout.strip()

def public_key(value):
 parts=value.strip().split()
 if len(parts) not in (2,3) or parts[0]!='ssh-ed25519':raise ValueError('Ed25519 public input required')
 blob=base64.b64decode(parts[1],validate=True)
 if len(blob)!=51 or blob[:4]!=struct.pack('!I',11) or blob[4:15]!=b'ssh-ed25519' or blob[15:19]!=struct.pack('!I',32):raise ValueError('invalid Ed25519 public blob')
 return parts[0]+' '+parts[1], 'SHA256:'+base64.b64encode(hashlib.sha256(blob).digest()).decode().rstrip('=')

def put(path,body,mode):
 if path.resolve(strict=False)!=path or path.is_symlink():raise RuntimeError('trusted installation path symlink rejected')
 path.parent.mkdir(parents=True,exist_ok=True,mode=0o755)
 temporary=path.with_name(path.name+'.dell-pending')
 if temporary.is_symlink():raise RuntimeError('pending trusted path symlink rejected')
 temporary.write_bytes(body);os.chown(temporary,0,0);temporary.chmod(mode);os.replace(temporary,path)

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--apply-reviewed240-transport-window',action='store_true');args=p.parse_args()
 if not args.apply_reviewed240_transport_window or os.geteuid()!=0 or socket.gethostname().split('.')[0]!='java-test-01' or Path('/etc/pve').exists():raise RuntimeError('approved manager transport window on240 required')
 if not any(x.get('local')=='10.63.20.20' for n in json.loads(run(['ip','-j','addr'])) for x in n.get('addr_info',[])):raise RuntimeError('wrong240 private address')
 raw=sys.stdin.buffer.read(4097)
 if len(raw)>4096:raise ValueError('public input too large')
 key,fingerprint=public_key(json.loads(raw)['publisher220_public_key'])
 try:user=pwd.getpwnam('deployer')
 except KeyError:
  run(['useradd','--system','--user-group','--create-home','--home-dir','/var/lib/dell-deployer','--shell','/bin/sh','deployer']);user=pwd.getpwnam('deployer')
 if user.pw_uid==0 or user.pw_dir!='/var/lib/dell-deployer' or user.pw_shell!='/bin/sh' or set(run(['id','-nG','deployer']).split())!={'deployer'}:raise RuntimeError('existing deployer identity is not isolated')
 home=Path(user.pw_dir)
 if home.resolve()!=home:raise RuntimeError('deployer home symlink rejected')
 os.chown(home,0,0);home.chmod(0o755)
 for source,target in FILES.items():put(target,(HERE/source).read_bytes(),0o755 if target.name!='publisher_protocol.py' else 0o644)
 authorized=Path('/etc/ssh/authorized_keys/deployer');sudo=Path('/etc/sudoers.d/dell-publisher-test240');fragment=Path('/etc/ssh/sshd_config.d/60-dell-publisher-deployer.conf')
 for path in (authorized,sudo,fragment):
  if path.is_symlink() or path.parent.resolve(strict=False)!=path.parent:raise RuntimeError('existing transport config symlink rejected')
 original={path:path.read_bytes() if path.exists() else None for path in (authorized,sudo,fragment)}
 try:
  put(authorized,('from="10.63.30.10",restrict,command="/usr/local/libexec/dell-publisher-dispatch" '+key+'\n').encode(),0o644)
  put(sudo,SUDO.encode(),0o440);put(fragment,SSH.encode(),0o644)
  run(['visudo','-cf',str(sudo)]);run(['sshd','-t'])
 except BaseException:
  for path,old in original.items():
   if old is None:path.unlink(missing_ok=True)
   else:put(path,old,0o644 if path==authorized else 0o440 if path==sudo else 0o644)
  raise
 policy=Path('/etc/dell-publisher/test240-policy.json')
 if not policy.exists():put(policy,json.dumps({'target_hostname':'java-test-01','target_ip':'10.63.20.20','baseline_migrated':False,'namespace_id':None,'fixed_deployer_sha256':hashlib.sha256((HERE/'fixed-deploy-test-chain.py').read_bytes()).hexdigest()}).encode(),0o600)
 run(['systemctl','reload','ssh.service'])
 print(json.dumps({'status':'transport-installed-apps-unmodified','target':'test240','publisher_key_fingerprint':fingerprint,'private_key_imported':False,'baseline_or_app_units_changed':False,'applications_restarted':False,'baseline_migration_required':True}))

if __name__=='__main__':
 try:main()
 except Exception:print(json.dumps({'status':'failed','message':'manager transport install failed; public key and sensitive details suppressed'}));sys.exit(1)
