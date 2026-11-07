#!/usr/bin/env python3
"""Manager-delegated preparation only for VM221/250. No source drain or writer start."""
import argparse
import io
import json
from pathlib import Path
import shlex
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import control

TARGETS = {221: ('nexus', 'artifact-service', '10.63.30.20'),
           250: ('penpot', 'penpot-service', '10.63.30.30')}


def targets():
    rows = json.loads((ROOT / 'evidence/implementation/private-guest-access.json').read_text())['roles']
    result = {}
    for row in rows:
        info = row['target']
        vmid = info['vmid']
        if vmid in TARGETS:
            role, hostname, ip = TARGETS[vmid]
            if info['ip'] != ip or info['host_key_alias'] != 'dell-vm' + str(vmid) or row['name'] != hostname:
                raise RuntimeError('Assigned target metadata mismatch')
            result[vmid] = info
    if set(result) != set(TARGETS):
        raise RuntimeError('Both manager-verified target entries are required')
    return result


def guest(vmid, code, data=None, timeout=120):
    role, hostname, ip = TARGETS[vmid]
    # All scripts first enforce the assigned host/IP and root; no trust_guest call.
    prelude = '''import os,pathlib,socket,subprocess,json
if pathlib.Path('/etc/pve').exists() or os.geteuid()!=0:raise SystemExit('Wrong target host/user')
if socket.gethostname()!=HOSTNAME:raise SystemExit('Wrong assigned hostname')
addresses=json.loads(subprocess.run(['ip','-j','address','show'],capture_output=True,text=True,check=True).stdout)
if ASSIGNED_IP not in {x.get('local') for a in addresses for x in a.get('addr_info',[])}:raise SystemExit('Wrong assigned IP')
'''.replace('HOSTNAME', repr(hostname)).replace('ASSIGNED_IP', repr(ip))
    command = 'sudo python3 -c ' + shlex.quote(prelude + '\n' + code)
    result = control.guest(vmid, command, data=data, timeout=timeout, info=targets()[vmid])
    if result['exit_code']:
        raise RuntimeError('Owned guest operation failed: VM' + str(vmid) + ', code=' + str(result['exit_code']) + '; output suppressed')
    return result['stdout']


def public_payload(role):
    base = ROOT / 'infra' / role
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode='w:gz') as tar:
        for path in sorted(base.rglob('*')):
            if not path.is_file() or '__pycache__' in path.parts:
                continue
            relative = path.relative_to(base)
            if path.name == '.env' or path.name.startswith('.worker-credentials'):
                raise RuntimeError('Unexpected private file in public package')
            if 'fixtures' in relative.parts or path.name.endswith('.log'):
                continue
            tar.add(path, arcname=str(relative), recursive=False)
    return stream.getvalue()


def copy_public(vmid):
    role = TARGETS[vmid][0]
    code = '''import sys,tarfile
base=pathlib.Path('/opt/dell/ROLE')
if base.is_symlink():raise SystemExit('Refusing symlink package destination')
base.mkdir(parents=True,exist_ok=True,mode=0o755)
with tarfile.open(fileobj=sys.stdin.buffer,mode='r|gz') as archive:
 for entry in archive:
  target=base/entry.name
  if not entry.isfile() or entry.issym() or entry.islnk() or not target.resolve().is_relative_to(base) or '..' in pathlib.PurePosixPath(entry.name).parts:raise SystemExit('Unsafe package member')
  target.parent.mkdir(parents=True,exist_ok=True,mode=0o755)
  target.write_bytes(archive.extractfile(entry).read())
  target.chmod(0o755 if target.suffix=='.py' else 0o644)
print(json.dumps({'public_package':'installed','role':'ROLE','source_data_included':False}))
'''.replace('ROLE', role)
    print(guest(vmid, code, data=public_payload(role), timeout=120).strip())


def copy_private():
    raise RuntimeError('Retired: generate new target identities; never transfer source credentials')


def configure(vmid):
    role = TARGETS[vmid][0]
    assignment = json.loads((ROOT / 'infra' / role / 'assignment.json').read_text())
    storage = assignment['storage']
    if role == 'penpot':
        commands = [['python3', '/opt/dell/penpot/configure.py', '--private-dir', '/etc/penpot',
                     '--public-uri', 'http://192.168.21.22:9001', '--bind-address', '0.0.0.0',
                     '--worker-base-url', 'http://penpot-frontend:8080', '--allow-insecure-lan',
                     '--storage-mode', 'dedicated', '--data-path', storage['data_path'],
                     '--mountpoint', storage['mountpoint'], '--filesystem-uuid', storage['filesystem_uuid']],
                    ['python3', '/opt/dell/penpot/target.py', 'check', '--private-dir', '/etc/penpot'],
                    ['python3', '/opt/dell/penpot/target.py', 'preflight', '--private-dir', '/etc/penpot']]
        extra = ''
    else:
        commands = [['python3', '/opt/dell/nexus/prepare.py', 'init-target', '--data-dir', storage['data_path'],
                     '--storage-mode', 'dedicated', '--mountpoint', storage['mountpoint'],
                     '--filesystem-uuid', storage['filesystem_uuid']],
                    ['python3', '/opt/dell/nexus/manage.py', 'check', '--env-file', '/etc/nexus.env']]
        extra = "p=pathlib.Path('/etc/nexus.env');p.write_text('NEXUS_DATA_DIR=/srv/nexus/data\\nNEXUS_BIND_ADDRESS=0.0.0.0\\n');p.chmod(0o600)\n"
    code = extra + 'commands=' + repr(commands) + '''
for command in commands:
 p=subprocess.run(command,capture_output=True,text=True)
 if p.returncode:raise SystemExit('Preparation command failed; details suppressed')
print(json.dumps({'role':ROLE,'configuration':'passed','writers_started':False}))
'''.replace('ROLE', repr(role))
    print(guest(vmid, code, timeout=180).strip())


def create(vmid):
    role = TARGETS[vmid][0]
    args = ['docker', '--host', 'unix:///var/run/docker.sock', 'compose']
    args += ['--env-file', '/etc/penpot/.env' if role == 'penpot' else '/etc/nexus.env']
    args += ['-f', '/opt/dell/' + role + '/compose.yaml', '-f', '/opt/dell/' + role + '/compose.mount-gated.yaml',
             'create', '--no-build', '--pull', 'never']
    code = 'command=' + repr(args) + '''
p=subprocess.run(command,capture_output=True,text=True,timeout=180)
if p.returncode:raise SystemExit('Container create failed; details suppressed')
p=subprocess.run(['docker','ps','--format','{{.Names}}'],capture_output=True,text=True,check=True)
if p.stdout.strip():raise SystemExit('Unexpected running target container; writers must remain stopped')
print(json.dumps({'role':ROLE,'containers':'created-stopped','writers_started':False}))
'''.replace('ROLE', repr(role))
    print(guest(vmid, code, timeout=210).strip())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['public', 'configure', 'create'])
    parser.add_argument('--vmid', type=int, choices=[221, 250])
    args = parser.parse_args()
    targets()
    if args.action == 'private':
        if args.vmid not in (None, 250):
            raise RuntimeError('Private Penpot identity can only be transferred to owned VM250')
        copy_private()
        return
    for vmid in ([args.vmid] if args.vmid else [221, 250]):
        if vmid == 250 and args.action in ('configure', 'create'):
            raise RuntimeError('Legacy Penpot bootstrap retired; use application/fresh-target.py and its mount-gated unit')
        {'public': copy_public, 'configure': configure, 'create': create}[args.action](vmid)


if __name__ == '__main__':
    main()
