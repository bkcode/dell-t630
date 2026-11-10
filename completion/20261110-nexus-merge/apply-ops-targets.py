#!/usr/bin/env python3
"""Exact221 SD retirement and notification role removal, no receiver/credential changes."""
import hashlib,json,os,socket,subprocess,sys
from pathlib import Path
assert os.geteuid()==0 and socket.gethostname()=='ops-service';os.umask(0o077)
x=json.load(sys.stdin);p=Path('/opt/dell/ops/config/prometheus/targets/guest-node.json');before=p.read_bytes();assert hashlib.sha256(before).hexdigest()==x['old_sha'];new=x['new'].encode();a,b=json.loads(before),json.loads(new);assert len(a)==11 and len(b)==10 and b==[r for r in a if r['labels']['vmid']!='221'];assert any(r['labels']['vmid']=='280'for r in b)
ids=subprocess.check_output(['docker','ps','-q','--filter','label=com.docker.compose.project=dell-ops','--filter','label=com.docker.compose.service=prometheus']).decode().split();assert len(ids)==1;cid=ids[0]
def run(args):return subprocess.check_output(args,stderr=subprocess.PIPE,timeout=40).decode().strip()
run(['docker','exec',cid,'/bin/promtool','check','config','/etc/prometheus/prometheus.yml'])
folder=Path('/root/dell-nexus-ops-retire221-20261110');assert not folder.exists();folder.mkdir(mode=0o700)
q=folder/'guest-node.before.json';q.write_bytes(before);q.chmod(0o600);mode=p.stat().st_mode&0o777;p.write_bytes(new);p.chmod(mode)
run(['docker','exec',cid,'/bin/promtool','check','config','/etc/prometheus/prometheus.yml'])
lark=Path('/usr/local/libexec/dell-lark-notify/bridge.py');old=lark.read_bytes();assert old.count(b"'artifact-service',")==1;after=old.replace(b"'artifact-service',",b'',1);compile(after,str(lark),'exec');assert not run(['ss','-H','-tn','state','established','sport','=',':19093'])
q=folder/'lark-bridge.before.py';q.write_bytes(old);q.chmod(0o600);mode=lark.stat().st_mode&0o777;lark.write_bytes(after);lark.chmod(mode);run(['systemctl','restart','dell-lark-notify.service']);assert run(['systemctl','is-active','dell-lark-notify.service'])=='active'
print(json.dumps({'status':'221-SD-and-Lark-role-removed','node_targets_before':len(a),'node_targets_after':len(b),'resource280_kept':True,'Prometheus_restarted':False,'notification_receiver_or_secrets_changed':False,'test_notifications_sent':False,'new_SD_public_SHA':hashlib.sha256(new).hexdigest(),'new_Lark_bridge_public_SHA':hashlib.sha256(after).hexdigest()}))
