#!/usr/bin/env python3
"""Record publisher preservation proof and CAS-install reviewed Nexus-only helper."""
import hashlib,json,os,socket,sqlite3,stat,subprocess,sys
from pathlib import Path
assert os.geteuid()==0 and socket.gethostname()=='publish-service' and not Path('/etc/pve').exists()
os.umask(0o077)
payload=json.load(sys.stdin)
def user(args):return subprocess.check_output(['runuser','-u','ub','--',*args],stderr=subprocess.PIPE).decode().strip()
root=Path('/opt/deploy-public');assert user(['git','-C',str(root),'rev-parse','HEAD'])=='213f1f42924f18e0d7b5848c2c1141a6230c1f5a';assert not user(['git','-C',str(root),'status','--porcelain'])
db=sqlite3.connect('file:/srv/dell-build/deploy-public/mcp-state/jobs.sqlite?mode=ro',uri=True);assert all(json.loads(x[0])['status']not in ('running','queued')for x in db.execute('SELECT payload FROM jobs'));db.close()
assert not subprocess.check_output(['docker','ps','-aq']).strip()
proof=Path('/root/dell-nexus-merge-publisher-proof-20261110.json');assert not proof.exists()
protected=['/opt/deploy-public/config.local.yaml','/etc/systemd/system/puyu-deploy-mcp.service','/opt/dell/deploy-public/check-build-mount.py','/etc/dell-publisher/client-test240.json']
proof.write_text(json.dumps({'files':{p:hashlib.sha256(Path(p).read_bytes()).hexdigest()for p in protected},'source_HEAD':'213f1f42924f18e0d7b5848c2c1141a6230c1f5a'}));proof.chmod(0o600)
target=Path('/opt/dell/cleanup/nexus/target.py');assert hashlib.sha256(target.read_bytes()).hexdigest()==payload['old_sha']
new=payload['source'].encode();compile(new,str(target),'exec');assert hashlib.sha256(new).hexdigest()==payload['new_sha']
backup=target.with_name('target.before-resume-20261110.py');assert not backup.exists();backup.write_bytes(target.read_bytes());backup.chmod(0o600)
target.write_bytes(new);target.chmod(0o644)
print(json.dumps({'publisher_checkpoint_VM_only_root600':True,'MCP_no_active_jobs':True,'Docker_no_containers':True,'Nexus_helper_CAS_updated':True,'new_public_helper_sha256':payload['new_sha'],'publisher_private_key_read_or_copied':False,'private_config_or_hashes_output':False}))
