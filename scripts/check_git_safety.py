#!/usr/bin/env python3
"""Inspect Git-bound files without printing sensitive values; no network or server actions."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOOK = re.compile(rb'https://open\.(?:larksuite|feishu)\.(?:com|cn)/open-apis/bot/v2/hook/([A-Za-z0-9-]{12,})')
FIXTURE_HOOKS = {b'00000000-0000-0000-0000-000000000000', b'11111111-1111-4111-8111-111111111111'}
PATTERNS = {
    'private-key-material': re.compile(rb'-----BEGIN (?:OPENSSH |RSA |EC |DSA |ENCRYPTED )?PRIVATE KEY-----'),
    'github-token': re.compile(rb'\bgh[pousr]_[A-Za-z0-9]{30,}\b|\bgithub_pat_[A-Za-z0-9_]{30,}\b'),
    'aws-access-key': re.compile(rb'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b'),
}
PAYLOAD_SUFFIXES = {'.dump', '.qcow2', '.iso', '.tar', '.gz', '.zst', '.zip', '.7z', '.vma', '.img', '.vmdk', '.sqlite', '.sqlite3', '.db'}


def git(*args: str) -> bytes:
    return subprocess.check_output(['git', '-C', str(ROOT), *args], stderr=subprocess.PIPE)


def inspect(staged: bool) -> dict:
    args = ('ls-files', '-z') if staged else ('ls-files', '--cached', '--others', '--exclude-standard', '-z')
    paths = sorted(set(filter(None, git(*args).decode().split('\0'))))
    findings = []
    for name in paths:
        path = Path(name)
        reason = None
        if 'private' in path.parts or '.git' in path.parts:
            reason = 'private-or-git-internals'
        elif path.name == '.env' or (path.name.startswith('.env.') and path.name != '.env.example'):
            reason = 'runtime-environment-file'
        elif path.suffix.lower() in PAYLOAD_SUFFIXES:
            reason = 'backup-or-database-payload'
        elif path.name.startswith(('id_rsa', 'id_ed25519', 'known_hosts')) or path.suffix.lower() in {'.key', '.pem'}:
            reason = 'machine-local-key-or-trust-file'
        if reason:
            findings.append({'path': name, 'rule': reason})
        if staged:
            mode = git('ls-files', '-s', '--', name).split(b' ', 1)[0]
            if mode == b'120000':
                findings.append({'path': name, 'rule': 'symlink-requires-review'})
                continue
            content = git('show', ':' + name)
        else:
            file = ROOT / name
            if file.is_symlink():
                findings.append({'path': name, 'rule': 'symlink-requires-review'})
                continue
            if not file.is_file():
                continue
            content = file.read_bytes()
        for rule, pattern in PATTERNS.items():
            for match in pattern.finditer(content):
                findings.append({'path': name, 'line': content[:match.start()].count(b'\n') + 1, 'rule': rule})
        for match in HOOK.finditer(content):
            if match.group(1) not in FIXTURE_HOOKS:
                findings.append({'path': name, 'line': content[:match.start()].count(b'\n') + 1, 'rule': 'live-lark-webhook'})
    return {'status': 'failed' if findings else 'passed', 'scope': 'Git index' if staged else 'Git candidate working files',
            'files_checked': len(paths), 'findings': findings,
            'limitations': 'Rule-based scan only; does not prove absence of all credentials. Fixture hooks are nonfunctional test values. No secret contents are emitted.'}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--staged', action='store_true', help='Inspect exact index blobs, including already tracked ignored files')
    args = parser.parse_args()
    try:
        result = inspect(args.staged)
    except (OSError, subprocess.CalledProcessError):
        print(json.dumps({'status': 'failed', 'error': 'Cannot inspect Git files; raw output suppressed'}))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return int(result['status'] != 'passed')


if __name__ == '__main__':
    raise SystemExit(main())
