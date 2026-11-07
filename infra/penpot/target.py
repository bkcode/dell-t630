#!/usr/bin/env python3
"""Target-only orchestration. No source Docker context is modified."""
import argparse
import json
import os
from pathlib import Path
import platform
import subprocess
from target_guard import DOCKER, assignment, verify_target
from runtime_logging import validate_runtime_logging

BASE = Path(__file__).resolve().parent


def compose(private, args, **kwargs):
    files = ['-f', str(BASE / 'compose.yaml')]
    if assignment()['storage']['mode'] == 'dedicated':
        files += ['-f', str(BASE / 'compose.mount-gated.yaml')]
    return subprocess.run(DOCKER + ['compose', '--env-file', str(private / '.env'), *files, *args], **kwargs)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('action', choices=['check', 'preflight', 'pull', 'build', 'create', 'start', 'stop', 'status'])
    p.add_argument('--private-dir', required=True, type=Path)
    args = p.parse_args()
    private = args.private_dir.resolve()
    for name in ('.env', 'worker-credentials.json', 'worker-credentials.uid1001.json', 'worker-credentials.uid1000.json'):
        path = private / name
        if not path.is_file() or path.stat().st_mode & 0o077:
            raise SystemExit('Private settings must exist and have no group/other permissions')
    proc = compose(private, ['config', '--format', 'json'], capture_output=True, text=True)
    if proc.returncode:
        raise SystemExit('Compose configuration failed; details suppressed to protect settings')
    config = json.loads(proc.stdout)
    validate_runtime_logging(config)
    services = config['services']
    assert len(services) == 11
    assert all(v.get('platform') == 'linux/amd64' for v in services.values())
    assert 'login-defaults' not in config.get('secrets', {})
    assert 'ports' not in services['penpot-mailpit']
    assert not services['penpot-frontend'].get('secrets')
    assert all('sha256:' in v['image'] for v in services.values() if 'build' not in v)
    if args.action == 'check':
        print('Compose valid: 11 services, AMD64 pinned, no login-default credential path, Mailpit unexposed; query-safe read-only runtime templates verified')
        return
    contract, daemon = verify_target(require_docker_data=True, require_storage=args.action != 'stop')
    if args.action == 'preflight':
        print('Assigned guest, local Docker daemon and selected storage verified.')
        return
    if args.action == 'start' and contract['storage']['mode'] == 'dedicated' and (os.environ.get('DELL_MOUNT_GATED') != '1' or not os.environ.get('INVOCATION_ID')):
        raise SystemExit('Dedicated storage must be started by the installed mount-gated systemd unit')
    for uid in (1001, 1000):
        if (private / ('worker-credentials.uid' + str(uid) + '.json')).stat().st_uid != uid:
            raise SystemExit('Target per-service secret owner mismatch; rerun configure.py as root')
    if args.action == 'pull':
        command = ['pull', '--ignore-buildable']
    elif args.action == 'build':
        command = ['build', 'penpot-frontend', 'penpot-worker', 'penpot-import']
    elif args.action == 'create':
        command = ['create']
    elif args.action == 'stop':
        command = ['stop']
    elif args.action == 'start':
        if not (private / 'restore-complete.json').exists():
            raise SystemExit('Restore receipt missing; refusing to start against an unverified empty database')
        command = ['up', '-d', '--no-build']
    else:
        command = ['ps']
    env = dict(os.environ, COMPOSE_PARALLEL_LIMIT='1')
    result = compose(private, command, env=env)
    raise SystemExit(result.returncode)


if __name__ == '__main__':
    main()
