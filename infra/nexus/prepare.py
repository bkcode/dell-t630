#!/usr/bin/env python3
"""Validate the immutable Nexus image; initialize directories only on target."""
import argparse
import json
from pathlib import Path
import platform
import subprocess
import os
from target_guard import DOCKER, assignment, verify_guest, verify_docker, verify_storage

BASE = Path(__file__).resolve().parent
p = argparse.ArgumentParser()
p.add_argument('action', choices=['verify-image', 'check', 'init-target'])
p.add_argument('--env-file', type=Path)
p.add_argument('--data-dir', type=Path)
p.add_argument('--storage-mode', choices=['rootfs', 'dedicated'])
p.add_argument('--mountpoint')
p.add_argument('--filesystem-uuid')
a = p.parse_args()
lock = json.loads((BASE / 'images.lock.json').read_text())
if a.action == 'verify-image':
    result = subprocess.run(['docker', 'buildx', 'imagetools', 'inspect', '--raw', lock['source_index']],
                            capture_output=True, text=True, timeout=60)
    if result.returncode:
        raise SystemExit('Registry manifest query failed')
    manifests = json.loads(result.stdout)['manifests']
    if not any(x['digest'] == lock['target'].split('@', 1)[1]
               and x.get('platform', {}).get('architecture') == 'amd64'
               and x.get('platform', {}).get('os') == 'linux' for x in manifests):
        raise SystemExit('Source version does not contain locked AMD64 digest')
    print('Nexus 3.84.0-03 source index contains the exact locked AMD64 image.')
elif a.action == 'check':
    if a.env_file is None:
        raise SystemExit('--env-file required')
    result = subprocess.run(['docker', 'compose', '--env-file', str(a.env_file),
                             '-f', str(BASE / 'compose.yaml'), 'config', '--quiet'])
    raise SystemExit(result.returncode)
else:
    contract = verify_guest()
    daemon = verify_docker()
    if a.data_dir is None or not a.data_dir.is_absolute():
        raise SystemExit('Absolute --data-dir required')
    if a.storage_mode:
        contract['storage'] = {'mode': a.storage_mode, 'data_path': str(a.data_dir),
                               'mountpoint': a.mountpoint, 'filesystem_uuid': a.filesystem_uuid}
    verify_storage(contract, daemon, data_path=a.data_dir)
    if a.data_dir.exists() and any(a.data_dir.iterdir()):
        raise SystemExit('Target data directory is not empty; refusing to change ownership')
    a.data_dir.mkdir(parents=True, exist_ok=True, mode=0o750)
    os.chown(a.data_dir, 200, 200)
    os.chmod(a.data_dir, 0o750)
    (BASE / 'assignment.json').write_text(json.dumps(contract, indent=2) + '\n')
    print('Empty assigned target Nexus data directory initialized for UID/GID 200.')
