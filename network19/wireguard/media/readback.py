#!/usr/bin/env python3
"""Read-only original19-source SMB/identity/data regression after VPN recognition change."""
import json,sys
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'scripts'));import control
control.BASE+=['-o','ForwardAgent=no'];info=json.loads((ROOT/'network19/evidence/migrated-access.json').read_text())['targets']['260'];nonce=json.loads((HERE/'window.json').read_text())['nonce']
SCRIPT=r'''
import hashlib,importlib.util,json,os,re,socket,subprocess,sys
from pathlib import Path
sys.dont_write_bytecode=True
s=importlib.util.spec_from_file_location('tx','/opt/dell/network19/services-media/guest_transaction.py');tx=importlib.util.module_from_spec(s);s.loader.exec_module(tx)
r=tx.guard(260,'new');folder=Path('/root/dell-wireguard-media')/NONCE;j=json.loads(tx.read(folder/'journal.json'));assert j['phase']=='committed-verified'
assert tx.protected(r)==j['protected_hashes']
source=Path('/root/private/dell-nas/acceptance');candidates=[p for p in source.glob('permissions-*') if all((p/(who+'.auth')).is_file() and (p/(who+'.auth')).stat().st_uid==0 and (p/(who+'.auth')).stat().st_mode&0o777==0o600 for who in ['writer','reader'])];assert candidates
credentials=max(candidates,key=lambda p:p.stat().st_mtime)
output=folder/'readback';output.mkdir(mode=0o700);results=[]
for share in ['media','games','incoming']:
 row={'share':share,'reads':{}}
 for who in ['writer','reader']:
  file=output/(share+'-'+who+'.bin');fixture='dell-acceptance-'+share+'.bin'
  p=subprocess.run(['/usr/bin/smbclient','//192.168.19.60/'+share,'-A',str(credentials/(who+'.auth')),'-m','SMB3','-c','get '+fixture+' '+str(file)],capture_output=True,text=True,timeout=30)
  assert p.returncode==0 and file.is_file() and hashlib.sha256(file.read_bytes()).hexdigest()=='fbbab289f7f94b25736c58be46a994c441fd02552cc6022352e3d86d2fab7c83'
  file.chmod(0o600);row['reads'][who]='authenticated-original-SHA-matches'
 p=subprocess.run(['/usr/bin/smbclient','//192.168.19.60/'+share,'-U','%','-N','-m','SMB3','-c','ls'],capture_output=True,text=True,timeout=20)
 assert p.returncode!=0 and any(v in p.stdout+p.stderr for v in ['NT_STATUS_ACCESS_DENIED','NT_STATUS_LOGON_FAILURE','NT_STATUS_ACCOUNT_DISABLED'])
 row['anonymous_denied']=True;results.append(row)
assert tx.protected(r)==j['protected_hashes']
result={'role':260,'status':'original19-source-SMB-read-identity-data-regression-passed','SMB3_results':results,'existing_same_guest_auth_files_reused':True,'no_user_password_role_or_share_write_request':True,'identity_shadow_key_guard_bytes_unchanged':True,'VPN_packet_source_exercised':False,'remote_VPN_proof_owner':'root real10.66.66 client batch','readback_copies_guest_private_mode600':True}
tx.save(folder/'original19-readback-result.json',result);print(json.dumps(result))
'''.replace('NONCE',repr(nonce))
r=control.guest(260,'sudo python3 -',data=SCRIPT.encode(),timeout=220,info=info)
if r['exit_code']:raise SystemExit('NAS original-source readback unconfirmed; raw output withheld')
v=json.loads(r['stdout']);(HERE/'readback-result.json').write_text(json.dumps(v,indent=2)+'\n');print(json.dumps({'role':260,'status':v['status']}))
