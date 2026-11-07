#!/usr/bin/env python3
"""Cold backup only; refuses while the source Nexus is running. Does not stop it."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
from zoneinfo import ZoneInfo
from source_guard import verify_source

p = argparse.ArgumentParser()
p.add_argument('--output', type=Path, required=True)
p.add_argument('--confirm-quiesced', action='store_true')
a = p.parse_args()
if not a.confirm_quiesced:
    raise SystemExit('Requires approved Nexus write-free window and --confirm-quiesced')
observed_source = verify_source()
r = subprocess.run(['docker', 'inspect', 'nexus3'], capture_output=True, text=True)
if r.returncode:
    raise SystemExit('Source Nexus not found')
s = json.loads(r.stdout)[0]
if s['State']['Running']:
    raise SystemExit('Source Nexus is running; schedule its controlled shutdown first')
mounts = [m for m in s['Mounts'] if m['Destination'] == '/nexus-data' and m['Type'] == 'bind']
if len(mounts) != 1:
    raise SystemExit('Source mount differs from reviewed plan')
if a.output.exists():
    raise SystemExit('Output already exists; refusing to mix snapshots')
a.output.mkdir(parents=True, mode=0o700)
os.chmod(a.output, 0o700)
archive = a.output / 'nexus-data.tar'
fd = os.open(archive, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(fd, 'wb') as file:
    r = subprocess.run(['docker', 'run', '--rm', '--network', 'none', '--read-only',
                        '--mount', 'type=bind,src=' + mounts[0]['Source'] + ',dst=/data,readonly',
                        '--entrypoint', 'tar', s['Image'], '-C', '/data', '-cf', '-', '.'],
                       stdout=file, stderr=subprocess.PIPE)
if r.returncode:
    raise SystemExit('Cold archive failed; partial archive retained privately')
with archive.open('rb') as file:
    digest = hashlib.file_digest(file, 'sha256').hexdigest()
receipt = {'captured_at': datetime.datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),
           'source_version': observed_source['containers']['nexus3']['versions']['version'],
           'verified_source': observed_source, 'source_image_id': s['Image'],
           'archive': archive.name, 'sha256': digest, 'source_stopped': True}
p = a.output / 'snapshot.json'
p.write_text(json.dumps(receipt, indent=2) + '\n')
p.chmod(0o600)
print('Nexus cold snapshot created privately; this script did not modify source services.')
