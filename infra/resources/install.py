#!/usr/bin/env python3
"""Guest-only fixed-path installation. Defaults to preparation, never starts Java/HTTP."""
import argparse
import fcntl
import grp
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import pwd
import re
import socket
import stat
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
STATE = Path('/var/lib/dell-resources/install-state.json')


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


prepare = module('resource_install_prepare', 'prepare.py')
guard = module('resource_install_guard', 'guard.py')


def run(args, accepted=(0,), timeout=30):
    result = subprocess.run(args, capture_output=True, timeout=timeout)
    if result.returncode not in accepted:
        raise ValueError('native-command-failed')
    return result


def digest(data):
    return hashlib.sha256(data).hexdigest()


def safe_path(path, regular=False):
    for item in [path, *path.parents]:
        try:
            st = item.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(st.st_mode) or st.st_uid != 0 or st.st_mode & 0o022:
            raise ValueError('untrusted-install-path')
        if item == path and regular and (not stat.S_ISREG(st.st_mode) or st.st_nlink != 1):
            raise ValueError('not-single-regular-file')


def policy_file(path):
    safe_path(path, regular=True)
    st = path.stat()
    if stat.S_IMODE(st.st_mode) != 0o600 or st.st_size > 8192:
        raise ValueError('policy-must-be-root600')
    value = json.loads(path.read_text())
    prepare.validate(value)
    return value


def atomic(path, data, mode):
    safe_path(path, regular=path.exists())
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o755)
    safe_path(path.parent)
    fd, temporary = tempfile.mkstemp(prefix='.resources-', dir=path.parent)
    try:
        os.fchmod(fd, mode)
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def file_map(files, role):
    server = {
        'policy.json': ('/etc/dell-resources/policy.json', 0o600),
        'dell-resources.exports': ('/etc/exports.d/dell-resources.exports', 0o644),
        '90-dell-resources.conf': ('/etc/nfs.conf.d/90-dell-resources.conf', 0o644),
        'srv-resources.mount': ('/etc/systemd/system/srv-resources.mount', 0o644),
        'nfs-server.service.d/50-dell-resources.conf': ('/etc/systemd/system/nfs-server.service.d/50-dell-resources.conf', 0o644),
        'dell-resources-input.nft': ('/etc/dell-resources/input.nft', 0o644),
        'dell-resources-firewall.service': ('/etc/systemd/system/dell-resources-firewall.service', 0o644),
        'apply-firewall.py': ('/opt/dell/resources/apply-firewall.py', 0o644),
    }
    client = {'policy.json': ('/etc/dell-resources/policy.json', 0o600),
              'mnt-resources.mount': ('/etc/systemd/system/mnt-resources.mount', 0o644),
              'mnt-resources.automount': ('/etc/systemd/system/mnt-resources.automount', 0o644)}
    if role not in ('server', 'client-230', 'client-240'):
        raise ValueError('exact-role-required')
    prefix = role + '/'
    allowed = server if role == 'server' else client
    result = {}
    for key, value in files.items():
        if not key.startswith(prefix):
            continue
        suffix = key[len(prefix):]
        if suffix == 'future-java-resource-dependency.conf' and role != 'server':
            continue  # Deliberately never install Java unit changes.
        if suffix not in allowed or not isinstance(value, str):
            raise ValueError('unknown-rendered-install-key')
        path, mode = allowed[suffix]
        result[Path(path)] = (value.encode(), mode)
    required = set(server) - {'apply-firewall.py'} if role == 'server' else set(client)
    if not required.issubset({key[len(prefix):] for key in files if key.startswith(prefix)}):
        raise ValueError('required-template-missing')
    for name in ['prepare.py', 'guard.py', 'policy.example.json']:
        source = HERE / name
        safe_path(source, regular=True)
        result[Path('/opt/dell/resources') / name] = (source.read_bytes(), 0o644)
    return result


def check_fstab(text, data_uuid):
    rows = [line.split() for line in text.splitlines() if line.strip() and not line.lstrip().startswith('#')]
    matches = [row for row in rows if len(row) >= 2 and row[1] == '/srv/resources']
    if len(matches) != 1:
        raise ValueError('one-bootstrap-fstab-mount-required')
    row = matches[0]
    if len(row) != 6 or row[0] != 'UUID=' + data_uuid or row[2] != 'ext4' or not {'nodev', 'nosuid', 'noexec'} <= set(row[3].split(',')):
        raise ValueError('fstab-UUID-or-options-mismatch')
    if any(row is not matches[0] and row[0] in ('UUID=' + data_uuid, '/srv/resources') for row in rows):
        raise ValueError('data-UUID-used-by-another-fstab-mount')


def group_conflict(by_name, by_gid):
    if by_name is not None and by_name != ('resources', 2980):
        raise ValueError('resource-group-name-conflict')
    if by_gid is not None and by_gid != ('resources', 2980):
        raise ValueError('resource-group-GID-conflict')
    if (by_name is None) != (by_gid is None):
        raise ValueError('inconsistent-group-database')


def lookup_group(key):
    try:
        value = grp.getgrgid(key) if isinstance(key, int) else grp.getgrnam(key)
        return value.gr_name, value.gr_gid
    except KeyError:
        return None


def mount_row(path, allow_autofs_only=False):
    result = run(['/usr/bin/findmnt', '--json', '--mountpoint', str(path), '--output', 'TARGET,SOURCE,FSTYPE,OPTIONS,UUID'], accepted=(0, 1))
    if result.returncode == 1:
        return None
    rows = json.loads(result.stdout)['filesystems']
    return guard.select_mount(rows, str(path), allow_autofs_only=allow_autofs_only)


def native_identity(policy, role):
    if os.geteuid() != 0 or Path('/etc/pve').exists():
        raise ValueError('guest-root-only')
    osrelease = Path('/etc/os-release').read_text()
    if not re.search(r'^ID=[\"\']?debian[\"\']?$', osrelease, re.M) or not re.search(r'^VERSION_ID=[\"\']?13[\"\']?$', osrelease, re.M):
        raise ValueError('Debian13-required')
    identity = policy['server'] if role == 'server' else next(x for x in policy['clients'] if role == 'client-' + str(x['vmid']))
    if socket.gethostname() != identity['hostname']:
        raise ValueError('wrong-role-hostname')
    addresses = json.loads(run(['/usr/sbin/ip', '-j', '-4', 'address', 'show', 'scope', 'global']).stdout)
    ips = [a['local'] for item in addresses for a in item.get('addr_info', [])]
    if ips != [identity['ip']]:
        raise ValueError('wrong-or-additional-global-IP')
    group_conflict(lookup_group('resources'), lookup_group(2980))
    if role != 'server':
        finger = pwd.getpwnam('finger')
        if (finger.pw_uid, finger.pw_gid) != (999, 989):
            raise ValueError('finger-primary-identity-mismatch')


def old_state(role, policy):
    if not STATE.exists():
        return {'files': {}}
    safe_path(STATE, regular=True)
    if stat.S_IMODE(STATE.stat().st_mode) != 0o600 or STATE.stat().st_size > 32768:
        raise ValueError('untrusted-install-state')
    value = json.loads(STATE.read_text())
    if value.get('role') != role or value.get('data_uuid') != policy['server']['data_uuid'] or not isinstance(value.get('files'), dict):
        raise ValueError('other-role-install-state')
    return value


def check_targets(targets, previous):
    changed = []
    for path, (data, _) in targets.items():
        safe_path(path, regular=path.exists())
        if not path.exists():
            changed.append(path)
            continue
        actual = path.read_bytes()
        if actual != data:
            if previous['files'].get(str(path)) != digest(actual):
                raise ValueError('foreign-or-drifted-config-refuse-overwrite')
            changed.append(path)
    return changed


def server_preflight(policy, targets):
    row = mount_row(Path('/srv/resources'))
    guard.check_mount(policy, 'server', row or {}, socket.gethostname(), ('resources', 2980))
    check_fstab(Path('/etc/fstab').read_text(), policy['server']['data_uuid'])
    if Path('/srv/resources').is_symlink():
        raise ValueError('symlink-data-root')
    for path in [Path('/etc/exports'), *Path('/etc/exports.d').glob('*')]:
        if path == Path('/etc/exports.d/dell-resources.exports'):
            continue
        if path.exists():
            safe_path(path, regular=True)
            if any(line.strip() and not line.lstrip().startswith('#') for line in path.read_text().splitlines()):
                raise ValueError('foreign-NFS-export-refused')
    default = Path('/etc/default/nfs-kernel-server')
    if default.exists():
        safe_path(default, regular=True)
        for line in default.read_text().splitlines():
            if re.match(r'^\s*(RPCNFSDOPTS|RPCMOUNTDOPTS)\s*=', line) and line.split('=', 1)[1].strip() not in ('', '""', "''", '"--manage-gids"', "'--manage-gids'"):
                raise ValueError('NFS-command-line-override-requires-review')
    for path in Path('/etc/systemd/system/nfs-server.service.d').glob('*.conf'):
        if path != Path('/etc/systemd/system/nfs-server.service.d/50-dell-resources.conf'):
            raise ValueError('foreign-NFS-unit-override-requires-review')
    listeners = run(['/usr/bin/ss', '-H', '-lntu']).stdout.decode()
    if any(re.search(r':2049\s', line) for line in listeners.splitlines()) and not STATE.exists():
        raise ValueError('existing-NFS-listener-refused')
    for command in ['/usr/bin/setfacl', '/usr/sbin/nfsconf', '/usr/sbin/nft', '/usr/sbin/exportfs']:
        if not Path(command).is_file():
            raise ValueError('required-server-package-missing')


def verify_mountd_groups():
    actual = run(['/usr/sbin/nfsconf', '--get', 'mountd', 'manage-gids']).stdout.decode().strip().lower()
    if actual != 'n':
        raise ValueError('effective-mountd-manage-gids-mismatch')


def client_directory(previous):
    path = Path('/mnt/resources')
    # The mounted data root is intentionally group-writable2770. Trust the
    # local parent first; apply config-path permissions only when not realNFS.
    safe_path(path.parent)
    if path.is_symlink() or path.resolve(strict=False) != path:
        raise ValueError('untrusted-client-mount-path')
    owned_mount = all(key in previous['files'] for key in ('/etc/systemd/system/mnt-resources.mount', '/etc/systemd/system/mnt-resources.automount'))
    row = mount_row(path, allow_autofs_only=owned_mount)
    if row:
        if not owned_mount or row.get('fstype') not in ('autofs', 'nfs4'):
            raise ValueError('existing-client-mount-refused')
        if row['fstype'] == 'nfs4':
            if row.get('source') != '192.168.19.80:/':
                raise ValueError('foreign-client-NFS-mount')
            item = path.stat()
            if item.st_uid != 0 or item.st_gid != 2980 or stat.S_IMODE(item.st_mode) != 0o2770:
                raise ValueError('client-NFS-root-permissions-mismatch')
        else:
            safe_path(path)
        return False
    safe_path(path)
    if path.exists() and (not path.is_dir() or any(path.iterdir())):
        raise ValueError('nonempty-client-directory-refused')
    for line in Path('/etc/fstab').read_text().splitlines():
        if line.strip() and not line.lstrip().startswith('#') and '/mnt/resources' in line.split():
            raise ValueError('preexisting-client-fstab-entry-refused')
    return True


def install(policy, role, activate=False):
    native_identity(policy, role)
    previous = old_state(role, policy)
    targets = file_map(prepare.render(policy), role)
    changed = check_targets(targets, previous)
    if role == 'server':
        server_preflight(policy, targets)
        active = run(['/usr/bin/systemctl', 'is-active', '--quiet', 'nfs-server.service'], accepted=(0, 3, 4)).returncode == 0
        if active and changed:
            raise ValueError('active-NFS-update-needs-separate-window')
    else:
        empty_client = client_directory(previous)
        if not Path('/sbin/mount.nfs').exists() and not Path('/usr/sbin/mount.nfs').exists():
            raise ValueError('nfs-common-not-installed')
    if lookup_group('resources') is None:
        run(['/usr/sbin/groupadd', '--gid', '2980', 'resources'])
    if role != 'server':
        if 2980 not in os.getgrouplist('finger', 989):
            run(['/usr/sbin/usermod', '--append', '--groups', 'resources', 'finger'])
        if empty_client:
            Path('/mnt/resources').mkdir(mode=0o555, exist_ok=True)
            os.chown('/mnt/resources', 0, 0)
            os.chmod('/mnt/resources', 0o555)
    else:
        os.chown('/srv/resources', 0, 2980)
        os.chmod('/srv/resources', 0o2770)
        run(['/usr/bin/setfacl', '-m', 'u::rwx,g::rwx,m::rwx,o::---,d:u::rwx,d:g::rwx,d:m::rwx,d:o::---', '/srv/resources'])
    Path('/etc/dell-resources').mkdir(mode=0o700, exist_ok=True)
    Path('/var/lib/dell-resources').mkdir(mode=0o700, exist_ok=True)
    for path, (data, mode) in targets.items():
        atomic(path, data, mode)
    run(['/usr/bin/systemctl', 'daemon-reload'])
    units = [str(path) for path in targets if str(path).startswith('/etc/systemd/system/') and path.suffix in ('.mount', '.automount', '.service')]
    if role == 'server':
        units.append('nfs-server.service')
    run(['/usr/bin/systemd-analyze', 'verify', *units])
    if role == 'server':
        run(['/usr/bin/python3', '-I', '-B', '/opt/dell/resources/guard.py', '--role', 'server'])
        # Parse configuration without exporting or starting the server.
        for key, expected in [('host', '192.168.19.80'), ('port', '2049'), ('vers3', 'n'), ('vers4', 'y'), ('vers4.0', 'n'), ('vers4.1', 'y'), ('vers4.2', 'n'), ('tcp', 'y'), ('udp', 'n')]:
            actual = run(['/usr/sbin/nfsconf', '--get', 'nfsd', key]).stdout.decode().strip().lower()
            if actual != expected:
                raise ValueError('effective-NFS-config-mismatch')
        verify_mountd_groups()
    new_state = {'schema_version': 1, 'role': role, 'data_uuid': policy['server']['data_uuid'], 'files': {str(path): digest(data) for path, (data, _) in targets.items()}}
    atomic(STATE, (json.dumps(new_state, indent=2) + '\n').encode(), 0o600)
    if activate:
        if role == 'server':
            run(['/usr/bin/systemctl', 'enable', '--now', 'srv-resources.mount', 'dell-resources-firewall.service', 'nfs-server.service'], timeout=60)
            try:
                run(['/usr/bin/systemctl', 'is-active', '--quiet', 'nfs-server.service'])
                versions = {token[1:] for token in Path('/proc/fs/nfsd/versions').read_text().split() if token.startswith('+')}
                if versions != {'4', '4.1'}:
                    raise ValueError('actual-NFS-version-set-mismatch')
            except Exception:
                if not active:
                    run(['/usr/bin/systemctl', 'stop', 'nfs-server.service'])
                raise
        else:
            run(['/usr/bin/systemctl', 'enable', '--now', 'mnt-resources.automount'], timeout=60)
            run(['/usr/bin/systemctl', 'is-active', '--quiet', 'mnt-resources.automount'])
    return {'status': 'activated-NFS-or-automount' if activate else 'configuration-prepared-no-service-start', 'role': role, 'installed_files': len(targets), 'Java_or_HTTP_started': False, 'packages_installed': False, 'existing_artifact_mount_changed': False}


def self_test():
    """Offline only; replaces path trust checks for the developer-owned checkout."""
    import copy
    import unittest
    from unittest.mock import patch

    class Offline(unittest.TestCase):
        def setUp(self):
            self.policy = copy.deepcopy(prepare.EXAMPLE)
            self.policy['server']['data_uuid'] = 'ea24ad76-517b-43df-a1d0-7c879506bc77'
            self.files = prepare.render(self.policy)

        def mapped(self, role, files=None):
            with patch(__name__ + '.safe_path'):
                return file_map(files or self.files, role)

        def test_server_fixed_destinations_and_no_optional_HTTP(self):
            result = self.mapped('server')
            self.assertIn(Path('/etc/exports.d/dell-resources.exports'), result)
            self.assertIn(Path('/etc/systemd/system/srv-resources.mount'), result)
            self.assertFalse(any('nginx' in str(path) or 'future-java' in str(path) for path in result))

        def test_clients_never_install_Java_or_artifact_mount(self):
            for role in ['client-230', 'client-240']:
                result = self.mapped(role)
                self.assertIn(Path('/etc/systemd/system/mnt-resources.automount'), result)
                self.assertFalse(any('finger' in str(path) or 'artifacts' in str(path) or 'nginx' in str(path) for path in result))

        def test_missing_required_or_unknown_server_key_rejected(self):
            for edit in [lambda x: x.pop('server/policy.json'), lambda x: x.update({'server/../../etc/passwd': 'x'}), lambda x: x.update({'server/run-arbitrary.sh': 'x'})]:
                bad = dict(self.files); edit(bad)
                with self.assertRaises(ValueError): self.mapped('server', bad)

        def test_unknown_client_key_rejected(self):
            bad = dict(self.files); bad['client-230/other.service'] = 'x'
            with self.assertRaises(ValueError): self.mapped('client-230', bad)

        def test_owned_wrapper_exact_mapping(self):
            bad = dict(self.files); bad['server/apply-firewall.py'] = '# reviewed wrapper\n'
            self.assertIn(Path('/opt/dell/resources/apply-firewall.py'), self.mapped('server', bad))

        def test_bootstrap_fstab_exact_UUID_and_preserved_unrelated_entries(self):
            text = 'UUID=root / ext4 defaults 0 1\nUUID=' + self.policy['server']['data_uuid'] + ' /srv/resources ext4 defaults,nofail,nodev,nosuid,noexec 0 2\n'
            check_fstab(text, self.policy['server']['data_uuid'])
            for bad in [text.replace('/srv/resources', '/srv/other'), text.replace('nodev,', ''), text.replace('UUID=' + self.policy['server']['data_uuid'], 'UUID=wrong'), text + text.splitlines()[-1] + '\n', text + 'UUID=' + self.policy['server']['data_uuid'] + ' /elsewhere ext4 defaults 0 2\n']:
                with self.assertRaises(ValueError): check_fstab(bad, self.policy['server']['data_uuid'])

        def test_group_name_gid_collision_never_reuses_unrelated_identity(self):
            group_conflict(None, None)
            group_conflict(('resources', 2980), ('resources', 2980))
            for name, gid in [(('resources', 989), ('other', 2980)), (None, ('other', 2980)), (('resources', 2980), None)]:
                with self.assertRaises(ValueError): group_conflict(name, gid)

        def test_foreign_or_drifted_config_refuses_overwrite(self):
            with tempfile.TemporaryDirectory() as temp:
                path = Path(temp) / 'owned.conf'; path.write_bytes(b'foreign')
                with patch(__name__ + '.safe_path'):
                    with self.assertRaises(ValueError): check_targets({path: (b'new', 0o644)}, {'files': {}})
                    with self.assertRaises(ValueError): check_targets({path: (b'new', 0o644)}, {'files': {str(path): digest(b'older')}})
                    self.assertEqual(check_targets({path: (b'new', 0o644)}, {'files': {str(path): digest(b'foreign')}}), [path])
                    self.assertEqual(check_targets({path: (b'foreign', 0o644)}, {'files': {}}), [])

    result = unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromTestCase(Offline))
    if not result.wasSuccessful():
        raise SystemExit(1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--self-test', action='store_true', help='Pure offline regressions; no guest or host mutations')
    parser.add_argument('--role', choices=['server', 'client-230', 'client-240'])
    parser.add_argument('--policy', type=Path)
    parser.add_argument('--activate', action='store_true', help='Explicit reviewed NFS/automount start window only; never Java/HTTP')
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    if args.role is None or args.policy is None:
        parser.error('--role and --policy are required for guest installation')
    if os.geteuid() != 0 or Path('/etc/pve').exists():
        raise ValueError('guest-root-only')
    policy = policy_file(args.policy)
    safe_path(Path('/run'))
    fd = os.open('/run/dell-resources-install.lock', os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'r+b') as lock:
        st = os.fstat(lock.fileno())
        if not stat.S_ISREG(st.st_mode) or st.st_uid != 0 or st.st_nlink != 1 or stat.S_IMODE(st.st_mode) != 0o600:
            raise ValueError('untrusted-install-lock')
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        print(json.dumps(install(policy, args.role, args.activate)))


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        code = str(exc) if isinstance(exc, ValueError) and re.fullmatch(r'[a-zA-Z0-9-]{1,80}', str(exc)) else 'resource-installation-failed'
        print(json.dumps({'status': 'failed', 'failure_code': code, 'Java_or_HTTP_started': False}))
        raise SystemExit(1) from None
