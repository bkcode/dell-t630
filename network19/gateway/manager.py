#!/usr/bin/env python3
"""Parent-reviewed190 transport only. Independent strict SSH for every request."""
import argparse,datetime,hashlib,importlib.util,io,json,shlex,subprocess,sys,tarfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('gw_control',ROOT/'scripts/control.py');ctl=importlib.util.module_from_spec(spec);spec.loader.exec_module(ctl)
COPY=r'''import io,json,os,socket,sys,tarfile
from pathlib import Path
if os.geteuid()!=0 or Path('/etc/pve').exists() or socket.gethostname().split('.')[0]!='network-gateway':raise SystemExit('190 only')
folder=Path('/usr/local/libexec/dell-gateway19')
if folder.resolve(strict=False)!=folder:raise SystemExit('symlink path refused')
folder.mkdir(parents=True,mode=0o755,exist_ok=True);folder.chmod(0o755)
bundle=Path('/var/lib/dell-gateway19/staged-bundle');bundle.mkdir(parents=True,mode=0o700,exist_ok=True);bundle.chmod(0o700)
raw=sys.stdin.buffer.read(262145)
if len(raw)>262144:raise SystemExit('public bundle size cap')
expected={'manage.py','policy.py','config.json'};seen=set()
with tarfile.open(fileobj=io.BytesIO(raw),mode='r:') as t:
 for member in t:
  if member.name not in expected or member.name in seen or not member.isfile() or member.size>65536:raise SystemExit('trusted member rejected')
  seen.add(member.name);dest=(bundle if member.name=='config.json' else folder)/member.name
  if dest.is_symlink():raise SystemExit('symlink refused')
  data=t.extractfile(member).read();compile(data,str(dest),'exec') if member.name.endswith('.py') else json.loads(data)
  fd=os.open(dest,os.O_WRONLY|os.O_CREAT|os.O_TRUNC|os.O_NOFOLLOW,0o600)
  with os.fdopen(fd,'wb') as f:f.write(data)
  os.chown(dest,0,0);dest.chmod(0o600 if member.name=='config.json' else 0o644)
 if seen!=expected:raise SystemExit('incomplete trusted bundle')
print(json.dumps({'copied_public_policy_code':True,'private_keys_copied':False}))'''
def ssh(target,command,data=None,timeout=180):
 opts=['-o','ControlMaster=no','-o','ControlPath=none','-o','ForwardAgent=no','-o','IdentityAgent=none','-o','PermitLocalCommand=no']
 proxy=shlex.join(ctl.BASE+opts+['-W','%h:%p','root@192.168.21.22'])
 args=ctl.BASE+opts+['-o','HostKeyAlias='+target['host_key_alias'],'-o','ProxyCommand='+proxy,'ub@'+target['ip'],command]
 r=subprocess.run(args,input=data,capture_output=True,timeout=timeout);return {'exit_code':r.returncode,'stdout':r.stdout.decode(),'stderr':r.stderr.decode()}
def package():
 output=io.BytesIO()
 with tarfile.open(fileobj=output,mode='w',format=tarfile.USTAR_FORMAT) as archive:
  for name,file in [('manage.py',HERE/'manage.py'),('policy.py',HERE/'policy.py'),('config.json',HERE/'bundle/config.json')]:
   data=file.read_bytes();entry=tarfile.TarInfo(name);entry.size=len(data);entry.mode=0o600;archive.addfile(entry,io.BytesIO(data))
 return output.getvalue()
def main():
 p=argparse.ArgumentParser();p.add_argument('action',choices=['stage','hot-stage','check','confirm','rollback']);p.add_argument('--reviewed-190-apply-window',action='store_true');p.add_argument('--nonce');args=p.parse_args()
 if args.action in ('stage','hot-stage') and not args.reviewed_190_apply_window:raise RuntimeError('parent exact apply window required')
 target=json.loads((HERE.parent/'evidence/gateway-initial-access.json').read_text())['target']
 if target['vmid']!=190 or target['ip']!='192.168.21.23':raise RuntimeError('root dual-IP trusted190 record required')
 report={'at':datetime.datetime.now().astimezone().isoformat(),'action':args.action,'target':target,'independent_strict_SSH':True,'client_key_copied':False,'code_sha256':{x:hashlib.sha256((HERE/x).read_bytes()).hexdigest() for x in ['manage.py','policy.py']}}
 if args.action in ('stage','hot-stage'):
  copy=ssh(target,'sudo -n python3 -c '+shlex.quote(COPY),package())
  if copy['exit_code']:raise RuntimeError('trusted public code copy failed; raw output withheld')
  command='sudo -n /usr/bin/python3 /usr/local/libexec/dell-gateway19/manage.py '+args.action+' --bundle /var/lib/dell-gateway19/staged-bundle --reviewed-190-apply-window'
 else:
  command='sudo -n /usr/bin/python3 /usr/local/libexec/dell-gateway19/manage.py '+args.action
  if args.action=='confirm':
   import re
   if not re.fullmatch('[a-f0-9]{32}',args.nonce or ''):raise RuntimeError('bounded activation nonce required')
   # This is a new SSH session, not an acknowledgement over the apply connection.
   reconnect=ssh(target,'id -un; hostname')
   if reconnect['exit_code'] or reconnect['stdout'].splitlines()[:2]!=['ub','network-gateway']:raise RuntimeError('fresh strict management SSH failed; leave watchdog armed')
   report['fresh_ub_SSH_verified']=True;command+=' --nonce '+args.nonce
 result=ssh(target,command,timeout=180);report['exit_code']=result['exit_code']
 try:report['result']=json.loads(result['stdout'])
 except ValueError:report['result']={'status':'failed-unstructured-output-withheld'}
 (HERE/('live-'+args.action+'.json')).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report));return result['exit_code']
if __name__=='__main__':
 try:sys.exit(main())
 except Exception:print(json.dumps({'status':'failed','message':'gateway management failed; leave watchdog/QGA recovery intact'}));sys.exit(1)
