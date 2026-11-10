#!/usr/bin/env python3
"""Install only the five pre-authorized Puyu backend read identities on VM220."""
import hmac
import json
import os
from pathlib import Path
import pwd
import socket
import sys

NAMES = ['puyu-auth', 'puyu-gateway', 'puyu-bff-web', 'puyu-service-core', 'puyu-common-lib']
assert os.geteuid() == 0 and socket.gethostname() == 'publish-service'
os.umask(0o077)
a = pwd.getpwnam('ub')
root = Path(a.pw_dir) / '.ssh/deploy-keys/bkcode'
assert root.resolve() == root and root.stat().st_uid == a.pw_uid and root.stat().st_mode & 0o077 == 0
payload = json.load(sys.stdin)
assert set(payload) == {'keys', 'config'} and set(payload['keys']) == set(NAMES)

def write_designated(path, raw):
    raw = raw.encode()
    if path.exists():
        assert not path.is_symlink() and path.stat().st_uid == a.pw_uid and path.stat().st_mode & 0o777 == 0o600
        assert hmac.compare_digest(path.read_bytes(), raw), 'existing-designated-file-differs'
        return
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    os.fchown(fd, a.pw_uid, a.pw_gid)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())

for name in NAMES:
    value = payload['keys'][name]
    assert set(value) == {'private', 'public'}
    write_designated(root / (name + '_ed25519'), value['private'])
    write_designated(root / (name + '_ed25519.pub'), value['public'])
write_designated(root / 'puyu-backends.conf', payload['config'])
write_designated(root / 'all-repos.conf', 'Include ' + str(root / 'deploy-public.conf') + '\nInclude ' + str(root / 'puyu-backends.conf') + '\n')
write_designated(Path(a.pw_dir) / '.ssh/config', 'Include ' + str(root / 'all-repos.conf') + '\n')
print(json.dumps({'backend_repo_identities_installed': NAMES, 'only_designated_Git_credentials_used': True,
                  'private_file_mode': '0600', 'original_publisher_private_key_read_or_exported': False,
                  'GitHub_host_verification': 'strict-existing-trust', 'credential_values_output': False}))
