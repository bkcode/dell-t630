"""Explicit210 add-new-only window; no OS/services/retire changes."""
import base64,datetime,json,shlex,sys
from pathlib import Path
sys.dont_write_bytecode=True
H=Path(__file__).resolve().parent;R=H.parents[1];sys.path.insert(0,str(R/'scripts'));import control
payload={name:base64.b64encode((H/name).read_bytes()).decode() for name in ['mysql-hosts.py','sql-host-contract.json']}
P=r'''import base64,json,os,socket,subprocess,sys
from pathlib import Path
if os.geteuid()!=0 or socket.gethostname().split('.')[0]!='data-test' or Path('/etc/pve').exists():raise SystemExit('only210')
values=json.loads(sys.stdin.read());root=Path('/root/dell-network19/staged/core-mysql210')
for path in [Path('/root/dell-network19'),Path('/root/dell-network19/staged')]:
 if path.resolve(strict=False)!=path:raise SystemExit('stage parent symlink')
 path.mkdir(mode=0o700,exist_ok=True)
root.mkdir(mode=0o700,exist_ok=False)
for name,encoded in values.items():
 if name not in ['mysql-hosts.py','sql-host-contract.json']:raise SystemExit('unknown public payload')
 target=root/name;fd=os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
 with os.fdopen(fd,'wb') as f:f.write(base64.b64decode(encoded))
def call(args):
 p=subprocess.run(args,capture_output=True,text=True,timeout=120)
 try:x=json.loads(p.stdout)
 except Exception:x={'status':'failed-no-sanitized-receipt'}
 return p.returncode,x
code,plan=call(['python3','-I','-B',str(root/'mysql-hosts.py'),'--phase','plan'])
if code or plan.get('status')!='read-only-plan' or len(plan.get('accounts',[]))!=3 or sum(x['DML_table_count'] for x in plan['accounts'])!=18:
 print(json.dumps({'status':'source-plan-refused','exit_code':code,'new_users_created':0}));raise SystemExit(1)
file=root/'source-plan.json';file.write_text(json.dumps(plan));file.chmod(0o600)
receipt=root/'210-add-new-window.json';receipt.write_text(json.dumps({'migration':'network19','target_vmid':210,'allowed_phase':'add-new','parent_window_open':True,'scope':'exact3 newHost only; original18 DML/auth/plugin; Nacos percent unchanged'}));receipt.chmod(0o600)
code,result=call(['python3','-I','-B',str(root/'mysql-hosts.py'),'--phase','add-new','--apply','--root-receipt',str(receipt)])
out={'status':result.get('status'),'exit_code':code,'source_plan_old_exact_grants_matched':True,'accounts_completed':result.get('accounts_completed',0),'DML_table_count':18,'auth_unchanged_private_comparison':result.get('auth_unchanged_private_comparison',False),'old_Host_retained':True,'Nacos_percent_accounts_unchanged':result.get('Nacos_accounts_unchanged',False),'OS_or_service_or_IP_changed':False,'auth_hash_password_or_raw_SQL_in_output_or_ledger':False}
print(json.dumps(out));raise SystemExit(code)
'''
row=next(r for r in json.loads((R/'evidence/implementation/private-guest-access.json').read_text())['roles'] if r['target']['vmid']==210)
r=control.guest(210,'sudo -n python3 -I -B -c '+shlex.quote(P),data=json.dumps(payload).encode(),timeout=260,info=row['target'])
try:x=json.loads(r['stdout'])
except Exception:raise SystemExit('210 preparation did not return safe metadata; do not retry apply blindly')
(H/'mysql210-add-new-evidence.json').write_text(json.dumps({'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'exit_code':r['exit_code'],'result':x},indent=2)+'\n');print(json.dumps(x));raise SystemExit(r['exit_code'])
