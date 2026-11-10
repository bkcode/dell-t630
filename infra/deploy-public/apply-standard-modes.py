#!/usr/bin/env python3
"""Controlled publisher-only update. Run as root on VM220; no business commands."""
import datetime
import json
from pathlib import Path
import re
import sqlite3
import subprocess
import sys
from zoneinfo import ZoneInfo

ROOT = Path('/opt/deploy-public')
EXPECTED = sys.argv[1]
UPDATER = sys.stdin.read()

def run(args, **kwargs):
    return subprocess.run(list(map(str, args)), check=True, capture_output=True, **kwargs).stdout.decode().strip()

def user(args, **kwargs):
    return run(['runuser', '-u', 'ub', '--', *args], **kwargs)

old_head = user(['git', '-C', ROOT, 'rev-parse', 'HEAD'])
assert not user(['git', '-C', ROOT, 'status', '--porcelain']), 'publisher-worktree-dirty'
old_config = (ROOT / 'config.local.yaml').read_bytes()
db = sqlite3.connect('file:/srv/dell-build/deploy-public/mcp-state/jobs.sqlite?mode=ro', uri=True)
assert all(json.loads(row[0])['status'] not in ('queued', 'running') for row in db.execute('SELECT payload FROM jobs')), 'active-job'
db.close()
nav_pid = run(['systemctl', 'show', 'dell-service-directory.service', '-p', 'MainPID', '--value'])
run(['systemctl', 'stop', 'puyu-deploy-mcp.service'])
try:
    user(['git', '-C', ROOT, 'pull', '--ff-only', 'origin', 'main'])
    head = user(['git', '-C', ROOT, 'rev-parse', 'HEAD'])
    assert head == EXPECTED, 'unexpected-publisher-HEAD'
    update = json.loads(user([ROOT / '.venv/bin/python', '-c', UPDATER, ROOT, ROOT / 'config.local.yaml']))
    log = Path('/root/deploy-public-standard-modes-tests.log')
    with log.open('wb') as stream:
        log.chmod(0o600)
        result = subprocess.run(['runuser', '-u', 'ub', '--', str(ROOT / '.venv/bin/python'), '-m', 'unittest', 'discover', '-s', 'tests', '-v'], cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT, timeout=180)
    content = log.read_text(errors='replace')
    match = re.search(r'Ran 65 tests in ([0-9.]+)s', content)
    assert result.returncode == 0 and match and re.search(r'(?m)^OK$', content), 'publisher-tests-failed'
except Exception:
    # Restore only our private YAML and restart. Code accepts the previous schema.
    config = ROOT / 'config.local.yaml'
    config.write_bytes(old_config)
    config.chmod(0o600)
    import os
    os.chown(config, 1000, 1000)
    run(['systemctl', 'start', 'puyu-deploy-mcp.service'])
    raise
run(['systemctl', 'start', 'puyu-deploy-mcp.service'])
assert run(['systemctl', 'is-active', 'puyu-deploy-mcp.service']) == 'active'
assert run(['systemctl', 'show', 'dell-service-directory.service', '-p', 'MainPID', '--value']) == nav_pid
print(json.dumps({'captured_at': datetime.datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(), 'old_HEAD': old_head, 'HEAD': head, 'config_update': update, 'Linux_tests_count': 65, 'Linux_tests_seconds': float(match.group(1)), 'Linux_tests_passed': True, 'MCP_active': True, 'navigation_PID_unchanged': nav_pid, 'real_backend_commands': False, 'credentials_output': False}))
