"""Read-only source daemon, exact image and version attestation for cold snapshots."""
import json
from pathlib import Path
import subprocess

BASE = Path(__file__).resolve().parent


def query(command):
    result = subprocess.run(command, capture_output=True, text=True, timeout=30)
    if result.returncode:
        raise RuntimeError('Source attestation query failed; details suppressed')
    return json.loads(result.stdout)


def image_meta(image):
    raw = query(['docker', 'image', 'inspect', image])[0]
    labels = raw.get('Config', {}).get('Labels') or {}
    versions = {key: labels[key] for key in ('version', 'bundle_version', 'org.opencontainers.image.version') if key in labels}
    pg_version = next((x.split('=', 1)[1] for x in raw.get('Config', {}).get('Env', []) if x.startswith('PG_VERSION=')), None)
    return {'id': raw['Id'], 'repo_digests': raw.get('RepoDigests', []),
            'architecture': raw.get('Architecture'), 'versions': versions, 'postgres_package_version': pg_version}


def same_image(observed, expected):
    fields = ('id', 'architecture', 'versions', 'postgres_package_version')
    return (all(observed.get(k) == expected.get(k) for k in fields)
            and set(expected.get('repo_digests', [])).issubset(observed.get('repo_digests', [])))


def verify_source():
    lock = json.loads((BASE / 'source-runtime.lock.json').read_text())
    context = subprocess.run(['docker', 'context', 'show'], capture_output=True, text=True, timeout=10)
    if context.returncode or context.stdout.strip() != lock['docker_context']:
        raise RuntimeError('Source Docker context differs from the captured source')
    daemon = query(['docker', 'info', '--format', '{{json .}}'])
    if daemon.get('ID') != lock['docker_daemon_id']:
        raise RuntimeError('Source Docker daemon identity mismatch')
    index_images = {}
    for role, expected in lock['index_images'].items():
        observed = image_meta(expected['source_index'])
        if not same_image(observed, expected['observed']) or expected['source_index'] not in observed['repo_digests']:
            raise RuntimeError('Source index/image drift: ' + role)
        index_images[role] = {'source_index': expected['source_index'], 'observed': observed}
    containers = {}
    for name, expected in lock['containers'].items():
        raw = query(['docker', 'inspect', name])[0]
        observed = image_meta(raw['Image'])
        if not same_image(observed, expected):
            raise RuntimeError('Source container image/version drift: ' + name)
        containers[name] = observed
    if 'nexus3' in containers:
        actual_release = containers['nexus3']['versions'].get('version')
    else:
        backend = next(value for name, value in containers.items() if name.endswith('penpot-backend-1'))
        actual_release = backend['versions']['bundle_version'].split('-', 1)[0]
    if actual_release != lock['application_release']:
        raise RuntimeError('Actual source application release does not match the migration plan')
    return {'application_release': actual_release,
            'docker_daemon_id': daemon['ID'], 'docker_context': lock['docker_context'],
            'index_images': index_images, 'containers': containers}


if __name__ == '__main__':
    source = verify_source()
    print('Source attestation passed: release=' + source['application_release']
          + ', indexes=' + str(len(source['index_images']))
          + ', containers=' + str(len(source['containers']))
          + '; no data exported')
