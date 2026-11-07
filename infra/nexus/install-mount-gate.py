#!/usr/bin/env python3
"""Install, but do not start, a dedicated-data mount-gated Nexus systemd unit."""
import argparse
from pathlib import Path
import re
import subprocess
from target_guard import verify_target

BASE = Path(__file__).resolve().parent
p = argparse.ArgumentParser()
p.add_argument('--env-file', required=True, type=Path)
a = p.parse_args()
contract, _ = verify_target()
if contract['storage']['mode'] != 'dedicated':
    raise SystemExit('Mount-gated unit requires an explicitly assigned dedicated filesystem')
for path in [BASE, a.env_file.resolve()]:
    if not re.fullmatch(r'/[A-Za-z0-9_./-]+', str(path)):
        raise SystemExit('Unit paths require canonical paths without whitespace or shell characters')
mount = contract['storage']['mountpoint']
unit = subprocess.run(['systemd-escape', '--path', '--suffix=mount', mount], capture_output=True, text=True, check=True).stdout.strip()
content = f'''[Unit]
Description=Dell Nexus with verified persistent storage
Requires=docker.service
BindsTo=docker.service {unit}
After=network-online.target docker.service {unit}
RequiresMountsFor={mount}
PartOf=docker.service
StartLimitIntervalSec=600
StartLimitBurst=5

[Service]
Type=simple
Environment=DELL_MOUNT_GATED=1
ExecStart=/usr/bin/python3 {BASE}/manage.py supervise --env-file {a.env_file.resolve()}
ExecStop=/usr/bin/python3 {BASE}/manage.py stop --env-file {a.env_file.resolve()}
Restart=on-failure
RestartSec=15
UMask=0077
TimeoutStartSec=600
TimeoutStopSec=180

[Install]
WantedBy=multi-user.target
'''
path = Path('/etc/systemd/system/dell-nexus.service')
path.write_text(content)
path.chmod(0o644)
subprocess.run(['systemctl', 'daemon-reload'], check=True)
subprocess.run(['systemctl', 'enable', 'dell-nexus.service'], check=True)
print('Mount-gated Nexus unit installed and enabled, not started.')
