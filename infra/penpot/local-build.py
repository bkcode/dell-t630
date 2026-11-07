#!/usr/bin/env python3
"""Independent local artifact preparation; never calls target deployment scripts.

Only three new dell-penpot tags are allowed. No .env is read, no source volume is
mounted, and no source tag is updated. Builds run sequentially with native JS
compilation and fixed AMD64 runtimes. Registry client auth is deliberately empty.
"""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from zoneinfo import ZoneInfo

BASE = Path(__file__).resolve().parent
OUTPUT = BASE.parent.parent / 'private' / 'images'
TAGS = {role: 'dell-penpot-' + role + ':2.18.5-amd64' for role in ('frontend', 'worker', 'import')}
SOURCE_NAMES = ['nacos', 'mysql', 'redis', 'rabbitmq', 'nexus3', 'nginx'] + [
    'penpot-' + name + '-1' for name in ['penpot-frontend', 'penpot-backend', 'penpot-exporter',
    'penpot-admin-console', 'penpot-mcp', 'penpot-worker', 'penpot-import', 'penpot-postgres',
    'penpot-valkey', 'penpot-dns', 'penpot-mailpit']]
DOCKER = []


def query(args):
    result = subprocess.run(DOCKER + args, capture_output=True, text=True, timeout=30)
    if result.returncode:
        raise RuntimeError('Docker metadata query failed: ' + args[0])
    return json.loads(result.stdout)


def snapshot():
    fmt = ('{"name":{{json .Name}},"id":{{json .Id}},"image_id":{{json .Image}},'
           '"image_reference":{{json .Config.Image}},"running":{{json .State.Running}},'
           '"oom_killed":{{json .State.OOMKilled}},"restarts":{{json .RestartCount}},'
           '"started_at":{{json .State.StartedAt}},"health":'
           '{{if (index .State "Health")}}{{json (index (index .State "Health") "Status")}}{{else}}null{{end}}}')
    result = subprocess.run(DOCKER + ['inspect', '--format', fmt, *SOURCE_NAMES],
                            capture_output=True, text=True, timeout=30)
    if result.returncode:
        raise RuntimeError('Expected source container metadata unavailable; no build started')
    containers = {x['name']: x for x in map(json.loads, result.stdout.splitlines())}
    images = {}
    image_fmt = '{"id":{{json .Id}},"architecture":{{json .Architecture}},"repo_tags":{{json .RepoTags}}}'
    for ref in sorted({x['image_reference'] for x in containers.values()}):
        images[ref] = query(['image', 'inspect', '--format', image_fmt, ref])
    return {'containers': containers, 'source_tags': images}


def stable(before, after, check_health=True):
    for name, expected in before['containers'].items():
        actual = after['containers'].get(name, {})
        for key in ('id', 'image_id', 'image_reference', 'running', 'oom_killed', 'restarts', 'started_at'):
            if actual.get(key) != expected[key]:
                raise RuntimeError('Source state changed during artifact prep: ' + name + '/' + key)
        if check_health and expected['health'] == 'healthy' and actual.get('health') != 'healthy':
            raise RuntimeError('Source health degraded during artifact prep: ' + name)
    if before['source_tags'] != after['source_tags']:
        raise RuntimeError('A source tag mapping changed during artifact preparation')


def available_memory(helper):
    # One isolated native helper reads kernel memory information, with no source volumes.
    command = DOCKER + ['run', '--rm', '--platform', 'linux/arm64', '--network', 'none',
                       '--read-only', '--memory', '32m', '--memory-swap', '32m', '--cpus', '0.25',
                       '--entrypoint', 'sh', helper, '-c',
                       'while read key value unit; do if [ "$key" = "MemAvailable:" ]; then echo "$value"; break; fi; done < /proc/meminfo']
    result = subprocess.run(command, capture_output=True, text=True, timeout=20)
    if result.returncode or not result.stdout.strip().isdigit():
        raise RuntimeError('Cannot measure source engine memory safely')
    return int(result.stdout.strip()) * 1024


def context_hash(role, build_args):
    root = BASE / 'contexts' / role
    files = {}
    for path in sorted(root.rglob('*')):
        if path.is_file():
            if path.name.startswith('.env') or 'credential' in path.name.lower() or path.name.endswith('.key'):
                raise RuntimeError('Forbidden private input in build context')
            files[str(path.relative_to(root))] = hashlib.sha256(path.read_bytes()).hexdigest()
    raw = json.dumps({'files': files, 'args': build_args, 'platform': 'linux/amd64'}, sort_keys=True).encode()
    return hashlib.sha256(raw).hexdigest(), files


def run_build(command, logfile, before, helper):
    fd = os.open(logfile, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'wb') as out:
        process = subprocess.Popen(command, stdout=out, stderr=subprocess.STDOUT)
        started = time.monotonic()
        try:
            while process.poll() is None:
                time.sleep(10)
                stable(before, snapshot())
                if available_memory(helper) < 2 * 1024**3:
                    raise RuntimeError('Engine memory headroom dropped below 2 GiB; stop and wait for Intel guest')
                if time.monotonic() - started > 900:
                    raise RuntimeError('Build exceeded 15 minute limit; wait for Intel guest')
            if process.returncode:
                raise RuntimeError('Build failed; inspect private log ' + logfile.name)
        except BaseException:
            process.terminate()
            try:
                process.wait(timeout=20)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            raise


def smoke(role, tag):
    if role == 'frontend':
        args = ['--entrypoint', 'sh', tag, '-ec',
                'test -f /var/www/app/css/selfhost-sidebar.css; '
                'test ! -e /var/www/app/js/selfhost-login-defaults.js; '
                'test ! -e /etc/nginx/overrides/server.d/selfhost-login.conf; '
                'echo frontend-safe-assets-ok']
    elif role == 'worker':
        args = ['--entrypoint', 'node', tag, '--input-type=module', '-e',
                "import fs from 'node:fs';import {chromium} from 'playwright';"
                "fs.accessSync('dist/index.js');if(process.arch!=='x64'||!chromium)process.exit(2);"
                "console.log('amd64-worker-modules-ok')"]
    else:
        args = ['--entrypoint', 'node', tag, '--input-type=module', '-e',
                "import fs from 'node:fs';import {McpServer} from '@modelcontextprotocol/sdk/server/mcp.js';"
                "import ipaddr from 'ipaddr.js';import transit from 'transit-js';"
                "fs.accessSync('dist/index.js');if(process.arch!=='x64'||!McpServer||!ipaddr||!transit)process.exit(2);"
                "console.log('amd64-import-modules-ok')"]
    result = subprocess.run(DOCKER + ['run', '--rm', '--platform', 'linux/amd64', '--network', 'none',
                            '--read-only', '--memory', '512m', '--memory-swap', '512m', '--cpus', '1',
                            '-e', 'NODE_OPTIONS=--max-old-space-size=256', *args],
                            capture_output=True, text=True, timeout=60)
    if result.returncode:
        raise RuntimeError('New target image isolated smoke test failed: ' + role)
    return result.stdout.strip()


def main():
    global DOCKER
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['check', 'build-and-save'])
    args = parser.parse_args()
    if sys.platform != 'darwin':
        raise RuntimeError('This independent artifact helper is scoped to the current Mac source host')
    lock = json.loads((BASE / 'images.lock.json').read_text())
    source_lock = json.loads((BASE / 'source-runtime.lock.json').read_text())
    context = subprocess.run(['docker', 'context', 'show'], capture_output=True, text=True, check=True).stdout.strip()
    if context != source_lock['docker_context']:
        raise RuntimeError('Unexpected source Docker context')
    raw = json.loads(subprocess.run(['docker', 'context', 'inspect', context], capture_output=True, text=True, check=True).stdout)[0]
    endpoint = raw['Endpoints']['docker']['Host']
    if not endpoint.startswith('unix://'):
        raise RuntimeError('Local Unix Docker endpoint required')
    OUTPUT.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(OUTPUT, 0o700)
    client = OUTPUT / 'public-only-docker-client'
    client.mkdir(exist_ok=True, mode=0o700)
    plugin_dirs = [str(Path.home() / '.docker' / 'cli-plugins'), '/usr/local/lib/docker/cli-plugins', '/opt/homebrew/lib/docker/cli-plugins']
    (client / 'config.json').write_text(json.dumps({'auths': {}, 'cliPluginsExtraDirs': plugin_dirs}))
    (client / 'config.json').chmod(0o600)
    DOCKER = ['docker', '--config', str(client), '--host', endpoint]
    daemon = query(['info', '--format', '{{json .}}'])
    if daemon['ID'] != source_lock['docker_daemon_id'] or daemon['Architecture'] != 'aarch64':
        raise RuntimeError('Artifact builder is not the expected local ARM64 engine')
    check = subprocess.run(DOCKER + ['buildx', 'version'], capture_output=True, text=True)
    if check.returncode:
        raise RuntimeError('Public-only Docker client cannot locate Buildx')
    before = snapshot()
    helper = lock['images']['postgres']['source_index']
    free = available_memory(helper)
    if free < 3 * 1024**3:
        raise RuntimeError('Less than 3 GiB engine headroom; wait for Intel guest')
    if shutil.disk_usage(OUTPUT).free < 12 * 1024**3:
        raise RuntimeError('Insufficient local disk reserve for build cache and image export')
    build_args = {'PENPOT_FRONTEND_IMAGE': lock['images']['frontend']['target'],
                  'PENPOT_EXPORTER_IMAGE': lock['images']['exporter']['target'],
                  'PENPOT_MCP_IMAGE': lock['images']['mcp']['target'],
                  'PENPOT_EXPORTER_BUILD_IMAGE': lock['images']['exporter']['source_index']}
    hashes = {role: context_hash(role, build_args) for role in TAGS}
    if args.action == 'check':
        print('Local artifact preflight passed; anonymous public client, 3 new tags, native JS build + AMD64 runtime.')
        return
    archive = OUTPUT / 'custom-penpot-amd64-images.tar'
    if archive.exists() or archive.with_suffix('.tar.partial').exists():
        raise RuntimeError('Artifact archive already exists; refusing to overwrite it')
    images = {}
    began = datetime.datetime.now(ZoneInfo('Asia/Shanghai')).isoformat()
    for role, tag in TAGS.items():
        signature, files = hashes[role]
        existing = subprocess.run(DOCKER + ['image', 'inspect', tag], capture_output=True, text=True)
        if existing.returncode == 0:
            image = json.loads(existing.stdout)[0]
            labels = image['Config'].get('Labels') or {}
            if image['Architecture'] != 'amd64' or labels.get('io.dell.penpot.context-sha256') != signature:
                raise RuntimeError('Target tag already exists with different contents; never overwrite: ' + tag)
        else:
            if available_memory(helper) < 3 * 1024**3:
                raise RuntimeError('Engine headroom too low for the next sequential build')
            logfile = OUTPUT / ('build-' + role + '-' + str(int(time.time())) + '.log')
            command = DOCKER + ['buildx', 'build', '--builder', 'default', '--platform', 'linux/amd64',
                       '--load', '--progress', 'plain', '--tag', tag,
                       '--label', 'io.dell.penpot.context-sha256=' + signature,
                       '--label', 'io.dell.penpot.artifact=amd64-migration',
                       '--label', 'io.dell.penpot.source-release=2.18.5']
            for key, value in build_args.items():
                command += ['--build-arg', key + '=' + value]
            command += [str(BASE / 'contexts' / role)]
            print('Building new artifact sequentially:', tag, flush=True)
            run_build(command, logfile, before, helper)
        image = query(['image', 'inspect', tag])[0]
        if image['Architecture'] != 'amd64' or image['Os'] != 'linux':
            raise RuntimeError('Final image platform mismatch: ' + tag)
        images[role] = {'tag': tag, 'id': image['Id'], 'platform': 'linux/amd64',
                        'context_sha256': signature, 'files': files, 'smoke': smoke(role, tag)}
        stable(before, snapshot())
        print('Artifact platform and isolated module/assets check passed:', role, flush=True)
    partial = archive.with_suffix('.tar.partial')
    result = subprocess.run(DOCKER + ['image', 'save', '--platform', 'linux/amd64',
                            '--output', str(partial), *TAGS.values()], capture_output=True, text=True, timeout=600)
    if result.returncode:
        raise RuntimeError('Image export failed; partial archive retained privately')
    partial.chmod(0o600)
    partial.rename(archive)
    with archive.open('rb') as file:
        sha = hashlib.file_digest(file, 'sha256').hexdigest()
    after = snapshot()
    stable(before, after)
    receipt = {'started_at': began, 'finished_at': datetime.datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),
               'scope': 'artifact-prep only; no deployment or source data migration',
               'archive': archive.name, 'bytes': archive.stat().st_size, 'sha256': sha,
               'images': images, 'build_args': build_args, 'source_before': before,
               'source_after': after, 'source_containers_and_tags_unchanged': True,
               'credentials_used_for_build': False, 'source_volumes_mounted': False,
               'runtime_acceptance': 'pending on Intel guest'}
    (OUTPUT / 'custom-penpot-amd64-images.json').write_text(json.dumps(receipt, indent=2) + '\n')
    (OUTPUT / 'custom-penpot-amd64-images.sha256').write_text(sha + '  ' + archive.name + '\n')
    print('Saved AMD64 artifact archive, checksum, context hashes and unchanged-source evidence.', flush=True)


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print('ARTIFACT PREP STOPPED: ' + str(error), file=sys.stderr)
        sys.exit(1)
