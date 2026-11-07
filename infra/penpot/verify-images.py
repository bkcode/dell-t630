#!/usr/bin/env python3
"""Read registry manifests only; no pull, build or publishing."""
import hashlib
import json
from pathlib import Path
import subprocess

base = Path(__file__).resolve().parent
lock = json.loads((base / 'images.lock.json').read_text())
for role, info in lock['images'].items():
    p = subprocess.run(['docker', 'buildx', 'imagetools', 'inspect', '--raw', info['source_index']],
                       capture_output=True, text=True, timeout=60)
    if p.returncode:
        raise SystemExit('Registry inspection failed for ' + role)
    data = json.loads(p.stdout)
    expected = info['target'].split('@', 1)[1]
    candidates = [m['digest'] for m in data.get('manifests', [])
                  if m.get('platform', {}).get('os') == 'linux'
                  and m.get('platform', {}).get('architecture') == 'amd64']
    if expected not in candidates:
        raise SystemExit('AMD64 digest mismatch: ' + role)
    print(role + ': source index contains the locked AMD64 manifest')
