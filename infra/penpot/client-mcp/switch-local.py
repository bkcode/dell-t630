#!/usr/bin/env python3
"""Replace only two Codex MCP transports; secrets remain on the Penpot server."""
import argparse
import copy
import datetime
import json
import os
from pathlib import Path
import re
import stat
import tomllib
import uuid
from zoneinfo import ZoneInfo

CONFIG = Path.home() / '.codex/config.toml'
ROOT = Path(__file__).resolve().parents[3]
CONNECTION = Path.home() / '.codex/penpot-server'


def section_replace(text, name, content):
    pattern = re.compile(r'(?ms)^\[' + re.escape(name) + r'\]\s*\n.*?(?=^\[|\Z)')
    if len(list(pattern.finditer(text))) != 1:
        raise RuntimeError('one-exact-MCP-section-required')
    return pattern.sub(lambda match: f'[{name}]\n{content}\n\n', text, count=1)


def command(mode):
    return ['/usr/bin/ssh', '-T', '-i', str(Path.home() / '.ssh/yang_local_rsa'),
        '-o', 'IdentitiesOnly=yes', '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=yes',
        '-o', 'UserKnownHostsFile=' + str(CONNECTION / 'known_hosts'), '-o', 'HostKeyAlias=dell-vm250',
        '-o', 'ConnectTimeout=8', '-o', 'ServerAliveInterval=30', '-o', 'ServerAliveCountMax=3',
        'ub@192.168.19.50',
        'sudo -n /usr/bin/python3 -B /opt/dell/penpot/runtime/client-mcp/launch.py ' + mode]


def create(path, body, mode=0o600):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, mode)
    os.fchmod(fd, mode)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(body)
        stream.flush()
        os.fsync(stream.fileno())


def main(apply):
    os.umask(0o077)
    if CONFIG.resolve() != CONFIG or CONFIG.stat().st_uid != os.getuid() or not stat.S_ISREG(CONFIG.stat().st_mode):
        raise RuntimeError('owned-regular-user-config-required')
    raw = CONFIG.read_bytes()
    before = tomllib.loads(raw.decode())
    expected = copy.deepcopy(before)
    core = expected['mcp_servers']['penpot']
    importer = expected['mcp_servers']['penpot_import']
    if 'url' not in core or 'url' not in importer:
        raise RuntimeError('existing-HTTP-transports-required-no-blind-retry')
    for target, mode in [(core, 'core'), (importer, 'import')]:
        target.pop('url')
        target.pop('http_headers', None)
        target.update(command='/usr/bin/ssh', args=command(mode)[1:])
    core['startup_timeout_sec'] = 30
    text = raw.decode()
    for name, mode, values in [('penpot', 'core', core), ('penpot_import', 'import', importer)]:
        lines = ['command = "/usr/bin/ssh"', 'args = ' + json.dumps(command(mode)[1:])]
        for key in ['startup_timeout_sec', 'tool_timeout_sec', 'enabled', 'required', 'enabled_tools', 'disabled_tools',
                    'default_tools_approval_mode', 'environment_id']:
            if key in values:
                lines.append(key + ' = ' + json.dumps(values[key]))
        text = section_replace(text, 'mcp_servers.' + name, '\n'.join(lines))
    header = re.compile(r'(?ms)^\[mcp_servers\.penpot_import\.http_headers\]\s*\n.*?(?=^\[|\Z)')
    if len(list(header.finditer(text))) != 1:
        raise RuntimeError('one-old-import-auth-header-section-required')
    text = header.sub('', text, count=1)
    if tomllib.loads(text) != expected:
        raise RuntimeError('unrelated-settings-or-approval-policies-would-change')
    entries = [line for line in (ROOT / 'private/known_hosts').read_text().splitlines()
               if line.startswith('dell-vm250 ')]
    if len(entries) != 1 or entries[0].split()[1] != 'ssh-ed25519':
        raise RuntimeError('existing-trusted-VM250-host-key-required')
    result = {'config': str(CONFIG), 'changed_MCPs': ['penpot', 'penpot_import'],
              'transport': 'SSH-stdio-to-existing-VM250-MCP', 'target': '192.168.19.50',
              'server_tokens_copied_to_Mac': False, 'other_settings_and_tool_approval_policies_unchanged': True,
              'SSH_host_verification': 'strict-existing-trusted-key', 'apply': apply}
    if apply:
        if CONNECTION.exists():
            raise RuntimeError('connection-directory-already-exists-review-before-retry')
        CONNECTION.mkdir(mode=0o700)
        create(CONNECTION / 'known_hosts', (entries[0] + '\n').encode())
        stamp = datetime.datetime.now(ZoneInfo('Asia/Shanghai')).strftime('%Y%m%d-%H%M%S')
        backup = Path.home() / '.codex/backups' / ('penpot-server-' + stamp)
        backup.mkdir(parents=True, mode=0o700)
        backup.chmod(0o700)
        create(backup / 'config.toml', raw)
        if CONFIG.read_bytes() != raw:
            raise RuntimeError('config-changed-during-prepare')
        temporary = CONFIG.with_name(CONFIG.name + '.penpot-' + uuid.uuid4().hex)
        try:
            create(temporary, text.encode())
            os.replace(temporary, CONFIG)
        finally:
            temporary.unlink(missing_ok=True)
        if tomllib.loads(CONFIG.read_text()) != expected or CONFIG.stat().st_mode & 0o777 != 0o600:
            raise RuntimeError('written-config-verification-failed')
        result['private_backup'] = str(backup / 'config.toml')
        result['config_mode'] = '0600'
        result['known_hosts_mode'] = '0600'
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    try:
        main(args.apply)
    except Exception as error:
        print(json.dumps({'status': 'local-switch-not-confirmed', 'error_type': type(error).__name__,
                          'code': str(error) if isinstance(error, RuntimeError) else 'private-details-withheld'}))
        raise SystemExit(1)
