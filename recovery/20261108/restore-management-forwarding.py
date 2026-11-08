#!/usr/bin/env python3
"""PVE-only restore of management/L2 forwarding invariant, without network reload."""
import hashlib,json,os,socket,subprocess,time
from pathlib import Path
assert os.geteuid()==0 and socket.gethostname()=='pve' and Path('/etc/pve').is_dir()
addr=json.loads(subprocess.check_output(['ip','-4','-j','addr','show','vmbr0']))
assert [a['local'] for a in addr[0]['addr_info'] if a['family']=='inet']==['192.168.21.22']
assert not json.loads(subprocess.check_output(['ip','-j','addr','show','vmbr19']))[0]['addr_info']
assert subprocess.check_output(['nft','list','tables'],text=True).splitlines()==['table bridge dell19_acl']
script=Path('/usr/local/sbin/dell-management-forwarding-off')
hook=Path('/etc/network/if-up.d/dell-management-forwarding-off')
drop=Path('/etc/systemd/system/dell-network19-bridge.service.d/20-management-only.conf')
contents={script:b'''#!/bin/sh
# PVE management/L2 only. Do not restart networking or change routing/ACL.
set -eu
[ "$(hostname -s)" = pve ] && [ -d /etc/pve ]
for family in ipv4 ipv6; do
    for path in /proc/sys/net/$family/conf/*/forwarding; do
        [ -f "$path" ] || continue
        printf '0\\n' > "$path"
    done
done
printf '0\\n' > /proc/sys/net/ipv4/ip_forward
''',hook:b'''#!/bin/sh
# ifupdown2 sets forwarding on bridges with IP; restore original management-only contract.
set -eu
[ "${IFACE:-}" = vmbr0 ] || exit 0
exec /usr/local/sbin/dell-management-forwarding-off
''',drop:b'''[Service]
# Runs after network.target on boot, before pve-guests.service.
ExecStartPost=/usr/local/sbin/dell-management-forwarding-off
'''}
assert all(not p.exists() and not p.is_symlink() for p in contents),'Owned destinations already exist; stop for review'
base=Path('/root/dell-bootstrap/recovery-20261108/management-forwarding');base.mkdir(parents=True,exist_ok=False);base.chmod(0o700)
before={str(p):p.read_text().strip() for fam in ['ipv4','ipv6'] for p in Path('/proc/sys/net',fam,'conf').glob('*/forwarding')}
assert all(v in ('0','1') for v in before.values())
interfaces_hash=hashlib.sha256(Path('/etc/network/interfaces').read_bytes()).hexdigest()
routes_before=json.loads(subprocess.check_output(['ip','-4','-j','route','show','table','main']))
acl_before=subprocess.check_output(['nft','-s','list','table','bridge','dell19_acl'])
global_forward_before=Path('/proc/sys/net/ipv4/ip_forward').read_text().strip()
assert global_forward_before=='0'
planpaths=[Path('/etc/sysctl.d/99-z-dell-management-only.conf'),Path('/etc/systemd/system/dell-network19-bridge.service')]
for p in planpaths:
 assert p.is_file() and not p.is_symlink();q=base/p.name;q.write_bytes(p.read_bytes());q.chmod(0o600)
receipt={'before_forwarding':before,'interfaces_SHA_before':interfaces_hash,'actions':[]}
try:
 for path,data in contents.items():
  path.parent.mkdir(parents=True,exist_ok=True);fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
  with os.fdopen(fd,'wb') as f:f.write(data)
  path.chmod(0o755 if path in (script,hook) else 0o644);receipt['actions'].append(str(path))
 for path in [script,hook]:subprocess.run(['/bin/sh','-n',str(path)],check=True)
 subprocess.run(['systemd-analyze','verify','dell-network19-bridge.service'],check=True,capture_output=True)
 subprocess.run(['systemctl','daemon-reload'],check=True)
 # Run the if-up hook explicitly; never reload or cycle a bridge.
 subprocess.run([str(hook)],env={'PATH':'/usr/sbin:/usr/bin:/sbin:/bin','IFACE':'vmbr0'},check=True)
 after={str(p):p.read_text().strip() for fam in ['ipv4','ipv6'] for p in Path('/proc/sys/net',fam,'conf').glob('*/forwarding')}
 assert all(v=='0' for v in after.values())
 assert hashlib.sha256(Path('/etc/network/interfaces').read_bytes()).hexdigest()==interfaces_hash
 assert json.loads(subprocess.check_output(['ip','-4','-j','route','show','table','main']))==routes_before
 assert subprocess.check_output(['nft','-s','list','table','bridge','dell19_acl'])==acl_before
 receipt.update(status='management-forwarding-restored-no-network-reload',after_all_forward_zero=True,management_interfaces_file_unchanged=True,bridges_routes_ACL_unchanged=True,guest_restart=False,network_restart=False,configured_files_SHA={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in contents})
except Exception as error:
 # Best effort every rollback step, preserving sanitized failure receipt.
 rollback_errors=[]
 for path in reversed(list(contents)):
  try:
   if str(path) in receipt['actions'] and path.is_file():path.unlink()
  except OSError:rollback_errors.append('remove-owned-file:'+str(path))
 for path,value in before.items():
  try:
   if Path(path).is_file():Path(path).write_text(value+'\n')
  except OSError:rollback_errors.append('restore-proc:'+path)
 try:Path('/proc/sys/net/ipv4/ip_forward').write_text(global_forward_before+'\n')
 except OSError:rollback_errors.append('restore-global-forward')
 if subprocess.run(['systemctl','daemon-reload'],check=False).returncode:rollback_errors.append('daemon-reload')
 receipt.update(status='failed-rollback-attempted',error_type=type(error).__name__,rollback_errors=rollback_errors)
 failed=base/'failure-receipt.json';failed.write_text(json.dumps(receipt,indent=2)+'\n');failed.chmod(0o600)
 raise RuntimeError('Management-forwarding update failed; inspect protected receipt; rollback errors='+str(len(rollback_errors))) from None
out=base/'receipt.json';out.write_text(json.dumps(receipt,indent=2)+'\n');out.chmod(0o600)
print(json.dumps(receipt))
