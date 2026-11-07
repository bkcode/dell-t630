#!/opt/homebrew/opt/python@3.14/bin/python3.14 -I
"""Fixed anonymous native Mac probes; installation and live delivery are separate actions."""
import argparse
import concurrent.futures
import datetime
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import time
import tempfile
import urllib.parse

ROOT = Path(__file__).resolve().parents[3]
PRIVATE = ROOT / 'private/notifications/mac-external-probe'
HOOK = ROOT / 'private/notifications/lark-webhook'
HOST = '192.168.21.22'
# Immutable endpoints: no user-supplied URL, port, header or authentication.
CHECKS = (
    ('pve-ssh', 'tcp', 22, ''),
    ('pve-ui', 'tcp', 8006, ''),
    ('penpot', 'http', 9001, '/'),
    ('nexus', 'http', 8081, '/service/rest/v1/status'),
    ('nas-web', 'http', 9080, '/'),
    ('jellyfin', 'http', 8096, '/health'),
    ('java-test-oidc', 'http', 19999, '/.well-known/openid-configuration'),
)
KEYS = ('pve-host',) + tuple(x[0] for x in CHECKS)
ENV = {'PATH': '/usr/bin:/bin', 'LANG': 'C', 'LC_ALL': 'C'}
MAX_ATTEMPTS = 3


class Rejected(Exception):
    pass


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def probe_one(item):
    if item not in CHECKS:
        raise Rejected('endpoint outside fixed allowlist')
    name, kind, port, path = item
    if kind == 'tcp':
        cmd = ['/usr/bin/nc', '-z', '-G', '3', '-w', '3', HOST, str(port)]
    else:
        cmd = ['/usr/bin/curl', '-q', '--noproxy', '*', '--proto', '=http',
               '--max-redirs', '0', '--connect-timeout', '3', '--max-time', '5',
               '--silent', '--output', '/dev/null', '--write-out', '%{http_code}',
               'http://' + HOST + ':' + str(port) + path]
    try:
        p = subprocess.run(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                           stderr=subprocess.DEVNULL, timeout=7, env=ENV)
        status = int(p.stdout) if kind == 'http' and re.fullmatch(rb'[0-9]{3}', p.stdout) else None
        ok = p.returncode == 0 and (kind == 'tcp' or status == 200)
        return {'name': name, 'ok': ok, 'exit_code': p.returncode, 'http_status': status}
    except (OSError, subprocess.TimeoutExpired):
        return {'name': name, 'ok': False, 'exit_code': None, 'http_status': None}


def sample():
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        rows = list(pool.map(probe_one, CHECKS))
    return {'at': now(), 'credentials_sent': False, 'response_bodies_saved': False,
            'native_clients': ['/usr/bin/nc', '/usr/bin/curl'], 'results': rows}


def empty_state():
    return {'version': 1, 'checks': {}, 'incidents': {}, 'cycles': 0}


def stable(checks, key, up):
    value = checks.setdefault(key, {'stable': None, 'last': None, 'count': 0})
    value['count'] = min(2, value['count'] + 1) if value['last'] == up else 1
    value['last'] = up
    if value['count'] == 2:
        value['stable'] = 'up' if up else 'down'
    return value['stable']


def transition(state, observations, timestamp):
    """Pure bounded state machine. Returns current queued transitions, never sends."""
    if set(observations) != set(KEYS[1:]) or any(type(v) is not bool for v in observations.values()):
        raise Rejected('incomplete fixed probe sample')
    last = state.get('last_sample')
    if last is not None and (timestamp - last > 180 or timestamp < last):
        for check in state['checks'].values():
            check['last'] = None
            check['count'] = 0
            check['stable'] = None
    state['last_sample'] = timestamp
    state['cycles'] += 1
    for key, up in observations.items():
        stable(state['checks'], key, up)
    host = stable(state['checks'], 'pve-host', observations['pve-ssh'] or observations['pve-ui'])
    suppressed = host == 'down'
    for key in KEYS:
        incident = state['incidents'].setdefault(key, {'desired': None, 'delivered': None, 'sequence': 0, 'pending': None})
        if key != 'pve-host' and suppressed:
            incident['pending'] = None
            # Retain acknowledged phase, so recovery never falsely forgets an earlier alert.
            incident['desired'] = incident['delivered']
            continue
        current = state['checks'][key]['stable']
        if current is None:
            continue
        desired = 'firing' if current == 'down' else ('resolved' if incident['delivered'] == 'firing' else None)
        if desired != incident['desired']:
            incident['desired'] = desired
            incident['sequence'] += 1
            incident['pending'] = None
            if desired is not None and desired != incident['delivered']:
                event_id = hashlib.sha256((key + ':' + desired + ':' + str(incident['sequence'])).encode()).hexdigest()[:16]
                incident['pending'] = {'id': event_id, 'check': key, 'phase': desired, 'created_at': timestamp,
                                       'attempts': 0, 'last_attempt': 0, 'exhausted': False}
    # A resumed/clock-shifted sample cannot release stale queued events. Both
    # the check and host aggregation must regain two fresh observations first.
    pending = [v['pending'] for k, v in state['incidents'].items() if v['pending']
               and state['checks'][k]['stable'] is not None
               and (k == 'pve-host' or host is not None)]
    return sorted(pending, key=lambda x: (x['check'] != 'pve-host', x['created_at'], x['check']))


def payload(event):
    if event['check'] not in KEYS or event['phase'] not in ('firing', 'resolved'):
        raise Rejected('unknown event')
    title = '告警' if event['phase'] == 'firing' else '恢复'
    scope = ('两个PVE管理端口连续两次同时不可达；合并主机故障，抑制各服务通知。'
             if event['check'] == 'pve-host' and event['phase'] == 'firing'
             else '连续两次固定匿名探测确认状态变化。')
    text = ('【Dell T630 外部' + title + '】\ncheck=' + event['check'] + '\n' + scope +
            '\nprobe=Mac LAN\nevent=' + event['id'] + '\nobserved=' + datetime.datetime.fromtimestamp(event['created_at'], datetime.timezone.utc).isoformat() +
            '\n此探测依赖Mac开机、唤醒和网络，不能单独判定物理硬件故障。')
    return json.dumps({'msg_type': 'text', 'content': {'text': text}}, ensure_ascii=False, separators=(',', ':')).encode()


def read_private(path, limit=4096):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        s = os.fstat(fd)
        if not stat.S_ISREG(s.st_mode) or stat.S_IMODE(s.st_mode) != 0o600 or s.st_uid != os.getuid() or s.st_size > limit or s.st_nlink != 1:
            raise Rejected('private file ownership, permissions or size invalid')
        return os.read(fd, limit + 1)
    finally:
        os.close(fd)


def validate_hook(raw):
    try:
        value = raw.decode('ascii').rstrip('\n')
        u = urllib.parse.urlsplit(value)
    except (UnicodeError, ValueError):
        raise Rejected('notification endpoint rejected') from None
    if (len(value) > 256 or u.scheme != 'https' or u.netloc != 'open.larksuite.com' or u.query or u.fragment or
        not re.fullmatch(r'/open-apis/bot/v2/hook/[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}', u.path)):
        raise Rejected('notification endpoint rejected')
    return value


def curl_quote(value):
    # Config grammar quoted string; raw input can never inject another option.
    return '"' + value.replace('\\', '\\\\').replace('"', '\\"').replace('\r', '\\r').replace('\n', '\\n') + '"'


def send_lark(body):
    url = validate_hook(read_private(HOOK))
    config = ('url = ' + curl_quote(url) + '\nheader = "Content-Type: application/json; charset=utf-8"\n' +
              'data = ' + curl_quote(body.decode('utf8')) + '\n').encode()
    # Both the webhook and message are stdin only, never URL/data argv or environment.
    cmd = ['/usr/bin/curl', '-q', '--config', '-', '--noproxy', '*', '--proto', '=https',
           '--max-redirs', '0', '--connect-timeout', '3', '--max-time', '8', '--max-filesize', '4096',
           '--silent', '--request', 'POST', '--write-out', '\n%{http_code}']
    try:
        result = subprocess.run(cmd, input=config, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=10, env=ENV)
        raw, status = result.stdout.rsplit(b'\n', 1)
        value = json.loads(raw) if len(raw) <= 4096 else None
        acknowledged = (result.returncode == 0 and status == b'200' and isinstance(value, dict) and
                        type(value.get('code')) is int and value['code'] == 0)
        return acknowledged
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return False


def deliver_one(state, pending, timestamp, sender):
    for event in pending:
        if event['attempts'] >= MAX_ATTEMPTS:
            event['exhausted'] = True
        if event['exhausted'] or timestamp - event['last_attempt'] < 60:
            continue
        event['attempts'] += 1
        event['last_attempt'] = timestamp
        try:
            ok = sender(payload(event)) is True
        except Exception:
            ok = False
        if ok:
            incident = state['incidents'][event['check']]
            incident['delivered'] = event['phase']
            incident['pending'] = None
        elif event['attempts'] >= MAX_ATTEMPTS:
            event['exhausted'] = True
        return {'event': 'delivery_acknowledged' if ok else 'delivery_failed', 'id': event['id'],
                'check': event['check'], 'phase': event['phase'], 'attempt': event['attempts'], 'exhausted': event['exhausted']}
    return None


def private_dir():
    # Existing secret parents also must belong to this user and be mode 0700.
    for path in [ROOT / 'private', ROOT / 'private/notifications']:
        s = path.lstat()
        if not stat.S_ISDIR(s.st_mode) or s.st_uid != os.getuid() or stat.S_IMODE(s.st_mode) != 0o700:
            raise Rejected('private parent permissions rejected')
    PRIVATE.mkdir(mode=0o700, exist_ok=True)
    s = PRIVATE.lstat()
    if not stat.S_ISDIR(s.st_mode) or s.st_uid != os.getuid() or stat.S_IMODE(s.st_mode) != 0o700:
        raise Rejected('private state directory rejected')


def atomic_json(path, value):
    # Exclusive new inode avoids following or truncating a preexisting temp/hardlink.
    fd, name = tempfile.mkstemp(prefix=path.name + '.', suffix='.tmp', dir=path.parent)
    try:
        os.fchmod(fd, 0o600)
        os.write(fd, (json.dumps(value, separators=(',', ':')) + '\n').encode())
        os.fsync(fd)
    finally:
        os.close(fd)
    try:
        os.replace(name, path)
    finally:
        if os.path.exists(name):os.unlink(name)


def save_state(state):
    atomic_json(PRIVATE / 'state.json', state)


def log(value):
    path = PRIVATE / 'events.jsonl'
    if path.exists():
        existing = path.lstat()
        if not stat.S_ISREG(existing.st_mode) or existing.st_uid != os.getuid() or existing.st_nlink != 1:
            raise Rejected('private log rejected')
    if path.exists() and path.lstat().st_size >= 262144:
        if path.is_symlink():raise Rejected('log symlink rejected')
        os.replace(path, PRIVATE / 'events.previous.jsonl')
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND | os.O_NOFOLLOW, 0o600)
    try:
        os.fchmod(fd, 0o600)
        os.write(fd, (json.dumps({'at': now(), **value}, separators=(',', ':')) + '\n').encode())
    finally:
        os.close(fd)


def run(deliver):
    private_dir()
    fd = os.open(PRIVATE / 'run.lock', os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        s = os.fstat(fd)
        if not stat.S_ISREG(s.st_mode) or s.st_uid != os.getuid() or stat.S_IMODE(s.st_mode) != 0o600 or s.st_nlink != 1:
            raise Rejected('private lock rejected')
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return {'event': 'overlap_skipped'}
        p = PRIVATE / 'state.json'
        state = json.loads(read_private(p, 65536)) if p.exists() else empty_state()
        if state.get('version') != 1:raise Rejected('unknown state version')
        measured = sample()
        pending = transition(state, {x['name']: x['ok'] for x in measured['results']}, time.time())
        # Persist attempt budget BEFORE sending to bound retries across a process crash.
        if deliver:
            event = None
            def sender(body):
                save_state(state)
                return send_lark(body)
            event = deliver_one(state, pending, time.time(), sender)
        else:
            event = {'event': 'dry_run', 'pending_count': len(pending)}
        save_state(state)
        log(event or {'event': 'sample_no_transition'})
        return {'at': measured['at'], 'cycles': state['cycles'], 'host_stable': state['checks']['pve-host']['stable'],
                'delivery_enabled': deliver, 'delivery': event, 'results': measured['results']}
    finally:
        os.close(fd)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('action', choices=['baseline', 'run'])
    p.add_argument('--deliver', action='store_true')
    args = p.parse_args()
    if args.deliver and args.action != 'run':raise Rejected('baseline cannot notify')
    print(json.dumps(sample() if args.action == 'baseline' else run(args.deliver), ensure_ascii=False))


if __name__ == '__main__':
    try:
        main()
    except Exception:
        print(json.dumps({'event': 'probe_failed', 'details_logged': False}))
        raise SystemExit(1)
