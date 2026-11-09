import sys,json,base64,hashlib
from pathlib import Path
sys.path.insert(0,'scripts');import control
raw=Path('infra/backup/prod-db/backup-alerts.yml').read_bytes();sha=hashlib.sha256(raw).hexdigest()
s=r'''import pathlib,subprocess,json,importlib.util,hashlib,base64,os,time,urllib.parse,datetime
p=pathlib.Path('/root/dell-local-backup-setup/alerts-install.py');spec=importlib.util.spec_from_file_location('a',p);a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a);locked=a.identity()
values={}
for n in ['enabled','state_valid','running','last_run_success','last_success_timestamp_seconds','archive_bytes']:
 v=a.get('/api/v1/query?'+urllib.parse.urlencode({'query':'dell_prod_db_backup_'+n}))['data']['result'];assert len(v)==1;values[n]=float(v[0]['value'][1])
assert values['enabled']==values['state_valid']==values['last_run_success']==1 and values['running']==0 and values['archive_bytes']>0 and 0<=time.time()-values['last_success_timestamp_seconds']<3600
rules=a.get('/api/v1/rules')['data']['groups'];assert not any(g['name']=='dell-pve-local-backup'for g in rules)
target=pathlib.Path('/opt/dell/ops/config/prometheus/rules/prod-db-backup.yml');assert not target.exists()and not target.is_symlink();raw=base64.b64decode(DATA);assert hashlib.sha256(raw).hexdigest()==__DIGEST__
fd=os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o644)
with os.fdopen(fd,'wb')as f:os.fchmod(f.fileno(),0o644);f.write(raw);f.flush();os.fsync(f.fileno())
stage='rules-check'
try:
 a.run(a.D+['exec',locked['ID'],'/bin/promtool','check','rules','/etc/prometheus/rules/prod-db-backup.yml']);stage='config-check';a.run(a.D+['exec',locked['ID'],'/bin/promtool','check','config','/etc/prometheus/prometheus.yml']);assert a.frame(locked['ID'])==locked
 stage='reload-and-health';before=a.get('/api/v1/status/runtimeinfo')['data']['lastConfigTime'];a.run(a.D+['kill','--signal=HUP',locked['ID']]);ok=False
 for _ in range(20):
  r=a.get('/api/v1/status/runtimeinfo')['data'];g=a.get('/api/v1/rules')['data']['groups'];group=[x for x in g if x['name']=='dell-prod-db-backup']
  if r['reloadConfigSuccess']and r['lastConfigTime']!=before and len(group)==1 and {x['name']for x in group[0]['rules']}==a.ALERTS and all(x['health']=='ok'and x['state']=='inactive'for x in group[0]['rules']):ok=True;break
  time.sleep(1)
 assert ok and a.frame(locked['ID'])==locked
except Exception as err:
 print(json.dumps({'status':'new-DB-rule-not-confirmed','stage':stage,'error_type':type(err).__name__,'rule_mode':oct(target.stat().st_mode&0o777)if target.exists()else None}))
 if target.is_file()and not target.is_symlink()and hashlib.sha256(target.read_bytes()).hexdigest()==__DIGEST__:target.unlink();a.run(a.D+['kill','--signal=HUP',locked['ID']])
 raise RuntimeError('new DB-only rule not confirmed; own file rolled back when safe')from None
print(json.dumps({'at':datetime.datetime.now().astimezone().isoformat(),'status':'prod-DB-only-rules-native-validated-SIGHUP-loaded','metrics':values,'old_whole_VM_group_absent':True,'new_group':'dell-prod-db-backup','same_three_approved_alert_names_and_receiver':True,'Prometheus_container_identity_unchanged':True,'rule_SHA':__DIGEST__,'notification_test_sent':False}))'''.replace('DATA',repr(base64.b64encode(raw).decode())).replace('__DIGEST__',repr(sha))
# Avoid replacing the output field label; only a public hash appears there.
compile(s,'prod-db-alert-window','exec')
info=json.loads(Path('completion/20261109/ops-audit.json').read_text())['target'];r=control.guest(270,'sudo -n python3 -I -B -',data=s.encode(),info=info,timeout=90)
if r['exit_code']!=0:
 print(r['stdout']);raise RuntimeError('DB-only rule activation unconfirmed; raw private error withheld')
d=json.loads(r['stdout']);Path('completion/20261109-prod-db-scope/alerts-installed.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d,indent=2))
