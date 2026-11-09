#!/usr/bin/env python3
"""Fixed public FileBrowser Quantum v2.1.4-beta renderer. No install/network actions."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
BINARY = '/opt/dell/filebrowser/releases/v2.1.4-beta/filebrowser'
BINARY_SHA256 = '4af557de16603bdfba2ae87b7807b8654612c542b2deff826eedee72086a5da2'
STATE = '/var/lib/dell-filebrowser'
CONFIG_PATH = '/etc/dell-filebrowser/config.yaml'
CREDENTIALS = '/run/credentials/dell-filebrowser.service'


def config():
    return {
        'http': {'listen': '192.168.19.80', 'port': 8080, 'baseURL': '/',
                 'tlsCert': '/etc/dell-filebrowser/tls.crt',
                 'tlsKey': '${CREDENTIALS_DIRECTORY}/tls-key',
                 'disableWebDAV': True, 'trustProxyHeaders': False},
        'server': {
            'database': {'path': STATE + '/database.sqlite'},
            'cacheDir': STATE + '/cache', 'disableUpdateCheck': True,
            'numImageProcessors': 1,
            'filesystem': {'createFilePermission': '660', 'createDirectoryPermission': '2770'},
            'logging': [{'levels': 'warning|error', 'apiLevels': '', 'apiFilter': '^/', 'output': 'stdout', 'noColors': True, 'json': True}],
            'sources': [{'path': '/srv/resources', 'name': 'resources', 'config': {
                'private': True, 'readOnly': False, 'defaultEnabled': True,
                'defaultUserScope': '/', 'createUserDir': False,
                'defaultPermissions': {'view': True, 'download': True, 'create': True,
                                       'modify': False, 'delete': False, 'configured': True},
                'rules': [{'folderPath': '/lost+found'}, {'folderPath': '/', 'ignoreSymlinks': True}],
            }}],
        },
        'auth': {'key': '${DELL_FB_JWT_KEY}', 'methods': {
            'noauth': False,
            'password': {'enabled': True, 'signup': False, 'minLength': 16, 'adminUsername': 'admin'},
            **{method: {'enabled': False} for method in ['passkey', 'proxy', 'oidc', 'ldap', 'jwt']},
        }},
        'userDefaults': {'account': {'permissions': {'admin': False, 'api': False, 'share': False, 'realtime': False}}},
    }


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False)


def validate_config(value):
    # JSON comparison preserves bool/int types, unlike Python's True == 1.
    if canonical(value) != canonical(config()):
        raise ValueError('exact-public-configuration-required')


def validate_lock(value):
    asset = value.get('asset', {})
    if (value.get('project') != 'gtsteffaniak/filebrowser' or value.get('tag') != 'v2.1.4-beta'
            or asset.get('name') != 'linux-amd64-filebrowser'
            or asset.get('url') != 'https://github.com/gtsteffaniak/filebrowser/releases/download/v2.1.4-beta/linux-amd64-filebrowser'
            or asset.get('digest') != 'sha256:' + BINARY_SHA256 or asset.get('size') != 29064968
            or value.get('native_install') is not True or value.get('automatic_upgrades') is not False):
        raise ValueError('exact-native-upstream-lock-required')


def input_nft():
    return '''table inet dell_filebrowser_input {
 chain input {
  type filter hook input priority -6; policy accept;
  tcp dport 8080 ct state invalid counter drop
  iifname "lo" tcp dport 8080 accept
  ip saddr { 192.168.21.0/24, 10.66.66.0/24, 192.168.19.80 } tcp dport 8080 counter accept
  tcp dport 8080 counter drop
  udp dport 8080 counter drop
 }
}
'''


def launch_source(config_text):
    return '''#!/usr/bin/env python3
"""Native launch adapter: secret files to process environment, never argv/logs."""
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import stat
import struct
import sys

BINARY = ''' + repr(BINARY) + '''
BINARY_SHA256 = ''' + repr(BINARY_SHA256) + '''
CONFIG = Path(''' + repr(CONFIG_PATH) + ''')
EXPECTED_CONFIG = ''' + repr(config_text.encode()) + '''
CREDS = Path(''' + repr(CREDENTIALS) + ''')
STATE = Path(''' + repr(STATE) + ''')
MARKER = Path('/etc/dell-filebrowser/bootstrap.complete')


def trusted_file(path, maximum, mode=None):
    for item in [path, *path.parents]:
        st = item.lstat()
        if stat.S_ISLNK(st.st_mode) or st.st_uid != 0 or st.st_mode & 0o022:
            raise ValueError('untrusted-public-path')
    st = path.stat()
    if not stat.S_ISREG(st.st_mode) or st.st_nlink != 1 or st.st_size > maximum:
        raise ValueError('invalid-public-file')
    if mode is not None and stat.S_IMODE(st.st_mode) != mode:
        raise ValueError('public-file-mode-mismatch')
    return path.read_bytes()


def readonly_systemd_acl(data, directory=False):
    # Linux POSIX ACL xattr: version2 then canonical little-endian <HHI> entries.
    # Accept exactly owner + named UID2000 + empty owning group + mask + empty other.
    if not isinstance(data, bytes) or len(data) != 44:
        return False
    try:
        version, = struct.unpack('<I', data[:4])
        entries = [struct.unpack('<HHI', data[offset:offset + 8]) for offset in range(4, 44, 8)]
    except struct.error:
        return False
    permission = 5 if directory else 4
    undefined = 0xffffffff
    expected = [(1, permission, undefined), (2, permission, 2000),
                (4, 0, undefined), (16, permission, undefined), (32, 0, undefined)]
    return version == 2 and entries == expected


def credential_access_allowed(uid, gid, mode, acl_data=None, directory=False):
    # Preserve the original owner-only branch exactly; no broad group-read exception.
    if uid in (0, 2000) and mode & 0o077 == 0:
        return True
    expected_mode = 0o550 if directory else 0o440
    return (uid == 0 and gid == 0 and stat.S_IMODE(mode) == expected_mode
            and readonly_systemd_acl(acl_data, directory))


def credential_access(st, fd, directory=False):
    acl_data = None
    if st.st_mode & 0o077:
        try:
            acl_data = os.getxattr(fd, 'system.posix_acl_access')
        except OSError:
            return False
    return credential_access_allowed(st.st_uid, st.st_gid, st.st_mode, acl_data, directory)


def credential(name):
    if name not in ('jwt-key', 'admin-password', 'tls-key'):
        raise ValueError('unknown-credential')
    if os.environ.get('CREDENTIALS_DIRECTORY') != str(CREDS):
        raise ValueError('fixed-credentials-directory-required')
    directory_fd = os.open(CREDS, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        st = os.fstat(directory_fd)
        if not stat.S_ISDIR(st.st_mode) or not credential_access(st, directory_fd, directory=True):
            raise ValueError('invalid-credential-directory')
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=directory_fd)
        try:
            st = os.fstat(fd)
            maximum = 65536 if name == 'tls-key' else 4096
            if (not stat.S_ISREG(st.st_mode) or st.st_nlink != 1
                    or not credential_access(st, fd) or st.st_size < 1 or st.st_size > maximum):
                raise ValueError('invalid-credential-file')
            data = os.read(fd, maximum + 1)
            if len(data) > maximum:
                raise ValueError('credential-too-large')
            return data
        finally:
            os.close(fd)
    finally:
        os.close(directory_fd)


def environment(bootstrap_complete, reader):
    # Build a fresh whitelist: inherited FILEBROWSER_* overrides never reach the app.
    jwt = reader('jwt-key').rstrip(b'\\n')
    if not re.fullmatch(rb'[A-Za-z0-9_+=/-]{32,512}', jwt):
        raise ValueError('invalid-JWT-credential-format')
    tls = reader('tls-key')
    if b'PRIVATE KEY-----' not in tls or len(tls) > 65536:
        raise ValueError('invalid-TLS-credential-format')
    env = {'PATH': '/usr/sbin:/usr/bin:/sbin:/bin', 'LANG': 'C.UTF-8',
           'HOME': str(STATE), 'CREDENTIALS_DIRECTORY': str(CREDS),
           'DELL_FB_JWT_KEY': jwt.decode('ascii'), 'FILEBROWSER_DISABLE_AUTOMATIC_BACKUP': 'true'}
    if not bootstrap_complete:
        password = reader('admin-password').rstrip(b'\\n').decode('utf-8')
        if len(password) < 16 or len(password.encode()) > 4096 or any(ord(c) < 32 or ord(c) == 127 for c in password):
            raise ValueError('invalid-bootstrap-password-format')
        env['FILEBROWSER_ADMIN_PASSWORD'] = password
    else:
        env.pop('FILEBROWSER_ADMIN_PASSWORD', None)
    return env


def bootstrapped():
    st = STATE.lstat()
    if not stat.S_ISDIR(st.st_mode) or st.st_uid != 2000 or st.st_gid != 2980 or stat.S_IMODE(st.st_mode) != 0o700:
        raise ValueError('private-state-identity-required')
    for item in [MARKER.parent, *MARKER.parent.parents]:
        st = item.lstat()
        if not stat.S_ISDIR(st.st_mode) or st.st_uid != 0 or st.st_mode & 0o022:
            raise ValueError('untrusted-bootstrap-parent')
    if MARKER.is_symlink():
        raise ValueError('symlink-bootstrap-marker')
    if not MARKER.exists():
        return False
    trusted_file(MARKER, 1024, 0o644)
    return True


def main():
    if os.geteuid() != 2000 or os.getegid() != 2980 or socket.gethostname() != 'resource-service' or Path('/etc/pve').exists():
        raise ValueError('fixed-guest-service-identity-required')
    actual = trusted_file(CONFIG, 32768, 0o644)
    if actual != EXPECTED_CONFIG:
        raise ValueError('public-configuration-drift')
    binary = trusted_file(Path(BINARY), 29064968, 0o755)
    if len(binary) != 29064968 or hashlib.sha256(binary).hexdigest() != BINARY_SHA256:
        raise ValueError('binary-integrity-mismatch')
    env = environment(bootstrapped(), credential)
    os.umask(0o002)
    os.execve(BINARY, [BINARY, '--no-input', '-c', str(CONFIG)], env)


def failure_summary(exc):
    message = str(exc)
    code = message if re.fullmatch(r'[a-zA-Z0-9-]{1,80}', message) else 'withheld'
    name = type(exc).__name__
    exception_class = name if re.fullmatch(r'[a-zA-Z0-9_]{1,80}', name) else 'withheld'
    return {'error': 'dell-filebrowser-launch-failed', 'failure_code': code, 'exception_class': exception_class}


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(json.dumps(failure_summary(exc)), file=sys.stderr)
        raise SystemExit(1) from None
'''


def firewall_source(nft):
    return '''#!/usr/bin/env python3
"""Replace only owned FileBrowser input table in a single nft transaction."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import socket
import stat
import subprocess

TABLE = 'dell_filebrowser_input'
INPUT = Path('/etc/dell-filebrowser/input.nft')
EXPECTED = ''' + repr(nft.encode()) + '''


def run(args, data=None):
    result = subprocess.run(args, input=data, capture_output=True, timeout=10)
    if result.returncode != 0:
        raise ValueError('native-command-failed')
    return result.stdout


def validate_input(actual):
    if actual != EXPECTED:
        raise ValueError('fixed-input-policy-required')


def transaction(tables):
    own = [row['table'] for row in tables.get('nftables', []) if 'table' in row and row['table'].get('family') == 'inet' and row['table'].get('name') == TABLE]
    if len(own) > 1:
        raise ValueError('ambiguous-owned-table')
    prefix = ('delete table inet ' + TABLE + '\\n').encode() if own else b''
    return prefix + EXPECTED


def check_identity():
    if os.geteuid() != 0 or socket.gethostname() != 'resource-service' or Path('/etc/pve').exists():
        raise ValueError('fixed-guest-root-required')
    data = json.loads(run(['/usr/sbin/ip', '-j', '-4', 'address', 'show', 'scope', 'global']))
    ips = [a['local'] for item in data for a in item.get('addr_info', [])]
    if ips != ['192.168.19.80']:
        raise ValueError('fixed-service-IP-required')
    for item in [INPUT, *INPUT.parents]:
        st = item.lstat()
        if stat.S_ISLNK(st.st_mode) or st.st_uid != 0 or st.st_mode & 0o022:
            raise ValueError('untrusted-input-path')
    st = INPUT.stat()
    if not stat.S_ISREG(st.st_mode) or st.st_nlink != 1 or stat.S_IMODE(st.st_mode) != 0o644 or st.st_size > 8192:
        raise ValueError('invalid-input-file')
    validate_input(INPUT.read_bytes())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    check_identity()
    fd = os.open('/run/dell-filebrowser-firewall.lock', os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'r+b') as lock:
        st = os.fstat(lock.fileno())
        if not stat.S_ISREG(st.st_mode) or st.st_uid != 0 or st.st_nlink != 1 or stat.S_IMODE(st.st_mode) != 0o600:
            raise ValueError('untrusted-firewall-lock')
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        tables = json.loads(run(['/usr/sbin/nft', '--json', 'list', 'tables']))
        payload = transaction(tables)
        run(['/usr/sbin/nft', '--check', '--file', '-'], payload)
        if not args.check:
            run(['/usr/sbin/nft', '--file', '-'], payload)
        print(json.dumps({'status': 'checked' if args.check else 'applied', 'owned_table': TABLE, 'other_tables_changed': False}))


if __name__ == '__main__':
    try:
        main()
    except Exception:
        raise SystemExit('dell-filebrowser-firewall-failed') from None
'''


def render():
    validate_lock(json.loads((HERE / 'upstream.lock.json').read_text()))
    public = config()
    validate_config(public)
    # JSON is a strict YAML subset; no third-party YAML dependency or secret interpolation here.
    yaml = json.dumps(public, ensure_ascii=False, indent=2) + '\n'
    nft = input_nft()
    return {
        'config.yaml': yaml,
        'dell-filebrowser.service': '''[Unit]
Description=Dell FileBrowser Quantum resource administration
Wants=network-online.target
Requires=srv-resources.mount dell-filebrowser-firewall.service
After=network-online.target srv-resources.mount dell-filebrowser-firewall.service
BindsTo=srv-resources.mount dell-filebrowser-firewall.service
RequiresMountsFor=/srv/resources
StartLimitIntervalSec=300
StartLimitBurst=3

[Service]
Type=simple
User=filebrowser
Group=resources
WorkingDirectory=/var/lib/dell-filebrowser
UMask=0002
LoadCredential=jwt-key:/etc/dell-filebrowser/secrets/jwt-key
LoadCredential=admin-password:/etc/dell-filebrowser/secrets/admin-password
LoadCredential=tls-key:/etc/dell-filebrowser/secrets/tls-key
ExecStartPre=+/usr/bin/python3 -I -B /opt/dell/resources/guard.py --role server
ExecStart=/usr/bin/python3 -I -B /opt/dell/filebrowser/launch.py
Restart=on-failure
RestartSec=5
NoNewPrivileges=yes
ProtectSystem=strict
ProtectHome=yes
PrivateTmp=yes
ReadWritePaths=/srv/resources /var/lib/dell-filebrowser
CPUQuota=100%
MemoryMax=384M
TasksMax=64
LimitNOFILE=1024
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
''',
        'dell-filebrowser-firewall.service': '''[Unit]
Description=Dell FileBrowser administration input allowlist
Before=dell-filebrowser.service

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStartPre=/usr/bin/python3 -I -B /opt/dell/filebrowser/firewall.py --check
ExecStart=/usr/bin/python3 -I -B /opt/dell/filebrowser/firewall.py
# No ExecStop: stopping the application must not remove protective input filtering.

[Install]
WantedBy=multi-user.target
''',
        'firewall.py': firewall_source(nft),
        'launch.py': launch_source(yaml),
        'input.nft': nft,
    }


def manifest():
    return {'schema_version': 1, 'status': 'prepared-not-installed', 'binary': BINARY,
            'binary_sha256': BINARY_SHA256,
            'files_sha256': {key: hashlib.sha256(value.encode()).hexdigest() for key, value in render().items()},
            'includes_secrets': False, 'remote_actions': False}


if __name__ == '__main__':
    print(json.dumps(manifest(), indent=2))
