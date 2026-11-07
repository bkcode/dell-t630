#!/usr/bin/env python3
"""Fail closed if the NAS data filesystem is absent, unexpected or the system disk."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--mountpoint', required=True)
p.add_argument('--uuid', required=True)
p.add_argument('--minimum-gib', type=int, default=1800)
a = p.parse_args()
try:
    point = Path(a.mountpoint)
    if not point.is_absolute() or point.resolve() != point or point == Path('/'):
        raise ValueError('mountpoint must be an absolute, canonical non-root path')
    if not re.fullmatch(r'[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}', a.uuid):
        raise ValueError('an explicit filesystem UUID is required')
    if not os.path.ismount(point):
        raise ValueError('data filesystem is not mounted')
    result = subprocess.run(['findmnt', '--json', '--mountpoint', str(point), '-o', 'TARGET,SOURCE,FSTYPE,UUID'],
                            text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    records = json.loads(result.stdout)['filesystems']
    if len(records) != 1 or records[0].get('target') != str(point):
        raise ValueError('mountpoint must identify exactly one filesystem')
    fs = records[0]
    if str(fs.get('uuid', '')).lower() != a.uuid.lower():
        raise ValueError('mounted filesystem UUID does not match assigned NAS data disk')
    if os.stat(point).st_dev == os.stat('/').st_dev:
        raise ValueError('data path resolves to the system filesystem')
    if fs.get('fstype') != 'ext4':
        raise ValueError('this recipe expects the assigned ext4 NAS data filesystem')
    capacity = os.statvfs(point)
    total = capacity.f_blocks * capacity.f_frsize
    if total < a.minimum_gib * 1024**3:
        raise ValueError('mounted filesystem is smaller than the assigned NAS capacity')
    print(json.dumps({'status': 'passed', 'mountpoint': str(point), 'filesystem_uuid': a.uuid,
                      'filesystem': fs['fstype'], 'total_bytes': total,
                      'available_bytes': capacity.f_bavail * capacity.f_frsize}))
except (ValueError, KeyError, OSError, subprocess.SubprocessError, json.JSONDecodeError) as e:
    print(json.dumps({'status': 'failed', 'reason': str(e) if isinstance(e, ValueError) else type(e).__name__}))
    sys.exit(1)
