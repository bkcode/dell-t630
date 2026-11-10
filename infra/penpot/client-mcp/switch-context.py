#!/usr/bin/env python3
"""Pin the existing VM250 resident editor to the user-selected Puyu file."""
import datetime
import importlib.util
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import time
import urllib.request
import uuid
from zoneinfo import ZoneInfo

BASE = Path('/opt/dell/penpot')
PRIVATE = Path('/etc/penpot')
TX = Path('/root/dell-penpot-client-context-20261110')
D = ['docker', '--host', 'unix:///var/run/docker.sock']
TARGET = {'team_id': '13a31dab-5204-818d-8008-e6fd5e2efc53',
          'file_id': '01b580ec-b5e6-8057-8008-ec70da4cd212',
          'page_id': '0c6166a2-b4f0-8093-8008-e31e54275406'}
ENV_TARGET = {'PENPOT_WORKER_TEAM_ID': TARGET['team_id'],
              'PENPOT_WORKER_FILE_ID': TARGET['file_id'],
              'PENPOT_WORKER_PAGE_ID': TARGET['page_id']}


def need(value, code):
    if not value:
        raise RuntimeError(code)


def run(args, timeout=40):
    p = subprocess.run(args, capture_output=True, timeout=timeout)
    need(p.returncode == 0, 'fixed-native-operation-failed')
    return p.stdout


def put(path, body):
    temporary = path.with_name(path.name + '.' + uuid.uuid4().hex)
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(body)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def api(role):
    spec = importlib.util.spec_from_file_location('existing_api', BASE / 'application/target-api.py')
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m.API(role)


def ready():
    if subprocess.run(['systemctl', 'is-active', '--quiet', 'dell-penpot.service']).returncode:
        return False
    ids = run(D + ['ps', '-q', '--filter', 'label=com.docker.compose.project=penpot']).decode().split()
    return len(ids) == 11 and all(run(D + ['inspect', '--format', '{{.State.Health.Status}}', i]).strip()
                                 == b'healthy' for i in ids)


def worker_status():
    networks = json.loads(run(D + ['inspect', '--format', '{{json .NetworkSettings.Networks}}',
                                  'penpot-penpot-worker-1']))
    ip = next(v['IPAddress'] for v in networks.values() if v.get('IPAddress'))
    op = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with op.open('http://' + ip + ':4404/readyz', timeout=8) as response:
        return json.load(response)


def start():
    run(['python3', '-I', '-B', str(BASE / 'runtime/health-supervision/supervisor.py'), 'check'])
    run(['systemctl', 'reset-failed', 'dell-penpot.service'])
    run(['systemctl', 'start', '--no-block', 'dell-penpot.service'])
    deadline = time.monotonic() + 420
    while time.monotonic() < deadline:
        if ready():
            return
        time.sleep(2)
    raise RuntimeError('eleven-services-not-ready')


def main():
    os.umask(0o077)
    sys.dont_write_bytecode = True
    need(os.geteuid() == 0 and socket.gethostname() == 'penpot-service', 'VM250-root-only')
    need(not TX.exists(), 'prior-context-transaction-requires-review')
    need(run(['git', '-C', str(BASE / 'source'), 'rev-parse', 'HEAD']).decode().strip()
         == '8a9b96154d9dd81dcc373155ae30dba094127cc8', 'current-source-required')
    need(ready(), 'old-eleven-services-must-be-healthy')
    old_worker = worker_status()
    need(old_worker['state'] == 'ready' and old_worker['activeTasks'] == 0, 'worker-must-be-idle')
    for p in Path('/srv/penpot/docker/volumes/penpot_penpot_import_jobs/_data').glob('*.json'):
        if not p.name.endswith('.tmp'):
            need(json.loads(p.read_text()).get('status') not in ['preparing', 'downloading', 'importing', 'unknown'],
                 'importer-must-be-idle')
    # Confirm the existing resident identity can already read the destination; no grants added.
    before_stats = api('worker').call('get-file-stats', {'id': TARGET['file_id']})
    need(before_stats['pageCount'] == 3 and before_stats['shapeCounts']['total'] == 58240,
         'worker-must-read-confirmed-Puyu-file')
    env_path = PRIVATE / '.env'
    old = env_path.read_bytes()
    new = old
    changed = []
    for key, value in ENV_TARGET.items():
        pattern = rb'(?m)^' + key.encode() + rb"='([0-9a-f-]{36})'$"
        matches = list(re.finditer(pattern, new))
        need(len(matches) == 1, 'exact-one-existing-target-field-required')
        if matches[0].group(1).decode() != value:
            changed.append(key)
        new = re.sub(pattern, key.encode() + b"='" + value.encode() + b"'", new)
    need(set(changed) == {'PENPOT_WORKER_FILE_ID', 'PENPOT_WORKER_PAGE_ID'},
         'only-existing-file-and-page-may-change')
    TX.mkdir(mode=0o700)
    put(TX / 'before.env', old)
    put(TX / 'candidate.env', new)
    put(TX / 'before-stats.json', json.dumps(before_stats).encode())
    need(env_path.read_bytes() == old, 'environment-CAS-drift')
    run(['systemctl', 'stop', 'dell-penpot.service'], timeout=180)
    try:
        put(env_path, new)
        start()
        status = worker_status()
        need(status['fileId'] == TARGET['file_id'] and status['pageId'] == TARGET['page_id']
             and status['state'] == 'ready', 'resident-Puyu-context-not-confirmed')
        after_stats = api('worker').call('get-file-stats', {'id': TARGET['file_id']})
        need(before_stats == after_stats, 'Puyu-design-statistics-or-revision-changed')
    except BaseException:
        run(['systemctl', 'stop', 'dell-penpot.service'], timeout=180)
        put(env_path, old)
        start()
        put(TX / 'recovered.json', json.dumps({'old_context_restored': True, 'eleven_healthy': True}).encode())
        raise
    record = {'captured_at': datetime.datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),
        'status': 'resident-Puyu-context-verified', **TARGET, 'page_name': 'puyu-components',
        'all11_healthy': True, 'worker_identity_already_authorized': True,
        'changed_nonsecret_environment_keys': changed, 'secrets_and_other_env_lines_unchanged': True,
        'Puyu_design_statistics_and_revision_unchanged': True, 'server_credential_exported': False}
    put(PRIVATE / 'client-mcp-context.json', json.dumps(record, indent=2).encode())
    put(TX / 'applied.json', json.dumps(record, indent=2).encode())
    print(json.dumps(record))


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        message = str(error)
        print(json.dumps({'status': 'context-switch-not-confirmed', 'error_type': type(error).__name__,
                          'code': message if re.fullmatch('[a-zA-Z0-9-]{1,100}', message) else 'private-details-withheld'}))
        sys.exit(1)
