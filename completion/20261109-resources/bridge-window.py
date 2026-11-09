#!/usr/bin/python3
"""Fixed resource VM identity and NFS/monitor bridge additions with independent180s watchdog. No L3/NAT changes."""
import datetime,hashlib,json,os,socket,subprocess,sys
from pathlib import Path
BASE=Path('/root/dell-bootstrap/resources-20261109')
ACTIVE=Path('/etc/dell-network19/bridge19.nft')
OLD='a6910d08db278527566e0b343c8a12b57989f7ba10b2df1b0d498e969e120bc0'
NEW='e50c999bc23ee62c2e0ae6ea98f1ad89cd22bfaec4a5602bfecf959450dfc266'
TIMER='dell-resource-bridge-rollback-20261109.timer'
COMMENT='trusted-LAN21-to-server19'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(a,data=None):
 p=subprocess.run(a,input=data,capture_output=True,timeout=25)
 if p.returncode:raise RuntimeError('fixed bridge operation failed; private details withheld')
 return p.stdout

def put(raw):
 tmp=BASE/'active.tmp';assert not tmp.exists();fd=os.open(tmp,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
 with os.fdopen(fd,'wb')as f:f.write(raw);f.flush();os.fsync(f.fileno())
 os.replace(tmp,ACTIVE)

def rollback():
 if not (BASE/'pending').exists():return {'status':'no-owned-pending-bridge-window'}
 assert sha(BASE/'before.nft')==OLD and sha(ACTIVE)in (OLD,NEW)
 if sha(ACTIVE)==NEW:put((BASE/'before.nft').read_bytes());run(['/usr/local/sbin/dell-apply-network19-bridge'])
 (BASE/'pending').unlink();return {'status':'owned-bridge-restored','existing_conntrack_may_live_until_close':True}

def main():
 assert os.geteuid()==0 and socket.gethostname()=='pve'and Path('/etc/pve').is_dir();assert BASE.resolve()==BASE and BASE.stat().st_uid==0 and BASE.stat().st_mode&0o777==0o700
 assert not ACTIVE.is_symlink()and ACTIVE.stat().st_uid==0 and ACTIVE.stat().st_mode&0o777==0o600
 action=sys.argv[1]
 if action=='rollback':result=rollback()
 elif action=='apply':
  assert sha(ACTIVE)==OLD and sha(BASE/'candidate.nft')==NEW and not (BASE/'pending').exists()
  raw=(BASE/'candidate.nft').read_bytes();run(['nft','-c','-f','-'],b'delete table bridge dell19_acl\n'+raw)
  (BASE/'pending').touch(mode=0o600)
  try:
   run(['systemd-run','--unit=dell-resource-bridge-rollback-20261109','--on-active=180s','--timer-property=AccuracySec=1s','--property=Type=oneshot','/usr/bin/python3','-I','-B',str(BASE/'bridge-window.py'),'rollback'])
   run(['systemctl','is-active','--quiet',TIMER]);put(raw);run(['/usr/local/sbin/dell-apply-network19-bridge'])
  except Exception:rollback();raise
  result={'status':'resource-identity-and-NFS-bridge-rules-active-watchdog-armed','watchdog_seconds':180,'persistent_candidate_SHA':NEW,'other_tables_or_L3_or_services_changed':False}
 elif action=='confirm':
  assert (BASE/'pending').exists()and sha(ACTIVE)==NEW
  rules=json.loads(run(['nft','-j','list','chain','bridge','dell19_acl','from_gateway']));matches=[x['rule']for x in rules['nftables']if 'rule'in x and x['rule'].get('comment')==COMMENT];assert len(matches)==1
  peer=run(['nft','list','set','bridge','dell19_acl','peer_tcp']).decode();assert all(x+' . 192.168.19.80 . '+str(p)in peer for x,p in [('192.168.19.40',2049),('192.168.19.45',2049),('192.168.19.70',9100)])
  run(['systemctl','stop',TIMER]);(BASE/'pending').unlink();result={'status':'resource-bridge-confirmed-watchdog-cancelled','persistent_candidate_SHA':NEW}
 else:raise RuntimeError('fixed action required')
 result['at']=datetime.datetime.now().astimezone().isoformat();p=BASE/(action+'-result.json');p.write_text(json.dumps(result,indent=2)+'\n');p.chmod(0o600);print(json.dumps(result))
if __name__=='__main__':main()
