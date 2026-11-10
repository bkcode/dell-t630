#!/usr/bin/env python3
"""Authenticated loopback MCP checks; never output credentials or raw task logs."""
import json
from pathlib import Path
import sys
import time
import urllib.error
import urllib.request

ROOT = Path('/opt/deploy-public')
sys.path.insert(0, str(ROOT))
from config_loader import load_config

config = load_config(ROOT / 'config.local.yaml').require_mcp()
URL = 'http://127.0.0.1:' + str(config.mcp['port']) + '/mcp'
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
number = 0


def rpc(method, params=None, authenticate=True, origin=False, notify=False):
    global number
    number += 1
    headers = {'Content-Type': 'application/json', 'Accept': 'application/json, text/event-stream'}
    if authenticate:
        headers['Authorization'] = 'Bearer ' + config.mcp['api_key']
    if origin:
        headers['Origin'] = 'http://example.invalid'
    body = {'jsonrpc': '2.0', 'method': method}
    if not notify:
        body['id'] = number
    if params is not None:
        body['params'] = params
    request = urllib.request.Request(URL, data=json.dumps(body).encode(), headers=headers, method='POST')
    try:
        with opener.open(request, timeout=30) as response:
            raw = response.read(1024 * 1024)
            if notify:
                return response.status, {}
            value = json.loads(raw)
            if 'error' in value:
                raise RuntimeError('MCP-RPC-rejected')
            return response.status, value['result']
    except urllib.error.HTTPError as error:
        error.read(4096)
        return error.code, {}


def call(name, arguments=None):
    status, result = rpc('tools/call', {'name': name, 'arguments': arguments or {}})
    assert status == 200
    if result.get('isError'):
        return result, None
    if isinstance(result.get('structuredContent'), dict):
        return result, result['structuredContent']
    for block in result.get('content', []):
        if block.get('type') == 'text':
            return result, json.loads(block['text'])
    raise RuntimeError('MCP-structured-result-missing')


initialize = {'protocolVersion': '2024-11-05', 'capabilities': {},
              'clientInfo': {'name': 'publisher-readonly-acceptance', 'version': '1'}}
anonymous, _ = rpc('initialize', initialize, authenticate=False)
origin, _ = rpc('initialize', initialize, origin=True)
assert anonymous == 401 and origin == 403
_, init = rpc('initialize', initialize)
rpc('notifications/initialized', notify=True)
_, tool_result = rpc('tools/list', {})
tools = [item['name'] for item in tool_result['tools']]
_, jobs = call('list_jobs')
job_flags = {item['name']: item['enabled'] for item in jobs['jobs']}
assert job_flags == {'validate-services': True, 'deploy-services': False}
_, services = call('list_services')
expected = ['puyu-auth', 'puyu-gateway', 'puyu-bff-admin', 'puyu-bff-web', 'puyu-service-core']
assert services['services'] == expected and all(row['source_ready'] for row in services['details'])
rejected, _ = call('run_job', {'job': 'deploy-services', 'parameters': {'services': ['puyu-auth']},
                             'request_id': 'publisher-disabled-deploy-check-20261110'})
assert rejected.get('isError') and any('JOB_DISABLED' in block.get('text', '') for block in rejected['content'])
rejected_prod, _ = call('run_job', {'job': 'validate-services',
    'parameters': {'services': ['puyu-auth'], 'environment': 'prod'},
    'request_id': 'publisher-prod-override-rejected-20261110'})
assert rejected_prod.get('isError') and any('ONLY_SERVICES_IS_ACCEPTED' in block.get('text', '') for block in rejected_prod['content'])
assert config.branch('dev') == 'dev' and config.branch('prod') == 'main'
assert not config.targets['puyu-prod']['ssh']
assert all(row['expected_branch'] == 'dev' and row['current_branch'] == 'main'
           and not row['target_branch_available'] for row in services['details'])
_, started = call('run_job', {'job': 'validate-services', 'parameters': {'services': expected},
                            'request_id': 'publisher-dev-missing-branch-20261110'})
for _ in range(60):
    _, job = call('get_job', {'job_id': started['job_id']})
    if job['status'] not in ['queued', 'running']:
        break
    time.sleep(0.5)
assert job['status'] == 'failed'
result = job.get('result', {})
# Error is a predictable missing source branch, not a build/deploy invocation.
assert 'origin/dev' in json.dumps(result) and 'not prepared' in json.dumps(result)
import subprocess
repos = {}
for name in ['puyu-common-lib', *expected]:
    folder = str(config.paths['repos'] / name)
    def git(*args):
        return subprocess.check_output(['git', '-C', folder, *args], stderr=subprocess.PIPE).decode().strip()
    repos[name] = {'HEAD': git('rev-parse', 'HEAD'), 'branch': git('branch', '--show-current'),
                   'clean': not git('status', '--porcelain')}
assert all(row['clean'] and row['branch'] == 'main' for row in repos.values())
print(json.dumps({'MCP_URL_without_credentials': URL, 'anonymous_HTTP': anonymous, 'browser_Origin_HTTP': origin,
    'environment': jobs['environment'], 'mode_branch_map': {'prod': config.branch('prod'), 'dev': config.branch('dev')},
    'source_details': services['details'], 'source_refs_are_cached': True,
    'prod_target_configured': False, 'deploy_enabled': False,
    'deploy_call_rejected_before_execution': True, 'prod_override_rejected': True,
    'validation_job_id': started['job_id'], 'validation_status': job['status'],
    'expected_failure': 'origin/dev not prepared; upstream branch audit reports missing dev',
    'backend_repos': repos, 'real_build_deploy_or_Java_start': False, 'credentials_output': False}))
