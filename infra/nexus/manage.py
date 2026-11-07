#!/usr/bin/env python3
"""Manage only the assigned Nexus guest, local Docker and selected storage."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import time
from target_guard import DOCKER, assignment, verify_target

BASE = Path(__file__).resolve().parent
p = argparse.ArgumentParser()
p.add_argument('action', choices=['check', 'pull', 'start', 'supervise', 'stop', 'status'])
p.add_argument('--env-file', required=True, type=Path)
a = p.parse_args()
contract, daemon = verify_target(require_storage=False)
files = ['-f', str(BASE / 'compose.yaml')]
if contract['storage']['mode'] == 'dedicated':
    files += ['-f', str(BASE / 'compose.mount-gated.yaml')]
command = DOCKER + ['compose', '--env-file', str(a.env_file), *files]
result = subprocess.run(command + ['config', '--format', 'json'], capture_output=True, text=True)
if result.returncode:
    raise SystemExit('Nexus config invalid; settings suppressed')
config = json.loads(result.stdout)
if set(config['services']['nexus'].get('networks', {})) != {'backend'} or not config['networks']['backend'].get('internal'):
    raise SystemExit('Nexus must remain internal-only until outbound access is explicitly reviewed')
if config['services']['nexus'].get('ports') or config['services']['gateway'].get('secrets'):
    raise SystemExit('Unsafe Nexus direct port or gateway secret mount')
allowed_gateway_mounts = config['services']['gateway'].get('volumes', [])
if len(allowed_gateway_mounts) != 1 or allowed_gateway_mounts[0].get('target') != '/etc/nginx/conf.d/default.conf' or not allowed_gateway_mounts[0].get('read_only'):
    raise SystemExit('Gateway must only mount its read-only fixed upstream configuration')
mount = next(x for x in config['services']['nexus']['volumes'] if x['target'] == '/nexus-data')
if a.action != 'stop':
    verify_target(data_path=mount['source'])
if a.action == 'check':
    print('Assigned guest, local Docker and selected data filesystem verified.')
    raise SystemExit(0)
if a.action in ('start', 'supervise'):
    restored = BASE / 'restore-complete.json'
    fresh = BASE / 'fresh-instance.json'
    if restored.exists() and fresh.exists():
        raise SystemExit('Ambiguous initialization mode')
    if fresh.exists():
        if fresh.is_symlink() or fresh.stat().st_uid != 0 or fresh.stat().st_mode & 0o077:
            raise SystemExit('Fresh-instance marker must be root-owned, private and non-symlink')
        marker = json.loads(fresh.read_text())
        if marker.get('mode') != 'new-instance-application-export-import' or marker.get('expected_guest_ip') != contract['expected_guest_ip'] or marker.get('expected_hostname') != contract['expected_hostname'] or marker.get('data_path') != contract['storage']['data_path'] or marker.get('filesystem_uuid') != contract['storage']['filesystem_uuid'] or marker.get('old_h2_or_credentials_imported') is not False:
            raise SystemExit('Fresh-instance identity/storage contract mismatch')
    elif not restored.exists():
        raise SystemExit('Neither reviewed restore nor explicitly armed fresh initialization exists')
    if contract['storage']['mode'] == 'dedicated' and (os.environ.get('DELL_MOUNT_GATED') != '1' or not os.environ.get('INVOCATION_ID')):
        raise SystemExit('Dedicated storage must start through the mount-gated systemd unit')
if a.action == 'supervise':
    started = subprocess.run(command + ['up', '-d'], capture_output=True, text=True, timeout=600)
    if started.returncode:
        raise SystemExit('Nexus container start failed; inspect protected local logs')
    deadline = time.monotonic() + 180
    try:
        while True:
            verify_target(data_path=mount['source'])
            state = subprocess.run(command + ['ps', '--all', '--quiet'], capture_output=True, text=True, timeout=20)
            if state.returncode:
                raise RuntimeError('Nexus state collection failed')
            ids = state.stdout.split()
            if ids:
                inspected = subprocess.run(DOCKER + ['inspect', *ids], capture_output=True, text=True, timeout=20)
                if inspected.returncode:
                    raise RuntimeError('Nexus container inspection failed')
                rows = [{'Service': x['Config']['Labels']['com.docker.compose.service'], 'State': x['State']['Status'], 'Health': x['State'].get('Health', {}).get('Status')} for x in json.loads(inspected.stdout)]
            else:
                rows = []
            complete = len(rows) == 2 and {x.get('Service') for x in rows} == {'nexus', 'gateway'}
            healthy = complete and all(x.get('State') == 'running' and x.get('Health') == 'healthy' for x in rows)
            if healthy:
                deadline = time.monotonic() + 30
            elif any(x.get('State') in ('exited', 'dead') for x in rows) or time.monotonic() >= deadline:
                raise RuntimeError('Nexus service set is incomplete or unhealthy')
            time.sleep(10)
    finally:
        subprocess.run(command + ['stop'], capture_output=True, text=True, timeout=180)
commands = {'pull': ['pull'], 'start': ['up', '-d'], 'stop': ['stop'], 'status': ['ps']}
raise SystemExit(subprocess.run(command + commands[a.action]).returncode)
