#!/usr/bin/env python3
"""Disable an idle boot-enabled diagnostic daemon; retain the package and manual client."""
import os,socket,subprocess,json,hashlib,datetime,re
from pathlib import Path
assert os.geteuid()==0 and socket.gethostname()=='pve' and Path('/etc/pve').is_dir()
def run(*args):return subprocess.run(args,capture_output=True,text=True,check=True,timeout=20).stdout
unit='iperf3.service';props=dict(l.split('=',1) for l in run('systemctl','show',unit,'--property=LoadState,ActiveState,UnitFileState,FragmentPath,MainPID').splitlines())
assert props['LoadState']=='loaded' and props['ActiveState']=='active' and props['UnitFileState']=='enabled'
assert props['FragmentPath'] in ['/lib/systemd/system/iperf3.service','/usr/lib/systemd/system/iperf3.service']
pid=props['MainPID'];argv=Path('/proc',pid,'cmdline').read_bytes().split(b'\0');assert argv[0]==b'/usr/bin/iperf3' and b'--server' in argv
connections=run('ss','-H','-tn','state','established');assert not any(re.search(r':5201\b',l) for l in connections.splitlines()),'Active test; do not stop'
p=Path('/etc/default/iperf3');assert p.is_file() and not p.is_symlink();old=p.read_bytes();text=old.decode();assert len(re.findall(r'^START_DAEMON=',text,re.M))==1
assert re.search(r'^START_DAEMON=["\x27]?yes["\x27]?\s*$',text,re.M)
new=re.sub(r'^START_DAEMON=.*$', 'START_DAEMON="no"',text,flags=re.M).encode()
base=Path('/root/dell-bootstrap/completion-20261109/disable-idle-iperf');base.mkdir(parents=True,exist_ok=False);base.chmod(0o700);b=base/'iperf3.default.before';b.write_bytes(old);b.chmod(0o600)
assert p.read_bytes()==old
try:
 temp=p.with_name('iperf3.dell-new');fd=os.open(temp,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
 with os.fdopen(fd,'wb') as f:f.write(new)
 temp.chmod(p.stat().st_mode&0o777);os.replace(temp,p)
 assert not any(re.search(r':5201\b',l) for l in run('ss','-H','-tn','state','established').splitlines())
 run('systemctl','disable','--now',unit)
 after=dict(l.split('=',1) for l in run('systemctl','show',unit,'--property=ActiveState,SubState,UnitFileState,MainPID').splitlines())
 assert after['ActiveState']=='inactive' and after['UnitFileState']=='disabled'
 assert not any(re.search(r':5201\b',l) for l in run('ss','-H','-ltn').splitlines())
except Exception:
 p.write_bytes(old);run('systemctl','enable','--now',unit);raise
receipt={'at':datetime.datetime.now().astimezone().isoformat(),'status':'idle-iperf-server-disabled-tool-retained','before':props,'after':after,'no_active_test_connections_before_stop':True,'port5201_closed':True,'package_removed':False,'application_or_guest_restart':False,'network_changed':False,'before_defaults_sha256':hashlib.sha256(old).hexdigest(),'after_defaults_sha256':hashlib.sha256(new).hexdigest()};r=base/'receipt.json';r.write_text(json.dumps(receipt,indent=2)+'\n');r.chmod(0o600);print(json.dumps(receipt))
