#!/usr/bin/env python3
"""Application API on owned target only; new target identities never leave guest."""
import argparse
import datetime
import hashlib
import http.cookiejar
import json
import os
from pathlib import Path
import re
import secrets
import sys
import urllib.error
import urllib.request

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))
from target_guard import verify_target
PRIVATE = Path('/etc/penpot')
DATA = Path('/srv/penpot/application-import')
ORIGIN = 'http://127.0.0.1:9001'


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):return None


class API:
    def __init__(self, role):
        self.cookie = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}),
            urllib.request.HTTPCookieProcessor(self.cookie), NoRedirect())
        item = json.loads((PRIVATE / 'new-identities.json').read_text())[role]
        self.call('login-with-password', {'email': item['email'], 'password': item['password']})
        if not list(self.cookie):raise RuntimeError('Fresh target login failed')

    def request(self, method, body, content_type='application/json', stream=False):
        req = urllib.request.Request(ORIGIN + '/api/main/methods/' + method, data=body, method='POST',
            headers={'Content-Type': content_type, 'Accept': 'application/json, text/event-stream'})
        try:
            with self.opener.open(req, timeout=600 if stream else 30) as response:return response.read()
        except urllib.error.HTTPError as error:
            error.read()
            raise RuntimeError('Target API ' + method + ' HTTP ' + str(error.code)) from None

    def call(self, method, params):
        raw = self.request(method, json.dumps(params).encode())
        return json.loads(raw) if raw.strip() else None

    def import_file(self, path, name, project):
        boundary = 'dell-' + secrets.token_hex(12)
        parts = []
        for key, value in [('project-id', project), ('name', name)]:
            parts.append(('--' + boundary + '\r\nContent-Disposition: form-data; name="' + key + '"\r\n\r\n' + value + '\r\n').encode())
        parts.append(('--' + boundary + '\r\nContent-Disposition: form-data; name="file"; filename="migration.penpot"\r\nContent-Type: application/octet-stream\r\n\r\n').encode())
        parts += [path.read_bytes(), ('\r\n--' + boundary + '--\r\n').encode()]
        raw = self.request('import-binfile', b''.join(parts), 'multipart/form-data; boundary=' + boundary, stream=True)
        complete = False
        for event in raw.decode().replace('\r\n', '\n').split('\n\n'):
            lines = event.splitlines()
            kind = next((x.split(':', 1)[1].strip() for x in lines if x.startswith('event:')), '')
            if kind == 'error':raise RuntimeError('Official target import rejected; no automatic retry')
            if kind == 'end':complete = True
        if not complete:raise RuntimeError('Official import completion unconfirmed; inspect target before retry')


def field(row, *names):return next((row[x] for x in names if x in row), None)


def save(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')
    path.chmod(0o600)


def migrate():
    verify_target(require_docker_data=True)
    source = json.loads((DATA / 'inventory.json').read_text())
    exported = json.loads((DATA / 'exports.json').read_text())
    if not exported['complete'] or len(exported['exports']) != len(source['files']):raise RuntimeError('Incomplete source export manifest')
    for item in exported['exports']:
        path = DATA / item['file']
        with path.open('rb') as file:
            if hashlib.file_digest(file, 'sha256').hexdigest() != item['sha256']:raise RuntimeError('Official archive checksum mismatch')
    owner = API('owner')
    ledger_path = PRIVATE / 'application-id-map.json'
    ledger = json.loads(ledger_path.read_text()) if ledger_path.exists() else {'teams': {}, 'projects': {}, 'files': {}, 'source_session_or_identity_imported': False, 'inflight': None}
    if ledger.get('inflight'):raise RuntimeError('Unconfirmed prior import; inspect target state instead of blindly retrying')
    for team in source['teams']:
        if team['id'] not in ledger['teams']:
            new = owner.call('create-team', {'name': team['name']})
            ledger['teams'][team['id']] = {'target_id': new['id'], 'name': team['name']}
            save(ledger_path, ledger)
    for project in source['projects']:
        if project.get('deleted_at'):continue
        if project['id'] in ledger['projects']:continue
        team = ledger['teams'][project['team_id']]['target_id']
        if project['is_default']:
            projects = owner.call('get-projects', {'team-id': team})
            target = next(p for p in projects if field(p, 'is-default', 'isDefault'))
        else:target = owner.call('create-project', {'team-id': team, 'name': project['name']})
        ledger['projects'][project['id']] = {'target_id': target['id'], 'name': project['name'], 'target_team_id': team}
        save(ledger_path, ledger)
    for item in exported['exports']:
        old_id = item['source_file_id']
        if old_id in ledger['files']:continue
        project = ledger['projects'][item['source_project_id']]['target_id']
        before = owner.call('get-project-files', {'project-id': project})
        before_ids = {x['id'] for x in before}
        ledger['inflight'] = {'source_file_id': old_id, 'target_project_id': project, 'before_ids': sorted(before_ids)}
        save(ledger_path, ledger)
        owner.import_file(DATA / item['file'], item['name'], project)
        after = owner.call('get-project-files', {'project-id': project})
        added = [x for x in after if x['id'] not in before_ids]
        if len(added) != 1 or added[0]['name'] != item['name']:
            raise RuntimeError('Import result cardinality/name ambiguous; do not retry blindly')
        new = added[0]
        ledger['files'][old_id] = {'target_id': new['id'], 'name': item['name'], 'source_export_sha256': item['sha256'],
            'target_project_id': project, 'target_team_id': ledger['projects'][item['source_project_id']]['target_team_id'],
            'imported_at': datetime.datetime.now(datetime.timezone.utc).isoformat()}
        ledger['inflight'] = None
        save(ledger_path, ledger)
        print(json.dumps({'imported_active_files': len(ledger['files']), 'source_id': old_id, 'target_id': new['id']}), flush=True)
    ledger['active_file_count'] = len(source['files'])
    ledger['source_library_edges'] = sum(len(x) for x in source['library_relations'].values())
    ledger['recoverable_deleted_projects_not_activated'] = sum(bool(x.get('deleted_at')) for x in source['projects'])
    ledger['active_content_complete'] = len(ledger['files']) == len(source['files'])
    save(ledger_path, ledger)
    print(json.dumps({'active_content_complete': ledger['active_content_complete'], 'files': len(ledger['files']), 'source_library_edges': ledger['source_library_edges']}), flush=True)


def automation():
    verify_target(require_docker_data=True)
    owner, worker = API('owner'), API('worker')
    owner_profile = owner.call('get-profile', {})
    worker_profile = worker.call('get-profile', {})
    team = field(owner_profile, 'default-team-id', 'defaultTeamId')
    project = field(owner_profile, 'default-project-id', 'defaultProjectId')
    if not team or not project:raise RuntimeError('New owner default workspace not confirmed')
    setup_path = PRIVATE / 'automation-setup.json'
    setup = json.loads(setup_path.read_text()) if setup_path.exists() else {}
    if 'file_id' not in setup:
        file = owner.call('create-file', {'project-id': project, 'name': 'Dell dedicated MCP acceptance'})
        full = file if isinstance(file.get('data'), dict) and file['data'].get('pages') else owner.call('get-file', {'id': file['id']})
        pages = full.get('data', {}).get('pages', [])
        if not pages:raise RuntimeError('Fresh dedicated file page not confirmed')
        setup.update(file_id=file['id'], page_id=pages[0], team_id=team, dedicated_acceptance_only=True)
        save(setup_path, setup)
    members = owner.call('get-team-members', {'team-id': team})
    if not any(x['id'] == worker_profile['id'] for x in members):
        email = json.loads((PRIVATE / 'new-identities.json').read_text())['worker']['email']
        owner.call('create-team-invitations', {'team-id': team, 'invitations': [{'email': email, 'role': 'editor'}]})
    members = owner.call('get-team-members', {'team-id': team})
    if not any(x['id'] == worker_profile['id'] for x in members):raise RuntimeError('New worker membership not confirmed')
    worker.call('update-profile-props', {'props': {'mcp-enabled': True}})
    tokens = worker.call('get-access-tokens', {})
    token = next((x['token'] for x in tokens if x.get('type') == 'mcp' and x.get('token')), None)
    if not token:token = worker.call('create-access-token', {'name': 'dell-resident-worker', 'type': 'mcp'})['token']
    item = json.loads((PRIVATE / 'new-identities.json').read_text())['worker']
    creds = json.dumps({'email': item['email'], 'password': item['password'], 'mcpKey': token}) + '\n'
    for filename, uid in [('worker-credentials.json', 0), ('worker-credentials.uid1001.json', 1001), ('worker-credentials.uid1000.json', 1000)]:
        path = PRIVATE / filename;path.write_text(creds);path.chmod(0o600);os.chown(path, uid, uid)
    env = {}
    for line in (PRIVATE / '.env').read_text().splitlines():
        k,v=line.split('=',1);env[k]=v[1:-1] if v.startswith("'") and v.endswith("'") else v
    env.update(PENPOT_WORKER_TEAM_ID=team, PENPOT_WORKER_FILE_ID=setup['file_id'], PENPOT_WORKER_PAGE_ID=setup['page_id'])
    path=PRIVATE/'.env';path.write_text(''.join(k+"='"+v+"'\n" for k,v in env.items()));path.chmod(0o600)
    save(PRIVATE/'automation-ready.json', {'team_id': team, 'file_id': setup['file_id'], 'page_id': setup['page_id'], 'new_identity': True, 'source_identity_copied': False, 'dedicated_acceptance_only': True})
    print(json.dumps({'automation_identity_configured': True, 'mcp_key_values_emitted': False, 'dedicated_file_id': setup['file_id'], 'source_designs_modified': False}))


def verify():
    verify_target(require_docker_data=True)
    owner = API('owner')
    ledger=json.loads((PRIVATE/'application-id-map.json').read_text())
    results={}
    for old,item in ledger['files'].items():results[old]={'target_id':item['target_id'],'stats':owner.call('get-file-stats',{'id':item['target_id']})}
    save(PRIVATE/'application-target-stats.json',results)
    print(json.dumps({'imported_files_readable':len(results),'stats':results}))


if __name__ == '__main__':
    p = argparse.ArgumentParser();p.add_argument('action', choices=['migrate', 'automation', 'verify']);args = p.parse_args()
    try:{'migrate': migrate, 'automation': automation, 'verify': verify}[args.action]()
    except Exception as error:
        print('APPLICATION MIGRATION ERROR: ' + str(error), file=sys.stderr)
        sys.exit(1)
