"""Assigned-guest, local-daemon and storage checks for target mutations."""
import ipaddress
import json
import os
from pathlib import Path
import platform
import re
import socket
import stat
import subprocess

BASE = Path(__file__).resolve().parent
DOCKER = ['docker', '--host', 'unix:///var/run/docker.sock']


def read_json(command):
    result = subprocess.run(command, capture_output=True, text=True, timeout=20)
    if result.returncode:
        raise RuntimeError('Target preflight command failed; details suppressed')
    return json.loads(result.stdout)


def assignment():
    return json.loads((BASE / 'assignment.json').read_text())


def verify_guest(contract=None):
    contract = contract or assignment()
    if Path('/etc/pve').exists():
        raise RuntimeError('Refusing to operate on the PVE host')
    if platform.system() != 'Linux' or platform.machine() not in ('x86_64', 'amd64') or os.geteuid() != 0:
        raise RuntimeError('Root on the assigned Linux AMD64 guest is required')
    expected = str(ipaddress.ip_address(contract['expected_guest_ip']))
    interfaces = read_json(['ip', '-j', 'address', 'show'])
    addresses = {entry.get('local') for interface in interfaces for entry in interface.get('addr_info', [])}
    if expected not in addresses:
        raise RuntimeError('Assigned guest IP is not configured locally')
    hostname = contract.get('expected_hostname')
    if hostname and socket.gethostname() != hostname:
        raise RuntimeError('Assigned hostname mismatch')
    return contract


def verify_docker():
    override = os.environ.get('DOCKER_HOST', '')
    if override not in ('', 'unix:///var/run/docker.sock'):
        raise RuntimeError('DOCKER_HOST override is not the local rootful Docker socket')
    context_name = subprocess.run(['docker', 'context', 'show'], capture_output=True, text=True, timeout=10)
    if context_name.returncode:
        raise RuntimeError('Cannot determine Docker context')
    contexts = read_json(['docker', 'context', 'inspect', context_name.stdout.strip()])
    if len(contexts) != 1 or contexts[0]['Endpoints']['docker']['Host'] != 'unix:///var/run/docker.sock':
        raise RuntimeError('Remote or alternate Docker context is not allowed')
    sock = Path('/var/run/docker.sock')
    if not sock.exists() or not stat.S_ISSOCK(sock.stat().st_mode):
        raise RuntimeError('Local Docker Unix socket is missing')
    daemon = read_json(DOCKER + ['info', '--format', '{{json .}}'])
    if daemon.get('OSType') != 'linux' or daemon.get('Architecture') not in ('x86_64', 'amd64'):
        raise RuntimeError('Docker daemon is not Linux AMD64')
    if daemon.get('Name') != socket.gethostname():
        raise RuntimeError('Docker daemon does not identify as this guest')
    return daemon


def canonical(path):
    path = Path(path)
    if not path.is_absolute() or not re.fullmatch(r'/[A-Za-z0-9_./-]+', str(path)) or '..' in path.parts or path.resolve() != path:
        raise RuntimeError('Storage paths must be absolute, canonical and without symlink escapes')
    return path


def verify_storage(contract, daemon, data_path=None, require_docker_data=False):
    storage = contract['storage']
    mode = storage.get('mode')
    if mode not in ('rootfs', 'dedicated'):
        raise RuntimeError('Storage mode is not assigned; manager must select rootfs or dedicated')
    target = canonical(storage['data_path'])
    if data_path is not None and canonical(data_path) != target:
        raise RuntimeError('Data directory differs from the assigned storage contract')
    if require_docker_data and canonical(daemon['DockerRootDir']) != target:
        raise RuntimeError('DockerRootDir differs from the assigned data directory')
    existing = target
    while not existing.exists():
        existing = existing.parent
    mounted = read_json(['findmnt', '-J', '-T', str(existing), '-o', 'TARGET,SOURCE,FSTYPE,UUID'])['filesystems']
    if len(mounted) != 1:
        raise RuntimeError('Cannot identify the data filesystem')
    fs = mounted[0]
    if fs['fstype'] in ('tmpfs', 'overlay', 'ramfs'):
        raise RuntimeError('Persistent data filesystem required')
    if mode == 'rootfs':
        if fs['target'] != '/':
            raise RuntimeError('Rootfs contract cannot silently use another mounted filesystem')
    else:
        mount = canonical(storage['mountpoint'])
        if mount == Path('/') or not target.is_relative_to(mount) or not storage.get('filesystem_uuid'):
            raise RuntimeError('Dedicated storage requires its actual mountpoint and filesystem UUID')
        if subprocess.run(['mountpoint', '-q', str(mount)], capture_output=True).returncode:
            raise RuntimeError('Dedicated data filesystem is not mounted')
        if fs['target'] != str(mount) or fs.get('uuid') != storage['filesystem_uuid']:
            raise RuntimeError('Mounted data filesystem does not match its assigned UUID')
    return mode


def verify_target(data_path=None, require_docker_data=False, require_storage=True):
    contract = verify_guest()
    daemon = verify_docker()
    if require_storage:
        verify_storage(contract, daemon, data_path, require_docker_data)
    return contract, daemon
