#!/usr/bin/python3
"""Bounded VM210 Nacos config replacement worker.

Only imports the reviewed private source manifest.  It does not touch Nacos
users, roles, permissions, services, or any MySQL business schema.  `apply`
never runs unless `prepare` has captured the exact target configuration set.
"""
from __future__ import annotations

import argparse
import datetime as dt
import fcntl
import hashlib
import importlib.util
import json
import os
import re
import socket
import stat
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

BASE = Path('/root/dell-nacos-config-import')
BUNDLE = Path('/opt/dell/data/test-data')
ENDPOINT = 'http://192.168.19.20:8848/nacos'
TARGET_UUID = 'dd1773f9-aa48-4401-a9c8-caf0f66845f3'
SOURCE_NAMESPACES = {
    '08e7191f-3ccd-411a-be00-56798d237533': 'finger-cloud-dev',
    '7bfe03c6-0590-4ff0-8def-e07015016b54': 'finger-trascan',
}
RUN = re.compile(r'[0-9a-f]{32}\Z')
MD5 = re.compile(r'[0-9a-f]{32}\Z')
MAX_CONFIG = 36
MAX_BODY = 1024 * 1024
MAX_JSON = 8 * 1024 * 1024


class Rejected(RuntimeError):
    pass


def need(value: bool, code: str) -> None:
    if not value:
        raise Rejected(code)


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def secure_dir(path: Path, *, create: bool = False) -> None:
    if create and not path.exists():
        path.mkdir(mode=0o700, parents=True)
    need(path.is_absolute() and path.resolve() == path and path.is_dir(), 'private-directory')
    for parent in [path, *path.parents]:
        item = parent.lstat()
        need(stat.S_ISDIR(item.st_mode) and item.st_uid == 0 and not item.st_mode & 0o022,
             'private-directory-owner-mode')
    need(stat.S_IMODE(path.stat().st_mode) == 0o700, 'private-directory-mode')


def read_json(path: Path, *, limit: int = MAX_JSON) -> dict:
    entry = path.lstat()
    need(not path.is_symlink() and stat.S_ISREG(entry.st_mode) and entry.st_uid == 0
         and entry.st_nlink == 1 and stat.S_IMODE(entry.st_mode) == 0o600
         and 0 < entry.st_size <= limit, 'private-json-file')
    raw = path.read_bytes()
    need(len(raw) == entry.st_size, 'private-json-size')
    pairs: dict[str, object] = {}
    def no_dupes(items: list[tuple[str, object]]) -> dict:
        result: dict[str, object] = {}
        for key, value in items:
            need(key not in result, 'duplicate-json-key')
            result[key] = value
        return result
    value = json.loads(raw, object_pairs_hook=no_dupes,
                       parse_constant=lambda _: (_ for _ in ()).throw(Rejected('nonfinite-json')))
    need(isinstance(value, dict), 'json-object')
    return value


def atomic_json(path: Path, value: dict) -> None:
    secure_dir(path.parent)
    need(not path.exists() and not path.is_symlink(), 'private-file-already-exists')
    raw = (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode()
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as output:
        output.write(raw)
        output.flush()
        os.fsync(output.fileno())
    folder = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(folder)
    finally:
        os.close(folder)


def guard_host() -> None:
    need(os.geteuid() == 0 and socket.gethostname() == 'data-test' and not Path('/etc/pve').exists(),
         'target-vm210-only')
    raw = subprocess.run(['findmnt', '-J', '--mountpoint', '/srv/dell-data', '-o', 'TARGET,UUID'],
                         capture_output=True, text=True, timeout=15)
    need(raw.returncode == 0, 'target-mount-query')
    fs = json.loads(raw.stdout).get('filesystems', [])
    need(len(fs) == 1 and fs[0].get('target') == '/srv/dell-data' and fs[0].get('uuid') == TARGET_UUID,
         'target-data-uuid')
    ips = subprocess.run(['ip', '-j', '-4', 'address', 'show', 'scope', 'global'],
                         capture_output=True, text=True, timeout=15)
    need(ips.returncode == 0, 'target-ip-query')
    observed = [a.get('local') for interface in json.loads(ips.stdout)
                if interface.get('ifname') not in ('lo', 'docker0')
                and not interface.get('ifname', '').startswith(('br-', 'veth'))
                for a in interface.get('addr_info', []) if a.get('family') == 'inet']
    need(observed == ['192.168.19.20'], 'target-ip')


def secret(name: str) -> str:
    path = BUNDLE / 'secrets' / name
    item = path.lstat()
    need(path.resolve() == path and stat.S_ISREG(item.st_mode) and item.st_uid == 0
         and item.st_nlink == 1 and stat.S_IMODE(item.st_mode) == 0o600, 'target-secret-file')
    value = path.read_text().strip()
    need(16 <= len(value) <= 256 and '\n' not in value, 'target-secret-shape')
    return value


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *_args, **_kwargs):
        return None


class Nacos:
    """Fixed local controller client. No dynamic host, redirect, or proxy."""
    def __init__(self):
        self.token: str | None = None
        self.open = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())

    def request(self, method: str, path: str, values: dict[str, str] | None = None,
                *, missing: bool = False) -> tuple[int, bytes]:
        allow = {
            'GET': {'/v1/console/namespaces', '/v1/cs/configs'},
            'POST': {'/v1/auth/users/login', '/v1/console/namespaces', '/v1/cs/configs'},
            'DELETE': {'/v1/cs/configs'},
        }
        need(path in allow.get(method, set()), 'fixed-nacos-api')
        headers = {'Accept': 'application/json'}
        data = None
        if self.token:
            headers['Authorization'] = 'Bearer ' + self.token
        if values is not None:
            encoded = urllib.parse.urlencode(values).encode()
            if method == 'GET':
                path += '?' + encoded.decode()
            else:
                data = encoded
                headers['Content-Type'] = 'application/x-www-form-urlencoded'
        try:
            request = urllib.request.Request(ENDPOINT + path, data=data, method=method, headers=headers)
            with self.open.open(request, timeout=15) as response:
                raw = response.read(MAX_BODY + 1)
                need(len(raw) <= MAX_BODY, 'nacos-response-limit')
                return response.status, raw
        except urllib.error.HTTPError as error:
            code = error.code
            error.close()
            if missing and code == 404:
                return code, b''
            raise Rejected('nacos-controller-http') from None

    def admin(self) -> None:
        self.token = None
        code, raw = self.request('POST', '/v1/auth/users/login',
                                 {'username': 'nacos', 'password': secret('nacos-admin-password')})
        need(code == 200, 'nacos-admin-login')
        value = json.loads(raw)
        need(isinstance(value, dict) and isinstance(value.get('accessToken'), str)
             and len(value['accessToken']) >= 16, 'nacos-admin-token')
        self.token = value['accessToken']


def mysql_metadata() -> list[dict]:
    """Metadata only: no config body, business rows, Env or command line."""
    spec = importlib.util.spec_from_file_location('nacos_target_metadata', BUNDLE / 'scripts' / 'acceptance.py')
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    sql = ("SELECT JSON_ARRAY(tenant_id,data_id,group_id,md5,COALESCE(type,''),"
           "COALESCE(app_name,''),COALESCE(c_desc,''),COALESCE(encrypted_data_key,'')) "
           "FROM nacos_test.config_info ORDER BY tenant_id,group_id,data_id;")
    _, raw = module.mysql({}, sql)
    rows = [json.loads(row) for row in raw.splitlines() if row]
    need(len(rows) <= 500, 'target-config-count-limit')
    out = []
    for row in rows:
        need(isinstance(row, list) and len(row) == 8
             and all(isinstance(v, str) for index, v in enumerate(row) if index != 3)
             and (isinstance(row[3], str) or row[3] is None), 'target-config-metadata')
        out.append({'namespace_id': row[0], 'data_id': row[1], 'group': row[2],
                    'md5': row[3] or '', 'type': row[4], 'app_name': row[5],
                    'description': row[6], 'encrypted_data_key': row[7]})
    return out


def side_tables_empty() -> bool:
    spec = importlib.util.spec_from_file_location('nacos_target_side', BUNDLE / 'scripts' / 'acceptance.py')
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    query = ("SELECT (SELECT COUNT(*) FROM nacos_test.config_info_beta)+"
             "(SELECT COUNT(*) FROM nacos_test.config_info_tag)+"
             "(SELECT COUNT(*) FROM nacos_test.config_info_aggr)+"
             "(SELECT COUNT(*) FROM nacos_test.config_tags_relation);")
    _, raw = module.mysql({}, query)
    return raw == '0'


def config_key(item: dict) -> tuple[str, str, str]:
    return item['namespace_id'], item['group'], item['data_id']


CONFIG_PROJECTION = ('namespace_id', 'data_id', 'group', 'md5', 'type', 'app_name',
                     'description', 'encrypted_data_key', 'config_tags', 'content')


def config_projection(item: dict) -> dict:
    """The only content-bearing comparison shape shared by source and target."""
    need(all(field in item for field in CONFIG_PROJECTION), 'config-projection-fields')
    return {field: item[field] for field in CONFIG_PROJECTION}


def check_text(value: object, field: str, *, limit: int = MAX_BODY) -> str:
    need(isinstance(value, str) and '\x00' not in value and len(value.encode()) <= limit,
         'source-' + field)
    return value


def optional_text(value: object, field: str) -> str:
    if value is None:
        return ''
    return check_text(value, field)


def validate_source(source: dict) -> tuple[list[dict], list[dict]]:
    need(set(source) == {'version', 'namespaces', 'items'}, 'source-schema')
    need(source['version'] == 1 and isinstance(source['namespaces'], list) and isinstance(source['items'], list),
         'source-version')
    namespaces = source['namespaces']
    need(len(namespaces) == 2, 'source-namespace-count')
    ns_map = {}
    declared_counts = {}
    for row in namespaces:
        need(isinstance(row, dict) and set(row) == {'id', 'name', 'count'}
             and isinstance(row['count'], int), 'source-namespace-shape')
        ident, name = check_text(row['id'], 'namespace-id', limit=128), check_text(row['name'], 'namespace-name', limit=256)
        need(ident in SOURCE_NAMESPACES and SOURCE_NAMESPACES[ident] == name and ident not in ns_map,
             'source-namespace-identity')
        ns_map[ident] = name
        declared_counts[ident] = row['count']
    items = source['items']
    need(len(items) == MAX_CONFIG, 'source-exact-count')
    required = {'namespace_id', 'namespace_name', 'data_id', 'group', 'type', 'app_name',
                'description', 'config_tags', 'encrypted_data_key', 'content', 'md5'}
    seen: set[tuple[str, str, str]] = set()
    counts = {key: 0 for key in SOURCE_NAMESPACES}
    checked = []
    for item in items:
        need(isinstance(item, dict) and set(item) == required, 'source-item-schema')
        row = {key: check_text(value, key) for key, value in item.items()
               if key not in {'app_name', 'description', 'config_tags', 'encrypted_data_key'}}
        for key in ('app_name', 'description', 'config_tags', 'encrypted_data_key'):
            row[key] = optional_text(item[key], key)
        need(row['namespace_id'] in ns_map and row['namespace_name'] == ns_map[row['namespace_id']],
             'source-item-namespace')
        need(row['encrypted_data_key'] == '', 'source-encrypted-key-not-supported')
        # config_tags use a side table in Nacos 2.4.3.  This worker deliberately
        # refuses a nonempty value until an exact side-table round-trip exists;
        # silently flattening tags would be data loss.
        need(row['config_tags'] == '', 'source-config-tags-not-supported')
        need(bool(MD5.fullmatch(row['md5'])), 'source-md5')
        need(hashlib.md5(row['content'].encode()).hexdigest() == row['md5'], 'source-content-md5')
        key = config_key(row)
        need(key not in seen, 'source-duplicate-key')
        seen.add(key)
        counts[row['namespace_id']] += 1
        checked.append(row)
    need(counts == {'08e7191f-3ccd-411a-be00-56798d237533': 32,
                    '7bfe03c6-0590-4ff0-8def-e07015016b54': 4}, 'source-namespace-counts')
    need(declared_counts == counts, 'source-declared-counts')
    return [{'id': ident, 'name': ns_map[ident]} for ident in sorted(ns_map)], sorted(checked, key=config_key)


def namespace_rows(api: Nacos) -> list[dict]:
    code, raw = api.request('GET', '/v1/console/namespaces')
    need(code == 200, 'target-namespace-query')
    doc = json.loads(raw)
    rows = doc.get('data') if isinstance(doc, dict) else None
    need(isinstance(rows, list) and len(rows) <= 100, 'target-namespace-metadata')
    selected = []
    for row in rows:
        need(isinstance(row, dict) and isinstance(row.get('namespace'), str)
             and isinstance(row.get('namespaceShowName'), str)
             and isinstance(row.get('configCount'), int), 'target-namespace-row')
        selected.append({'id': row['namespace'], 'name': row['namespaceShowName'], 'config_count': row['configCount']})
    return sorted(selected, key=lambda row: row['id'])


def config_all(api: Nacos, item: dict) -> tuple[str, dict]:
    """Read ordinary content and ConfigAllInfo; list MD5 may be nullable."""
    key = {'dataId': item['data_id'], 'group': item['group'], 'tenant': item['namespace_id']}
    code, plain = api.request('GET', '/v1/cs/configs', key, missing=True)
    need(code == 200, 'target-config-plain-readback')
    code, raw = api.request('GET', '/v1/cs/configs', {**key, 'show': 'all'}, missing=True)
    need(code == 200, 'target-config-showall-readback')
    try:
        detail = json.loads(raw)
    except (ValueError, TypeError):
        raise Rejected('target-config-showall-json') from None
    need(isinstance(detail, dict) and isinstance(detail.get('content'), str)
         and isinstance(detail.get('md5'), str) and bool(MD5.fullmatch(detail['md5'])),
         'target-config-showall-shape')
    body = plain.decode('utf-8')
    need(body == detail['content'] and hashlib.md5(body.encode()).hexdigest() == detail['md5'],
         'target-config-controller-body-md5')
    expected_fields = {'dataId': 'data_id', 'group': 'group', 'tenant': 'namespace_id',
                       'type': 'type', 'appName': 'app_name', 'desc': 'description',
                       'encryptedDataKey': 'encrypted_data_key'}
    for wire, internal in expected_fields.items():
        if wire in detail:
            need(optional_text(detail[wire], internal) == item[internal],
                 'target-config-showall-metadata')
    return body, detail


def enriched_target_metadata(api: Nacos) -> list[dict]:
    """Controller stored MD5 is authoritative when database list reports null."""
    result = []
    for listed in mysql_metadata():
        body, detail = config_all(api, listed)
        if listed['md5']:
            need(listed['md5'] == detail['md5'], 'target-db-controller-md5-drift')
        row = dict(listed)
        row.update(md5=detail['md5'], content=body, config_tags='')
        result.append(row)
    return result


def target_snapshot(api: Nacos, metadata: list[dict]) -> list[dict]:
    """Compatibility wrapper; metadata is re-read with ConfigAllInfo."""
    return enriched_target_metadata(api)


def result_row(items: list[dict]) -> dict:
    counts: dict[str, int] = {}
    groups: dict[str, int] = {}
    for row in items:
        counts[row['namespace_id']] = counts.get(row['namespace_id'], 0) + 1
        groups[row['group']] = groups.get(row['group'], 0) + 1
    return {'config_count': len(items), 'namespace_counts': counts, 'group_counts': groups,
            'configuration_content_or_md5_values_emitted': False}


def journal(run_dir: Path, phase: str, **details: object) -> None:
    value = {'at': now(), 'phase': phase, **details}
    existing = run_dir / ('journal-' + phase + '.json')
    atomic_json(existing, value)


def prepare(run_id: str) -> dict:
    guard_host()
    secure_dir(BASE, create=True)
    run_dir = BASE / run_id
    secure_dir(run_dir)
    need({child.name for child in run_dir.iterdir()} == {'source.json'}, 'run-upload-contract')
    source = read_json(run_dir / 'source.json')
    namespaces, items = validate_source(source)
    api = Nacos(); api.admin()
    need(side_tables_empty(), 'target-beta-tag-aggr-present')
    metadata = enriched_target_metadata(api)
    target_namespaces = namespace_rows(api)
    by_id = {row['id']: row for row in target_namespaces}
    by_name = {row['name']: row for row in target_namespaces}
    for source_ns in namespaces:
        conflicting = by_name.get(source_ns['name'])
        need(conflicting is None or conflicting['id'] == source_ns['id'], 'target-namespace-name-conflict')
        if source_ns['id'] in by_id:
            need(by_id[source_ns['id']]['name'] == source_ns['name'], 'target-namespace-id-conflict')
    backup = target_snapshot(api, metadata)
    atomic_json(run_dir / 'target-before.json', {'version': 1, 'run_id': run_id,
                                                  'namespaces': target_namespaces, 'items': backup})
    atomic_json(run_dir / 'source-manifest.json', {'version': 1, 'run_id': run_id,
                                                    'namespaces': namespaces, 'items': items})
    journal(run_dir, 'prepared', **result_row(metadata), source_config_count=len(items),
            target_namespace_count=len(target_namespaces), side_tables_empty=True)
    return {'status': 'prepared-no-target-write', 'run_id': run_id,
            'target_before_config_count': len(metadata), 'source_config_count': len(items),
            'source_namespace_names': [row['name'] for row in namespaces],
            'configuration_content_or_md5_values_emitted': False}


def require_stable_before(api: Nacos, before: dict) -> list[dict]:
    current = enriched_target_metadata(api)
    need([config_projection(row) for row in current] ==
         [config_projection(row) for row in before['items']], 'target-metadata-drift')
    need(side_tables_empty(), 'target-side-table-drift')
    return current


def wait_for_absent(api: Nacos, item: dict) -> None:
    """Nacos cache may briefly serve the just-deleted baseline entry."""
    key = {'dataId': item['data_id'], 'group': item['group'], 'tenant': item['namespace_id']}
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        code, raw = api.request('GET', '/v1/cs/configs', key, missing=True)
        if code == 404:
            return
        # ConfigInfo controller cache can outlive its backing row briefly after
        # DELETE.  Do not call show=all in that window: it may already observe
        # the deleted row and return a malformed/empty detail object.  Ordinary
        # GET must still be byte-for-byte the pre-delete body and hash.
        need(code == 200 and raw.decode('utf-8') == item['content']
             and hashlib.md5(raw).hexdigest() == item['md5'], 'target-delete-readback-drift')
        time.sleep(.5)
    raise Rejected('target-delete-readback-timeout')


def wait_for_present(api: Nacos, item: dict) -> None:
    """Wait only for controller visibility; first different visible body fails."""
    key = {'dataId': item['data_id'], 'group': item['group'], 'tenant': item['namespace_id']}
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        code, raw = api.request('GET', '/v1/cs/configs', key, missing=True)
        if code == 404:
            time.sleep(.5)
            continue
        need(code == 200 and raw.decode('utf-8') == item['content'], 'target-config-body-mismatch')
        body, detail = config_all(api, item)
        need(body == item['content'] and detail['md5'] == item['md5'], 'target-config-body-mismatch')
        return
    raise Rejected('target-config-visibility-timeout')


def apply(run_id: str) -> dict:
    guard_host()
    run_dir = BASE / run_id; secure_dir(run_dir)
    source = read_json(run_dir / 'source.json')
    namespaces, items = validate_source(source)
    before = read_json(run_dir / 'target-before.json')
    prepared_source = read_json(run_dir / 'source-manifest.json')
    need(prepared_source == {'version': 1, 'run_id': run_id, 'namespaces': namespaces, 'items': items},
         'source-payload-drift')
    need(before.get('version') == 1 and before.get('run_id') == run_id and isinstance(before.get('items'), list),
         'target-backup-required')
    api = Nacos(); api.admin()
    require_stable_before(api, before)
    current_ns = {row['id']: row for row in namespace_rows(api)}
    for item in namespaces:
        if item['id'] not in current_ns:
            code, raw = api.request('POST', '/v1/console/namespaces',
                                    {'customNamespaceId': item['id'], 'namespaceName': item['name'],
                                     'namespaceDesc': 'Imported test Nacos configuration namespace'})
            need(code == 200 and raw.strip() in (b'true', b'"true"'), 'target-namespace-create')
            current_ns = {row['id']: row for row in namespace_rows(api)}
        need(current_ns[item['id']]['name'] == item['name'], 'target-namespace-readback')
    deleted = 0
    for item in before['items']:
        body, detail = config_all(api, item)
        need(body == item['content'] and detail['md5'] == item['md5'], 'target-delete-precondition-drift')
        code, raw = api.request('DELETE', '/v1/cs/configs',
                                {'dataId': item['data_id'], 'group': item['group'], 'tenant': item['namespace_id']})
        need(code == 200 and raw.strip() in (b'true', b'"true"'), 'target-delete-rejected')
        wait_for_absent(api, item)
        deleted += 1
    need(mysql_metadata() == [] and side_tables_empty(), 'target-not-empty-after-clear')
    published = 0
    for item in items:
        code, _ = api.request('GET', '/v1/cs/configs',
                              {'dataId': item['data_id'], 'group': item['group'], 'tenant': item['namespace_id']},
                              missing=True)
        need(code == 404, 'target-unexpected-config-collision')
        values = {'dataId': item['data_id'], 'group': item['group'], 'tenant': item['namespace_id'],
                  'content': item['content'], 'type': item['type']}
        for internal, wire in [('app_name', 'appName'), ('description', 'desc'),
                               ('config_tags', 'config_tags'), ('encrypted_data_key', 'encryptedDataKey')]:
            if item[internal]:
                values[wire] = item[internal]
        code, raw = api.request('POST', '/v1/cs/configs', values)
        need(code == 200 and raw.strip() in (b'true', b'"true"'), 'target-config-publish-rejected')
        wait_for_present(api, item)
        published += 1
    actual = enriched_target_metadata(api)
    expected = [config_projection(item) for item in items]
    need([config_projection(row) for row in actual] == expected and side_tables_empty(),
         'target-final-metadata-mismatch')
    journal(run_dir, 'applied', deleted_config_count=deleted, published_config_count=published,
            **result_row(actual), target_namespace_ids=sorted({row['namespace_id'] for row in actual}))
    return {'status': 'target-configs-replaced-from-reviewed-source', 'run_id': run_id,
            'deleted_config_count': deleted, 'published_config_count': published,
            **result_row(actual), 'namespaces_created_only_if_missing': [row['name'] for row in namespaces],
            'users_roles_permissions_services_or_business_DB_changed': False,
            'automatic_rollback_performed': False}


def verify(run_id: str) -> dict:
    guard_host()
    run_dir = BASE / run_id; secure_dir(run_dir)
    source = read_json(run_dir / 'source.json')
    namespaces, items = validate_source(source)
    manifest = read_json(run_dir / 'source-manifest.json')
    need(manifest == {'version': 1, 'run_id': run_id, 'namespaces': namespaces, 'items': items},
         'source-payload-drift')
    api = Nacos(); api.admin()
    actual = enriched_target_metadata(api)
    expected = [config_projection(item) for item in items]
    need([config_projection(row) for row in actual] == expected and side_tables_empty(),
         'verify-target-metadata')
    ns = {row['id']: row for row in namespace_rows(api)}
    need(all(ns[row['id']]['name'] == row['name'] for row in namespaces), 'verify-namespaces')
    journal(run_dir, 'verified', **result_row(actual), source_config_count=len(items),
            target_config_count=len(actual), users_roles_permissions_services_or_business_DB_changed=False)
    return {'status': 'target-config-import-verified', 'run_id': run_id,
            **result_row(actual), 'source_config_count': len(items),
            'body_and_metadata_checked_private': True,
            'users_roles_permissions_services_or_business_DB_changed': False}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['prepare', 'apply', 'verify'])
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    need(bool(RUN.fullmatch(args.run_id)), 'run-id')
    os.umask(0o077)
    guard_host(); secure_dir(BASE, create=True)
    fd = os.open(BASE / '.worker.lock', os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        lock = os.fstat(fd)
        need(stat.S_ISREG(lock.st_mode) and lock.st_uid == 0 and lock.st_nlink == 1
             and stat.S_IMODE(lock.st_mode) == 0o600, 'worker-lock')
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        result = {'prepare': prepare, 'apply': apply, 'verify': verify}[args.action](args.run_id)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    finally:
        os.close(fd)


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        code = str(error) if isinstance(error, Rejected) and re.fullmatch(r'[a-z0-9-]{1,80}', str(error)) else None
        print(json.dumps({'status': 'nacos-target-import-not-confirmed',
                          'error_type': type(error).__name__, 'failure_code': code,
                          'automatic_rollback_or_delete_performed': False}), file=sys.stderr)
        raise SystemExit(1)
