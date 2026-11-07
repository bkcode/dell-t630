#!/usr/bin/env python3
"""Only220: create dedicated identity/key; private bytes are never read or exported."""
import datetime,importlib.util,json,shlex,sys
from pathlib import Path
from zoneinfo import ZoneInfo
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[2]
s=importlib.util.spec_from_file_location('publisher_control',ROOT/'scripts/control.py');ctl=importlib.util.module_from_spec(s);s.loader.exec_module(ctl)
REMOTE=r'''import json,os,socket,subprocess,pwd,grp,stat
from pathlib import Path
if os.geteuid()!=0 or Path('/etc/pve').exists() or socket.gethostname().split('.')[0]!='publish-service':raise SystemExit('only publisher VM220 allowed')
def run(args):
 p=subprocess.run(args,capture_output=True,text=True,timeout=30)
 if p.returncode:raise SystemExit('publisher identity operation failed; output suppressed')
 return p.stdout.strip()
addresses=json.loads(run(['ip','-j','addr']))
if not any(a.get('local')=='10.63.30.10' for n in addresses for a in n.get('addr_info',[])):raise SystemExit('wrong publisher private address')
if run(['systemd-detect-virt','--vm']) not in ('kvm','qemu'):raise SystemExit('KVM publisher guest required')
created=False
try:user=pwd.getpwnam('publisher')
except KeyError:
 run(['useradd','--system','--user-group','--create-home','--home-dir','/var/lib/dell-publisher','--shell','/bin/sh','publisher']);user=pwd.getpwnam('publisher');created=True
if user.pw_uid==0 or user.pw_dir!='/var/lib/dell-publisher' or user.pw_shell!='/bin/sh':raise SystemExit('existing publisher identity differs')
groups=run(['id','-nG','publisher']).split()
if set(groups)!={'publisher'}:raise SystemExit('publisher has unexpected groups')
home=Path(user.pw_dir);ssh=home/'.ssh';key=ssh/'test240_ed25519';public=ssh/'test240_ed25519.pub'
for directory in [home,ssh]:
 if directory.resolve(strict=False)!=directory:raise SystemExit('publisher identity path symlink')
 directory.mkdir(mode=0o700,exist_ok=True);os.chown(directory,user.pw_uid,user.pw_gid);directory.chmod(0o700)
if key.is_symlink() or public.is_symlink():raise SystemExit('publisher key symlink rejected')
if key.exists()!=public.exists():raise SystemExit('partial publisher keypair exists; inspect before continuing')
key_created=False
if not key.exists():
 run(['runuser','--user','publisher','--','ssh-keygen','-q','-t','ed25519','-N','','-C','dell-test240-publisher-v1','-f',str(key)]);key_created=True
for file in [key,public]:
 st=file.lstat()
 if not stat.S_ISREG(st.st_mode) or st.st_uid!=user.pw_uid:raise SystemExit('publisher key owner/type invalid')
 file.chmod(0o600)
# Only public file is read. The private file is stat'ed, never opened or copied.
pub=public.read_text().strip().split()
if len(pub)<2 or pub[0]!='ssh-ed25519':raise SystemExit('unexpected public key type')
fingerprint=run(['ssh-keygen','-lf',str(public)])
print(json.dumps({'vmid':220,'role':'publish-service','private_ip':'10.63.30.10','user':'publisher','uid':user.pw_uid,'groups':groups,'identity_created':created,'key_created':key_created,'private_key_path':str(key),'private_key_mode':'0600','private_key_read_or_exported':False,'public_key':' '.join(pub),'public_fingerprint':fingerprint,'target240_modified':False,'services_started':False}))'''

def main():
 if sys.argv[1:]!=['--execute-authorized220-only']:raise SystemExit('explicit220-only flag required')
 rows=json.loads((ROOT/'evidence/implementation/private-guest-access.json').read_text())['roles'];row=next(x for x in rows if x['target']['vmid']==220)
 if row['name']!='publish-service' or row['status']!='ssh-verified' or row['target']['ip']!='10.63.30.10':raise RuntimeError('publisher SSH proof mismatch')
 result=ctl.guest(220,'sudo -n python3 -',data=REMOTE.encode(),timeout=120,info=row['target'])
 if result['exit_code']:raise RuntimeError('220 identity operation failed: '+result['stderr'][-500:])
 value=json.loads(result['stdout']);public_key=value.pop('public_key');private=ROOT/'private/publisher';private.mkdir(mode=0o700,exist_ok=True);private.chmod(0o700)
 p=private/'publisher220-test240.pub';p.write_text(public_key+'\n');p.chmod(0o600)
 (ROOT/'evidence/implementation/publisher220-identity.json').write_text(json.dumps({'at':datetime.datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),'result':value},indent=2)+'\n')
 print(json.dumps(value))
if __name__=='__main__':main()
