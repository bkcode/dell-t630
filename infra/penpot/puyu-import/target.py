#!/usr/bin/env python3
"""One new Puyu project/file via official API; original target designs untouched."""
import argparse
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import uuid
import zipfile
from zoneinfo import ZoneInfo

BASE = Path('/opt/dell/penpot')
DATA = Path('/srv/penpot/application-import-puyu-20261110')
JOURNAL = Path('/etc/penpot/puyu-import-20261110.json')
D = ['docker', '--host', 'unix:///var/run/docker.sock']
SOURCE_FILE = '9eb8678d-764d-810b-8008-e237712e9048'
PAGES = ['puyu-mobile', 'puyu-components', 'puyu-mobile · 商城']


def need(value, code):
    if not value:
        raise RuntimeError(code)


def save(path, value):
    temporary = path.with_name(path.name + '.' + uuid.uuid4().hex)
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def run(args):
    result = subprocess.run(args, capture_output=True, timeout=40)
    need(result.returncode == 0, 'fixed-readonly-operation-failed')
    return result.stdout


def guard():
    need(os.geteuid() == 0 and socket.gethostname() == 'penpot-service'
         and not Path('/etc/pve').exists(), 'VM250-only')
    fs = json.loads(run(['findmnt', '--json', '--mountpoint', '/srv/penpot', '--output', 'UUID']))['filesystems']
    need(len(fs) == 1 and fs[0]['uuid'] == 'ccccda03-bffd-4054-afd3-e0e22f0c607e', 'existing-volume-required')
    run(['python3', '-I', '-B', str(BASE / 'runtime/health-supervision/supervisor.py'), 'check'])
    need(subprocess.run(['systemctl', 'is-active', '--quiet', 'dell-penpot.service']).returncode == 0,
         'healthy-supervised-service-required')
    ids = run(D + ['ps', '-q', '--filter', 'label=com.docker.compose.project=penpot']).decode().split()
    need(len(ids) == 11 and all(run(D + ['inspect', '--format', '{{.State.Health.Status}}', identity]).strip()
                              == b'healthy' for identity in ids), 'exact11-healthy-required')


def api():
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location('existing_target_api', BASE / 'application/target-api.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, module.API('owner')


def canonical(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                   separators=(',', ':')).encode()).hexdigest()


def original_snapshot(client):
    originals = {}
    for team in client.call('get-teams', {}):
        for project in client.call('get-projects', {'team-id': team['id']}):
            for row in client.call('get-project-files', {'project-id': project['id']}):
                full = client.call('get-file', {'id': row['id']})
                originals[row['id']] = {'name': full['name'], 'project_id': project['id'],
                    'revn': full.get('revn'), 'vern': full.get('vern'), 'data_SHA256': canonical(full['data'])}
    return originals


def check_originals(client, before):
    for identity, expected in before.items():
        full = client.call('get-file', {'id': identity})
        actual = {'name': full['name'], 'project_id': full.get('projectId', full.get('project-id')),
                  'revn': full.get('revn'), 'vern': full.get('vern'), 'data_SHA256': canonical(full['data'])}
        need(actual == expected, 'original-target-design-changed-do-not-retry')


def archive_manifest():
    for path, mode in [(DATA, 0o700), (DATA / 'export.json', 0o600), (DATA / 'puyu.penpot', 0o600)]:
        need(path.resolve() == path and path.lstat().st_uid == 0 and path.stat().st_mode & 0o777 == mode,
             'protected-root-owned-nonsymlink-transfer-required')
    manifest = json.loads((DATA / 'export.json').read_text())
    need(manifest['source_file_id'] == SOURCE_FILE and manifest['pages'] == PAGES
         and manifest['source_unchanged_after_export'] and manifest['external_library_edges'] == 0,
         'exact-confirmed-Puyu-export-required')
    archive = DATA / 'puyu.penpot'
    with archive.open('rb') as stream:
        need(hashlib.file_digest(stream, 'sha256').hexdigest() == manifest['archive_SHA256'], 'archive-transfer-mismatch')
    need(archive.stat().st_size == manifest['archive_bytes'] < 300 * 1024**2, 'bounded-official-archive-required')
    with zipfile.ZipFile(archive) as zipped:
        index = json.loads(zipped.read('manifest.json'))
        need(len(index['files']) == 1 and index['files'][0]['id'] == SOURCE_FILE, 'one-Puyu-file-required')
    return manifest, archive


def import_new():
    guard()
    need(not JOURNAL.exists(), 'prior-transaction-requires-reconciliation-no-retry')
    manifest, archive = archive_manifest()
    module, client = api()
    profile = client.call('get-profile', {})
    team = module.field(profile, 'defaultTeamId', 'default-team-id')
    need(bool(team), 'owner-default-team-required')
    projects = client.call('get-projects', {'team-id': team})
    need(not any(project['name'].casefold() == 'puyu' for project in projects), 'Puyu-project-name-conflict')
    before = original_snapshot(client)
    record = {'status': 'project-create-inflight', 'source_file_id': SOURCE_FILE,
              'source_revn': manifest['source_revn'], 'archive_SHA256': manifest['archive_SHA256'],
              'team_id': team, 'target_project_name': 'puyu', 'original_files': before}
    save(JOURNAL, record)
    project = client.call('create-project', {'team-id': team, 'name': 'puyu'})
    record.update(status='project-created', project_id=project['id'])
    save(JOURNAL, record)
    need(not client.call('get-project-files', {'project-id': project['id']}), 'new-project-must-be-empty')
    record['status'] = 'file-import-inflight'
    save(JOURNAL, record)
    client.import_file(archive, 'puyu', project['id'])
    added = client.call('get-project-files', {'project-id': project['id']})
    need(len(added) == 1, 'one-import-result-required-no-retry')
    record.update(status='file-imported', file_id=added[0]['id'])
    save(JOURNAL, record)
    # The official ZIP importer can preserve the manifest name; rename this new copy only.
    if added[0]['name'] != 'puyu':
        client.call('rename-file', {'id': added[0]['id'], 'name': 'puyu'})
    verify()


def verify():
    guard()
    manifest, _ = archive_manifest()
    record = json.loads(JOURNAL.read_text())
    need(record['status'] in ['file-imported', 'verified'], 'unconfirmed-import-do-not-retry')
    module, client = api()
    full = client.call('get-file', {'id': record['file_id']})
    need(full['name'] == 'puyu', 'target-Puyu-name-required')
    data = full['data']
    index = module.field(data, 'pagesIndex', 'pages-index')
    names = [index[identity]['name'] for identity in data['pages']]
    counts = {identity: len(index[identity].get('objects', {})) for identity in data['pages']}
    need(names == PAGES and counts == manifest['page_object_counts'], 'page-order-or-object-count-mismatch')
    stats = client.call('get-file-stats', {'id': record['file_id']})
    stable = ['pageCount', 'shapeCounts', 'deletedComponentCount', 'typographyCount',
              'componentCount', 'colorCount', 'libraryCount', 'referencedByCount']
    need({key: stats.get(key) for key in stable} == {key: manifest['source_stats'].get(key) for key in stable},
         'source-target-semantic-statistics-mismatch')
    need(not client.call('get-file-libraries', {'file-id': record['file_id']}), 'unexpected-library-relations')
    check_originals(client, record['original_files'])
    record.update(status='verified', verified_at=datetime.datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),
                  page_names=names, page_object_counts=counts, source_target_stats_equal=True,
                  original_files_unchanged=True)
    save(JOURNAL, record)
    result = {'captured_at': record['verified_at'], 'status': 'Puyu-project-imported-and-API-verified',
              'team_id': record['team_id'], 'project_id': record['project_id'], 'file_id': record['file_id'],
              'name': 'puyu', 'pages': names, 'objects_per_page': list(counts.values()),
              'shapes': stats['shapeCounts']['total'], 'components': stats['componentCount'],
              'source_target_semantic_statistics_equal': True,
              'protected_original_files': len(record['original_files']), 'original_files_unchanged': True,
              'source_identity_or_password_imported': False, 'service_restarted': False,
              'real_browser_verification_pending': True}
    save(DATA / 'result.json', result)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    os.umask(0o077)
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['import', 'verify'])
    args = parser.parse_args()
    try:
        import_new() if args.action == 'import' else verify()
    except Exception as error:
        print(json.dumps({'status': 'Puyu-import-not-confirmed-no-automatic-retry',
                          'error_type': type(error).__name__,
                          'code': str(error) if isinstance(error, RuntimeError) else 'private-details-withheld'}))
        sys.exit(1)
