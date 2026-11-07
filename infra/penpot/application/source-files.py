#!/usr/bin/env python3
"""Official application-level inventory/export. Old identities stay on Mac loopback."""
import argparse
import datetime
import hashlib
import http.cookiejar
import json
import os
from pathlib import Path
import re
import urllib.error
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT.parent / 'penpot'
OUT = ROOT / 'private' / 'penpot' / 'application-export'
BASE = 'http://127.0.0.1:9001'


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


class Source:
    def __init__(self, credentials):
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}),
            urllib.request.HTTPCookieProcessor(self.jar), NoRedirect())
        self.call('login-with-password', {key: credentials[key] for key in ('email', 'password')})
        if not list(self.jar):
            raise RuntimeError('Source authentication did not establish a loopback session')

    def call(self, method, params, stream=False):
        if not re.fullmatch(r'[a-z-]+', method):
            raise RuntimeError('Invalid API method')
        request = urllib.request.Request(BASE + '/api/main/methods/' + method,
            data=json.dumps(params).encode(), method='POST',
            headers={'Content-Type': 'application/json', 'Accept': 'application/json, text/event-stream'})
        try:
            response = self.opener.open(request, timeout=600 if stream else 30)
        except urllib.error.HTTPError as e:
            e.read()
            raise RuntimeError('Source API ' + method + ' HTTP ' + str(e.code)) from None
        with response:
            if stream:
                return response.read()
            return json.load(response)

    def read(self, method, params):
        try:
            return self.call(method, params)
        except RuntimeError as error:
            if 'HTTP 400' not in str(error) or not any('-' in x for x in params):
                raise
            camel = {re.sub(r'-([a-z])', lambda m: m.group(1).upper(), k): v for k, v in params.items()}
            return self.call(method, camel)

    def download(self, uri):
        parsed = urllib.parse.urlsplit(uri)
        if not re.fullmatch(r'/assets/by-id/[0-9a-f-]{36}', parsed.path):
            raise RuntimeError('Export did not return the expected official asset path')
        # Ignore source public hostname. Old cookie is sent only to the Mac loopback origin.
        request = urllib.request.Request(BASE + parsed.path)
        try:
            with self.opener.open(request, timeout=180) as response:
                return response.read()
        except urllib.error.HTTPError as e:
            e.read()
            raise RuntimeError('Source archive download HTTP ' + str(e.code)) from None


def key(row, *names):
    return next((row[n] for n in names if n in row), None)


def save(path, value):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'w') as file:
        json.dump(value, file, indent=2, ensure_ascii=False)
        file.write('\n')


def main():
    os.umask(0o077)
    p = argparse.ArgumentParser()
    p.add_argument('action', choices=['inventory', 'export'])
    args = p.parse_args()
    OUT.mkdir(parents=True, exist_ok=True, mode=0o700)
    identities = [('source-owner', SOURCE / '.local-credentials.json'),
                  ('source-worker', SOURCE / '.worker-credentials.json')]
    clients = {}
    teams, projects, files, libraries, errors = {}, {}, {}, {}, []
    for alias, path in identities:
        if not path.exists():
            errors.append({'identity': alias, 'error': 'known-local-account-file-missing'})
            continue
        try:
            credentials = json.loads(path.read_text())
            client = Source(credentials)
            clients[alias] = client
            ts = client.read('get-teams', {})
            for team in ts:
                tid = team['id'];teams[tid] = {'id': tid, 'name': team.get('name')}
                ps = client.read('get-projects', {'team-id': tid})
                for project in ps:
                    pid = project['id'];projects[pid] = {'id': pid, 'team_id': tid, 'name': project.get('name'), 'is_default': key(project, 'isDefault', 'is-default'), 'deleted_at': key(project, 'deletedAt', 'deleted-at')}
                    fs = client.read('get-project-files', {'project-id': pid})
                    for item in fs:
                        fid = item['id']
                        files.setdefault(fid, {'id': fid, 'team_id': tid, 'project_id': pid, 'name': item.get('name'),
                                               'is_shared': key(item, 'isShared', 'is-shared'), 'readable_by': []})['readable_by'].append(alias)
                        libs = client.read('get-file-libraries', {'file-id': fid})
                        libraries[fid] = [{'id': value['id'], 'name': value.get('name')} for value in libs]
        except (RuntimeError, KeyError, TypeError) as error:
            errors.append({'identity': alias, 'error': str(error)[:180]})
    inventory = {'at': datetime.datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(), 'source_origin': BASE,
                 'runtime_release': '2.18.5-RC1', 'teams': list(teams.values()), 'projects': list(projects.values()),
                 'files': list(files.values()), 'library_relations': libraries, 'errors': errors,
                 'identity_files_copied': False, 'sessions_or_tokens_exported': False,
                 'scope': 'union of known owner/worker account permissions; no source design mutation'}
    save(OUT / 'inventory.json', inventory)
    print(json.dumps({'teams': len(teams), 'projects': len(projects), 'files': len(files),
                      'library_edges': sum(len(x) for x in libraries.values()), 'errors': errors}))
    if errors:
        raise SystemExit('Source inventory incomplete; no export started')
    if args.action == 'inventory':
        return
    exports = []
    for item in files.values():
        filename = item['id'] + '.penpot'
        destination = OUT / filename
        if destination.exists():
            raise SystemExit('Export artifact already exists; refusing to silently replace snapshot')
        client = clients[item['readable_by'][0]]
        params = {'file-id': item['id'], 'include-libraries': True, 'embed-assets': False}
        try:
            raw = client.call('export-binfile', params, stream=True)
        except RuntimeError as error:
            if 'HTTP 400' not in str(error):raise
            raw = client.call('export-binfile', {'fileId': item['id'], 'includeLibraries': True, 'embedAssets': False}, stream=True)
        uri = None
        for event in raw.decode().replace('\r\n', '\n').split('\n\n'):
            lines = event.splitlines()
            event_type = next((x.split(':', 1)[1].strip() for x in lines if x.startswith('event:')), '')
            if event_type == 'error':raise RuntimeError('Official source export rejected; no error body printed')
            if event_type == 'end':
                data = '\n'.join(x.split(':', 1)[1].lstrip() for x in lines if x.startswith('data:'))
                value = json.loads(data)
                if isinstance(value, dict) and set(value) == {'~#uri'} and isinstance(value['~#uri'], str):
                    value = value['~#uri']
                if not isinstance(value, str):
                    save(OUT / 'completion-diagnostic.json', {'value': value})
                    descriptor = {'type': type(value).__name__, 'keys': list(value) if isinstance(value, dict) else None, 'list_prefix': value[0] if isinstance(value, list) and value and isinstance(value[0], str) and len(value[0]) < 30 else None}
                    raise RuntimeError('Official completion shape: ' + json.dumps(descriptor))
                uri = value
        if not uri:raise RuntimeError('Official SSE export completion unconfirmed')
        archive = client.download(uri)
        if not archive.startswith(b'PK'):raise RuntimeError('Official export is not a ZIP .penpot archive')
        fd = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'wb') as output:output.write(archive)
        exports.append({'source_file_id': item['id'], 'source_project_id': item['project_id'], 'source_team_id': item['team_id'],
                        'name': item['name'], 'file': filename, 'bytes': len(archive), 'sha256': hashlib.sha256(archive).hexdigest(),
                        'format': 'official-binfile-v3', 'include_libraries': True, 'embed_assets': False})
        save(OUT / 'exports.json', {'inventory_file_count': len(files), 'exports': exports, 'complete': len(exports) == len(files)})
        print(json.dumps({'exported_files': len(exports), 'source_file_id': item['id'], 'bytes': len(archive)}))


if __name__ == '__main__':
    main()
