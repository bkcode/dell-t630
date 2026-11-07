#!/usr/bin/env python3
"""Active190 nft syntax/delta check only; no service or forwarding changes."""
import base64,datetime,hashlib,importlib.util,json,shlex
from pathlib import Path
HERE=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('transport',HERE/'manager.py');transport=importlib.util.module_from_spec(s);s.loader.exec_module(transport)
CODE=r'''import base64,importlib.util,json,os,socket,sys
from pathlib import Path
if os.geteuid()!=0 or Path('/etc/pve').exists() or socket.gethostname().split('.')[0]!='network-gateway':raise SystemExit('190 only')
folder=Path('/tmp/dell-gateway19-hotcheck')
if folder.resolve(strict=False)!=folder:raise SystemExit('symlink refused')
folder.mkdir(mode=0o700,exist_ok=True);raw=sys.stdin.buffer.read(262145)
if len(raw)>262144:raise SystemExit('cap')
x=json.loads(raw)
for name,value in x.items():
 if name not in ['policy.py','manage.py','config.json']:raise SystemExit('fixed fields')
 file=folder/name
 if file.is_symlink():raise SystemExit('symlink refused')
 file.write_bytes(base64.b64decode(value,validate=True));file.chmod(0o600)
def load(name,file):
 s=importlib.util.spec_from_file_location(name,file);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
p=load('new_policy',folder/'policy.py');m=load('new_manage',folder/'manage.py');m.load_policy=lambda:p
new=json.loads((folder/'config.json').read_text());old=json.loads(Path('/etc/dell-gateway19/config.json').read_text());m.guard_identity();interfaces=m.guard(old,True);m.validate_hot_delta(old,new);before=m.service_fingerprints();forward_before=m.forwarding_values(interfaces);m.native_checks(new,interfaces,folder/'syntax');after=m.service_fingerprints();forward_after=m.forwarding_values(interfaces)
print(json.dumps({'status':'hot-delta-and-native-nft-check-passed','nft_check_exit_code':0,'only_change':[key for key in ['OW_fake_IP_proxy','CF_fake_IP_proxy','WireGuard_client_access'] if new.get(key)!=old.get(key)],'persistent_services_unchanged':before==after,'forward_before':forward_before,'forward_after':forward_after,'rule_load_performed':False,'addresses_or_sysctls_changed':False}))'''
def main():
 target=json.loads((HERE.parent/'evidence/gateway-initial-access.json').read_text())['target'];data=json.dumps({name:base64.b64encode((HERE/name if name.endswith('.py') else HERE/'bundle'/name).read_bytes()).decode() for name in ['policy.py','manage.py','config.json']}).encode();result=transport.ssh(target,'sudo -n python3 -c '+shlex.quote(CODE),data,timeout=120)
 if result['exit_code']:raise RuntimeError('hot syntax/delta failed; raw withheld')
 record={'at':datetime.datetime.now().astimezone().isoformat(),'code_sha256':{name:hashlib.sha256((HERE/name).read_bytes()).hexdigest() for name in ['policy.py','manage.py']},'result':json.loads(result['stdout'])};(HERE/'hot-native-check.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record))
if __name__=='__main__':main()
