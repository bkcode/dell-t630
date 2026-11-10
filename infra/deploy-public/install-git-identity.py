#!/usr/bin/env python3
"""Install only the caller-designated deploy-public read key on owned VM220."""
import hmac
import json
import os
from pathlib import Path
import pwd
import socket
import sys

if os.geteuid() != 0 or socket.gethostname() != 'publish-service':
    raise SystemExit('assigned-publisher-only')
os.umask(0o077)
account = pwd.getpwnam('ub')
ssh = Path(account.pw_dir) / '.ssh'
if ssh.resolve() != ssh or ssh.stat().st_uid != account.pw_uid or ssh.stat().st_mode & 0o077:
    raise SystemExit('private-owned-SSH-directory-required')
for path in [ssh / 'deploy-keys', ssh / 'deploy-keys/bkcode']:
    if not path.exists():
        path.mkdir(mode=0o700)
        os.chown(path, account.pw_uid, account.pw_gid)
    if path.resolve() != path or path.stat().st_uid != account.pw_uid or path.stat().st_mode & 0o077:
        raise SystemExit('private-owned-key-directory-required')
root = ssh / 'deploy-keys/bkcode'
payload = json.load(sys.stdin)
if set(payload) != {'private', 'public', 'known_hosts', 'config'}:
    raise SystemExit('exact-designated-input-required')
files = {'deploy-public_ed25519': payload['private'], 'deploy-public_ed25519.pub': payload['public'],
         'deploy-public_known_hosts': payload['known_hosts'], 'deploy-public.conf': payload['config']}
for name, body in files.items():
    path = root / name
    raw = body.encode()
    if path.exists():
        if path.is_symlink() or path.stat().st_uid != account.pw_uid or path.stat().st_mode & 0o777 != 0o600:
            raise SystemExit('existing-designated-file-requires-review')
        if not hmac.compare_digest(path.read_bytes(), raw):
            raise SystemExit('existing-designated-content-differs')
        continue
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    os.fchown(fd, account.pw_uid, account.pw_gid)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
print(json.dumps({'repo': 'bkcode/deploy-public', 'designated_readonly_DeployKey_installed': True,
    'identity_path': str(root / 'deploy-public_ed25519'), 'private_file_mode': '0600',
    'key_directory_mode': '0700', 'trusted_GitHub_host_key_reused_from_verified_Mac': True,
    'original_publisher_key_read_or_exported': False, 'credential_values_output': False}))
