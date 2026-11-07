from pathlib import Path
import sys,json,shlex
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'scripts'));import control
old=next(x['target'] for x in json.loads((R/'evidence/implementation/private-guest-access.json').read_text())['roles'] if x['target']['vmid']==260)
for name in ['nas-os-network.py','omv_payload.py']:
 r=control.guest(260,'sudo install -m 750 /dev/stdin /opt/dell/network19/services-media/'+name,data=(R/'network19/services-media'/name).read_bytes(),info=old);assert r['exit_code']==0
nonce=json.loads((R/'network19/services-media/stage-nonces.json').read_text())
print(json.dumps(nonce))
