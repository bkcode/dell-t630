#!/usr/bin/env python3
"""Explicitly authorized NAS-only VPN network recognition window; no gateway/firewall action."""
import base64,hashlib,importlib.util,json,sys,uuid
from pathlib import Path
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
s=importlib.util.spec_from_file_location('jf_native',ROOT/'network19/services-media/nas-jellyfin-native-verify.py');jf=importlib.util.module_from_spec(s);s.loader.exec_module(jf)
admin,_=jf.credential('jellyfin-admin-password');auth=jf.call('POST','/Users/AuthenticateByName',{'Username':'delladmin','Pw':admin});token=auth['AccessToken']
sys.path.insert(0,str(ROOT/'scripts'));import control
control.BASE+=['-o','ForwardAgent=no'];info=json.loads((ROOT/'network19/evidence/migrated-access.json').read_text())['targets']['260'];assert info['ip']=='192.168.19.60'
nonce=uuid.uuid4().hex
files={name:{'data':base64.b64encode((HERE/name).read_bytes()).decode(),'sha256':hashlib.sha256((HERE/name).read_bytes()).hexdigest()} for name in ['changes.py','transaction.py']}
payload={'nonce':nonce,'files':files,'adminToken':token}
(HERE/'window.json').write_text(json.dumps({'nonce':nonce,'role':260,'target':'192.168.19.60','authorized_scope':'onlyVPN-source-recognition append; no account or privilege change'},indent=2)+'\n')
# Payload is transmitted through SSH STDIN. The token never enters argv/env/public files.
SCRIPT=r'''
import ast,base64,hashlib,json,os,socket,subprocess,sys,tempfile
from pathlib import Path
sys.dont_write_bytecode=True
v=json.load(sys.stdin)
assert os.geteuid()==0 and socket.gethostname().split('.')[0]=='nas-media' and not Path('/etc/pve').exists()
os.umask(0o077);base=Path('/opt/dell/network19/wireguard/media')
for path in [Path('/opt'),Path('/opt/dell'),Path('/opt/dell/network19')]:assert path.resolve()==path and path.stat().st_uid==0 and not(path.stat().st_mode&0o022)
for path in [base.parent,base]:
 path.mkdir(mode=0o700,exist_ok=True);assert path.resolve()==path and path.stat().st_uid==0 and path.stat().st_mode&0o777==0o700
assert set(v['files'])=={'changes.py','transaction.py'}
for name,item in v['files'].items():
 raw=base64.b64decode(item['data']);assert hashlib.sha256(raw).hexdigest()==item['sha256'];ast.parse(raw.decode());target=base/name
 if target.exists():assert target.resolve()==target and target.read_bytes()==raw,'no blind overwrite of existing tool'
for name,item in v['files'].items():
 target=base/name
 if target.exists():continue
 raw=base64.b64decode(item['data']);fd,tmp=tempfile.mkstemp(prefix='.VPN-tools-',dir=base)
 with os.fdopen(fd,'wb') as f:os.fchmod(f.fileno(),0o555);f.write(raw);f.flush();os.fsync(f.fileno())
 os.replace(tmp,target)
receipts=[]
for action in ['stage','commit']:
 raw=b'' if action=='stage' else json.dumps({'adminToken':v['adminToken']}).encode()
 p=subprocess.run(['/usr/bin/python3','-I','-B',str(base/'transaction.py'),action,'--nonce',v['nonce']],input=raw,capture_output=True,timeout=850)
 try:result=json.loads(p.stdout)
 except ValueError:result={'role':260,'status':'VPN-source-recognition-no-public-receipt'}
 receipts.append({'action':action,'exit_code':p.returncode,'result':result})
 if p.returncode:break
out={'role':260,'status':receipts[-1]['result']['status'],'nonce':v['nonce'],'actions':receipts,'secret_values_or_hashes_emitted':False,'gateway_firewall_or_other_role_changed':False}
print(json.dumps(out))
'''
# Use python -c for a public driver so private JSON input remains STDIN, not embedded argv.
import shlex
command='sudo /usr/bin/python3 -I -B -c '+shlex.quote(SCRIPT)
res=control.guest(260,command,data=json.dumps(payload).encode(),timeout=1000,info=info)
if res['exit_code']:raise SystemExit('NAS VPN action unconfirmed; private raw details withheld')
value=json.loads(res['stdout']);(HERE/'apply-result.json').write_text(json.dumps(value,indent=2)+'\n');print(json.dumps({'role':260,'status':value['status']}))
if value['status']!='VPN-source-recognition-committed-verified':raise SystemExit(1)
