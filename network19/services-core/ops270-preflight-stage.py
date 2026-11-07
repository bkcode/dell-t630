"""270 only public active config census + no-send native checks, stage public targets only."""
import datetime,json,sys,shlex,base64
from pathlib import Path
sys.dont_write_bytecode=True
H=Path(__file__).resolve().parent;R=H.parents[1];sys.path.insert(0,str(R/'scripts'));import control
P=r'''import json,hashlib,re,subprocess,os,sys,base64
from pathlib import Path
v=json.loads(sys.stdin.read());root=Path('/root/dell-network19/staged/services-core-v1');out={'status':'ops-public-stage-and-native-nosend-checks','active_configs':{},'native_checks':[],'network_secrets_or_mode_changed':False,'outbound_probe_or_message_sent':False}
paths=['/opt/dell/ops/.env','/opt/dell/ops/compose.yaml','/opt/dell/ops/scripts/manage.py','/opt/dell/ops/config/prometheus/prometheus.yml','/opt/dell/ops/config/prometheus/rules/infra.yml','/opt/dell/ops/config/prometheus/targets/guest-node.json','/opt/dell/ops/config/prometheus/targets/http-services.json','/opt/dell/ops/config/alertmanager/alertmanager.yml','/opt/dell/ops/lark-notify-state.json','/etc/dell-lark-notify/policy.json','/usr/local/libexec/dell-lark-notify/bridge.py','/etc/systemd/system/dell-lark-notify.service']
for path in paths:
 p=Path(path)
 if not p.is_file():out['active_configs'][path]={'exists':False};continue
 data=p.read_bytes();out['active_configs'][path]={'sha256':hashlib.sha256(data).hexdigest(),'old_private_IP_literal_present':b'10.63.30.40' in data,'IPv4_values':sorted(set(re.findall(r'(?<![0-9])(?:[0-9]{1,3}\.){3}[0-9]{1,3}(?![0-9])',data.decode(errors='replace'))))}
# Stage public target only in private staged tree, never under watched live file_sd.
for name,encoded in v['public_files'].items():
 if name!='prepared/ops/guest-node.json':raise SystemExit('publicstagewhitelist')
 target=root/name;target.parent.mkdir(mode=0o700,parents=True,exist_ok=True);data=base64.b64decode(encoded)
 if target.exists() and target.read_bytes()!=data:raise SystemExit('public candidate conflicts')
 target.write_bytes(data);target.chmod(0o600)
D=['docker','--host','unix:///var/run/docker.sock']
for args,label in [(D+['exec','dell-ops-alertmanager-1','/bin/amtool','check-config','/etc/alertmanager/alertmanager.yml'],'amtool-active-config'),(D+['exec','dell-ops-prometheus-1','/bin/promtool','check','config','/etc/prometheus/prometheus.yml'],'promtool-active-config')]:
 p=subprocess.run(args,capture_output=True,text=True,timeout=25);out['native_checks'].append({'tool':label,'exit_code':p.returncode,'no_send':True})
# check action reads runtime LoadCredential and parses URL only; no Sender invocation.
import tempfile
with tempfile.TemporaryDirectory(prefix='network19-lark-config-only-') as tmp:
 cred=Path(tmp);cred.chmod(0o700)
 (cred/'bridge-auth').write_text('A'*64);(cred/'bridge-auth').chmod(0o600)
 (cred/'lark-webhook').write_text('https://open.larksuite.com/open-apis/bot/v2/hook/11111111-1111-4111-8111-111111111111');(cred/'lark-webhook').chmod(0o600)
 p=subprocess.run(['/usr/bin/python3','-I','-B','/usr/local/libexec/dell-lark-notify/bridge.py','check'],env={'PATH':'/usr/bin:/bin','CREDENTIALS_DIRECTORY':str(cred)},capture_output=True,text=True,timeout=20)
 try:x=json.loads(p.stdout)
 except Exception:x={}
 out['native_checks'].append({'tool':'actual-bridge-config-check-with-synthetic-credentials-only','exit_code':p.returncode,'ok':x.get('ok') is True,'mode':x.get('mode'),'real_Webhook_or_token_read':False,'no_send':True})
files=[p.name for p in Path('/usr/local/libexec/dell-lark-notify').iterdir() if p.is_file()];out['installed_bridge_public_file_names']=files
p=subprocess.run(['systemctl','show','dell-lark-notify.service','--property=ActiveState,SubState,MainPID,NRestarts'],capture_output=True,text=True,timeout=10);out['bridge_state']=dict(l.split('=',1) for l in p.stdout.splitlines() if '=' in l)
out['all_native_checks_pass']=all(x['exit_code']==0 for x in out['native_checks']);print(json.dumps(out));raise SystemExit(0 if out['all_native_checks_pass'] else 1)
'''
old=next(x['target'] for x in json.loads((R/'evidence/implementation/private-guest-access.json').read_text())['roles'] if x['target']['vmid']==270);targets=json.loads((R/'network19/evidence/migrated-access.json').read_text())['targets'];info=targets.get('270',old)
data={'public_files':{'prepared/ops/guest-node.json':base64.b64encode((H/'prepared/ops/guest-node.json').read_bytes()).decode()}}
wrapped='try:\n'+''.join(' '+line+'\n' for line in P.splitlines())+'except Exception as e:\n import json,traceback\n print(json.dumps({\"status\":\"stage-check-exception\",\"error_category\":type(e).__name__,\"public_program_line\":traceback.extract_tb(e.__traceback__)[-1].lineno}))\n raise SystemExit(1)\n'
r=control.guest(270,'sudo -n python3 -I -B -c '+shlex.quote(wrapped),data=json.dumps(data).encode(),timeout=120,info=info)
try:x=json.loads(r['stdout'])
except Exception:raise SystemExit('Ops no-send preflight no safe result; do not send or stop')
(H/'ops270-active-census-native-evidence.json').write_text(json.dumps({'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'exit_code':r['exit_code'],'result':x},indent=2)+'\n');print(json.dumps(x));raise SystemExit(r['exit_code'])
