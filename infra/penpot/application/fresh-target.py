#!/usr/bin/env python3
"""Fresh target identity + Git-backed runtime. Never reads source .env or identity."""
import argparse
import datetime
import hashlib
import http.cookiejar
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import time
import urllib.error
import urllib.request

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))
from target_guard import DOCKER, verify_target
from runtime_logging import validate_runtime_logging

PRIVATE = Path('/etc/penpot')
GIT = BASE / 'source'
HEAD = 'ff1783e7865af7aae571c985f03e057631b7af63'
FRONTEND = 'dell-penpot-frontend:2.18.5-ff1783e-amd64'


def write(path, value, mode=0o600):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.write_text(value)
    path.chmod(mode)


def run(command, label):
    result = subprocess.run(command, capture_output=True, text=True, timeout=300)
    PRIVATE.mkdir(parents=True, exist_ok=True, mode=0o700)
    PRIVATE.chmod(0o700)
    log = PRIVATE / 'fresh-private.log'
    fd = os.open(log, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    with os.fdopen(fd, 'a') as file:
        file.write('\n' + label + '\n' + result.stdout + result.stderr)
    if result.returncode:
        raise RuntimeError(label + ' failed; details retained privately')
    return result.stdout


def compose(core, args):
    return DOCKER + ['compose', '--env-file', str(PRIVATE / '.env'), '-f',
                     str(BASE / ('compose.fresh.core.yaml' if core else 'compose.fresh.yaml')), *args]


def identities():
    return json.loads((PRIVATE / 'new-identities.json').read_text())


def init():
    contract, daemon = verify_target(require_docker_data=True)
    if daemon['Driver'] != 'overlay2':
        raise RuntimeError('Classic overlay2 store required')
    actual = run(['git', '-C', str(GIT), 'rev-parse', 'HEAD'], 'verify Git HEAD').strip()
    if actual != HEAD or run(['git', '-C', str(GIT), 'status', '--porcelain=v1'], 'verify Git clean').strip():
        raise RuntimeError('Exact clean modified Git checkout required')
    defaults = json.loads((GIT / 'frontend/selfhost/login-defaults.example.json').read_text())
    if defaults.get('password'):
        raise RuntimeError('Browser default password is forbidden')
    PRIVATE.mkdir(parents=True, exist_ok=True, mode=0o700)
    PRIVATE.chmod(0o700)
    marker = PRIVATE / 'fresh-instance.json'
    if not marker.exists():
        if (PRIVATE / '.env').exists():
            raise RuntimeError('Unclassified existing identity must not be overwritten')
        if run(DOCKER + ['ps', '-aq', '--filter', 'label=com.docker.compose.project=penpot'], 'check empty project').strip():
            raise RuntimeError('Fresh initialization requires no existing Penpot containers')
        info = {'owner': {'email': 'owner@dell.local', 'password': secrets.token_urlsafe(30), 'fullname': 'Dell Penpot Owner'},
                'worker': {'email': 'mcp-worker@dell.local', 'password': secrets.token_urlsafe(30), 'fullname': 'Dell MCP Worker'},
                'generation': 'new-on-target; no source identity copied'}
        write(PRIVATE / 'new-identities.json', json.dumps(info, indent=2) + '\n')
        values = {'PENPOT_SECRET_KEY': secrets.token_urlsafe(64), 'PENPOT_DATABASE_PASSWORD': secrets.token_urlsafe(30),
                  'PENPOT_PUBLIC_URI': 'http://192.168.21.22:9001', 'PENPOT_BIND_ADDRESS': '0.0.0.0',
                  'PENPOT_FLAGS': 'disable-email-verification enable-smtp enable-prepl-server disable-secure-session-cookies enable-mcp enable-admin-console',
                  'PENPOT_WORKER_TEAM_ID': '', 'PENPOT_WORKER_FILE_ID': '', 'PENPOT_WORKER_PAGE_ID': ''}
        write(PRIVATE / '.env', ''.join(k + "='" + v + "'\n" for k, v in values.items()))
        write(marker, json.dumps({'mode': 'new-service-application-export-import', 'source_credentials_copied': False,
                                   'git_head': HEAD, 'created_at': datetime.datetime.now(datetime.timezone.utc).isoformat()}, indent=2) + '\n')
    # Build from the actual Git checkout, without changing any tracked source file.
    exists = subprocess.run(DOCKER + ['image', 'inspect', FRONTEND], capture_output=True, text=True)
    if exists.returncode:
        image = json.loads((BASE / 'images.lock.json').read_text())['images']['frontend']['target']
        digest = image.split('@', 1)[1]
        run(DOCKER + ['build', '--platform', 'linux/amd64', '--tag', FRONTEND,
                     '--label', 'org.opencontainers.image.revision=' + HEAD,
                     '--build-arg', 'PENPOT_VERSION=2.18.5@' + digest,
                     str(GIT / 'frontend/selfhost')], 'build Git frontend')
    config = json.loads(run(compose(True, ['config', '--format', 'json']), 'core config'))
    validate_runtime_logging(config)
    browser = Path(config['secrets']['login-defaults']['file'])
    if json.loads(browser.read_text()).get('password'):
        raise RuntimeError('No real password may reach the browser default helper')
    # Persistent filesystem gates cover both the daemon and application service.
    mount = contract['storage']['mountpoint']
    unit = run(['systemd-escape', '--path', '--suffix=mount', mount], 'data mount unit').strip()
    write(Path('/etc/systemd/system/docker.service.d/dell-penpot-storage.conf'),
          '[Unit]\nRequiresMountsFor=' + mount + '\nBindsTo=' + unit + '\nAfter=' + unit + '\n', 0o644)
    text = f'''[Unit]
Description=Dell Git-backed fresh Penpot
Requires=docker.service
BindsTo=docker.service {unit}
After=network-online.target docker.service {unit}
RequiresMountsFor={mount}
PartOf=docker.service
[Service]
Type=oneshot
RemainAfterExit=yes
Environment=DELL_MOUNT_GATED=1
ExecStart=/usr/bin/python3 {BASE}/application/fresh-target.py start
ExecStop=/usr/bin/python3 {BASE}/application/fresh-target.py stop
TimeoutStartSec=300
TimeoutStopSec=180
[Install]
WantedBy=multi-user.target
'''
    write(Path('/etc/systemd/system/dell-penpot.service'), text, 0o644)
    run(['systemctl', 'daemon-reload'], 'systemd reload')
    run(['systemctl', 'enable', 'dell-penpot.service'], 'enable target unit')
    print(json.dumps({'fresh_identity_generated_on_target': True, 'git_head': HEAD,
                      'frontend': FRONTEND, 'default_browser_password': 'empty', 'writers_started': False}))


def start():
    verify_target(require_docker_data=True)
    if os.environ.get('DELL_MOUNT_GATED') != '1' or not os.environ.get('INVOCATION_ID'):
        raise RuntimeError('Use the mount-gated systemd unit')
    if not (PRIVATE / 'fresh-instance.json').exists():
        raise RuntimeError('Fresh identity marker missing')
    core = not (PRIVATE / 'automation-ready.json').exists()
    run(compose(core, ['up', '-d', '--no-build', '--pull', 'never']), 'start target ' + ('core' if core else 'full'))


def accounts():
    verify_target(require_docker_data=True)
    for _ in range(60):
        try:
            with urllib.request.build_opener(urllib.request.ProxyHandler({})).open('http://127.0.0.1:9001/readyz', timeout=5) as response:
                if response.status == 200:break
        except Exception:pass
        time.sleep(2)
    else:raise RuntimeError('Fresh target backend not ready')
    state_path = PRIVATE / 'profiles-created.json'
    if not state_path.exists():
        for role, item in identities().items():
            if role not in ('owner', 'worker'):continue
            run(compose(True, ['exec', '-T', 'penpot-backend', 'python3', 'manage.py', 'create-profile',
                              '-e', item['email'], '-p', item['password'], '-n', item['fullname'],
                              '--skip-tutorial', '--skip-walkthrough']), 'create fresh ' + role)
        write(state_path, json.dumps({'owner': True, 'worker': True, 'source_identities_copied': False}) + '\n')
    print(json.dumps({'target_profiles_created': True, 'password_values_emitted': False}))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['init', 'start', 'stop', 'accounts'])
    args = parser.parse_args()
    if args.action == 'init':init()
    elif args.action == 'accounts':accounts()
    elif args.action == 'start':start()
    else:
        verify_target(require_storage=False)
        run(compose(False, ['stop']), 'stop target only')


if __name__ == '__main__':
    try:main()
    except Exception as error:
        print('FRESH TARGET ERROR: ' + str(error), file=sys.stderr)
        sys.exit(1)
