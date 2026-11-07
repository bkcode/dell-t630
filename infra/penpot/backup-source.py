#!/usr/bin/env python3
"""Export a consistent source snapshot only after its writers are already stopped.

This script NEVER stops/restarts source services. The manager schedules the short
write-free window. No backup is taken while any listed writer remains running.
"""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
from zoneinfo import ZoneInfo
from source_guard import verify_source

BASE = Path(__file__).resolve().parent
WRITERS = ['penpot-backend', 'penpot-worker', 'penpot-import', 'penpot-admin-console']


def inspect(name):
    p = subprocess.run(['docker', 'inspect', name], capture_output=True, text=True)
    if p.returncode:
        raise SystemExit('Cannot inspect required source container: ' + name)
    return json.loads(p.stdout)[0]


def stream_file(command, path):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'wb') as out:
        p = subprocess.run(command, stdout=out, stderr=subprocess.PIPE)
    if p.returncode:
        raise SystemExit('Snapshot command failed; partial file retained privately: ' + path.name)
    return hashlib.file_digest(path.open('rb'), 'sha256').hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--output', required=True, type=Path)
    p.add_argument('--private-dir', required=True, type=Path)
    p.add_argument('--source-project', default='penpot')
    p.add_argument('--confirm-quiesced', action='store_true')
    args = p.parse_args()
    if not args.confirm_quiesced:
        raise SystemExit('Requires scheduled write-free window and --confirm-quiesced')
    observed_source = verify_source()
    prefix = args.source_project + '-'
    if not all(name.startswith(prefix) for name in observed_source['containers']):
        raise SystemExit('Source project does not match locked source containers')
    for role in WRITERS:
        state = inspect(prefix + role + '-1')['State']
        if state['Running']:
            raise SystemExit('Source writer is running; stop it in the approved window: ' + role)
    postgres = inspect(prefix + 'penpot-postgres-1')
    if not postgres['State']['Running']:
        raise SystemExit('Source PostgreSQL must remain running for logical pg_dump')
    output = args.output.resolve()
    if output.exists():
        raise SystemExit('Output path already exists; refusing to mix snapshots')
    output.mkdir(parents=True, mode=0o700)
    os.chmod(output, 0o700)
    hashes = {}
    hashes['postgres.dump'] = stream_file(
        ['docker', 'exec', prefix + 'penpot-postgres-1',
         'pg_dump', '-Fc', '--no-owner', '--no-privileges', '-U', 'penpot', '-d', 'penpot'],
        output / 'postgres.dump')
    for role, target, filename in [('penpot-backend', '/opt/data/assets', 'assets.tar'),
                                   ('penpot-import', '/data/jobs', 'import-jobs.tar')]:
        container = inspect(prefix + role + '-1')
        matches = [m for m in container['Mounts'] if m['Destination'] == target and m['Type'] == 'volume']
        if len(matches) != 1:
            raise SystemExit('Source volume mapping differs from reviewed plan: ' + role)
        volume = matches[0]['Name']
        hashes[filename] = stream_file(
            ['docker', 'run', '--rm', '--network', 'none', '--read-only',
             '--mount', 'type=volume,src=' + volume + ',dst=/data,readonly',
             '--entrypoint', 'tar', postgres['Image'], '-C', '/data', '-cf', '-', '.'],
            output / filename)
    private = output / 'private'
    private.mkdir(mode=0o700)
    for filename in ('.env', 'worker-credentials.json'):
        src = args.private_dir / filename
        shutil.copyfile(src, private / filename)
        os.chmod(private / filename, 0o600)
        hashes['private/' + filename] = hashlib.file_digest((private / filename).open('rb'), 'sha256').hexdigest()
    receipt = {'captured_at': datetime.datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),
               'version': observed_source['application_release'], 'source_project': args.source_project,
               'verified_source': observed_source,
               'writers_stopped': WRITERS, 'files': hashes,
               'scope': 'database + assets + import jobs + private deployment identity'}
    fd = os.open(output / 'snapshot.json', os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as file:
        json.dump(receipt, file, indent=2)
        file.write('\n')
    print('Consistent snapshot prepared; source containers were not modified by this script.')
    print('Artifacts:', len(hashes), '; protect the complete snapshot directory as private data.')


if __name__ == '__main__':
    main()
