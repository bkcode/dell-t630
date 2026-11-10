#!/usr/bin/python3
"""Start the VM250 bridge in the existing importer; no keys enter argv or stdout."""
import os
from pathlib import Path
import socket
import sys


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ('core', 'import'):
        raise RuntimeError('invalid-mode')
    if os.geteuid() != 0 or socket.gethostname() != 'penpot-service' or Path('/etc/pve').exists():
        raise RuntimeError('assigned-VM250-root-only')
    directory = Path(__file__).absolute().parent
    script = directory / 'relay.mjs'
    for path in (directory, script):
        if path.resolve() != path or path.stat().st_uid != 0 or path.stat().st_mode & 0o022:
            raise RuntimeError('trusted-root-owned-code-required')
    if not script.is_file():
        raise RuntimeError('regular-script-required')
    body = script.read_text()
    if not body or len(body.encode()) > 64 * 1024:
        raise RuntimeError('bounded-script-required')
    os.execv('/usr/bin/docker', [
        '/usr/bin/docker', '--host', 'unix:///var/run/docker.sock', 'exec', '-i',
        'penpot-penpot-import-1', 'node', '--input-type=module', '--eval', body, sys.argv[1],
    ])


if __name__ == '__main__':
    try:
        main()
    except Exception:
        sys.stderr.write('Penpot MCP launcher unavailable.\n')
        raise SystemExit(1)
