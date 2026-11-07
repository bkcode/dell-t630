#!/usr/bin/env python3
"""Restore a cold Nexus archive only into an empty Linux AMD64 target directory."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import subprocess
import tarfile
from target_guard import verify_target

p = argparse.ArgumentParser()
p.add_argument('--snapshot', type=Path, required=True)
p.add_argument('--data-dir', type=Path, required=True)
p.add_argument('--confirm-empty-target', action='store_true')
a = p.parse_args()
if not a.confirm_empty_target or platform.system() != 'Linux' or platform.machine() != 'x86_64' or os.geteuid() != 0:
    raise SystemExit('Requires root on Linux AMD64 target and --confirm-empty-target')
verify_target(data_path=a.data_dir)
snapshot = a.snapshot.resolve()
receipt = json.loads((snapshot / 'snapshot.json').read_text())
if receipt['source_version'] != '3.84.0-03' or receipt['archive'] != 'nexus-data.tar' or not receipt['source_stopped']:
    raise SystemExit('Snapshot is not the reviewed cold source version')
archive = snapshot / 'nexus-data.tar'
with archive.open('rb') as file:
    if hashlib.file_digest(file, 'sha256').hexdigest() != receipt['sha256']:
        raise SystemExit('Archive checksum mismatch')
with tarfile.open(archive) as tar:
    for member in tar:
        paths = [member.name] + ([member.linkname] if member.issym() or member.islnk() else [])
        if any(PurePosixPath(x).is_absolute() or '..' in PurePosixPath(x).parts for x in paths):
            raise SystemExit('Unsafe archive path')
        if member.isdev() or member.isfifo():
            raise SystemExit('Unexpected special file in Nexus snapshot')
if not a.data_dir.is_absolute() or not a.data_dir.is_dir() or any(a.data_dir.iterdir()):
    raise SystemExit('Target must be an existing empty absolute directory')
proc = subprocess.run(['tar', '--no-same-owner', '-xf', str(archive), '-C', str(a.data_dir)], capture_output=True)
if proc.returncode:
    raise SystemExit('Target extraction failed; partial target retained for inspection')
for root, dirs, files in os.walk(a.data_dir):
    os.chown(root, 200, 200)
    for name in dirs + files:
        os.chown(Path(root) / name, 200, 200, follow_symlinks=False)
marker = Path(__file__).resolve().parent / 'restore-complete.json'
marker.write_text(json.dumps({'source': receipt, 'functional_acceptance': 'pending'}, indent=2) + '\n')
marker.chmod(0o600)
print('Cold Nexus data restored for UID/GID 200; start the pinned image and validate repositories before cutover.')
