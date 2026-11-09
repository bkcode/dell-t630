#!/usr/bin/python3
"""VM210 isolated restore drill. Never queries production or restores in place."""
from __future__ import annotations
import argparse
import datetime
import fcntl
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import re
import secrets
import select
import signal
import shutil
import socket
import stat
import subprocess
import sys
import time

BASE = Path('/srv/dell-data/_prod_db_restore_drill')
MOUNT = Path('/srv/dell-data')
UUID = 'dd1773f9-aa48-4401-a9c8-caf0f66845f3'
IMAGE = 'sha256:a0f6c7786c75739bd76a37b4b85e0f47b7c5d5a17a094bdd522412fb464d5cbe'
PARSER_SHA = '9af7511e26f6530fef7043e593d2a5533822f77eb83205a05c6d9ca726f1d35e'
FORMAT = 'dell-prod-db-isolated-restore-v1'
RUN_RE = re.compile(r'[0-9a-f]{32}\Z')
DOCKER = ['/usr/bin/docker', '--host', 'unix:///var/run/docker.sock']
ENV = {'PATH': '/usr/sbin:/usr/bin:/sbin:/bin', 'LANG': 'C.UTF-8'}
MAX_ARCHIVE, MAX_SQL = 1024 ** 3, 64 * 1024 ** 2
INITIAL = {'marker.json', 'mysql.sql.gz', 'expected.json'}
KNOWN = INITIAL | {'mysql-data', 'root-password', 'import-password'}
LABEL = 'dell.prod-db.restore.run'
OWNER = 'target-worker-v1'
DEADLINE = None
INSPECT = '{"Id":{{json .Id}},"Name":{{json .Name}},"Image":{{json .Image}},"User":{{json .Config.User}},"Labels":{"run":{{json (index .Config.Labels "dell.prod-db.restore.run")}},"owner":{{json (index .Config.Labels "dell.prod-db.restore.owner")}},"project":{{json (index .Config.Labels "com.docker.compose.project")}},"service":{{json (index .Config.Labels "com.docker.compose.service")}}},"State":{"Status":{{json .State.Status}},"Pid":{{json .State.Pid}},"StartedAt":{{json .State.StartedAt}},"Health":{{if (index .State "Health")}}{{json (index (index .State "Health") "Status")}}{{else}}null{{end}},"OOMKilled":{{json .State.OOMKilled}}},"RestartCount":{{json .RestartCount}},"Mounts":{{json .Mounts}},"Host":{"NetworkMode":{{json .HostConfig.NetworkMode}},"ReadonlyRootfs":{{json .HostConfig.ReadonlyRootfs}},"Privileged":{{json .HostConfig.Privileged}},"CapDrop":{{json .HostConfig.CapDrop}},"CapAdd":{{json .HostConfig.CapAdd}},"SecurityOpt":{{json .HostConfig.SecurityOpt}},"NanoCpus":{{json .HostConfig.NanoCpus}},"Memory":{{json .HostConfig.Memory}},"MemorySwap":{{json .HostConfig.MemorySwap}},"PidsLimit":{{json .HostConfig.PidsLimit}},"PortBindings":{{json .HostConfig.PortBindings}}},"Ports":{{json .NetworkSettings.Ports}}}'
SOURCE_INSPECT = '{"Id":{{json .Id}},"Name":{{json .Name}},"Image":{{json .Image}},"Labels":{"run":{{json (index .Config.Labels "dell.prod-db.restore.run")}},"owner":{{json (index .Config.Labels "dell.prod-db.restore.owner")}},"project":{{json (index .Config.Labels "com.docker.compose.project")}},"service":{{json (index .Config.Labels "com.docker.compose.service")}}},"State":{"Status":{{json .State.Status}},"Pid":{{json .State.Pid}},"StartedAt":{{json .State.StartedAt}},"Health":{{if (index .State "Health")}}{{json (index (index .State "Health") "Status")}}{{else}}null{{end}},"OOMKilled":{{json .State.OOMKilled}}},"RestartCount":{{json .RestartCount}}}'
REFERENCE_INSPECT = SOURCE_INSPECT[:-1] + ',"Mounts":{{json .Mounts}}}'



class Rejected(RuntimeError):
    pass

FAILURE_CODES = frozenset({
    'charset-collation-mismatch',
    'collation-metadata',
    'archive-metadata',
    'archive-sha',
    'base-symlink',
    'cached-exact-image',
    'check-table',
    'cid-changed',
    'cleanup-container-without-run',
    'cleanup-data-directory',
    'cleanup-file-identity',
    'cleanup-missing-run',
    'cleanup-report',
    'cleanup-still-referenced',
    'cleanup-top-symlink',
    'cleanup-unknown-entry',
    'column-name-order-mismatch',
    'command-failed',
    'command-input-limit',
    'command-output-limit',
    'command-timeout',
    'container-cid',
    'container-name-collision',
    'create-table-metadata',
    'data-mount-identity',
    'ddl-quote',
    'directory-not-private',
    'directory-owner-mode',
    'directory-path',
    'duplicate-json-key',
    'expanded-sql-limit',
    'expected-archive',
    'expected-empty-file',
    'expected-run',
    'expected-schema',
    'expected-scope',
    'fresh-password-shape',
    'fresh-run-only',
    'full-table-ddl-mismatch',
    'image-nonroot-identity',
    'importer-grants',
    'interrupted',
    'missing-create-table',
    'mount-path',
    'mysqlx-active',
    'non-owned-volume',
    'object-shape',
    'object-size',
    'old-run-report',
    'owned-container-identity',
    'owned-container-isolation',
    'owned-mount-set',
    'private-object-metadata',
    'pure-parser-sha',
    'resource-headroom',
    'restart-persistence-mismatch',
    'restore-not-fresh-prepared',
    'restored-database-set',
    'restored-row-digest',
    'restored-row-width',
    'restored-table-set',
    'run-id',
    'run-marker',
    'run-path',
    'scratch-not-empty',
    'scratch-readiness-timeout',
    'scratch-server-exited',
    'server-restrictions',
    'snapshot-table-set',
    'source-four-only',
    'source-identity-changed',
    'source-identity-health',
    'source-metadata-target',
    'source-service-duplicate',
    'source-service-set',
    'target-ip',
    'target210-only',
    'unexpected-global-sql',
    'unexpected-programmable-object',
    'unexpected-restored-object',
    'unknown-tmpfs',
    'worker-lock',
})



def need(ok, code):
    if not ok:
        raise Rejected(code)


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def run(args, data=None, timeout=30, limit=1024 * 1024, check=True):
    """Concurrent bounded pipe IO, without raw stderr/SQL/secret logging."""
    end = time.monotonic() + timeout
    if DEADLINE is not None:
        end = min(end, DEADLINE)
    need(data is None or len(data) <= MAX_SQL, 'command-input-limit')
    child = subprocess.Popen(args, stdin=subprocess.PIPE if data is not None else subprocess.DEVNULL,
                             stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, env=ENV)
    raw, position = bytearray(), 0
    out = child.stdout.fileno()
    os.set_blocking(out, False)
    input_fd = None
    if data is not None:
        input_fd = child.stdin.fileno()
        os.set_blocking(input_fd, False)
    try:
        output_open = True
        while output_open or input_fd is not None:
            need(time.monotonic() < end, 'command-timeout')
            if input_fd is not None and position == len(data):
                child.stdin.close()
                input_fd = None
            readable, writable, _ = select.select([out] if output_open else [],
                                                   [input_fd] if input_fd is not None else [], [],
                                                   min(.2, max(.001, end - time.monotonic())))
            if writable:
                position += os.write(input_fd, memoryview(data)[position:position + 65536])
            if readable:
                chunk = os.read(out, min(65536, limit + 1 - len(raw)))
                if not chunk:
                    output_open = False
                else:
                    raw.extend(chunk)
                    need(len(raw) <= limit, 'command-output-limit')
        code = child.wait(timeout=max(.01, end - time.monotonic()))
        if check:
            need(code == 0, 'command-failed')
        return code, bytes(raw)
    finally:
        if child.stdin and not child.stdin.closed:
            child.stdin.close()
        child.stdout.close()
        if child.poll() is None:
            child.terminate()
            try:
                child.wait(timeout=2)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait(timeout=2)


def docker(*args, **kwargs):
    return run(DOCKER + list(args), **kwargs)


def pairs(items):
    value = {}
    for key, item in items:
        need(key not in value, 'duplicate-json-key')
        value[key] = item
    return value


def read_object(path, *, uid=0, empty=False):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        s = os.fstat(fd)
        need(stat.S_ISREG(s.st_mode) and s.st_uid == uid and s.st_nlink == 1
             and stat.S_IMODE(s.st_mode) == 0o600 and s.st_size <= 65536,
             'private-object-metadata')
        raw = os.read(fd, 65537)
        need(len(raw) <= 65536, 'object-size')
        if empty:
            need(not raw, 'expected-empty-file')
            return None
        value = json.loads(raw, object_pairs_hook=pairs)
        need(type(value) is dict, 'object-shape')
        return value
    finally:
        os.close(fd)


def private_new(path, data, uid=0):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        os.fchown(fd, uid, uid)
        with os.fdopen(fd, 'wb', closefd=False) as out:
            out.write(data)
            out.flush()
            os.fsync(fd)
    finally:
        os.close(fd)


def atom(path, value):
    temp = path.with_name('.' + path.name + '.tmp')
    created = False
    try:
        fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        created = True
        with os.fdopen(fd, 'wb') as output:
            output.write((json.dumps(value, sort_keys=True) + '\n').encode())
            output.flush()
            os.fsync(output.fileno())
        os.replace(temp, path)
    finally:
        if created:
            try:
                temp.unlink()
            except FileNotFoundError:
                pass


def trusted_dir(path, private=False):
    need(path.is_absolute() and path.resolve(strict=True) == path and '..' not in path.parts,
         'directory-path')
    for p in [path, *path.parents]:
        s = p.lstat()
        need(stat.S_ISDIR(s.st_mode) and s.st_uid == 0 and not s.st_mode & 0o022,
             'directory-owner-mode')
    if private:
        need(stat.S_IMODE(path.stat().st_mode) == 0o700, 'directory-not-private')


def mount_identity(path):
    _, raw = run(['/usr/bin/findmnt', '-J', '--target', str(path), '-o', 'TARGET,UUID,FSTYPE,OPTIONS'])
    fs = json.loads(raw).get('filesystems')
    need(type(fs) is list and len(fs) == 1 and fs[0].get('target') == str(MOUNT)
         and fs[0].get('uuid') == UUID and fs[0].get('fstype') == 'ext4'
         and 'rw' in fs[0].get('options', '').split(','), 'data-mount-identity')


def host_guard():
    need(os.geteuid() == 0 and platform.system() == 'Linux'
         and platform.machine() in ('x86_64', 'amd64')
         and socket.gethostname().split('.')[0] == 'data-test'
         and not Path('/etc/pve').exists(), 'target210-only')
    _, raw = run(['/usr/sbin/ip', '-j', '-4', 'address', 'show', 'scope', 'global'])
    ips = [a.get('local') for i in json.loads(raw)
           if i.get('ifname') not in ('lo', 'docker0') and not i.get('ifname', '').startswith(('br-', 'veth'))
           for a in i.get('addr_info', []) if a.get('family') == 'inet']
    need(ips == ['192.168.19.20'], 'target-ip')
    mount_identity(MOUNT)
    if not BASE.exists():
        need(not BASE.is_symlink(), 'base-symlink')
        BASE.mkdir(mode=0o700)
    trusted_dir(BASE, private=True)
    mount_identity(BASE)
    reports = BASE / 'reports'
    if not reports.exists():
        reports.mkdir(mode=0o700)
    trusted_dir(reports, private=True)


def validate_expected(e, run_id):
    keys = {'version', 'run_id', 'source_run_id', 'archive_bytes', 'archive_sha256',
            'image_id', 'databases', 'table_counts'}
    need(type(e) is dict and set(e) == keys and type(e['version']) is int and e['version'] == 1,
         'expected-schema')
    need(e['run_id'] == run_id and bool(RUN_RE.fullmatch(e['source_run_id'])), 'expected-run')
    need(type(e['archive_bytes']) is int and 0 < e['archive_bytes'] <= MAX_ARCHIVE
         and type(e['archive_sha256']) is str and re.fullmatch('[0-9a-f]{64}', e['archive_sha256']),
         'expected-archive')
    need(e['image_id'] == IMAGE and e['databases'] == ['nacos_prod']
         and e['table_counts'] == {'nacos_prod': 12}, 'expected-scope')
    return e


def marker(work, run_id):
    need(type(run_id) is str and bool(RUN_RE.fullmatch(run_id)) and work == BASE / run_id,
         'run-path')
    trusted_dir(work, private=True)
    m = read_object(work / 'marker.json')
    need(m.get('format') == FORMAT and m.get('run_id') == run_id
         and m.get('image_id') == IMAGE, 'run-marker')
    return m


def prepare(run_id):
    need(type(run_id) is str and bool(RUN_RE.fullmatch(run_id)), 'run-id')
    work = BASE / run_id
    need(not (BASE / 'reports' / (run_id + '.json')).exists(), 'old-run-report')
    work.mkdir(mode=0o700)
    atom(work / 'marker.json', {'format': FORMAT, 'run_id': run_id, 'image_id': IMAGE,
                              'prepared_at': now()})
    private_new(work / 'mysql.sql.gz', b'')
    private_new(work / 'expected.json', b'')
    return {'prepared': True, 'run_id': run_id, 'container_created': False}


def snapshot_module():
    sibling = Path(__file__).resolve().with_name('sql_snapshot.py')
    # Development-only fallback to the unchanged pure module, never old worker.
    original = Path(__file__).resolve().parents[2] / 'full-snapshot-restore' / 'sql_snapshot.py'
    source = sibling if sibling.is_file() else original
    need(source.is_file() and not source.is_symlink()
         and hashlib.sha256(source.read_bytes()).hexdigest() == PARSER_SHA, 'pure-parser-sha')
    spec = importlib.util.spec_from_file_location('dell_restore_snapshot_pure', source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_snapshot(work, expected):
    p = work / 'mysql.sql.gz'
    fd = os.open(p, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        s = os.fstat(fd)
        need(stat.S_ISREG(s.st_mode) and s.st_uid == 0 and s.st_nlink == 1
             and stat.S_IMODE(s.st_mode) == 0o600 and s.st_size == expected['archive_bytes'], 'archive-metadata')
        digest = hashlib.sha256()
        while data := os.read(fd, 65536):
            digest.update(data)
        need(digest.hexdigest() == expected['archive_sha256'], 'archive-sha')
        os.lseek(fd, 0, os.SEEK_SET)
        raw = bytearray()
        with os.fdopen(os.dup(fd), 'rb') as compressed:
            with gzip.GzipFile(fileobj=compressed) as stream:
                while data := stream.read(min(65536, MAX_SQL + 1 - len(raw))):
                    raw.extend(data)
                    need(len(raw) <= MAX_SQL, 'expanded-sql-limit')
        text = bytes(raw).decode('utf-8')
        pure = snapshot_module()
        tables = pure.parse(text)
        need(len(tables) == 12 and all(re.fullmatch('[A-Za-z0-9_]+', t) for t in tables), 'snapshot-table-set')
        # Parser supplies row equivalence, not SQL authorization. The import user
        # additionally has only nacos_prod.* privileges and no grant/global/FILE.
        for statement in pure.statements(text):
            clean = pure.clean(statement).strip()
            if clean.upper().startswith('CREATE TABLE'):
                table = re.match(r'CREATE TABLE `([A-Za-z0-9_]+)`', clean)
                need(table and table[1] in tables and 'create_statement' not in tables[table[1]],
                     'create-table-metadata')
                tables[table[1]]['create_statement'] = canonical_ddl(clean, pure)
            need(not re.match(r'(?is)^(?:GRANT|REVOKE|CREATE\s+USER|DROP\s+USER|SET\s+(?:GLOBAL|@@GLOBAL))\b', clean),
                 'unexpected-global-sql')
        need(all('create_statement' in metadata for metadata in tables.values()), 'missing-create-table')
        return bytes(raw), tables, pure
    finally:
        os.close(fd)


def canonical_ddl(statement, pure):
    """Normalize only whitespace outside SQL quotes; COMMENT literals stay exact."""
    text = pure.clean(statement).strip()
    if text.endswith(';'):
        text = text[:-1].rstrip()
    out, quote, whitespace, i = [], None, False, 0
    while i < len(text):
        char = text[i]
        if quote:
            out.append(char)
            if ord(char) == 92 and i + 1 < len(text):
                i += 1
                out.append(text[i])
            elif char == quote:
                if i + 1 < len(text) and text[i + 1] == quote:
                    i += 1
                    out.append(text[i])
                else:
                    quote = None
        elif char.isspace():
            whitespace = True
        else:
            if whitespace and out:
                out.append(' ')
            whitespace = False
            out.append(char)
            if ord(char) in (39, 34, 96):
                quote = char
        i += 1
    need(quote is None, 'ddl-quote')
    return ''.join(out)


def collation_mapping(cid, work, run_id):
    """Authority is this exact isolated server, never name-prefix guessing."""
    raw = sql(cid, work, run_id,
              'SELECT COLLATION_NAME,CHARACTER_SET_NAME FROM information_schema.COLLATIONS ORDER BY COLLATION_NAME;')
    mapping = {}
    for row in raw.splitlines():
        fields = row.split('\t')
        need(len(fields) == 2 and all(re.fullmatch('[A-Za-z0-9_]{1,64}', v) for v in fields),
             'collation-metadata')
        collation, charset = (v.lower() for v in fields)
        need(collation not in mapping, 'collation-metadata')
        mapping[collation] = charset
    need(bool(mapping), 'collation-metadata')
    return mapping


def semantic_ddl(ddl, mapping):
    """Remove only proven redundant CHARACTER SET X immediately before COLLATE Y.

    MySQL verified bug110825: replaying SHOW CREATE can add this redundant
    column declaration. COLLATE is retained verbatim. No quoted text is touched.
    https://bugs.mysql.com/bug.php?id=110825
    https://dev.mysql.com/doc/refman/8.4/en/charset-column.html
    """
    def outside(text):
        for match in re.finditer(r'\bCOLLATE\b\s*=?\s*([A-Za-z0-9_]+)\b', text, re.I):
            need(match[1].lower() in mapping, 'collation-metadata')
        def redundant(match):
            charset, collation = match[1].lower(), match[3].lower()
            need(mapping.get(collation) == charset, 'charset-collation-mismatch')
            return match[2]  # retain the exact COLLATE name/keyword, no other DDL
        return re.sub(r'\bCHARACTER\s+SET\s+([A-Za-z0-9_]+)\s+(COLLATE\s+([A-Za-z0-9_]+)\b)',
                      redundant, text, flags=re.I)
    parts, start, i = [], 0, 0
    while i < len(ddl):
        if ord(ddl[i]) not in (39, 34, 96):
            i += 1
            continue
        parts.append(outside(ddl[start:i]))
        quote, quoted_start = ddl[i], i
        i += 1
        closed = False
        while i < len(ddl):
            current = ddl[i]
            i += 1
            if ord(current) == 92 and i < len(ddl):
                i += 1
            elif current == quote:
                if i < len(ddl) and ddl[i] == quote:
                    i += 1
                else:
                    closed = True
                    break
        need(closed, 'ddl-quote')
        parts.append(ddl[quoted_start:i])
        start = i
    parts.append(outside(ddl[start:]))
    return ''.join(parts)


def ddl_difference(source, target, table, charset_names=None):
    """Classify privately compared DDL without returning SQL/literals/digests."""
    def mask_literals(text):
        out, i = [], 0
        while i < len(text):
            ch = text[i]
            if ord(ch) not in (39, 34, 96):
                out.append(ch)
                i += 1
                continue
            quote, start = ch, i
            i += 1
            while i < len(text):
                current = text[i]
                i += 1
                if ord(current) == 92 and i < len(text):
                    i += 1
                elif current == quote:
                    if i < len(text) and text[i] == quote:
                        i += 1
                    else:
                        break
            out.append(text[start:i] if ord(quote) == 96 else '<literal>')
        return ''.join(out)
    result = {'table': table, 'only_quoted_literals_differ': source != target and
              mask_literals(source) == mask_literals(target),
              'non_ascii_positions_differ': [i for i, ch in enumerate(source) if ord(ch) > 127] !=
                                           [i for i, ch in enumerate(target) if ord(ch) > 127],
              'non_ascii_characters_differ': ''.join(ch for ch in source if ord(ch) > 127) !=
                                            ''.join(ch for ch in target if ord(ch) > 127),
              'source_length': len(source), 'target_length': len(target),
              'charset_names_available': False}
    if charset_names is not None:
        names = charset_names.strip().split('\t')
        if len(names) == 2 and all(re.fullmatch('[A-Za-z0-9_]{1,32}', name) for name in names):
            result.update(charset_names_available=True,
                          character_set_client=names[0], character_set_results=names[1])
    return result


def inspect(cid, template=INSPECT):
    need(bool(re.fullmatch('[0-9a-f]{64}', cid)), 'container-cid')
    _, raw = docker('inspect', '--format', template, cid)
    return json.loads(raw)


def all_containers(refs=False):
    _, raw = docker('ps', '--all', '--quiet', '--no-trunc')
    return [inspect(cid, REFERENCE_INSPECT if refs else SOURCE_INSPECT) for cid in raw.decode().splitlines()]


def source_snapshot():
    rows = all_containers()
    need(len(rows) == 4, 'source-four-only')
    result = {}
    for c in rows:
        need(c['Labels']['project'] == 'dell-data-test-data'
             and c['Labels']['service'] in ('mysql', 'nacos', 'redis', 'rabbitmq')
             and c['State']['Status'] == 'running' and c['State']['Health'] == 'healthy'
             and not c['State']['OOMKilled'], 'source-identity-health')
        service = c['Labels']['service']
        need(service not in result, 'source-service-duplicate')
        result[service] = {k: c[k] for k in ('Id', 'Name', 'Image', 'State', 'RestartCount')}
    need(set(result) == {'mysql', 'nacos', 'redis', 'rabbitmq'}, 'source-service-set')
    return result


def resource_guard():
    mount_identity(BASE)
    free = shutil.disk_usage(BASE).free
    available = int(re.search(r'^MemAvailable:\s+(\d+)', Path('/proc/meminfo').read_text(), re.M)[1]) * 1024
    need(available >= 2 * 1024 ** 3 and free >= 3 * 1024 ** 3, 'resource-headroom')
    return {'mem_available_bytes': available, 'free_bytes': free}


def cached_image_and_uid(before):
    _, raw = docker('image', 'inspect', IMAGE, '--format', '{"Id":{{json .Id}},"Architecture":{{json .Architecture}},"Os":{{json .Os}}}')
    image = json.loads(raw)
    need(image == {'Id': IMAGE, 'Architecture': 'amd64', 'Os': 'linux'}
         and before['mysql']['Image'] == IMAGE, 'cached-exact-image')
    cid = before['mysql']['Id']
    need(inspect(cid, SOURCE_INSPECT)['Labels']['service'] == 'mysql', 'source-metadata-target')
    _, raw = docker('exec', cid, 'sh', '-ec', 'id -u mysql; id -g mysql')
    need(raw.decode().split() == ['999', '999'], 'image-nonroot-identity')


def container_name(run_id):
    return 'dell-prod-db-restore-' + run_id


def owned(c, work, run_id):
    need(c['Name'] == '/' + container_name(run_id) and c['Image'] == IMAGE
         and c['Labels']['run'] == run_id and c['Labels']['owner'] == OWNER
         and c['User'] == '999:999', 'owned-container-identity')
    h = c['Host']
    need(h['NetworkMode'] == 'none' and h['ReadonlyRootfs'] is True and not h['Privileged']
         and not h['CapAdd'] and h['CapDrop'] == ['ALL']
         and 'no-new-privileges:true' in h['SecurityOpt']
         and h['NanoCpus'] == 1000000000 and h['Memory'] == 1024 ** 3
         and h['MemorySwap'] == 1024 ** 3 and h['PidsLimit'] == 256
         and not h['PortBindings'] and not any((c.get('Ports') or {}).values()), 'owned-container-isolation')
    binds = {(str(work / 'mysql-data'), '/var/lib/mysql', True),
             (str(work / 'root-password'), '/run/secrets/root-password', False),
             (str(work / 'import-password'), '/run/secrets/import-password', False)}
    actual = set()
    for mount in c['Mounts']:
        if mount['Type'] == 'tmpfs':
            need(mount['Destination'] in ('/tmp', '/var/run/mysqld', '/run/mysqld'), 'unknown-tmpfs')
        else:
            need(mount['Type'] == 'bind', 'non-owned-volume')
            source = Path(mount['Source'])
            need(source.resolve(strict=False) == source and source.parent == work, 'mount-path')
            actual.add((str(source), mount['Destination'], bool(mount['RW'])))
    need(actual == binds, 'owned-mount-set')
    return c['Id']


def guard_cid(cid, work, run_id):
    c = inspect(cid)
    need(c['Id'] == cid, 'cid-changed')
    owned(c, work, run_id)
    return c


def create(work, run_id):
    need(set(p.name for p in work.iterdir()) == INITIAL, 'fresh-run-only')
    need(not any(c['Name'] == '/' + container_name(run_id) for c in all_containers()), 'container-name-collision')
    resource_guard()  # fresh, immediately before creation, not an old audit value
    data = work / 'mysql-data'
    data.mkdir(mode=0o700)
    os.chown(data, 999, 999)
    private_new(work / 'root-password', secrets.token_hex(32).encode(), 999)
    private_new(work / 'import-password', secrets.token_hex(32).encode(), 999)
    args = ['create', '--name', container_name(run_id), '--label', LABEL + '=' + run_id,
            '--label', 'dell.prod-db.restore.owner=' + OWNER, '--pull=never', '--platform=linux/amd64',
            '--network=none', '--read-only', '--user=999:999', '--cap-drop=ALL',
            '--security-opt=no-new-privileges:true', '--cpus=1', '--memory=1g', '--memory-swap=1g',
            '--pids-limit=256', '--restart=no', '--tmpfs=/tmp:size=32m,mode=1777',
            '--tmpfs=/var/run/mysqld:size=16m,uid=999,gid=999,mode=0755',
            '--mount', 'type=bind,src=' + str(data) + ',dst=/var/lib/mysql',
            '--mount', 'type=bind,src=' + str(work / 'root-password') + ',dst=/run/secrets/root-password,readonly',
            '--mount', 'type=bind,src=' + str(work / 'import-password') + ',dst=/run/secrets/import-password,readonly',
            '--env=MYSQL_ROOT_PASSWORD_FILE=/run/secrets/root-password', IMAGE,
            '--innodb-buffer-pool-size=128M', '--performance-schema=OFF', '--max-connections=10',
            '--skip-networking', '--mysqlx=OFF', '--event-scheduler=DISABLED', '--local-infile=0',
            '--secure-file-priv=NULL', '--skip-log-bin']
    _, raw = docker(*args, timeout=60)
    cid = raw.decode().strip()
    guard_cid(cid, work, run_id)
    docker('start', cid, timeout=60)
    return cid


def sql(cid, work, run_id, query, importer=False):
    guard_cid(cid, work, run_id)
    identity, filename = ('restore_importer', 'import-password') if importer else ('root', 'root-password')
    shell = ('export MYSQL_PWD="$(cat /run/secrets/' + filename + ')"; exec mysql --no-defaults '
             '--user=' + identity + ' --default-character-set=utf8mb4 --binary-mode --protocol=socket --connect-timeout=5 '
             '--skip-reconnect --batch --raw --skip-column-names --local-infile=0')
    _, raw = docker('exec', '--user=999:999', '-i', cid, 'sh', '-ec', shell,
                    data=query.encode() if isinstance(query, str) else query,
                    timeout=180, limit=128 * 1024 ** 2)
    return raw.decode('utf-8')


def ready(cid, work, run_id):
    end = time.monotonic() + 180
    while time.monotonic() < end:
        c = guard_cid(cid, work, run_id)
        need(c['State']['Status'] in ('created', 'running'), 'scratch-server-exited')
        try:
            if sql(cid, work, run_id, 'SELECT 1;').strip() == '1':
                return
        except Rejected:
            pass
        time.sleep(1)
    raise Rejected('scratch-readiness-timeout')


def server_restrictions(cid, work, run_id):
    value = sql(cid, work, run_id, 'SELECT @@event_scheduler,@@local_infile,@@secure_file_priv,@@log_bin,@@skip_networking;').strip()
    need(value == 'DISABLED\t0\tNULL\t0\t1', 'server-restrictions')
    need(sql(cid, work, run_id, "SELECT COUNT(*) FROM information_schema.PLUGINS WHERE PLUGIN_NAME='mysqlx' AND PLUGIN_STATUS='ACTIVE';").strip() == '0', 'mysqlx-active')


def import_user(cid, work, run_id):
    password = (work / 'import-password').read_bytes().decode('ascii')
    need(bool(re.fullmatch('[0-9a-f]{64}', password)), 'fresh-password-shape')
    # This SQL is sent only via STDIN, never argv/Env/logs. No GRANT OPTION,
    # global privileges, FILE, SUPER or source credentials are used.
    sql(cid, work, run_id, "CREATE USER 'restore_importer'@'localhost' IDENTIFIED BY '" + password + "'; GRANT ALL PRIVILEGES ON `nacos_prod`.* TO 'restore_importer'@'localhost';")
    grants = sql(cid, work, run_id, "SHOW GRANTS FOR 'restore_importer'@'localhost';").splitlines()
    need(len(grants) == 2 and any('GRANT USAGE ON *.*' in row for row in grants)
         and any('GRANT ALL PRIVILEGES ON `nacos_prod`.*' in row for row in grants)
         and all('WITH GRANT OPTION' not in row for row in grants), 'importer-grants')


def compare(cid, work, run_id, expected, pure):
    server_restrictions(cid, work, run_id)
    need(set(sql(cid, work, run_id, 'SHOW DATABASES;').splitlines()) ==
         {'mysql', 'sys', 'information_schema', 'performance_schema', 'nacos_prod'}, 'restored-database-set')
    found_rows = [json.loads(line) for line in sql(cid, work, run_id,
                  "SELECT JSON_ARRAY(TABLE_NAME,TABLE_TYPE,COALESCE(ENGINE,'')) FROM information_schema.TABLES WHERE TABLE_SCHEMA='nacos_prod' ORDER BY TABLE_NAME;").splitlines()]
    need(all(type(row) is list and len(row) == 3 and row[1:] == ['BASE TABLE', 'InnoDB'] for row in found_rows),
         'unexpected-restored-object')
    found = [row[0] for row in found_rows]
    need(set(found) == set(expected) and len(found) == 12, 'restored-table-set')
    collations = collation_mapping(cid, work, run_id)
    for table, column in [('ROUTINES', 'ROUTINE_SCHEMA'), ('EVENTS', 'EVENT_SCHEMA'), ('TRIGGERS', 'TRIGGER_SCHEMA')]:
        need(sql(cid, work, run_id, "SELECT COUNT(*) FROM information_schema." + table +
                 " WHERE " + column + "='nacos_prod';").strip() == '0', 'unexpected-programmable-object')
    total = 0
    for table, metadata in expected.items():
        columns = metadata['columns']
        actual = sql(cid, work, run_id, "SELECT column_name FROM information_schema.columns WHERE table_schema='nacos_prod' AND table_name='" + table + "' ORDER BY ordinal_position;").splitlines()
        need(actual == columns, 'column-name-order-mismatch')
        shown = sql(cid, work, run_id, 'SHOW CREATE TABLE `nacos_prod`.`' + table + '`;')
        shown_name, separator, shown_ddl = shown.rstrip('\n').partition('\t')
        need(separator and shown_name == table, 'full-table-ddl-mismatch')
        normalized = canonical_ddl(shown_ddl + ';', pure)
        source_semantics = semantic_ddl(metadata['create_statement'], collations)
        target_semantics = semantic_ddl(normalized, collations)
        if target_semantics != source_semantics:
            names = None
            try:
                names = sql(cid, work, run_id, 'SELECT @@character_set_client,@@character_set_results;')
            except Exception:
                pass  # Diagnostic failure never downgrades the strict DDL check.
            failure = Rejected('full-table-ddl-mismatch')
            failure.ddl_difference = ddl_difference(metadata['create_statement'], normalized, table, names)
            raise failure
        select_columns = ','.join("IFNULL(HEX(CAST(`" + name + "` AS BINARY)),'NULL')" for name in columns)
        raw = sql(cid, work, run_id, 'SELECT ' + select_columns + ' FROM `nacos_prod`.`' + table + '`;')
        rows = []
        for line in raw.splitlines():
            cells = line.split('\t')
            need(len(cells) == len(columns), 'restored-row-width')
            rows.append(tuple(None if value == 'NULL' else bytes.fromhex(value) for value in cells))
        need(len(rows) == metadata['rows'] and pure.row_digest(rows) == metadata['digest'], 'restored-row-digest')
        check = sql(cid, work, run_id, 'CHECK TABLE `nacos_prod`.`' + table + '`;').rstrip('\n')
        need(check.endswith('\tstatus\tOK'), 'check-table')
        total += len(rows)
    return {'table_count': len(expected), 'row_count': total,
            'column_names_order_match': True, 'row_digests_match': True,
            'full_table_DDL_match': True,
            'charset_collation_semantics_verified': True,
            'CHECK_TABLE_passed': True, 'event_scheduler_DISABLED': True}


def own_containers(work, run_id):
    result = []
    for c in all_containers():
        if c['Labels']['run'] == run_id or c['Name'] == '/' + container_name(run_id):
            full = inspect(c['Id'])
            owned(full, work, run_id)
            result.append(full)
    return result


def cleanup(work, run_id, allow_report=False):
    need(type(run_id) is str and bool(RUN_RE.fullmatch(run_id)) and work == BASE / run_id,
         'run-path')
    if not work.exists():
        need(allow_report and not work.is_symlink(), 'cleanup-missing-run')
        report = read_object(BASE / 'reports' / (run_id + '.json'))
        need(report.get('format') == FORMAT and report.get('run_id') == run_id, 'cleanup-report')
        need(not own_containers(work, run_id), 'cleanup-container-without-run')
        for c in all_containers(refs=True):
            need(not any(Path(m.get('Source', '/')) == work or work in Path(m.get('Source', '/')).parents
                         for m in c['Mounts']), 'cleanup-still-referenced')
        return True
    marker(work, run_id)
    need(set(p.name for p in work.iterdir()) <= KNOWN, 'cleanup-unknown-entry')
    for c in own_containers(work, run_id):
        guard_cid(c['Id'], work, run_id)
        docker('rm', '--force', c['Id'], timeout=60)
    # No container, including stopped/unrelated containers, may still reference
    # any member of the run. A path-prefix string alone is never cleanup proof.
    for c in all_containers(refs=True):
        for m in c['Mounts']:
            source = Path(m.get('Source', '/'))
            need(source != work and work not in source.parents, 'cleanup-still-referenced')
    need(set(p.name for p in work.iterdir()) <= KNOWN, 'cleanup-unknown-entry')
    for child in work.iterdir():
        need(not child.is_symlink(), 'cleanup-top-symlink')
        if child.name == 'mysql-data':
            need(child.is_dir() and child.resolve() == child, 'cleanup-data-directory')
            mount_identity(child)
        else:
            fd = os.open(child, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
            try:
                s = os.fstat(fd)
                uid = 999 if child.name in ('root-password', 'import-password') else 0
                need(stat.S_ISREG(s.st_mode) and s.st_uid == uid and s.st_nlink == 1
                     and stat.S_IMODE(s.st_mode) == 0o600, 'cleanup-file-identity')
            finally:
                os.close(fd)
    # shutil.rmtree does not follow child symlinks; only the validated own
    # mysql-data tree is recursive. Unknown top-level directories are refused.
    data = work / 'mysql-data'
    if data.exists():
        shutil.rmtree(data)
    for name in sorted(KNOWN - {'mysql-data'}):
        path = work / name
        if path.exists():
            path.unlink()
    work.rmdir()
    return True


def restore(run_id):
    global DEADLINE
    need(type(run_id) is str and bool(RUN_RE.fullmatch(run_id)), 'run-id')
    work = BASE / run_id
    need(not (BASE / 'reports' / (run_id + '.json')).exists(), 'old-run-report')
    before = None
    report = {'format': FORMAT, 'run_id': run_id, 'image_id': IMAGE,
              'started_at': now(), 'status': 'failed', 'cleanup_failed': False,
              'source_containers_unchanged': False, 'stage': 'load-snapshot'}
    start = time.monotonic()
    DEADLINE = start + 1200
    try:
        marker(work, run_id)
        need(set(p.name for p in work.iterdir()) == INITIAL, 'restore-not-fresh-prepared')
        before = source_snapshot()
        expected = validate_expected(read_object(work / 'expected.json'), run_id)
        raw, tables, pure = load_snapshot(work, expected)
        report['stage'] = 'create'
        cached_image_and_uid(before)
        cid = create(work, run_id)
        report['stage'] = 'ready'
        ready(cid, work, run_id)
        report['stage'] = 'restrictions'
        server_restrictions(cid, work, run_id)
        need(set(sql(cid, work, run_id, 'SHOW DATABASES;').splitlines()) ==
             {'mysql', 'sys', 'information_schema', 'performance_schema'}, 'scratch-not-empty')
        report['stage'] = 'import-user'
        import_user(cid, work, run_id)
        # No pre-created schema: importer executes the dump's CREATE DATABASE,
        # preserving its charset/collation instead of using target defaults.
        report['stage'] = 'import'
        sql(cid, work, run_id, raw, importer=True)  # never fallback to scratch root
        report['stage'] = 'compare'
        first = compare(cid, work, run_id, tables, pure)
        report['stage'] = 'restart'
        guard_cid(cid, work, run_id)
        docker('restart', '--time=30', cid, timeout=60)
        ready(cid, work, run_id)
        after = compare(cid, work, run_id, tables, pure)
        need(first == after, 'restart-persistence-mismatch')
        report.update(first)
        report.update(status='passed', restart_persistence_verified=True,
                      source_archive_SHA_matches=True, gzip_CRC_verified=True,
                      importer_scope_only_nacos_prod=True)
    except Exception as error:
        report['error_type'] = type(error).__name__
        if isinstance(error, Rejected) and str(error) in FAILURE_CODES:
            report['failure_code'] = str(error)
            if str(error) == 'full-table-ddl-mismatch' and hasattr(error, 'ddl_difference'):
                report['ddl_difference'] = error.ddl_difference
    finally:
        DEADLINE = None  # bounded cleanup commands must still run after work timeout
        try:
            cleanup(work, run_id)
            if report['status'] == 'passed':
                report['stage'] = 'cleanup'
        except Exception as error:
            report.update(status='failed', cleanup_failed=True, stage='cleanup')
            if isinstance(error, Rejected) and str(error) in FAILURE_CODES:
                report['cleanup_failure_code'] = str(error)
        try:
            report['source_containers_unchanged'] = before is not None and source_snapshot() == before
        except Exception:
            report['source_containers_unchanged'] = False
        if not report['source_containers_unchanged']:
            report['status'] = 'failed'
            report.setdefault('failure_code', 'source-identity-changed')
        report.update(finished_at=now(), elapsed_seconds=round(time.monotonic() - start, 3),
                      production_queried=False, source_credentials_used=False,
                      notifications_or_external_connections=False,
                      independent_DR_claimed=False, RPO_RTO_approved=False)
        atom(BASE / 'reports' / (run_id + '.json'), report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['prepare', 'restore', 'cleanup'])
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    need(bool(RUN_RE.fullmatch(args.run_id)), 'run-id')
    os.umask(0o077)
    host_guard()
    lock = os.open(BASE / '.worker.lock', os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
    try:
        st = os.fstat(lock)
        need(stat.S_ISREG(st.st_mode) and st.st_uid == 0 and st.st_nlink == 1
             and stat.S_IMODE(st.st_mode) == 0o600, 'worker-lock')
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if args.action == 'prepare':
            result = prepare(args.run_id)
        elif args.action == 'restore':
            result = restore(args.run_id)
        else:
            cleanup(BASE / args.run_id, args.run_id, allow_report=True)
            result = {'cleaned': True, 'run_id': args.run_id}
        print(json.dumps(result, sort_keys=True))
        if result.get('status') == 'failed':
            raise SystemExit(1)
    finally:
        os.close(lock)


if __name__ == '__main__':
    def interrupted(signum, frame):
        raise Rejected('interrupted')
    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    try:
        main()
    except Exception as error:
        print(json.dumps({'status': 'failed', 'error_type': type(error).__name__}))
        raise SystemExit(1)
