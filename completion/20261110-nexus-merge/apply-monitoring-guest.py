#!/usr/bin/env python3
"""CAS paired registry/profile update only; never run the installer or restart workloads."""
import hashlib,importlib.util,json,os,socket,stat,subprocess,sys,tempfile
from pathlib import Path
assert os.geteuid()==0 and not Path('/etc/pve').exists();x=json.load(sys.stdin);assert socket.gethostname()==x['hostname']
allowed={'/opt/dell/guest-monitoring/guest-targets.json','/opt/dell/guest-monitoring/install-guest-baseline.py','/etc/dell-guest-monitoring/health.json'}
assert set(x['files'])<=allowed and len(x['files']) in (2,3)
os.umask(0o077);backup=Path('/root/dell-nexus-monitoring-20261110');assert not backup.exists();backup.mkdir(mode=0o700)
old={};modes={}
for name,spec in x['files'].items():
 p=Path(name);assert p.resolve()==p and p.stat().st_uid==0 and not p.stat().st_mode&0o022;raw=p.read_bytes();assert hashlib.sha256(raw).hexdigest()==spec['before_sha'];old[name]=raw;modes[name]=stat.S_IMODE(p.stat().st_mode)
 q=backup/p.name;q.write_bytes(raw);q.chmod(0o600)
source=x['files']['/opt/dell/guest-monitoring/install-guest-baseline.py']['text'];compile(source,'candidate-installer','exec')
with tempfile.TemporaryDirectory(prefix='nexus-monitor-pair-')as temp:
 folder=Path(temp);(folder/'install-guest-baseline.py').write_text(source);(folder/'guest-targets.json').write_text(x['files']['/opt/dell/guest-monitoring/guest-targets.json']['text'])
 spec=importlib.util.spec_from_file_location('candidate_monitor',folder/'install-guest-baseline.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);row=m.guest_gate(x['hostname']);m.require_private_ip(row);assert 'artifact-service'not in m.ROLES
active=subprocess.run(['systemctl','is-active','dell-guest-health.timer'],capture_output=True,text=True).stdout.strip()=='active'
if active:subprocess.run(['systemctl','stop','dell-guest-health.timer'],check=True,capture_output=True)
subprocess.run(['systemctl','stop','dell-guest-health.service'],check=True,capture_output=True)
try:
 for name,spec in x['files'].items():
  p=Path(name);assert p.read_bytes()==old[name];p.write_text(spec['text']);p.chmod(modes[name])
 subprocess.run(['runuser','-u','prometheus','--','python3','/opt/dell/guest-monitoring/collect-guest-health.py','--check'],check=True,capture_output=True,timeout=60)
 subprocess.run(['systemctl','start','dell-guest-health.service'],check=True,capture_output=True,timeout=60)
except Exception:
 for name,raw in old.items():p=Path(name);p.write_bytes(raw);p.chmod(modes[name])
 raise
finally:
 if active:subprocess.run(['systemctl','start','dell-guest-health.timer'],check=True,capture_output=True)
print(json.dumps({'hostname':x['hostname'],'status':'paired-registry-CAS-and-native-collector-passed','files':[Path(p).name for p in x['files']],'workloads_or_exporter_restarted':False,'NFS_exports_or_workload_settings_changed':False}))
