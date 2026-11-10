#!/usr/bin/env python3
"""Add the explicitly registered bff-admin read identity; no application build/start."""
import hmac
import json
import os
from pathlib import Path
import pwd
import socket
import subprocess
import sys

assert os.geteuid() == 0 and socket.gethostname() == 'publish-service'
os.umask(0o077)
account = pwd.getpwnam('ub')
base = Path(account.pw_dir) / '.ssh/deploy-keys/bkcode'
assert base.resolve() == base and base.stat().st_uid == account.pw_uid
payload = json.load(sys.stdin)
assert set(payload) == {'private', 'public', 'block'}
for filename, value in [('puyu-bff-admin_ed25519', payload['private']),
                         ('puyu-bff-admin_ed25519.pub', payload['public'])]:
    path = base / filename
    if path.exists():
        assert not path.is_symlink() and path.stat().st_uid == account.pw_uid
        assert path.stat().st_mode & 0o777 == 0o600 and hmac.compare_digest(path.read_bytes(), value.encode())
    else:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        os.fchown(fd, account.pw_uid, account.pw_gid)
        with os.fdopen(fd, 'w') as stream:
            stream.write(value)
config = base / 'puyu-backends.conf'
assert not config.is_symlink() and config.stat().st_uid == account.pw_uid and config.stat().st_mode & 0o777 == 0o600
old = config.read_text()
if 'Host github-bkcode-puyu-bff-admin\n' not in old:
    temporary = config.with_name(config.name + '.bff-admin-tmp')
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    os.fchown(fd, account.pw_uid, account.pw_gid)
    with os.fdopen(fd, 'w') as stream:
        stream.write(old + '\n' + payload['block'])
    os.replace(temporary, config)
ssh = '/usr/bin/ssh -F /home/ub/.ssh/deploy-keys/bkcode/all-repos.conf'
repo = Path('/srv/dell-build/deploy-public/repos/puyu-bff-admin')

def user(args):
    p = subprocess.run(['runuser', '-u', 'ub', '--', *map(str, args)], capture_output=True, timeout=150)
    assert p.returncode == 0, 'bff-admin-Git-read-failed'
    return p.stdout.decode().strip()

url = 'git@github-bkcode-puyu-bff-admin:bkcode/puyu-bff-admin.git'
head = user(['git', '-c', 'core.sshCommand=' + ssh, 'ls-remote', url, 'refs/heads/main']).split()[0]
if not repo.exists():
    user(['git', '-c', 'core.sshCommand=' + ssh, 'clone', '--branch', 'main', '--single-branch', url, repo])
assert user(['git', '-C', repo, 'rev-parse', 'HEAD']) == head
assert not user(['git', '-C', repo, 'status', '--porcelain'])
user(['git', '-C', repo, 'config', 'core.sshCommand', ssh])
user(['git', '-C', repo, 'config', 'remote.origin.pushurl', 'no-push://disabled'])
print(json.dumps({'repository': 'bkcode/puyu-bff-admin', 'Git_HEAD': head, 'source_path': str(repo),
                  'source_clean': True, 'designated_identity_installed': True,
                  'private_file_mode': '0600', 'server_push_URL_disabled': True,
                  'no_business_build_or_start': True, 'credential_values_output': False}))
