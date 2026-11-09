#!/usr/bin/python3
"""VM200-only logical export. No restore, imports, service changes or off-host export.

cleanup is called only after the trusted PVE coordinator has stored and verified
both artifacts. That off-guest receipt is the coordinator's responsibility.
"""
from __future__ import annotations
import argparse
import datetime
import fcntl
import gzip
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import select
import signal
import shlex
import socket
import stat
import subprocess
import sys
import time

POLICY_PATH = '/etc/dell-prod-db-backup/policy.json'
MOUNT = '/srv/dell-data'
UUID = 'd61c0e22-941e-447a-9e9a-1e9e50deb02f'
STAGING = MOUNT + '/_prod_db_backups'
DATA = MOUNT + '/prod-db/mysql'
DOCKER = ['/usr/bin/docker', '--host', 'unix:///var/run/docker.sock']
ENV = {'PATH': '/usr/sbin:/usr/bin:/sbin:/bin', 'LANG': 'C.UTF-8'}
FORMAT = 'dell-prod-db-backup-v1'
FILES = {'mysql.sql.gz', 'manifest.json'}
SYSTEM_DATABASES = {'mysql', 'sys', 'information_schema', 'performance_schema'}
IDENT = re.compile(r'[A-Za-z_][A-Za-z0-9_]{0,63}\Z')
RUN_ID = re.compile(r'[0-9a-f]{32}\Z')
MAX_BYTES = 1073741824
MAX_META = 1024 * 1024
SECRET_PREFIX = 'export MYSQL_PWD="$(cat /run/secrets/mysql-root-password)"; exec '
MYSQL = 'mysql --protocol=socket --user=root --connect-timeout=5 --skip-reconnect --default-character-set=utf8mb4 --batch --raw --skip-column-names --unbuffered'
INSPECT_FORMAT = '{"Id":{{json .Id}},"Name":{{json .Name}},"State":{"Status":{{json .State.Status}},"StartedAt":{{json .State.StartedAt}},"Pid":{{json .State.Pid}},"Health":{{if .State.Health}}{{json .State.Health.Status}}{{else}}null{{end}}},"RestartCount":{{json .RestartCount}},"Labels":{"project":{{json (index .Config.Labels "com.docker.compose.project")}},"service":{{json (index .Config.Labels "com.docker.compose.service")}}},"Mounts":{{json .Mounts}}}'


class Rejected(RuntimeError):
    """Only a fixed code is allowed into error metadata, never command output."""


def need(ok, code):
    if not ok:
        raise Rejected(code)


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def remaining(deadline, cap=20):
    value = min(cap, deadline - time.monotonic())
    need(value > 0, 'deadline-exceeded')
    return value


def object_pairs(pairs):
    result = {}
    for key, value in pairs:
        need(key not in result, 'duplicate-json-key')
        result[key] = value
    return result


def parse_json(raw):
    need(len(raw) <= MAX_META, 'metadata-size')
    return json.loads(raw, object_pairs_hook=object_pairs,
                      parse_constant=lambda _: (_ for _ in ()).throw(Rejected('nonfinite-json')))


def open_dir(path, private=False):
    p = Path(path)
    need(p.is_absolute() and str(p) == path and '..' not in p.parts, 'directory-path')
    fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in p.parts[1:]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = child
            st = os.fstat(fd)
            need(st.st_uid == 0 and not st.st_mode & 0o022, 'directory-owner-mode')
        if private:
            need(stat.S_IMODE(os.fstat(fd).st_mode) == 0o700, 'directory-not-private')
        return fd
    except BaseException:
        os.close(fd)
        raise


def checked_file(fd):
    st = os.fstat(fd)
    need(stat.S_ISREG(st.st_mode) and st.st_uid == 0 and st.st_nlink == 1
         and stat.S_IMODE(st.st_mode) == 0o600, 'file-owner-mode-links')
    return st


def read_json_at(parent, name):
    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
    try:
        st = checked_file(fd)
        need(0 < st.st_size <= MAX_META, 'json-file-size')
        raw = bytearray()
        while True:
            chunk = os.read(fd, min(65536, MAX_META + 1 - len(raw)))
            if not chunk:
                break
            raw.extend(chunk)
            need(len(raw) <= MAX_META, 'json-file-size')
        return parse_json(bytes(raw))
    finally:
        os.close(fd)


def validate_policy(p):
    keys = {'schema_version', 'databases', 'nacos_database', 'expected_mysql_container',
            'expected_compose_project', 'data_uuid', 'staging_root', 'max_archive_bytes'}
    need(type(p) is dict and set(p) == keys and type(p['schema_version']) is int
         and p['schema_version'] == 1, 'policy-schema')
    names = p['databases']
    need(type(names) is list and 1 <= len(names) <= 32
         and all(type(n) is str and IDENT.fullmatch(n) for n in names)
         and len(set(names)) == len(names), 'database-list')
    need(not set(names) & SYSTEM_DATABASES
         and not any(re.search(r'(^|_)(test|fixture|synthetic)(_|$)', n, re.I) for n in names),
         'forbidden-database')
    need(p['nacos_database'] in names, 'nacos-not-selected')
    need(p['expected_mysql_container'] == 'dell-data-prod-db-mysql-1'
         and p['expected_compose_project'] == 'dell-data-prod-db', 'container-policy')
    need(p['data_uuid'] == UUID and p['staging_root'] == STAGING
         and type(p['max_archive_bytes']) is int and p['max_archive_bytes'] == MAX_BYTES,
         'storage-policy')
    return {k: p[k] for k in keys}


def load_policy():
    fd = open_dir(str(Path(POLICY_PATH).parent), private=True)
    try:
        return validate_policy(read_json_at(fd, Path(POLICY_PATH).name))
    finally:
        os.close(fd)


def stop_child(child, deadline):
    """Terminate only our own docker CLI; MySQL session cleanup is separate."""
    if child.poll() is None:
        child.terminate()
        try:
            child.wait(timeout=min(2, max(.1, deadline - time.monotonic())))
        except subprocess.TimeoutExpired:
            child.kill()
    child.wait(timeout=2)


def small_command(args, deadline, data=None, cap=MAX_META):
    child = subprocess.Popen(args, stdin=subprocess.PIPE if data is not None else subprocess.DEVNULL,
                             stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, env=ENV)
    try:
        if data is not None:
            need(len(data) <= MAX_META, 'command-input-size')
            child.stdin.write(data)
            child.stdin.close()
        fd = child.stdout.fileno()
        os.set_blocking(fd, False)
        output = bytearray()
        end = time.monotonic() + remaining(deadline)
        while True:
            ready, _, _ = select.select([fd], [], [], remaining(end))
            need(bool(ready), 'metadata-command-timeout')
            chunk = os.read(fd, min(65536, cap + 1 - len(output)))
            if not chunk:
                break
            output.extend(chunk)
            need(len(output) <= cap, 'command-output-size')
        need(child.wait(timeout=remaining(end)) == 0, 'metadata-command-failed')
        return bytes(output)
    finally:
        child.stdout.close()
        stop_child(child, deadline)


def host_guard(p, deadline):
    need(os.geteuid() == 0 and platform.system() == 'Linux'
         and platform.machine() in ('x86_64', 'amd64')
         and socket.gethostname().split('.')[0] == 'data-prod-db'
         and not Path('/etc/pve').exists(), 'wrong-guest')
    addresses = parse_json(small_command(['/usr/sbin/ip', '-j', '-4', 'address', 'show', 'scope', 'global'], deadline))
    ips = [v.get('local') for interface in addresses
           if interface.get('ifname') not in ('docker0', 'lo')
           and not interface.get('ifname', '').startswith(('br-', 'veth'))
           for v in interface.get('addr_info', []) if v.get('family') == 'inet']
    need(ips == ['192.168.19.10'], 'wrong-guest-IP')
    for flag, path in [('--mountpoint', MOUNT), ('--target', DATA), ('--target', STAGING)]:
        fs = parse_json(small_command(['/usr/bin/findmnt', '-J', flag, path,
                                     '-o', 'TARGET,SOURCE,FSTYPE,UUID,OPTIONS'], deadline)).get('filesystems')
        need(type(fs) is list and len(fs) == 1 and fs[0].get('target') == MOUNT
             and fs[0].get('uuid') == p['data_uuid'] and fs[0].get('fstype') == 'ext4'
             and 'rw' in fs[0].get('options', '').split(','), 'mount-identity')
    need(Path(DATA).resolve(strict=True) == Path(DATA), 'mysql-data-symlink')
    st = os.stat('/var/run/docker.sock')
    need(stat.S_ISSOCK(st.st_mode) and st.st_uid == 0, 'docker-socket')
    fd = open_dir(STAGING, private=True)
    os.close(fd)


def inspect_container(p, deadline, expected=None):
    raw = parse_json(small_command(DOCKER + ['inspect', '--format', INSPECT_FORMAT,
                                            p['expected_mysql_container']], deadline))
    need(type(raw.get('Id')) is str and re.fullmatch('[0-9a-f]{64}', raw['Id'])
         and raw.get('Name') == '/' + p['expected_mysql_container'], 'container-identity')
    need(raw.get('Labels') == {'project': p['expected_compose_project'], 'service': 'mysql'}
         and raw.get('State', {}).get('Status') == 'running'
         and raw['State'].get('Health') == 'healthy'
         and type(raw['State'].get('Pid')) is int and raw['State']['Pid'] > 1, 'container-role-state')
    mounts = [m for m in raw.get('Mounts', []) if m.get('Destination') == '/var/lib/mysql']
    need(len(mounts) == 1 and mounts[0].get('Type') == 'bind'
         and mounts[0].get('Source') == DATA and mounts[0].get('RW') is True,
         'container-data-mount')
    identity = {k: raw[k] for k in ('Id', 'Name', 'State', 'RestartCount', 'Labels')}
    if expected is not None:
        need(identity == expected, 'container-changed')
    return identity


class Mysql:
    def __init__(self, ident, deadline):
        self.container = ident['Id']
        self.deadline = deadline
        self.pid_namespace = os.readlink('/proc/' + str(ident['State']['Pid']) + '/ns/pid')

    def args(self, program):
        return DOCKER + ['exec', '-i', self.container, 'sh', '-ec', SECRET_PREFIX + program]

    def query(self, sql, release=False):
        deadline = self.deadline if release else self.deadline - 30
        return small_command(self.args(MYSQL), deadline, (sql + '\n').encode()).decode('utf-8')

    def own_session_exists(self, connection, release=False):
        need(type(connection) is int and connection > 0, 'connection-id')
        value = self.query('SELECT COUNT(*) FROM information_schema.PROCESSLIST WHERE ID=' + str(connection) + ';', release=release).strip()
        need(value in ('0', '1'), 'connection-check')
        return value == '1'

    def start(self, program):
        return subprocess.Popen(self.args(program), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                stderr=subprocess.DEVNULL, env=ENV)


class BackupLock:
    def __init__(self, mysql, run_id):
        self.mysql, self.run_id = mysql, run_id
        self.child, self.connection = None, None
        self.acquired, self.released = False, False
        self.buffer = bytearray()

    def send(self, sql):
        need(self.child.poll() is None, 'lock-session-dead')
        self.child.stdin.write((sql + '\n').encode())
        self.child.stdin.flush()

    def line(self, seconds):
        end = min(self.mysql.deadline - 20, time.monotonic() + seconds)
        fd = self.child.stdout.fileno()
        os.set_blocking(fd, False)
        while b'\n' not in self.buffer:
            need(self.child.poll() is None, 'lock-session-dead')
            ready, _, _ = select.select([fd], [], [], remaining(end, .25))
            if not ready:
                continue
            chunk = os.read(fd, 256)
            need(bool(chunk), 'lock-session-eof')
            self.buffer.extend(chunk)
            need(len(self.buffer) <= 1024, 'lock-response-size')
        result, _, rest = self.buffer.partition(b'\n')
        self.buffer = bytearray(rest)
        return result.decode('ascii').rstrip('\r')

    def acquire(self):
        self.child = self.mysql.start('/usr/bin/timeout --signal=TERM --kill-after=5 ' +
                                      str(max(1, int(remaining(self.mysql.deadline, 1800)))) + ' ' + MYSQL)
        try:
            # Capture our session before requesting a lock, so failure can kill
            # only this owned session, never an unidentified server connection.
            self.send("SELECT CONCAT('SESSION:',CONNECTION_ID());")
            value = self.line(5)
            need(bool(re.fullmatch(r'SESSION:[1-9][0-9]{0,19}', value)), 'lock-session-id')
            self.connection = int(value.split(':')[1])
            self.send("SET SESSION lock_wait_timeout=10; LOCK INSTANCE FOR BACKUP; SELECT 'LOCKED_" + self.run_id + "';")
            need(self.line(10) == 'LOCKED_' + self.run_id, 'lock-not-ready')
            self.acquired = True
            self.ensure_alive()
            return self
        except BaseException:
            self.release()
            raise

    def ensure_alive(self):
        need(self.acquired and self.child.poll() is None, 'lock-session-dead')

    def release(self):
        if self.child is None or self.released:
            return
        closed = False
        try:
            if self.child.poll() is None:
                try:
                    if self.acquired:
                        self.send('UNLOCK INSTANCE;')
                    self.child.stdin.close()
                    closed = self.child.wait(timeout=min(5, remaining(self.mysql.deadline))) == 0
                except (OSError, Rejected, subprocess.TimeoutExpired):
                    closed = False
            else:
                # An unexpected exit cannot prove a successful dump, but the
                # separate server session existence check can prove lock release.
                closed = self.child.poll() == 0
        finally:
            try:
                stop_child(self.child, self.mysql.deadline)
            except Exception:
                closed = False
            self.child.stdout.close()
            if self.child.stdin and not self.child.stdin.closed:
                self.child.stdin.close()
        if self.connection is not None:
            if self.mysql.own_session_exists(self.connection, release=True):
                self.mysql.query('KILL CONNECTION ' + str(self.connection) + ';', release=True)
            need(not self.mysql.own_session_exists(self.connection, release=True), 'lock-release-unconfirmed')
        else:
            # No LOCK was submitted before SESSION was received.
            need(closed, 'session-exit-unconfirmed')
        need(self.child.poll() is not None, 'lock-client-exit-unconfirmed')
        self.released = True
        need(closed and self.child.poll() == 0, 'lock-client-abnormal-exit')


def schema_manifest(mysql, databases):
    sql_names = ','.join("'" + n + "'" for n in databases)
    all_databases = set(mysql.query('SHOW DATABASES;').splitlines())
    need(all_databases - SYSTEM_DATABASES == set(databases), 'unlisted-database')
    raw = mysql.query('SELECT JSON_ARRAY(TABLE_SCHEMA,TABLE_NAME,COALESCE(ENGINE,\'\'),TABLE_TYPE) '
                      'FROM information_schema.TABLES WHERE TABLE_SCHEMA IN (' + sql_names + ') '
                      'ORDER BY TABLE_SCHEMA,TABLE_NAME;')
    rows = [parse_json_row(line) for line in raw.splitlines()]
    counts = {name: 0 for name in databases}
    for row in rows:
        need(type(row) is list and len(row) == 4 and all(type(x) is str for x in row)
             and row[0] in counts and row[2] == 'InnoDB' and row[3] == 'BASE TABLE',
             'unsupported-table-or-engine')
        counts[row[0]] += 1
    need(len({(r[0], r[1]) for r in rows}) == len(rows), 'duplicate-schema-metadata')
    for table, column in [('ROUTINES', 'ROUTINE_SCHEMA'), ('EVENTS', 'EVENT_SCHEMA'),
                          ('TRIGGERS', 'TRIGGER_SCHEMA')]:
        result = mysql.query('SELECT COUNT(*) FROM information_schema.' + table +
                             ' WHERE ' + column + ' IN (' + sql_names + ');').strip()
        need(result == '0', 'programmable-object-review-required')
    canonical = json.dumps(sorted(rows), ensure_ascii=True, separators=(',', ':')).encode()
    return {'columns': ['table_schema', 'table_name', 'engine', 'table_type'],
            'sha256': hashlib.sha256(canonical).hexdigest(), 'table_counts': counts,
            'programmable_objects': {'routines': 0, 'events': 0, 'triggers': 0}}


def parse_json_row(value):
    need(len(value) <= 65536, 'schema-row-size')
    # mysql batch escapes JSON backslashes. --raw is safe for this fixed query:
    # JSON strings already escape embedded LF/TAB/control characters.
    return json.loads(value)


class LimitedWriter:
    def __init__(self, fd, maximum):
        self.fd, self.maximum, self.count = fd, maximum, 0

    def write(self, raw):
        need(self.count + len(raw) <= self.maximum, 'compressed-size-limit')
        view = memoryview(raw)
        while view:
            written = os.write(self.fd, view)
            need(written > 0, 'payload-write-failed')
            view = view[written:]
        self.count += len(raw)
        return len(raw)

    def flush(self):
        os.fsync(self.fd)


class DumpOwner:
    """Own exec PID, not the docker CLI or timeout parent; signal by pidfd."""
    def __init__(self, mysql, run_id, deadline):
        need(bool(RUN_ID.fullmatch(run_id)), 'run-id')
        need(hasattr(os, 'pidfd_open') and hasattr(signal, 'pidfd_send_signal'), 'pidfd-required')
        self.mysql, self.deadline = mysql, deadline
        self.directory = '/tmp/dell-prod-db-dump-' + run_id
        self.owner = None
        self.created = False

    def metadata(self, tail):
        # No MYSQL_PWD export for this helper: it only reads our PID marker.
        guard = ('d=' + shlex.quote(self.directory) + '; '
                 'if [ ! -e "$d" ]; then printf "MISSING\\n"; exit 0; fi; '
                 '[ ! -L "$d" ] && [ "$(stat -c %u:%a "$d")" = 0:700 ]; '
                 '[ ! -L "$d/owner" ] && [ "$(stat -c %u:%a:%h "$d/owner")" = 0:600:1 ]; ')
        return small_command(DOCKER + ['exec', self.mysql.container, 'sh', '-ec', guard + tail],
                             self.mysql.deadline, cap=4096).decode('ascii').strip()

    def read_owner(self):
        result = self.metadata('cat "$d/owner"')
        if result == 'MISSING':
            return None
        need(bool(re.fullmatch(r'[1-9][0-9]{0,19} [1-9][0-9]{0,19}', result)), 'dump-owner-record')
        pid, started = map(int, result.split())
        need(pid > 1, 'dump-owner-pid')
        return pid, started

    def command(self, dump):
        need(self.read_owner() is None, 'dump-owner-already-exists')
        # timeout is the parent. Its child shell records its own PID/starttime,
        # then execs mysqldump; the PID is therefore not timeout's PID.
        inner = ('umask 077; d=' + shlex.quote(self.directory) + '; mkdir -m 700 "$d"; '
                 'set -- $(cat /proc/$$/stat); printf "%s %s\\n" "$$" "${22}" > "$d/owner"; '
                 'exec ' + dump)
        seconds = max(1, int(remaining(self.deadline, 1770)))
        return '/usr/bin/timeout --signal=TERM --kill-after=5 ' + str(seconds) + ' sh -ec ' + shlex.quote(inner)

    def capture(self, child):
        self.created = True
        end = min(self.deadline, time.monotonic() + 5)
        while True:
            self.owner = self.read_owner()
            if self.owner is not None:
                return
            need(child.poll() is None, 'dump-before-owner-failed')
            remaining(end)
            time.sleep(.05)

    def matches(self):
        need(self.owner is not None, 'dump-owner-unknown')
        expected_pid, expected_start = self.owner
        result = []
        for directory in Path('/proc').iterdir():
            if not directory.name.isdigit():
                continue
            try:
                if os.readlink(directory / 'ns/pid') != self.mysql.pid_namespace:
                    continue
                status = (directory / 'status').read_text()
                ids = [line.split()[1:] for line in status.splitlines() if line.startswith('NSpid:')]
                if len(ids) != 1 or int(ids[0][-1]) != expected_pid:
                    continue
                raw = (directory / 'stat').read_text()
                fields = raw[raw.rfind(')') + 2:].split()
                if int(fields[19]) != expected_start:
                    continue
                comm = (directory / 'comm').read_text().strip()
                need(comm in ('mysqldump', 'sh'), 'dump-owner-comm-mismatch')
                # A zombie has exited and cannot query or write; timeout/docker
                # will reap it. Do not signal a different reused PID.
                if fields[0] != 'Z':
                    result.append(int(directory.name))
            except (FileNotFoundError, ProcessLookupError):
                continue
        need(len(result) <= 1, 'dump-owner-ambiguous')
        return result

    def signal_owned(self, number):
        for pid in self.matches():
            try:
                fd = os.pidfd_open(pid)
            except ProcessLookupError:
                continue
            try:
                # Recheck after pidfd_open; pidfd pins the process identity even
                # if the numeric PID exits/reuses between this check and signal.
                if self.matches() == [pid]:
                    signal.pidfd_send_signal(fd, number)
            except ProcessLookupError:
                pass
            finally:
                os.close(fd)

    def wait_gone(self, seconds):
        end = min(self.mysql.deadline, time.monotonic() + seconds)
        while self.matches():
            if time.monotonic() >= end:
                return False
            time.sleep(.05)
        return True

    def stop_and_remove(self):
        if not self.created:
            return
        if self.owner is None:
            self.owner = self.read_owner()
        # No known owner is not evidence that a submitted docker exec never ran.
        need(self.owner is not None, 'dump-stop-unconfirmed')
        if self.matches():
            self.signal_owned(signal.SIGTERM)
            if not self.wait_gone(2):
                self.signal_owned(signal.SIGKILL)
        need(self.wait_gone(2), 'dump-stop-unconfirmed')
        pid, started = self.owner
        tail = ('[ "$(cat "$d/owner")" = ' + shlex.quote(str(pid) + ' ' + str(started)) +
                ' ]; rm -- "$d/owner"; rmdir -- "$d"; printf "REMOVED\\n"')
        need(self.metadata(tail) == 'REMOVED', 'dump-owner-remove-failed')
        self.created = False


def dump_stream(mysql, lock, databases, fd, maximum, deadline, *, run_id):
    command = ('mysqldump --protocol=socket --user=root '
               '--single-transaction --quick --routines --triggers --events --hex-blob '
               '--no-tablespaces --set-gtid-purged=OFF --databases ' + ' '.join(databases))
    owner = DumpOwner(mysql, run_id, deadline)
    wrapped = owner.command(command)
    child = None
    writer = LimitedWriter(fd, maximum)
    owner.created = True
    try:
        child = mysql.start(wrapped)
        child.stdin.close()
        owner.capture(child)
        descriptor = child.stdout.fileno()
        os.set_blocking(descriptor, False)
        with gzip.GzipFile(filename='', fileobj=writer, mode='wb', mtime=0) as output:
            while True:
                remaining(deadline, 1)
                lock.ensure_alive()
                ready, _, _ = select.select([descriptor], [], [], .2)
                if not ready:
                    continue
                chunk = os.read(descriptor, 65536)
                if not chunk:
                    break
                output.write(chunk)
            need(child.wait(timeout=remaining(deadline, 5)) == 0, 'mysqldump-failed')
            lock.ensure_alive()
        os.fsync(fd)
        return writer.count
    finally:
        # Stop/confirm the actual owned container exec before releasing the DDL
        # lock. Killing or reaping only the docker client is never stop proof.
        try:
            owner.stop_and_remove()
        finally:
            if child is not None:
                child.stdout.close()
                stop_child(child, mysql.deadline)


def verify_payload(fd, deadline):
    st = checked_file(fd)
    need(0 < st.st_size <= MAX_BYTES, 'payload-size')
    os.lseek(fd, 0, os.SEEK_SET)
    with os.fdopen(os.dup(fd), 'rb') as raw:
        with gzip.GzipFile(fileobj=raw, mode='rb') as stream:
            while stream.read(65536):
                remaining(deadline)
    os.lseek(fd, 0, os.SEEK_SET)
    digest = hashlib.sha256()
    while True:
        remaining(deadline)
        chunk = os.read(fd, 65536)
        if not chunk:
            break
        digest.update(chunk)
    return st.st_size, digest.hexdigest()


def write_manifest(directory, value):
    name = '.manifest.tmp'
    fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600,
                 dir_fd=directory)
    try:
        with os.fdopen(fd, 'wb') as output:
            output.write((json.dumps(value, ensure_ascii=True, indent=2) + '\n').encode())
            output.flush()
            os.fsync(output.fileno())
        os.replace(name, 'manifest.json', src_dir_fd=directory, dst_dir_fd=directory)
        os.fsync(directory)
    finally:
        try:
            os.unlink(name, dir_fd=directory)
        except FileNotFoundError:
            pass


def export_run(p, run_id, parent, deadline, mysql_factory=Mysql):
    need(type(run_id) is str and bool(RUN_ID.fullmatch(run_id)), 'run-id')
    os.mkdir(run_id, mode=0o700, dir_fd=parent)
    directory = os.open(run_id, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
    lock = None
    payload = None
    try:
        identity = inspect_container(p, deadline)
        mysql = mysql_factory(identity, deadline)
        lock = BackupLock(mysql, run_id)
        lock.acquire()
        try:
            lock.ensure_alive()
            before = schema_manifest(mysql, p['databases'])
            need(mysql.own_session_exists(lock.connection), 'lock-session-missing')
            payload = os.open('mysql.sql.gz', os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                              0o600, dir_fd=directory)
            # Reserve 30 seconds for confirmed unlock; total work has one deadline.
            dump_stream(mysql, lock, p['databases'], payload, p['max_archive_bytes'], deadline - 30, run_id=run_id)
            lock.ensure_alive()
            after = schema_manifest(mysql, p['databases'])
            need(before == after, 'schema-metadata-changed')
            need(mysql.own_session_exists(lock.connection), 'lock-session-missing')
            inspect_container(p, deadline - 30, expected=identity)
        finally:
            lock.release()
        need(lock.released, 'lock-release-unconfirmed')
        size, digest = verify_payload(payload, deadline)
        result = {'format': FORMAT, 'status': 'complete', 'run_id': run_id,
                  'databases': p['databases'], 'nacos_database': p['nacos_database'],
                  'table_counts': before['table_counts'], 'schema_manifest': before,
                  'compressed_bytes': size, 'sha256': digest,
                  'DDL_lock_proof': {'type': 'LOCK INSTANCE FOR BACKUP', 'acquired': True,
                                     'same_session_alive_before_and_after_dump': True,
                                     'session_exit_confirmed': True, 'released': True,
                                     'schema_metadata_equal': True},
                  'created_at': now(), 'gzip_full_CRC_verified': True,
                  'ddl_lock_held': True, 'lock_released': True, 'gzip_verified': True,
                  'coverage': 'selected production MySQL databases including complete Nacos external metadata; only BASE TABLE/InnoDB and zero programmable objects supported',
                  'restore_performed': False}
        write_manifest(directory, result)
        return result
    except BaseException as error:
        # Release even if acquisition or an interruption fell before the inner
        # transaction's finally. Failure manifests are never cleanup-authorized.
        if lock is not None and not lock.released:
            try:
                lock.release()
            except Exception:
                pass
        # No SQL, exception text, credentials or source response is persisted here.
        try:
            write_manifest(directory, {'format': FORMAT, 'status': 'failed', 'run_id': run_id,
                                       'created_at': now(), 'error_type': type(error).__name__,
                                       'lock_release_confirmed': bool(lock and lock.released)})
        except Exception:
            pass
        raise
    finally:
        if payload is not None:
            os.close(payload)
        os.close(directory)


def cleanup_run(p, run_id, parent):
    need(type(run_id) is str and bool(RUN_ID.fullmatch(run_id)), 'run-id')
    directory = os.open(run_id, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
    try:
        st = os.fstat(directory)
        need(st.st_uid == 0 and stat.S_IMODE(st.st_mode) == 0o700, 'run-directory-privacy')
        need(set(os.listdir(directory)) == FILES, 'cleanup-unknown-files')
        manifest = read_json_at(directory, 'manifest.json')
        need(type(manifest) is dict and manifest.get('format') == FORMAT
             and manifest.get('status') == 'complete' and manifest.get('run_id') == run_id
             and manifest.get('databases') == p['databases']
             and manifest.get('nacos_database') == p['nacos_database']
             and manifest.get('gzip_full_CRC_verified') is True
             and manifest.get('ddl_lock_held') is True
             and manifest.get('lock_released') is True and manifest.get('gzip_verified') is True
             and manifest.get('DDL_lock_proof', {}).get('released') is True
             and type(manifest.get('sha256')) is str
             and re.fullmatch('[0-9a-f]{64}', manifest['sha256']), 'cleanup-not-worker-artifact')
        checked = {}
        for name in sorted(FILES):
            fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
            try:
                checked[name] = checked_file(fd)
            finally:
                os.close(fd)
        need(checked['mysql.sql.gz'].st_size == manifest.get('compressed_bytes'), 'cleanup-size-mismatch')
        # Validate every entry before deleting anything. No glob, recursive delete,
        # failed-run deletion, symlink traversal or cleanup of a caller-chosen path.
        for name in ['mysql.sql.gz', 'manifest.json']:
            current = os.stat(name, dir_fd=directory, follow_symlinks=False)
            need((current.st_ino, current.st_dev, current.st_nlink) ==
                 (checked[name].st_ino, checked[name].st_dev, 1), 'cleanup-file-changed')
            os.unlink(name, dir_fd=directory)
        os.fsync(directory)
    finally:
        os.close(directory)
    os.rmdir(run_id, dir_fd=parent)
    os.fsync(parent)


def main():
    args = argparse.ArgumentParser(description=__doc__)
    args.add_argument('action', choices=['export', 'cleanup'])
    args.add_argument('--run-id', required=True)
    options = args.parse_args()
    need(bool(RUN_ID.fullmatch(options.run_id)), 'run-id')
    os.umask(0o077)
    deadline = time.monotonic() + 1800
    p = load_policy()
    host_guard(p, deadline)
    parent = open_dir(p['staging_root'], private=True)
    lockfd = None
    try:
        lockfd = os.open('.worker.lock', os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK,
                         0o600, dir_fd=parent)
        checked_file(lockfd)
        fcntl.flock(lockfd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if options.action == 'export':
            space = os.fstatvfs(parent)
            need(space.f_bavail * space.f_frsize >= MAX_BYTES + 64 * 1024 * 1024,
                 'staging-space-headroom')
            result = export_run(p, options.run_id, parent, deadline)
            print(json.dumps({'status': 'complete', 'run_id': options.run_id,
                              'compressed_bytes': result['compressed_bytes'],
                              'databases': result['databases'],
                              'schema_count': len(result['databases']),
                              'coverage': 'production-MySQL-and-Nacos-only',
                              'restore_performed': False}))
        else:
            cleanup_run(p, options.run_id, parent)
            print(json.dumps({'status': 'cleaned', 'run_id': options.run_id}))
    finally:
        if lockfd is not None:
            os.close(lockfd)
        os.close(parent)


if __name__ == '__main__':
    # Termination inside Python flows through the same release/failure path.
    def interrupted(signum, frame):
        raise Rejected('interrupted')
    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    try:
        main()
    except Exception as error:
        print(json.dumps({'status': 'failed', 'error_type': type(error).__name__}), file=sys.stderr)
        raise SystemExit(1)
