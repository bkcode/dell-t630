#!/usr/bin/env python3
"""One VM250 source transaction; prepare from public Git, then bounded switch.

Never run against another guest. No credentials are copied into Git or builds.
This is a one-shot transaction, not a bootstrap or a general upgrade command.
"""
import argparse
import copy
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys
import time
import uuid
from zoneinfo import ZoneInfo

BASE = Path('/opt/dell/penpot')
HEALTH = BASE / 'runtime/health-supervision'
TX = Path('/root/dell-penpot-no-onboarding-20261110-v2')
D = ['docker', '--host', 'unix:///var/run/docker.sock']
OLD_HEAD = 'ff1783e7865af7aae571c985f03e057631b7af63'
BASE_IMAGE = '2.18.5@sha256:d5bec7ab86328a2bce02b331291eab5833dcb56e403428ad07ccd6740be73735'
OLD_SHA = {
    'compose.fresh.yaml': '21051d4e8c4cd468c166aa03cd8f2df7b8793c5df04f75d978b9e064da981b0f',
    'runtime/health-supervision/compose.health-supervision.yaml': 'b7239c36bdacdf05c1ee24ef244f053f1d8ebec728e80de099557525e7a6768d',
    'runtime/health-supervision/deployment-lock.json': 'a37bf7c68fa204d6efa15e037fe012b02e9a4a51116a39c6707aff3a8ff749ff',
}
FILES = {name: BASE / name for name in OLD_SHA}
LOCK_NAME = 'runtime/health-supervision/deployment-lock.json'
OVERLAY_NAME = 'runtime/health-supervision/compose.health-supervision.yaml'


def need(condition, code):
    if not condition:
        raise RuntimeError(code)


def run(args, timeout=45, data=None, cwd=None):
    result = subprocess.run(args, input=data, capture_output=True, timeout=timeout, cwd=cwd)
    need(result.returncode == 0, 'fixed-native-operation-failed')
    return result.stdout


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def put(path, data):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = path.with_name(path.name + '.onboarding-tmp-' + uuid.uuid4().hex)
    fd = os.open(temporary, os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_WRONLY, 0o600)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def identity():
    need(os.geteuid() == 0 and socket.gethostname() == 'penpot-service'
         and not Path('/etc/pve').exists(), 'VM250-root-only')
    fs = json.loads(run(['findmnt', '--json', '--mountpoint', '/srv/penpot',
                         '--output', 'TARGET,FSTYPE,UUID']))['filesystems']
    need(len(fs) == 1 and fs[0]['uuid'] == 'ccccda03-bffd-4054-afd3-e0e22f0c607e'
         and fs[0]['fstype'] == 'ext4', 'existing-data-volume-required')
    need(json.loads(run(D + ['info', '--format', '{{json .DockerRootDir}}']))
         == '/srv/penpot/docker', 'existing-Docker-root-required')


def git_head(source):
    need(source.resolve() == source, 'real-source-directory-required')
    need(not run(['git', '--no-optional-locks', '-C', str(source), 'status', '--porcelain']).strip(),
         'source-must-be-clean')
    return run(['git', '-C', str(source), 'rev-parse', 'HEAD']).decode().strip()


def baseline():
    identity()
    need(git_head(BASE / 'source') == OLD_HEAD, 'existing-custom-source-required')
    for name, path in FILES.items():
        need(path.resolve() == path and path.stat().st_uid == 0
             and not path.stat().st_mode & 0o022 and sha(path.read_bytes()) == OLD_SHA[name],
             'public-baseline-drift')
    run(['python3', '-I', '-B', str(HEALTH / 'supervisor.py'), 'check'])
    need(subprocess.run(['systemctl', 'is-active', '--quiet', 'dell-penpot.service']).returncode == 0,
         'existing-supervisor-required')


def frame():
    ids = run(D + ['ps', '-q', '--filter', 'label=com.docker.compose.project=penpot']).decode().split()
    rows = [json.loads(run(D + ['inspect', '--format',
        '{"name":{{json .Name}},"image":{{json .Image}},"health":{{json .State.Health.Status}}}', cid]))
        for cid in ids]
    return {row['name'].removeprefix('/penpot-').removesuffix('-1'): row for row in rows}


def ready(lock):
    if subprocess.run(['systemctl', 'is-active', '--quiet', 'dell-penpot.service']).returncode:
        return False
    rows = frame()
    return set(rows) == set(lock['services']) and all(
        row['health'] == 'healthy' and row['image'] == lock['services'][name]['image_id']
        for name, row in rows.items())


def data_fingerprint():
    # Only protected local metadata; no secret values or digests printed.
    secrets = ['new-identities.json', 'browser-login-defaults.json', 'worker-credentials.json',
               'worker-credentials.uid1000.json', 'worker-credentials.uid1001.json', '.env']
    secret_hashes = {name: sha((Path('/etc/penpot') / name).read_bytes()) for name in secrets}
    assets = Path('/srv/penpot/docker/volumes/penpot_penpot_assets/_data')
    asset_hash = hashlib.sha256()
    count = 0
    for path in sorted(assets.rglob('*')):
        if path.is_file():
            asset_hash.update(str(path.relative_to(assets)).encode() + b'\0')
            with path.open('rb') as stream:
                while chunk := stream.read(1024 * 1024):
                    asset_hash.update(chunk)
            count += 1
    query = "SELECT json_build_object('profiles',(SELECT count(*) FROM profile),'teams',(SELECT count(*) FROM team),'projects',(SELECT count(*) FROM project),'files',(SELECT count(*) FROM file));"
    counts = json.loads(run(D + ['exec', 'penpot-penpot-postgres-1', 'psql', '-XAt',
                                 '-U', 'penpot', '-d', 'penpot', '-c', query]))
    return {'secret_file_SHA256': secret_hashes, 'asset_count': count,
            'asset_aggregate_SHA256': asset_hash.hexdigest(), 'object_counts': counts}


def compose(files):
    return D + ['compose', '--project-directory', str(BASE), '--env-file', '/etc/penpot/.env',
                '-f', str(files['compose.fresh.yaml']), '-f', str(files[OVERLAY_NAME])]


def candidate_files(old, new_head, image_id, tag):
    import yaml
    lock = json.loads(old[LOCK_NAME])
    frontend = lock['services']['penpot-frontend']
    before_tag, before_id = frontend['image_reference_before'], frontend['image_id']
    need(old['compose.fresh.yaml'].count(before_tag.encode()) == 1, 'one-original-frontend-tag-required')
    need(old[OVERLAY_NAME].count(before_id.encode()) == 1, 'one-original-frontend-overlay-required')
    base = old['compose.fresh.yaml'].replace(before_tag.encode(), tag.encode(), 1)
    overlay = old[OVERLAY_NAME].replace(before_id.encode(), image_id.encode(), 1)
    expected = yaml.safe_load(old['compose.fresh.yaml'])
    expected['services']['penpot-frontend']['image'] = tag
    need(yaml.safe_load(base) == expected, 'only-frontend-base-image-may-change')
    expected = yaml.safe_load(old[OVERLAY_NAME])
    expected['services']['penpot-frontend']['image'] = image_id
    need(yaml.safe_load(overlay) == expected, 'only-frontend-overlay-image-may-change')
    lock['Git']['HEAD'] = new_head
    frontend['image_reference_before'], frontend['image_id'] = tag, image_id
    lock['package_file_sha256']['compose.fresh.yaml'] = sha(base)
    lock['supervision_file_sha256']['compose.health-supervision.yaml'] = sha(overlay)
    return {'compose.fresh.yaml': base, OVERLAY_NAME: overlay,
            LOCK_NAME: (json.dumps(lock, indent=2) + '\n').encode()}


def prepare(target):
    baseline()
    need(re.fullmatch('[0-9a-f]{40}', target) and target != OLD_HEAD, 'new-immutable-Git-commit-required')
    need(not TX.exists(), 'fresh-transaction-required')
    run(D + ['buildx', 'version'])
    builder = run(D + ['buildx', 'inspect', 'default']).decode()
    need(re.search(r'^Driver:\s+docker\s*$', builder, re.MULTILINE)
         and 'linux/amd64' in builder, 'native-docker-BuildKit-amd64-required')
    need(shutil.disk_usage('/srv/penpot').free > 12 * 1024**3, 'build-disk-reserve-required')
    TX.mkdir(mode=0o700)
    old = {name: path.read_bytes() for name, path in FILES.items()}
    old_lock = json.loads(old[LOCK_NAME])
    need(ready(old_lock), 'exact11-healthy-before-build')
    for name, raw in old.items():
        put(TX / 'before' / name, raw)
    put(TX / 'data-before.json', json.dumps(data_fingerprint()).encode())
    source = BASE / ('source-onboarding-' + target[:12])
    need(not source.exists(), 'fresh-candidate-source-required')
    run(['git', 'clone', '--no-hardlinks', '--no-checkout', str(BASE / 'source'), str(source)], timeout=120)
    run(['git', '-C', str(source), 'remote', 'set-url', 'origin', 'https://github.com/bkcode/penpot.git'])
    # Public repo: no private key, token, credential helper, or agent forwarding.
    run(['git', '-c', 'credential.helper=', '-c', 'core.askPass=/bin/false', '-C', str(source),
         'fetch', '--depth=4', 'origin', 'main'], timeout=180)
    need(run(['git', '-C', str(source), 'rev-parse', 'origin/main']).decode().strip() == target,
         'remote-main-moved-before-build')
    run(['git', '-C', str(source), 'merge-base', '--is-ancestor', OLD_HEAD, target])
    run(['git', '-C', str(source), 'checkout', '-B', 'main', target])
    need(git_head(source) == target, 'candidate-Git-checkout-mismatch')
    # Keep the full worker/import contexts byte-identical; official services stay pinned.
    changed = run(['git', '-C', str(source), 'diff', '--name-only', OLD_HEAD, target]).decode().splitlines()
    need(changed and all(path.startswith('frontend/selfhost/') for path in changed),
         'only-selfhost-frontend-source-change-allowed')
    tag = 'dell-penpot-frontend:2.18.5-' + target[:12] + '-amd64'
    need(subprocess.run(D + ['image', 'inspect', tag], stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL).returncode != 0, 'new-image-tag-must-not-exist')
    run(D + ['image', 'inspect', 'penpotapp/frontend:' + BASE_IMAGE])
    with (TX / 'build.log').open('wb') as log:
        result = subprocess.run(D + ['build', '--platform', 'linux/amd64', '--pull=false',
            '--network=none', '--tag', tag, '--label', 'org.opencontainers.image.revision=' + target,
            '--build-arg', 'PENPOT_VERSION=' + BASE_IMAGE, str(source / 'frontend/selfhost')],
            stdout=log, stderr=subprocess.STDOUT, timeout=180,
            env={**os.environ, 'DOCKER_BUILDKIT': '1', 'BUILDX_BUILDER': 'default'})
    need(result.returncode == 0, 'fixed-base-frontend-build-failed')
    meta = json.loads(run(D + ['image', 'inspect', '--format',
        '{"id":{{json .Id}},"arch":{{json .Architecture}},"os":{{json .Os}},"entrypoint":{{json .Config.Entrypoint}},"cmd":{{json .Config.Cmd}},"revision":{{json (index .Config.Labels "org.opencontainers.image.revision")}}}', tag]))
    need(meta['arch'] == 'amd64' and meta['os'] == 'linux' and meta['revision'] == target
         and meta['entrypoint'] == ['/bin/bash', '/selfhost-entrypoint.sh']
         and meta['cmd'] == ['nginx', '-g', 'daemon off;'], 'new-image-native-contract-mismatch')
    # Prove the exact image's public assets are readable as the runtime UID.
    # BuildKit uses no Docker-API workload containers that could trip supervision.
    read_check = ('FROM ' + tag + '\nUSER 1001:1001\nRUN test -r /selfhost-entrypoint.sh'
        ' && test -r /var/www/app/js/selfhost-login-defaults.js'
        ' && test -r /var/www/app/css/selfhost-sidebar.css'
        ' && test -r /etc/nginx/overrides/server.d/selfhost-login.conf\n')
    with (TX / 'read-check.log').open('wb') as log:
        result = subprocess.run(D + ['build', '--platform', 'linux/amd64', '--pull=false',
            '--network=none', '--tag', tag + '-readcheck', '--file', '-',
            str(source / 'frontend/selfhost')], input=read_check.encode(),
            stdout=log, stderr=subprocess.STDOUT, timeout=90,
            env={**os.environ, 'DOCKER_BUILDKIT': '1', 'BUILDX_BUILDER': 'default'})
    need(result.returncode == 0, 'unprivileged-image-read-check-failed')
    new = candidate_files(old, target, meta['id'], tag)
    for name, raw in new.items():
        put(TX / 'candidate' / name, raw)
    paths = {name: TX / 'candidate' / name for name in FILES}
    resolved = json.loads(run(compose(paths) + ['config', '--format', 'json']))
    current = json.loads(run(compose(FILES) + ['config', '--format', 'json']))
    expected = copy.deepcopy(current)
    expected['services']['penpot-frontend']['image'] = meta['id']
    need(resolved == expected, 'resolved-only-frontend-image-change-required')
    baseline()
    need(ready(old_lock), 'old11-healthy-after-build')
    receipt = {'status': 'prepared-from-GitHub-no-runtime-switch', 'target': target,
               'candidate_source': str(source), 'rollback_source': str(BASE / ('source-before-onboarding-' + target[:12])),
               'new_frontend': meta, 'tag': tag, 'source_changes': changed,
               'public_SHA256': {name: sha(raw) for name, raw in new.items()},
               'private_key_or_token_distributed': False, 'old11_healthy': True,
               'unprivileged_image_public_files_readable': True}
    put(TX / 'prepared.json', json.dumps(receipt, indent=2).encode())
    print(json.dumps(receipt))


def start_and_wait(lock):
    run(['python3', '-I', '-B', str(HEALTH / 'supervisor.py'), 'check'])
    run(['systemctl', 'reset-failed', 'dell-penpot.service'])
    run(['systemctl', 'start', '--no-block', 'dell-penpot.service'])
    deadline = time.monotonic() + 240
    while time.monotonic() < deadline:
        if ready(lock):
            return
        time.sleep(2)
    raise RuntimeError('exact11-healthy-start-timeout')


def apply():
    baseline()
    receipt = json.loads((TX / 'prepared.json').read_text())
    need(not (TX / 'applied.json').exists(), 'transaction-already-applied')
    source, rollback = Path(receipt['candidate_source']), Path(receipt['rollback_source'])
    need(git_head(source) == receipt['target'] and not rollback.exists(), 'candidate-or-rollback-path-drift')
    old = {name: (TX / 'before' / name).read_bytes() for name in FILES}
    new = {name: (TX / 'candidate' / name).read_bytes() for name in FILES}
    need(all(sha(new[name]) == receipt['public_SHA256'][name] and FILES[name].read_bytes() == old[name]
             for name in FILES), 'public-CAS-before-maintenance')
    before_data = data_fingerprint()
    put(TX / 'data-before-switch.json', json.dumps(before_data).encode())
    run(['systemctl', 'stop', 'dell-penpot.service'], timeout=180)
    need(subprocess.run(['systemctl', 'is-active', '--quiet', 'dell-penpot.service']).returncode != 0,
         'old-supervisor-not-stopped')
    source_moved = False
    try:
        os.rename(BASE / 'source', rollback)
        os.rename(source, BASE / 'source')
        source_moved = True
        for name, path in FILES.items():
            put(path, new[name])
            path.chmod(0o644)
        start_and_wait(json.loads(new[LOCK_NAME]))
        need(data_fingerprint() == before_data, 'existing-identities-or-design-metadata-drift')
        need(git_head(BASE / 'source') == receipt['target'], 'running-Git-mismatch')
    except BaseException:
        run(['systemctl', 'stop', 'dell-penpot.service'], timeout=180)
        if source_moved:
            os.rename(BASE / 'source', source)
        if rollback.exists():
            os.rename(rollback, BASE / 'source')
        for name, path in FILES.items():
            put(path, old[name])
            path.chmod(0o644)
        start_and_wait(json.loads(old[LOCK_NAME]))
        put(TX / 'rolled-back.json', json.dumps({'status': 'old-source-and-public-config-restored',
                                                'Git': OLD_HEAD, 'old11_healthy': True}).encode())
        raise
    result = {'captured_at': datetime.datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),
              'status': 'source-and-frontend-switched-exact11-healthy', 'Git_HEAD': receipt['target'],
              'Git_clean': True, 'frontend_image': receipt['new_frontend']['id'],
              'other10_image_ids_unchanged': True, 'original_private_files_assets_counts_unchanged': True,
              'containers_healthy': 11, 'real_browser_verification_pending': True,
              'private_key_or_token_distributed': False}
    put(TX / 'applied.json', json.dumps(result, indent=2).encode())
    print(json.dumps(result))


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['prepare', 'apply'])
    parser.add_argument('--target')
    args = parser.parse_args()
    prepare(args.target or '') if args.action == 'prepare' else apply()


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        code = str(error)
        print(json.dumps({'status': 'not-confirmed', 'error_type': type(error).__name__,
                          'code': code if re.fullmatch('[a-zA-Z0-9-]{1,100}', code) else 'private-details-withheld'}))
        sys.exit(1)
