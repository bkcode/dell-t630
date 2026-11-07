"""Validate the immutable query-safe runtime templates and their Compose bindings."""
import hashlib
import json
from pathlib import Path
import re

BASE = Path(__file__).resolve().parent


def validate_runtime_logging(config):
    root = BASE / 'runtime' / 'logging'
    lock = json.loads((root / 'templates.lock.json').read_text())
    bindings = config['services']['penpot-frontend'].get('volumes', [])
    texts = {}
    for filename, entry in lock['templates'].items():
        original_path = root / 'public-source' / filename
        if hashlib.sha256(original_path.read_bytes()).hexdigest() != entry['source_sha256']:
            raise RuntimeError('Original public template fingerprint mismatch: ' + filename)
        path = BASE / entry['runtime_source']
        if hashlib.sha256(path.read_bytes()).hexdigest() != entry['target_sha256']:
            raise RuntimeError('Query-safe runtime template checksum mismatch: ' + filename)
        if path.stat().st_mode & 0o777 != 0o644:
            raise RuntimeError('Public runtime template must be readable mode 0644: ' + filename)
        matches = [x for x in bindings if x.get('target') == entry['source_image_path']]
        if len(matches) != 1:
            raise RuntimeError('Missing or duplicate query-safe runtime template bind')
        mount = matches[0]
        if (mount.get('type') != 'bind' or Path(mount.get('source', '')).resolve() != path.resolve()
                or not mount.get('read_only') or mount.get('bind', {}).get('create_host_path') is not False):
            raise RuntimeError('Query-safe runtime template must use the exact read-only file bind')
        texts[filename] = path.read_text()
    main = texts['nginx.conf.template']
    match = re.search(r'log_format\s+penpot_upstream\s+(.*?);', main, re.S)
    if not match or '$request_method $uri $server_protocol' not in match.group(1):
        raise RuntimeError('Request log must preserve method/path/protocol')
    if re.search(r'\$(request|request_uri|args|query_string|http_referer)(?![A-Za-z0-9_])', match.group(1)):
        raise RuntimeError('Query-sensitive variable found in access log format')
    original = (root / 'public-source' / 'nginx-mcp-locations.conf.template').read_text()
    mcp = texts['nginx-mcp-locations.conf.template']
    if mcp.count('error_log /dev/null;') != 2 or mcp.replace('    error_log /dev/null;\n', '') != original:
        raise RuntimeError('MCP runtime patch must only suppress its sensitive error log; routing must remain identical')
