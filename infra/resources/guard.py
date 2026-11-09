#!/usr/bin/env python3
"""Guest-side read-only mount/identity gate; does not mount or change services."""
import argparse
import grp
import importlib.util
import json
import os
from pathlib import Path
import pwd
import socket
import stat
import subprocess

spec = importlib.util.spec_from_file_location('resource_prepare', Path(__file__).with_name('prepare.py'))
prepare = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prepare)
POLICY = Path('/etc/dell-resources/policy.json')


def trusted_policy(path):
    for item in [path, *path.parents]:
        st = item.lstat()
        if stat.S_ISLNK(st.st_mode) or st.st_uid != 0 or st.st_mode & 0o022:
            raise ValueError('untrusted-policy-path')
    st = path.stat()
    if not stat.S_ISREG(st.st_mode) or stat.S_IMODE(st.st_mode) != 0o600 or st.st_nlink != 1 or st.st_size > 8192:
        raise ValueError('untrusted-policy-file')
    policy = json.loads(path.read_text())
    prepare.validate(policy)
    return policy


def select_mount(rows, target, allow_autofs_only=False):
    """Select only a real mount or the exact known systemd direct/NFS stack.

    allow_autofs_only is reserved for the installer's owned previous-state
    path; the read-only runtime guard always requires the real NFS mount.
    """
    if not isinstance(rows, list) or not rows or any(not isinstance(row, dict)
            or row.get('target') != target or row.get('children') for row in rows):
        raise ValueError('one-exact-mount-required')
    if target != '/mnt/resources':
        if len(rows) != 1:
            raise ValueError('one-exact-mount-required')
        return rows[0]
    autofs = [row for row in rows if row.get('fstype') == 'autofs']
    nfs = [row for row in rows if row.get('fstype') == 'nfs4']
    if autofs:
        if len(autofs) != 1 or autofs[0].get('source') != 'systemd-1' or 'direct' not in set(autofs[0].get('options', '').split(',')):
            raise ValueError('foreign-automount-stack')
        if len(rows) == 1:
            if allow_autofs_only:
                return autofs[0]
            raise ValueError('real-NFS-mount-required')
        if len(rows) != 2 or len(nfs) != 1:
            raise ValueError('foreign-automount-stack')
        return nfs[0]
    if len(rows) != 1:
        raise ValueError('one-exact-mount-required')
    return rows[0]  # Source/options/UUID remain validated by the existing gate.


def check_mount(policy, role, row, hostname, group, runtime=None, supplementary=None):
    """Pure validation for selected findmnt fields; no filesystem or data reads."""
    if role == 'server':
        target = policy['server']['mount']
        if hostname != policy['server']['hostname']:
            raise ValueError('wrong-server-hostname')
        if row.get('target') != target or row.get('fstype') != 'ext4' or row.get('uuid') != policy['server']['data_uuid']:
            raise ValueError('wrong-data-filesystem')
    elif role in ['client-230', 'client-240']:
        client = next(x for x in policy['clients'] if role == 'client-' + str(x['vmid']))
        if hostname != client['hostname']:
            raise ValueError('wrong-client-hostname')
        target = policy['client_mount']
        if row.get('target') != target or row.get('fstype') != 'nfs4' or row.get('source') != '192.168.19.80:/':
            raise ValueError('wrong-NFS-mount')
        options = set(row.get('options', '').split(','))
        if not {'vers=4.1', 'proto=tcp', 'hard', 'sec=sys'} <= options:
            raise ValueError('wrong-NFS-options')
        if runtime != (999, 989) or 2980 not in (supplementary or []):
            raise ValueError('runtime-identity-or-supplementary-group-mismatch')
    else:
        raise ValueError('unknown-role')
    if group != ('resources', 2980):
        raise ValueError('resource-group-conflict')
    if not {'rw', 'nodev', 'nosuid', 'noexec'} <= set(row.get('options', '').split(',')):
        raise ValueError('unsafe-mount-options')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--role', choices=['server', 'client-230', 'client-240'], required=True)
    args = parser.parse_args()
    if os.geteuid() != 0 or Path('/etc/pve').exists():
        raise ValueError('guest-root-only')
    policy = trusted_policy(POLICY)
    target = policy['server']['mount'] if args.role == 'server' else policy['client_mount']
    if Path(target).is_symlink():
        raise ValueError('symlink-mountpoint')
    result = subprocess.run(['/usr/bin/findmnt', '--json', '--mountpoint', target, '--output', 'TARGET,SOURCE,FSTYPE,OPTIONS,UUID'], capture_output=True, timeout=5, check=True)
    rows = json.loads(result.stdout)['filesystems']
    row = select_mount(rows, target)
    group = grp.getgrgid(2980)
    runtime = supplementary = None
    if args.role != 'server':
        finger = pwd.getpwnam('finger')
        runtime = (finger.pw_uid, finger.pw_gid)
        supplementary = os.getgrouplist('finger', finger.pw_gid)
    check_mount(policy, args.role, row, socket.gethostname(), (group.gr_name, group.gr_gid), runtime, supplementary)
    if args.role == 'server':
        st = Path(target).stat()
        if st.st_uid != 0 or st.st_gid != 2980 or stat.S_IMODE(st.st_mode) != 0o2770:
            raise ValueError('data-root-permissions-mismatch')
    print(json.dumps({'mount_guard': True, 'role': args.role}))


if __name__ == '__main__':
    try:
        main()
    except Exception:
        # No raw command stderr, paths, group databases or application data logged.
        raise SystemExit('resource-mount-guard-failed') from None
