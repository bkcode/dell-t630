#!/usr/bin/env python3
"""Restore reviewed snapshots to an empty Linux AMD64 target. Never contacts source."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path, PurePosixPath
import platform
import subprocess
import tarfile
import time
from zoneinfo import ZoneInfo
from target_guard import DOCKER, assignment, verify_target

BASE = Path(__file__).resolve().parent


def compose(private, args, **kwargs):
    files = ['-f', str(BASE / 'compose.yaml')]
    if assignment()['storage']['mode'] == 'dedicated':
        files += ['-f', str(BASE / 'compose.mount-gated.yaml')]
    return subprocess.run(DOCKER + ['compose', '--env-file', str(private / '.env'), *files, *args], **kwargs)


def checked(command, **kwargs):
    p = subprocess.run(command, stderr=subprocess.PIPE, **kwargs)
    if p.returncode:
        raise SystemExit('Target restore command failed; source remains untouched, review private target logs')
    return p


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--snapshot', required=True, type=Path)
    p.add_argument('--private-dir', required=True, type=Path)
    p.add_argument('--confirm-empty-target', action='store_true')
    args = p.parse_args()
    if not args.confirm_empty_target or platform.system() != 'Linux' or platform.machine() != 'x86_64':
        raise SystemExit('Requires Linux AMD64 target and --confirm-empty-target')
    verify_target(require_docker_data=True)
    private, snapshot = args.private_dir.resolve(), args.snapshot.resolve()
    if (private / 'restore-complete.json').exists():
        raise SystemExit('Restore receipt already exists; refusing to overwrite target data')
    receipt = json.loads((snapshot / 'snapshot.json').read_text())
    if receipt['version'] != '2.18.5':
        raise SystemExit('Snapshot version mismatch')
    for name, expected in receipt['files'].items():
        path = snapshot / name
        if path.resolve().is_relative_to(snapshot) is False:
            raise SystemExit('Invalid snapshot manifest path')
        with path.open('rb') as file:
            if hashlib.file_digest(file, 'sha256').hexdigest() != expected:
                raise SystemExit('Snapshot checksum mismatch: ' + name)
    for filename in ('assets.tar', 'import-jobs.tar'):
        with tarfile.open(snapshot / filename) as archive:
            for member in archive:
                if member.isdev() or member.isfifo():
                    raise SystemExit('Unexpected special file in snapshot')
                paths = [member.name] + ([member.linkname] if member.issym() or member.islnk() else [])
                if any(PurePosixPath(x).is_absolute() or '..' in PurePosixPath(x).parts for x in paths):
                    raise SystemExit('Unsafe archive path')
    config = compose(private, ['config', '--format', 'json'], capture_output=True, text=True)
    if config.returncode:
        raise SystemExit('Target Compose config invalid; values suppressed')
    config = json.loads(config.stdout)
    for role in ['penpot-backend', 'penpot-worker', 'penpot-import', 'penpot-admin-console']:
        c = compose(private, ['ps', '-q', role], capture_output=True, text=True)
        if c.stdout.strip():
            raise SystemExit('Target writer is already running: ' + role)
    if compose(private, ['create']).returncode:
        raise SystemExit('Target container creation failed')
    if compose(private, ['up', '-d', 'penpot-postgres']).returncode:
        raise SystemExit('Target PostgreSQL start failed')
    cid = compose(private, ['ps', '-q', 'penpot-postgres'], capture_output=True, text=True).stdout.strip()
    if not cid:
        raise SystemExit('Target PostgreSQL container missing')
    for attempt in range(60):
        status = subprocess.run(DOCKER + ['exec', cid, 'pg_isready', '-U', 'penpot'], capture_output=True)
        if status.returncode == 0:
            break
        time.sleep(1)
    else:
        raise SystemExit('Target PostgreSQL not ready')
    tables = checked(DOCKER + ['exec', cid, 'psql', '-U', 'penpot', '-d', 'penpot', '-Atc',
                      "SELECT count(*) FROM pg_tables WHERE schemaname NOT IN ('pg_catalog','information_schema');"],
                     stdout=subprocess.PIPE, text=True).stdout.strip()
    if tables != '0':
        raise SystemExit('Target database is not empty; refusing overwrite')
    postgres_image = config['services']['penpot-postgres']['image']
    volumes = [('penpot_assets', 'assets.tar'), ('penpot_import_jobs', 'import-jobs.tar')]
    # Preflight EVERY target volume before the first archive extraction.
    for key, filename in volumes:
        volume = config['volumes'][key]['name']
        mount = 'type=volume,src=' + volume + ',dst=/data'
        result = subprocess.run(DOCKER + ['run', '--rm', '--network', 'none', '--read-only',
                                 '--mount', mount + ',readonly', '--entrypoint', 'sh', postgres_image,
                                 '-c', 'test -z "$(ls -A /data)"'], capture_output=True)
        if result.returncode:
            raise SystemExit('Target volume is not empty: ' + key)
    for key, filename in volumes:
        volume = config['volumes'][key]['name']
        mount = 'type=volume,src=' + volume + ',dst=/data'
        with (snapshot / filename).open('rb') as source:
            checked(DOCKER + ['run', '--rm', '-i', '--network', 'none', '--read-only',
                     '--mount', mount, '--entrypoint', 'tar', postgres_image,
                     '-C', '/data', '-xf', '-'], stdin=source, stdout=subprocess.DEVNULL)
    with (snapshot / 'postgres.dump').open('rb') as source:
        checked(DOCKER + ['exec', '-i', cid, 'pg_restore', '--exit-on-error', '--no-owner',
                 '--no-privileges', '-U', 'penpot', '-d', 'penpot'],
                stdin=source, stdout=subprocess.DEVNULL)
    result = {'restored_at': datetime.datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),
              'source_captured_at': receipt['captured_at'], 'version': '2.18.5',
              'functional_acceptance': 'pending', 'source_unchanged': True}
    target = private / 'restore-complete.json'
    target.write_text(json.dumps(result, indent=2) + '\n')
    target.chmod(0o600)
    print('Target restore completed. Application startup and functional acceptance remain pending.')


if __name__ == '__main__':
    main()
