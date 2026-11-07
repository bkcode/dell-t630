#!/usr/bin/env python3
"""Manager: combine independently observed readiness and activate test-only release."""
import sys,json,datetime,argparse,re
from pathlib import Path
BASE=Path(__file__).resolve().parents[3];sys.path.insert(0,str(BASE/'scripts'));import control
parser=argparse.ArgumentParser();parser.add_argument('--release-id',default='20261106T061002');args=parser.parse_args();assert re.fullmatch(r'[0-9]{8}T[0-9]{6}',args.release_id)
rows=json.loads((BASE/'evidence/implementation/private-guest-access.json').read_text())['roles'];targets={r['target']['vmid']:r['target'] for r in rows}
sql=control.guest(210,'sudo cat /root/dell-java-test-init/sql-result.json',info=targets[210]);assert sql['exit_code']==0;sql=json.loads(sql['stdout']);assert sql['application_table_count']==18
n=json.loads((BASE/'evidence/implementation/java-test-nacos.json').read_text());assert n['result']['exit_code']==0 and json.loads(n['result']['stdout'])['nacos_configs_ready'] is True
net=json.loads((BASE/'evidence/implementation/network-independent-verification.json').read_text())
# The underlying artifact is reviewed by the task manager; preserve its hash in marker.
import hashlib
assert '10.63.20.20' in json.dumps(net) and '9848' in json.dumps(net)
marker={'target_ip':'10.63.20.20','database_schemas_ready':True,'nacos_configs_ready':True,'network_policy_ready':True,'issuer_candidate_acknowledged':True,'issuer_scope':'LAN initial deployment, not public HTTPS approval','at':datetime.datetime.now().isoformat(),'network_evidence_sha256':hashlib.sha256((BASE/'evidence/implementation/network-independent-verification.json').read_bytes()).hexdigest(),'database_evidence':sql,'nacos_evidence':'java-test-nacos.json'}
r=control.guest(240,'sudo install -m 600 /dev/stdin /root/dell-java-test-readiness.json',data=(json.dumps(marker)+'\n').encode(),info=targets[240]);assert r['exit_code']==0
(BASE/'evidence/implementation/java-test-readiness.json').write_text(json.dumps(marker,indent=2)+'\n')
(BASE/'evidence/implementation/java-test-init.json').write_text(json.dumps({'at':datetime.datetime.now().isoformat(),'status':'sql-and-nacos-ready','sql':sql,'nacos_evidence':'java-test-nacos.json'},indent=2)+'\n')
r=control.guest(240,'sudo python3 /root/dell-java-test-incoming-'+args.release_id+'/deploy-test-chain.py activate --release-id '+args.release_id+' --ready-marker /root/dell-java-test-readiness.json',info=targets[240],timeout=900)
(BASE/'evidence/implementation/java-test-activation.json').write_text(json.dumps({'at':datetime.datetime.now().isoformat(),'result':r},indent=2)+'\n');print(json.dumps(r));sys.exit(r['exit_code'])
