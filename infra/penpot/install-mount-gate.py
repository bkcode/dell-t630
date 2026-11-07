#!/usr/bin/env python3
"""Install, but do not start, a dedicated-data mount-gated systemd unit."""
import argparse
import os
from pathlib import Path
import re
import subprocess
from target_guard import verify_target

BASE = Path(__file__).resolve().parent
p = argparse.ArgumentParser()
p.add_argument('--private-dir', required=True, type=Path)
a = p.parse_args()
contract, _ = verify_target(require_docker_data=True)
if contract['storage']['mode'] != 'dedicated':
    raise SystemExit('Mount-gated unit only applies to an explicitly assigned dedicated filesystem')
for path in [BASE, a.private_dir.resolve()]:
    if not re.fullmatch(r'/[A-Za-z0-9_./-]+', str(path)):
        raise SystemExit('Unit paths require canonical paths without whitespace or shell characters')
mount = contract['storage']['mountpoint']
unit = subprocess.run(['systemd-escape', '--path', '--suffix=mount', mount], capture_output=True, text=True, check=True).stdout.strip()
content = f'''[Unit]
Description=Dell Penpot with verified persistent storage
Requires=docker.service
BindsTo=docker.service {unit}
After=network-online.target docker.service {unit}
RequiresMountsFor={mount}
PartOf=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
Environment=DELL_MOUNT_GATED=1
ExecStart=/usr/bin/python3 {BASE}/target.py start --private-dir {a.private_dir.resolve()}
ExecStop=/usr/bin/python3 {BASE}/target.py stop --private-dir {a.private_dir.resolve()}
TimeoutStartSec=600
TimeoutStopSec=180

[Install]
WantedBy=multi-user.target
'''
# DockerRootDir itself is on this filesystem: gate the daemon as well as apps.
dropin = Path('/etc/systemd/system/docker.service.d/dell-penpot-storage.conf')
dropin.parent.mkdir(parents=True, exist_ok=True)
dropin.write_text(f'[Unit]\nRequiresMountsFor={mount}\nBindsTo={unit}\nAfter={unit}\n')
dropin.chmod(0o644)
path = Path('/etc/systemd/system/dell-penpot.service')
path.write_text(content)
path.chmod(0o644)
subprocess.run(['systemctl', 'daemon-reload'], check=True)
subprocess.run(['systemctl', 'enable', 'dell-penpot.service'], check=True)
print('Mount-gated unit installed and enabled, not started. Start only after successful restore.')
