#!/usr/bin/env python3
"""Prepared270 exact public target commit; default inspect, no send/restart."""
import argparse,hashlib,json,os,socket,stat,subprocess,tempfile
from pathlib import Path
class Refused(RuntimeError):pass

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--contract-dir',type=Path,required=True);p.add_argument('--apply-quiesced',action='store_true');p.add_argument('--root-receipt',type=Path);a=p.parse_args()
 if os.geteuid()!=0 or socket.gethostname().split('.')[0]!='ops-service' or Path('/etc/pve').exists():raise Refused('only270')
 root=a.contract_dir;contract=json.loads((root/'data-ops-patch-contract.json').read_text());item=next(x for x in contract['files'] if x['vmid']==270 and x['path'].endswith('/guest-node.json'));active=Path(item['path']);candidate=root/item['prepared_public_path']
 if sha(active)!=item['source_sha256'] or sha(candidate)!=item['new_sha256']:raise Refused('exact-old-new-target-SHA-required')
 old=json.loads(active.read_text());new=json.loads(candidate.read_text())
 if len(old)!=12 or len(new)!=12 or any(x['labels']!=y['labels'] or x['targets'][0].split(':')[1]!='9100' or not y['targets'][0].startswith('192.168.19.') for x,y in zip(old,new)):raise Refused('only12-node-hosts-change')
 if not a.apply_quiesced:print(json.dumps({'status':'inspected-targets-no-write','nodes':12,'Lark_or_own_HTTP_targets_changed':False}));return
 if a.root_receipt is None or a.root_receipt.resolve()!=a.root_receipt or a.root_receipt.stat().st_uid!=0 or a.root_receipt.stat().st_mode&0o077:raise Refused('root600-Ops-window-required')
 r=json.loads(a.root_receipt.read_text())
 if r.get('migration')!='network19' or r.get('vmid')!=270 or r.get('phase')!='commit-ops-targets' or r.get('parent_window_open') is not True:raise Refused('Ops-target-window-mismatch')
 state=subprocess.run(['systemctl','is-active','dell-ops.service'],capture_output=True,text=True,timeout=10).stdout.strip()
 if state not in ['inactive','failed']:raise Refused('Ops-supervisor-must-be-quiesced')
 backup=Path('/root/dell-network19/ops-target-backup.json')
 if backup.exists():raise Refused('target-backup-exists-no-blind-retry')
 backup.write_bytes(active.read_bytes());backup.chmod(0o600);st=active.stat();fd,tmp=tempfile.mkstemp(prefix='.network19-targets-',dir=active.parent)
 with os.fdopen(fd,'wb') as f:f.write(candidate.read_bytes());f.flush();os.fsync(f.fileno())
 os.chown(tmp,st.st_uid,st.st_gid);os.chmod(tmp,stat.S_IMODE(st.st_mode));os.replace(tmp,active)
 print(json.dumps({'status':'12-node-targets-committed-role-still-quiesced','active_source_SHA_matches_candidate':sha(active)==item['new_sha256'],'Lark_secrets_policy_bridge_or_mode_changed':False,'notifications_or_HUP_or_restart_issued':False}))
if __name__=='__main__':
 try:main()
 except Exception as e:print(json.dumps({'status':'refused-or-failed','error_category':type(e).__name__,'reason':str(e) if isinstance(e,Refused) else 'details-withheld'}));raise SystemExit(1)
