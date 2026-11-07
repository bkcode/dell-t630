#!/usr/bin/env python3
"""Inspect only the built public frontend image and test dummy query logging offline.
No source container, private .env, real credentials or production endpoint is used.
"""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import time
import uuid
from zoneinfo import ZoneInfo

BASE = Path(__file__).resolve().parent
IMAGE = 'dell-penpot-frontend:2.18.5-amd64'
EXPECTED_ID = 'sha256:fa395b809ed21c53a01387567264100fb28c553f1dd4af113f38c50de3b739bc'
DUMMY = 'DELL_LOG_AUDIT_DUMMY_NOT_A_REAL_TOKEN'
DOCKER = ['docker']


def run(args, **kwargs):
    result = subprocess.run(DOCKER + args, capture_output=True, text=True, timeout=30, **kwargs)
    if result.returncode:
        raise RuntimeError('Audit command failed: ' + args[0] + '; ' + result.stderr[:300])
    return result.stdout


def copy_public(path):
    return run(['run', '--rm', '--pull', 'never', '--platform', 'linux/amd64', '--network', 'none',
                '--read-only', '--memory', '192m', '--cpus', '1', '--entrypoint', 'cat', IMAGE, path])


def fetch(cid, path, port=8080, ws=False):
    # Public frontend image deliberately has no curl/wget; bash TCP stays in loopback.
    script = ('exec 3<>/dev/tcp/127.0.0.1/"$1"; '
              'printf "GET %s HTTP/1.1\\r\\nHost: 127.0.0.1\\r\\nConnection: close\\r\\n%s\\r\\n" "$2" "$3" >&3; '
              'cat <&3')
    extra = 'Upgrade: websocket\r\n' if ws else ''
    p = subprocess.run(DOCKER + ['exec', cid, 'bash', '-ec', script, 'bash', str(port), path, extra],
                       capture_output=True, text=True, timeout=10)
    return p


def request(cid, path, ws=False):
    result = fetch(cid, path + '?userToken=' + DUMMY, ws=ws)
    if result.returncode:
        raise RuntimeError('Dummy loopback request failed')
    return result.stdout


def case(name, safe, upstream_available, main_template, mcp_template):
    fixtures = BASE / 'fixtures'
    main = fixtures / (name + '-main.template')
    mcp = fixtures / (name + '-mcp.template')
    main.write_text(main_template.replace('worker_processes auto;', 'worker_processes 1;', 1))
    mcp.write_text(mcp_template)
    empty = fixtures / 'external-locations-empty.conf'
    empty.write_text('# Offline audit fixture: no public font/template upstreams.\n')
    stub = fixtures / 'stub-http.conf'
    stub.write_text('''server {
    listen 127.0.0.1:8765;
    access_log off;
    location / { return 200 "$request_uri"; }
}
''')
    args = ['run', '-d', '--pull', 'never', '--platform', 'linux/amd64', '--network', 'none',
            '--name', 'dell-penpot-log-audit-' + uuid.uuid4().hex[:10],
            '--label', 'io.dell.audit=penpot-query-logging', '--memory', '256m', '--cpus', '1',
            '-e', 'PENPOT_FLAGS=enable-mcp', '-e', 'PENPOT_PUBLIC_URI=http://127.0.0.1:8080',
            '-e', 'PENPOT_BACKEND_URI=http://127.0.0.1:9', '-e', 'PENPOT_EXPORTER_URI=http://127.0.0.1:9',
            '-e', 'PENPOT_MCP_URI=http://127.0.0.1:' + ('8765' if upstream_available else '9'),
            '-e', 'PENPOT_MCP_URI_WS=http://127.0.0.1:' + ('8765' if upstream_available else '9')]
    for source, target in [(main, '/tmp/nginx.conf.template'), (mcp, '/tmp/nginx-mcp-locations.conf.template'),
                           (empty, '/etc/nginx/overrides/location.d/external-locations.conf'),
                           (stub, '/etc/nginx/overrides/http.d/audit-stub.conf')]:
        args += ['--mount', 'type=bind,source=' + str(source) + ',target=' + target + ',readonly']
    cid = run(args + [IMAGE]).strip()
    try:
        for attempt in range(40):
            state = json.loads(run(['inspect', '--format', '{{json .State}}', cid]))
            if not state['Running']:
                raise RuntimeError('Isolated audit frontend failed to start; no real data involved')
            ready = fetch(cid, '/', port=8765)
            if ready.returncode == 0:
                break
            time.sleep(0.25)
        else:
            raise RuntimeError('Isolated Nginx readiness timeout')
        bodies = {path: request(cid, path, ws=path.endswith('/ws')) for path in ('/mcp/stream', '/mcp/ws')}
        statuses = {path: int(response.splitlines()[0].split()[1]) for path, response in bodies.items()}
        expected_status = 200 if upstream_available else 502
        if any(value != expected_status for value in statuses.values()):
            raise RuntimeError('Dummy upstream HTTP status changed unexpectedly')
        # Wait for access_log flush only; no live system is contacted.
        time.sleep(0.1)
        # Docker logs includes stderr separately; retrieve both streams without printing them.
        p = subprocess.run(DOCKER + ['logs', cid], capture_output=True, text=True, timeout=10)
        combined = p.stdout + p.stderr
        relevant = [line for line in combined.splitlines() if '/mcp/' in line]
        observed = {'case': name, 'network': 'none', 'dummy_only': True,
                    'upstream_available': upstream_available, 'http_status': statuses,
                    'query_in_any_log': DUMMY in combined,
                    'mcp_log_lines': [line.replace(DUMMY, '<DUMMY>') for line in relevant],
                    'access_line_count': sum('[error]' not in line for line in relevant),
                    'error_line_count': sum('[error]' in line for line in relevant),
                    'stream_query_preserved': DUMMY in bodies['/mcp/stream'] if upstream_available else None,
                    'ws_query_preserved': DUMMY in bodies['/mcp/ws'] if upstream_available else None}
        if safe and DUMMY in combined:
            raise RuntimeError('Candidate still leaks dummy query into logs')
        if safe and upstream_available and not all(observed[k] for k in ('stream_query_preserved', 'ws_query_preserved')):
            raise RuntimeError('Candidate changed query forwarding')
        if not safe and DUMMY not in combined:
            raise RuntimeError('Baseline did not reproduce expected inherited query logging')
        return observed
    except BaseException:
        diagnostics = subprocess.run(DOCKER + ['logs', cid], capture_output=True, text=True, timeout=10)
        (fixtures / (name + '-failure.log')).write_text(diagnostics.stdout + diagnostics.stderr)
        raise
    finally:
        # Only the freshly created audit container ID is removed.
        label = run(['inspect', '--format', '{{index .Config.Labels "io.dell.audit"}}', cid]).strip()
        if label != 'penpot-query-logging':
            raise RuntimeError('Refusing cleanup of an unexpected container')
        run(['rm', '-f', '-v', cid])


def main():
    meta = json.loads(run(['image', 'inspect', IMAGE]))[0]
    if meta['Id'] != EXPECTED_ID or meta['Architecture'] != 'amd64':
        raise RuntimeError('Audited frontend image differs from the reviewed artifact')
    main_template = copy_public('/tmp/nginx.conf.template')
    mcp_template = copy_public('/tmp/nginx-mcp-locations.conf.template')
    entrypoint = copy_public('/entrypoint.sh')
    for name, data in [('nginx.conf.template', main_template), ('nginx-mcp-locations.conf.template', mcp_template), ('entrypoint.sh', entrypoint)]:
        (BASE / 'public-source' / name).write_text(data)
    safe_main = main_template.replace('"$request"', '"$request_method $uri $server_protocol"').replace('"$http_referer" ', '')
    if safe_main == main_template:
        raise RuntimeError('Expected request logging source did not match')
    safe_mcp = mcp_template.replace('location /mcp/ws {', 'location /mcp/ws {\n    error_log /dev/null;').replace('location /mcp/stream {', 'location /mcp/stream {\n    error_log /dev/null;')
    (BASE / 'proposed' / 'nginx.conf.template').write_text(safe_main)
    (BASE / 'proposed' / 'nginx-mcp-locations.conf.template').write_text(safe_mcp)
    results = [case('baseline-upstream-failure', False, False, main_template, mcp_template),
               case('candidate-upstream-failure', True, False, safe_main, safe_mcp),
               case('candidate-loopback-stub', True, True, safe_main, safe_mcp)]
    after = json.loads(run(['image', 'inspect', IMAGE]))[0]
    if after['Id'] != EXPECTED_ID:
        raise RuntimeError('Artifact tag unexpectedly changed')
    record = {'checked_at': datetime.datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),
              'image': IMAGE, 'image_id': EXPECTED_ID, 'source_or_private_settings_used': False,
              'archive_modified': False, 'deployment_overlay_applied': False,
              'proposal': 'Query-free access format; omit referer; suppress MCP location error logs only; preserve query forwarding',
              'baseline_confirmed_query_leak_in_access_and_error': results[0]['query_in_any_log'] and results[0]['access_line_count'] > 0 and results[0]['error_line_count'] > 0,
              'candidate_dummy_query_absent_from_access_and_error': not any(x['query_in_any_log'] for x in results[1:]),
              'candidate_query_forwarding_preserved': results[2]['stream_query_preserved'] and results[2]['ws_query_preserved'],
              'upstream_http_502_preserved': all(x == 502 for x in results[1]['http_status'].values()),
              'real_mcp_authentication_acceptance': 'not-run',
              'cases': results, 'scope': 'isolated Nginx only; full MCP server authentication/function acceptance remains separate'}
    (BASE / 'audit.json').write_text(json.dumps(record, indent=2) + '\n')
    print('Offline query-log audit completed; baseline reproduced, candidate logs redacted, query forwarding preserved.')


if __name__ == '__main__':
    main()
