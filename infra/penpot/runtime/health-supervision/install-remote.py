#!/usr/bin/env python3
"""Only approved250: install additive runtime files/unit drop-in, validate, do not restart."""
import ast,base64,hashlib,json,os,socket,subprocess,sys
from pathlib import Path
if os.geteuid()!=0 or socket.gethostname().split('.')[0]!='penpot-service' or Path('/etc/pve').exists():raise SystemExit('assigned250 only')
BASE=Path('/opt/dell/penpot');HERE=BASE/'runtime/health-supervision'
values=json.loads(sys.stdin.read());files=values['files'];baseline=values['baseline']
allowed={'supervisor.py','deployment-lock.json','compose.health-supervision.yaml','20-health-supervision.conf','frontend-health.sh','ready-health.sh','node-health.mjs','dns-health.sh','dns-health.hosts','snapshot.py','mcp-readonly.mjs'}
if set(files)!=allowed or baseline.get('worker_idle') is not True or len(baseline['original_files'])!=3:raise SystemExit('installation payload contract rejected')
# Neither source/.git, old deployment files, nor private identity files are written.
for directory in [Path('/opt'),Path('/opt/dell'),BASE,BASE/'runtime']:
 if directory.resolve()!=directory or directory.stat().st_uid!=0 or directory.stat().st_mode&0o022:raise SystemExit('unsafe existing package parent')
HERE.mkdir(mode=0o700,exist_ok=True);HERE.chmod(0o700)
if HERE.resolve()!=HERE:raise SystemExit('supervision directory symlink')
for name,encoded in files.items():
 data=base64.b64decode(encoded);path=HERE/name
 if path.is_symlink():raise SystemExit('supervision file symlink rejected')
 if name.endswith('.py'):ast.parse(data.decode())
 fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_TRUNC|os.O_NOFOLLOW,0o600 if name=='deployment-lock.json' else 0o555 if name.endswith(('.sh','.py','.mjs')) else 0o444)
 with os.fdopen(fd,'wb') as f:f.write(data)
 path.chmod(0o600 if name=='deployment-lock.json' else 0o555 if name.endswith(('.sh','.py','.mjs')) else 0o444)
evidence=HERE/'evidence';evidence.mkdir(mode=0o700,exist_ok=True);p=evidence/'before-install.json';p.write_text(json.dumps(baseline));p.chmod(0o600)
backup=evidence/'original-unit.service';backup.write_text(baseline['unit_content']);backup.chmod(0o600)
# Unit change is additive and not reloaded until syntax and all read-only gates pass.
dropdir=Path('/etc/systemd/system/dell-penpot.service.d');dropdir.mkdir(mode=0o755,exist_ok=True)
if dropdir.resolve()!=dropdir:raise SystemExit('unit dropin symlink rejected')
drop=dropdir/'20-health-supervision.conf'
if drop.is_symlink():raise SystemExit('unit dropin file symlink rejected')
drop.write_bytes((HERE/'20-health-supervision.conf').read_bytes());drop.chmod(0o644)
checks=[]
for args in [['bash','-n',str(HERE/'frontend-health.sh'),str(HERE/'ready-health.sh'),str(HERE/'dns-health.sh')],['systemd-analyze','verify','/etc/systemd/system/dell-penpot.service'],['python3','-I','-B',str(HERE/'supervisor.py'),'check']]:
 env=None
 if args[0]=='systemd-analyze':
  paths=subprocess.run(['systemctl','show','--property=UnitPath','--value'],capture_output=True,text=True,timeout=15,check=True).stdout.split()
  env={'PATH':'/usr/sbin:/usr/bin:/sbin:/bin','LANG':'C.UTF-8','SYSTEMD_UNIT_PATH':':'.join(paths)}
 p=subprocess.run(args,capture_output=True,text=True,timeout=180,env=env)
 checks.append({'tool':args[0],'exit_code':p.returncode})
 if p.returncode:
  print(json.dumps({'status':'installed-validation-failed-not-activated','checks':checks,'services_stopped_or_recreated':False,'raw_details_emitted':False}));sys.exit(1)
print(json.dumps({'status':'installed-validated-not-activated','checks':checks,'old_unit_SHA_unchanged':hashlib.sha256(Path('/etc/systemd/system/dell-penpot.service').read_bytes()).hexdigest()==baseline['unit_sha256'],'services_stopped_or_recreated':False,'new_files_only':True}))
