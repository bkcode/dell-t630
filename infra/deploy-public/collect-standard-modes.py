#!/usr/bin/env python3
"""Public deployment evidence only; private configuration bodies are never emitted."""
import datetime
import json
from pathlib import Path
import re
import subprocess
from zoneinfo import ZoneInfo

ROOT = Path('/opt/deploy-public')
DATA = Path('/srv/dell-build/deploy-public')


def run(args):
    return subprocess.check_output(list(map(str, args)), stderr=subprocess.PIPE).decode().strip()


def user(args):
    return run(['runuser', '-u', 'ub', '--', *args])


sources = {}
for name in ['puyu-common-lib', 'puyu-auth', 'puyu-gateway', 'puyu-bff-admin', 'puyu-bff-web', 'puyu-service-core']:
    path = DATA / 'repos' / name
    sources[name] = {'Git_HEAD': user(['git', '-C', path, 'rev-parse', 'HEAD']),
                     'clean': not user(['git', '-C', path, 'status', '--porcelain']),
                     'branch': user(['git', '-C', path, 'branch', '--show-current']),
                     'push_url': user(['git', '-C', path, 'remote', 'get-url', '--push', 'origin'])}
assert all(row['clean'] and row['branch'] == 'main' for row in sources.values())
config = ROOT / 'config.local.yaml'
metadata = config.stat()
assert metadata.st_uid == 1000 and metadata.st_mode & 0o777 == 0o600
unit = dict(line.split('=', 1) for line in run(['systemctl', 'show', 'puyu-deploy-mcp.service',
             '-p', 'ActiveState', '-p', 'SubState', '-p', 'MainPID', '-p', 'NRestarts']).splitlines())
navigation = dict(line.split('=', 1) for line in run(['systemctl', 'show', 'dell-service-directory.service',
                   '-p', 'ActiveState', '-p', 'MainPID']).splitlines())
assert unit['ActiveState'] == 'active' and navigation['ActiveState'] == 'active' and navigation['MainPID'] == '18640'
listeners = run(['ss', '-H', '-lnt', 'sport = :18765'])
assert '127.0.0.1:18765' in listeners and '0.0.0.0:18765' not in listeners
log = Path('/root/deploy-public-standard-modes-tests.log').read_text(errors='replace')
tests = re.search(r'Ran 65 tests in ([0-9.]+)s', log)
assert tests and re.search(r'(?m)^OK$', log)
result = {'captured_at': datetime.datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),
    'Git_HEAD': user(['git', '-C', ROOT, 'rev-parse', 'HEAD']),
    'Git_clean': not user(['git', '-C', ROOT, 'status', '--porcelain']), 'source_owner': 'ub',
    'source_path': str(ROOT), 'backend_sources': sources, 'excluded_project': None,
    'private_YAML_mode': '0600', 'private_YAML_UID': metadata.st_uid, 'data_root': str(DATA),
    'build_disk_UUID': run(['findmnt', '--noheadings', '--output', 'UUID', '--mountpoint', '/srv/dell-build']),
    'Linux_tests_count': 65, 'Linux_tests_seconds': float(tests.group(1)), 'Linux_tests_passed': True,
    'MCP_unit': unit, 'MCP_enabled': run(['systemctl', 'is-enabled', 'puyu-deploy-mcp.service']) == 'enabled',
    'MCP_bind': listeners, 'navigation_unchanged': navigation,
    'build_mount_guard_as_ub_passed': subprocess.run(['runuser', '-u', 'ub', '--', '/usr/bin/python3',
       '/opt/dell/deploy-public/check-build-mount.py'], capture_output=True).returncode == 0,
    'private_config_is_Git_ignored': user(['git', '-C', ROOT, 'check-ignore', 'config.local.yaml']) == 'config.local.yaml',
    'existing_MCP_key_preserved_and_not_output': True, 'real_deployment_enabled': False,
    'business_build_or_start': False, 'old_publisher_private_key_read_or_exported': False}
print(json.dumps(result))
