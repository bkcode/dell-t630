#!/usr/bin/env python3
"""Capture source identity privately and configure an explicitly assigned target."""
import argparse
import json
import os
from pathlib import Path
from urllib.parse import urlsplit
import platform
from target_guard import assignment, verify_guest, verify_docker, verify_storage

BASE = Path(__file__).resolve().parent
SOURCE = Path('/Users/yangzhaohui/work/www/harness/penpot')
DEFAULT_PRIVATE = BASE.parent.parent / 'private' / 'penpot'
FLAGS = 'disable-email-verification enable-smtp enable-prepl-server enable-mcp enable-admin-console'
COPY_KEYS = ('PENPOT_SECRET_KEY', 'PENPOT_DATABASE_PASSWORD', 'PENPOT_WORKER_TEAM_ID',
             'PENPOT_WORKER_FILE_ID', 'PENPOT_WORKER_PAGE_ID',
             'PENPOT_WORKER_FAILURE_THRESHOLD', 'PENPOT_WORKER_RECOVERY_GRACE_MS',
             'PENPOT_WORKER_TASK_BUDGET_MS')


def read_env(path):
    result = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        key, value = key.strip(), value.strip()
        if value.startswith(('"', "'")):
            if len(value) < 2 or value[-1] != value[0]:
                raise SystemExit('Unsupported multiline dotenv value; no values printed')
            value = value[1:-1]
        if '\n' in value or '\r' in value:
            raise SystemExit('Invalid dotenv value; no values printed')
        result[key] = value
    return result


def write_private(path, data):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'w') as stream:
        stream.write(data)
    os.chmod(path, 0o600)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--private-dir', type=Path, default=DEFAULT_PRIVATE)
    parser.add_argument('--capture-source', action='store_true')
    parser.add_argument('--storage-mode', choices=['rootfs', 'dedicated'])
    parser.add_argument('--data-path')
    parser.add_argument('--mountpoint')
    parser.add_argument('--filesystem-uuid')
    parser.add_argument('--public-uri')
    parser.add_argument('--bind-address', default=None)
    parser.add_argument('--worker-base-url', default=None)
    parser.add_argument('--allow-insecure-lan', action='store_true')
    args = parser.parse_args()
    if platform.system() == 'Linux':
        contract = verify_guest()
    if args.storage_mode:
        if platform.system() != 'Linux':
            raise SystemExit('Storage assignment must be verified on the target guest')
        daemon = verify_docker()
        contract['storage'] = {'mode': args.storage_mode, 'data_path': args.data_path or daemon['DockerRootDir'],
                               'mountpoint': args.mountpoint, 'filesystem_uuid': args.filesystem_uuid}
        verify_storage(contract, daemon, require_docker_data=True)
        (BASE / 'assignment.json').write_text(json.dumps(contract, indent=2) + '\n')
    private = args.private_dir.resolve()
    private.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(private, 0o700)
    target = private / '.env'
    env = read_env(target) if target.exists() else {}
    if args.capture_source:
        if target.exists() or (private / 'worker-credentials.json').exists():
            raise SystemExit('Private capture already exists; refusing to overwrite identities')
        source_env = read_env(SOURCE / '.env')
        missing = [key for key in COPY_KEYS[:5] if not source_env.get(key)]
        if missing:
            raise SystemExit('Required source settings missing (names only): ' + ', '.join(missing))
        for key in COPY_KEYS:
            if key in source_env:
                env[key] = source_env[key]
        raw = (SOURCE / '.worker-credentials.json').read_text()
        credential = json.loads(raw)
        if not all(credential.get(key) for key in ('email', 'password', 'mcpKey')):
            raise SystemExit('Worker credential structure incomplete; values suppressed')
        write_private(private / 'worker-credentials.json', raw)
        env.update(PENPOT_PUBLIC_URI='', PENPOT_WORKER_BASE_URL='',
                   PENPOT_FLAGS=FLAGS, PENPOT_BIND_ADDRESS='127.0.0.1')
    if args.public_uri:
        parsed = urlsplit(args.public_uri)
        if not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise SystemExit('Public URI must be a clean assigned origin, without credentials/query')
        if parsed.path not in ('', '/'):
            raise SystemExit('Penpot requires an origin URL, not a path prefix')
        if parsed.scheme not in ('http', 'https'):
            raise SystemExit('Public URI requires HTTP or HTTPS')
        if parsed.scheme == 'http' and not args.allow_insecure_lan:
            raise SystemExit('HTTP requires explicit --allow-insecure-lan for private LAN testing')
        env['PENPOT_PUBLIC_URI'] = args.public_uri.rstrip('/')
        env['PENPOT_FLAGS'] = FLAGS + (' disable-secure-session-cookies' if parsed.scheme == 'http' else '')
        # The browser worker uses the same real origin, so secure cookies work over HTTPS.
        env['PENPOT_WORKER_BASE_URL'] = ('http://penpot-frontend:8080' if parsed.scheme == 'http' else env['PENPOT_PUBLIC_URI'])
    if args.worker_base_url:
        worker_origin = urlsplit(args.worker_base_url)
        if worker_origin.scheme not in ('http', 'https') or not worker_origin.hostname or worker_origin.username or worker_origin.password:
            raise SystemExit('Worker origin must be HTTP(S), without credentials')
        env['PENPOT_WORKER_BASE_URL'] = args.worker_base_url.rstrip('/')
    if args.bind_address:
        import ipaddress
        ipaddress.ip_address(args.bind_address)
        env['PENPOT_BIND_ADDRESS'] = args.bind_address
    if not env:
        raise SystemExit('Capture source privately first or supply an existing private configuration')
    env['PENPOT_PRIVATE_DIR'] = str(private)
    # Compose dotenv single quotes keep secret dollar signs literal.
    # Single quotes keep dollar signs literal; reject the rare embedded quote for manual treatment.
    if any("'" in value or '\n' in value for value in env.values()):
        raise SystemExit('A value needs manual dotenv escaping; values suppressed')
    write_private(target, ''.join(key + "='" + value + "'\n" for key, value in sorted(env.items())))
    raw_credentials = (private / 'worker-credentials.json').read_text()
    for uid in (1001, 1000):
        copy = private / ('worker-credentials.uid' + str(uid) + '.json')
        write_private(copy, raw_credentials)
        if os.name == 'posix' and __import__('platform').system() == 'Linux':
            if os.geteuid() != 0:
                raise SystemExit('Configure target secrets as root to assign per-service file ownership')
            os.chown(copy, uid, uid)
    print('Private configuration saved with mode 600; no secret values emitted.')
    print('Target origin configured:', bool(env.get('PENPOT_PUBLIC_URI')))


if __name__ == '__main__':
    main()
