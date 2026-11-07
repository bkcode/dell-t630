#!/usr/bin/env python3
"""Anonymous Mac-loopback hosted export only. Never follows downloadUrl/proxy URL."""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'private/nexus/application-export'
BASE = 'http://127.0.0.1:8081'


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())


def get_json(path):
    with OPENER.open(BASE + path, timeout=30) as response:
        return json.load(response)


def save(path, value):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'w') as file:
        json.dump(value, file, indent=2)
        file.write('\n')


def main():
    os.umask(0o077)
    OUT.mkdir(parents=True, exist_ok=True, mode=0o700)
    records = []
    repositories = [r for r in get_json('/service/rest/v1/repositories') if r['type'] == 'hosted']
    for repo in repositories:
        components = []
        token = None
        while True:
            params = {'repository': repo['name']}
            if token:
                params['continuationToken'] = token
            page = get_json('/service/rest/v1/components?' + urllib.parse.urlencode(params))
            components.extend(page['items'])
            token = page.get('continuationToken')
            if not token:
                break
        component_by_asset = {asset['id']: component for component in components for asset in component['assets']}
        all_assets = []
        token = None
        while True:
            params = {'repository': repo['name']}
            if token:params['continuationToken'] = token
            page = get_json('/service/rest/v1/assets?' + urllib.parse.urlencode(params))
            all_assets.extend(page['items']);token = page.get('continuationToken')
            if not token:break
        for asset in all_assets:
                component = component_by_asset.get(asset['id'], {})
                raw_path = asset['path']
                if raw_path.startswith('//') or '://' in raw_path:
                    raise RuntimeError('Hosted path is not a local repository path')
                relative = PurePosixPath(raw_path[1:] if raw_path.startswith('/') else raw_path)
                if relative.is_absolute() or '..' in relative.parts or not relative.parts:
                    raise RuntimeError('Unsafe hosted asset path')
                destination = OUT / 'assets' / repo['name'] / relative
                destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                url_path = '/repository/' + urllib.parse.quote(repo['name'], safe='') + '/' + '/'.join(urllib.parse.quote(x, safe='') for x in relative.parts)
                # Only localhost hosted storage is requested; never trust downloadUrl.
                if not destination.exists():
                    partial = destination.with_name(destination.name + '.part')
                    if partial.exists():
                        raise RuntimeError('Partial export exists; review before retry')
                    fd = os.open(partial, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                    with os.fdopen(fd, 'wb') as file, OPENER.open(BASE + url_path, timeout=120) as response:
                        while True:
                            data = response.read(1024 * 1024)
                            if not data:
                                break
                            file.write(data)
                    partial.rename(destination)
                with destination.open('rb') as file:
                    sha256 = hashlib.file_digest(file, 'sha256').hexdigest()
                for algorithm, expected in asset.get('checksum', {}).items():
                    if algorithm in ('sha1', 'md5', 'sha256', 'sha512'):
                        with destination.open('rb') as file:
                            actual = hashlib.file_digest(file, algorithm).hexdigest()
                        if actual.lower() != expected.lower():
                            raise RuntimeError('Hosted asset checksum mismatch: ' + asset['id'])
                records.append({'source_asset_id': asset['id'], 'source_component_id': component.get('id'),
                    'source_repository': repo['name'], 'format': repo['format'], 'group': component.get('group'),
                    'name': component.get('name'), 'version': component.get('version'), 'path': asset['path'],
                    'source_api_checksums': asset.get('checksum', {}), 'maven2': asset.get('maven2', {}),
                    'classification': 'checksum' if destination.suffix.lower() in ('.md5','.sha1','.sha256','.sha512') else ('maven-metadata' if destination.name=='maven-metadata.xml' else 'primary'),
                    'extension': destination.suffix.lstrip('.'), 'normalized_path': str(relative), 'file': str(destination.relative_to(OUT)), 'bytes': destination.stat().st_size, 'sha256': sha256})
                if len(records) % 50 == 0:
                    save(OUT / 'assets.json', {'complete': False, 'assets': records})
                    print(json.dumps({'hosted_assets_exported': len(records)}), flush=True)
    save(OUT / 'assets.json', {'complete': True, 'source_origin': BASE,
        'repositories': [{k: r[k] for k in ('name', 'format', 'type')} for r in repositories],
        'assets': records, 'proxy_or_group_requests': 0, 'source_authentication_used': False,
        'source_credentials_or_H2_exported': False})
    print(json.dumps({'hosted_assets_exported': len(records), 'bytes': sum(r['bytes'] for r in records),
                      'proxy_or_group_requests': 0, 'source_processes_stopped': False}), flush=True)


if __name__ == '__main__':
    main()
