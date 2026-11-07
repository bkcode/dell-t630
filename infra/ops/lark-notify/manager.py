#!/usr/bin/env python3
"""Explicit parent-approved ops270 windows only; secret bytes use SSH stdin."""
import argparse,base64,datetime,hashlib,importlib.util,io,json,os,shlex,sys,tarfile
from pathlib import Path
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
spec=importlib.util.spec_from_file_location('control',ROOT/'scripts/control.py');control=importlib.util.module_from_spec(spec);spec.loader.exec_module(control)
FILES=['bridge.py','configuration.py','install270.py','acceptance270.py','rebuild270-network.py','dell-lark-notify.service']
COPY=r'''import io,json,os,socket,sys,tarfile
from pathlib import Path
if os.geteuid()!=0 or Path('/etc/pve').exists() or socket.gethostname().split('.')[0]!='ops-service':raise SystemExit('ops270 only')
folder=Path('/tmp/dell-lark-notify')
if folder.resolve(strict=False)!=folder or folder.is_symlink():raise SystemExit('symlink refused')
folder.mkdir(mode=0o700,exist_ok=True);folder.chmod(0o700)
raw=sys.stdin.buffer.read(262145)
if len(raw)>262144:raise SystemExit('fixed tools cap')
expected=set(FILES);seen=set()
with tarfile.open(fileobj=io.BytesIO(raw),mode='r:') as t:
 for member in t:
  if member.name not in expected or member.name in seen or not member.isfile() or member.size>65536:raise SystemExit('fixed tools member refused')
  seen.add(member.name);file=folder/member.name
  if file.is_symlink():raise SystemExit('symlink refused')
  fd=os.open(file,os.O_WRONLY|os.O_CREAT|os.O_TRUNC|os.O_NOFOLLOW,0o600)
  with os.fdopen(fd,'wb') as f:f.write(t.extractfile(member).read())
 if seen!=expected:raise SystemExit('fixed tool set missing')
print(json.dumps({'tools_copied':len(seen),'secret_material_in_tool_archive':False}))'''
def tools():
 out=io.BytesIO()
 with tarfile.open(fileobj=out,mode='w',format=tarfile.USTAR_FORMAT) as archive:
  for name in FILES:
   data=(HERE/name).read_bytes();info=tarfile.TarInfo(name);info.mode=0o600;info.size=len(data);archive.addfile(info,io.BytesIO(data))
 return out.getvalue()

def main():
 p=argparse.ArgumentParser();p.add_argument('action',choices=['rebuild-ops-network','install-acceptance-only','send-acceptance-pair','enable-live-after-maintenance']);p.add_argument('--parent-reviewed-270-window',action='store_true');p.add_argument('--maintenance-complete',action='store_true');args=p.parse_args()
 if not args.parent_reviewed_270_window:raise RuntimeError('parent code review and explicit 270 window required')
 if args.action=='enable-live-after-maintenance' and not args.maintenance_complete:raise RuntimeError('maintenance complete gate required')
 targets=json.loads((ROOT/'evidence/implementation/private-guest-access.json').read_text())['roles'];target=next(r['target'] for r in targets if r['target']['vmid']==270)
 if target['ip']!='10.63.30.40':raise RuntimeError('fixed ops270 target required')
 report={'at':datetime.datetime.now().astimezone().isoformat(),'action':args.action,'target':'ops270','status':'running','secret_values_emitted':False,'private_webhook_on_argv_or_env':False,'code_sha256':{name:hashlib.sha256((HERE/name).read_bytes()).hexdigest() for name in FILES}}
 if args.action in ('rebuild-ops-network','install-acceptance-only'):
  code=COPY.replace('expected=set(FILES)','expected=set('+repr(FILES)+')');result=control.guest(270,'sudo -n python3 -c '+shlex.quote(code),data=tools(),timeout=120,info=target)
  if result['exit_code']:raise RuntimeError('fixed public tool transfer failed; raw output withheld')
  report['copy']=json.loads(result['stdout'])
 if args.action=='rebuild-ops-network':
  token=ROOT/'private/ops/lark-bridge-token'
  if token.is_symlink() or token.stat().st_mode&0o777!=0o600:raise RuntimeError('stable private token source600 required')
  raw=json.dumps({'compose_b64':base64.b64encode((HERE.parent/'compose.yaml').read_bytes()).decode(),'manager_b64':base64.b64encode((HERE.parent/'scripts/manage.py').read_bytes()).decode(),'token_b64':base64.b64encode(token.read_bytes()).decode()}).encode()
  command='sudo -n /usr/bin/python3 -I /tmp/dell-lark-notify/rebuild270-network.py --reviewed-ops270-network-window'
 elif args.action=='install-acceptance-only':
  file=ROOT/'private/notifications/lark-webhook'
  if file.is_symlink() or file.stat().st_mode&0o777!=0o600 or file.stat().st_size>1024:raise RuntimeError('private webhook source must be bounded regular600')
  raw=json.dumps({'webhook_b64':base64.b64encode(file.read_bytes()).decode()}).encode()
  command='sudo -n /usr/bin/python3 -I /tmp/dell-lark-notify/install270.py install-acceptance-only --reviewed-ops270-window'
 elif args.action=='send-acceptance-pair':
  raw=None;command='sudo -n /usr/bin/python3 -I /tmp/dell-lark-notify/acceptance270.py --send-reviewed-acceptance-pair'
 else:
  raw=None;command='sudo -n /usr/bin/python3 -I /tmp/dell-lark-notify/install270.py enable-live-after-maintenance --reviewed-ops270-window --maintenance-complete'
 result=control.guest(270,command,data=raw,timeout=1500 if args.action=='rebuild-ops-network' else 240,info=target);report['exit_code']=result['exit_code']
 try:report['result']=json.loads(result['stdout'])
 except ValueError:report['result']={'status':'failed','message':'unstructured output withheld'}
 report['status']='passed' if result['exit_code']==0 else 'failed';path=ROOT/'evidence/implementation'/('lark-notify-'+args.action+'.json');path.write_text(json.dumps(report,indent=2)+'\n')
 if report['status']=='passed' and args.action in ('install-acceptance-only','enable-live-after-maintenance'):
  # Preserve local-template notification ownership so generic prepare cannot reset it.
  folder=ROOT/'private/ops/bundle';state={'mode':'acceptance' if args.action=='install-acceptance-only' else 'active','owner':'native-lark-notify','generic_prepare':'refuse-reset'}
  file=folder/'lark-notify-state.json';file.write_text(json.dumps(state,indent=2)+'\n');file.chmod(0o600)
  sys.path.insert(0,str(HERE));import configuration
  file=folder/'config/alertmanager/alertmanager.yml';file.write_text(configuration.dump(state['mode']));file.chmod(0o644)
 print(json.dumps(report));return result['exit_code']
if __name__=='__main__':
 try:sys.exit(main())
 except Exception:print(json.dumps({'status':'failed','message':'fixed notification manager failed; raw output/secrets withheld'}));sys.exit(1)
