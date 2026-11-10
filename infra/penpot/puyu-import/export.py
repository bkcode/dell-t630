#!/usr/bin/env python3
"""Export the one confirmed local Puyu design; no source designs are edited."""
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import zipfile
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'private/penpot/puyu-import-20261110'
FILE = '9eb8678d-764d-810b-8008-e237712e9048'
PAGES = ['puyu-mobile', 'puyu-components', 'puyu-mobile · 商城']


def main():
    os.umask(0o077)
    spec = importlib.util.spec_from_file_location('local_source_api', ROOT / 'infra/penpot/application/source-files.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    api = module.Source(json.loads((ROOT.parent / 'penpot/.local-credentials.json').read_text()))
    before = api.read('get-file', {'id': FILE})
    data = before['data']
    pages = module.key(data, 'pages-index', 'pagesIndex')
    names = [pages[identity]['name'] for identity in data['pages']]
    if names != PAGES:
        raise RuntimeError('confirmed-three-Puyu-pages-required')
    libraries = api.read('get-file-libraries', {'file-id': FILE})
    if libraries:
        raise RuntimeError('external-libraries-require-separate-dependency-plan')
    stats = api.read('get-file-stats', {'id': FILE})
    archive = OUT / 'puyu.penpot'
    manifest = OUT / 'export.json'
    if archive.exists() or manifest.exists():
        raise RuntimeError('existing-export-snapshot-must-not-be-replaced')
    raw = api.call('export-binfile', {'file-id': FILE, 'include-libraries': True, 'embed-assets': False}, stream=True)
    uri = None
    for event in raw.decode().replace('\r\n', '\n').split('\n\n'):
        lines = event.splitlines()
        kind = next((line.split(':', 1)[1].strip() for line in lines if line.startswith('event:')), '')
        if kind == 'error':
            raise RuntimeError('official-export-error-no-retry')
        if kind == 'end':
            value = json.loads('\n'.join(line.split(':', 1)[1].lstrip() for line in lines if line.startswith('data:')))
            uri = value.get('~#uri') if isinstance(value, dict) else value
    if not isinstance(uri, str):
        raise RuntimeError('official-export-completion-unconfirmed')
    body = api.download(uri)
    if not body.startswith(b'PK'):
        raise RuntimeError('official-ZIP-required')
    fd = os.open(archive, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(body)
    with zipfile.ZipFile(archive) as zipped:
        if zipped.testzip() is not None:
            raise RuntimeError('archive-CRC-failed')
        members = zipped.namelist()
        if any(Path(name).is_absolute() or '..' in Path(name).parts for name in members):
            raise RuntimeError('unsafe-archive-member')
    after = api.read('get-file', {'id': FILE})
    if (before.get('revn'), before.get('vern'), before['data']) != (after.get('revn'), after.get('vern'), after['data']):
        raise RuntimeError('source-edited-during-export-do-not-import')
    result = {'captured_at': datetime.datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),
        'source_file_id': FILE, 'source_name': before['name'], 'source_revn': before.get('revn'),
        'source_vern': before.get('vern'), 'pages': PAGES, 'page_object_counts':
        {identity: len(pages[identity].get('objects', {})) for identity in data['pages']},
        'source_stats': stats, 'archive': archive.name, 'archive_bytes': len(body),
        'archive_SHA256': hashlib.sha256(body).hexdigest(), 'zip_members': len(members),
        'external_library_edges': 0, 'include_libraries': True, 'embed_assets': False,
        'source_unchanged_after_export': True, 'target_project_name': 'puyu', 'target_file_name': 'puyu'}
    fd = os.open(manifest, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    print(json.dumps({key: value for key, value in result.items() if key != 'archive_SHA256'}, ensure_ascii=False))


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(json.dumps({'status': 'export-not-confirmed', 'error_type': type(error).__name__,
                          'code': str(error) if isinstance(error, RuntimeError) else 'private-details-withheld'}))
        raise SystemExit(1)
