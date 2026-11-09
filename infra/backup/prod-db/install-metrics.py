import sys,json,base64,hashlib
from pathlib import Path
sys.path.insert(0,'scripts');import control
src=Path('infra/ops/pve-push-metrics.py').read_bytes();expected='11febe546d8fb98ba2e623c33e7af7aa03332edcfe719232a812cfb736e95d88';digest=hashlib.sha256(src).hexdigest()
s=r'''import pathlib,hashlib,os,base64,json,subprocess,stat,datetime
p=pathlib.Path('/root/dell-bootstrap/pve-push-metrics.py');raw=p.read_bytes();assert hashlib.sha256(raw).hexdigest()==OLD
b=pathlib.Path('/root/dell-prod-db-backup-transition');b.mkdir(mode=0o700,exist_ok=True);assert b.resolve()==b and stat.S_IMODE(b.stat().st_mode)==0o700
old=b/'pve-push-metrics.before-prod.py';assert not old.exists();old.write_bytes(raw);old.chmod(0o600)
new=base64.b64decode(DATA);assert hashlib.sha256(new).hexdigest()==NEW;compile(new,str(p),'exec');tmp=b/'pve-push-metrics.new.py';tmp.write_bytes(new);tmp.chmod(stat.S_IMODE(p.stat().st_mode));os.replace(tmp,p)
subprocess.run(['systemctl','start','dell-pve-metrics.service'],check=True,timeout=70)
state=dict(l.split('=',1)for l in subprocess.check_output(['systemctl','show','dell-pve-metrics.service','--property=Result,ExecMainStatus'],text=True).splitlines()if '='in l);assert state['Result']=='success'and state['ExecMainStatus']=='0'
print(json.dumps({'at':datetime.datetime.now().astimezone().isoformat(),'status':'prod-DB-metadata-added-to-existing-collector','collector_SHA':NEW,'native_unit':state,'new_listener_or_key_or_notification':False}))'''.replace('OLD',repr(expected)).replace('DATA',repr(base64.b64encode(src).decode())).replace('NEW',repr(digest))
d=json.loads(control.pve('python3 -I -B -',data=s.encode(),timeout=100));Path('completion/20261109-prod-db-scope/metrics-installed.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d,indent=2))
