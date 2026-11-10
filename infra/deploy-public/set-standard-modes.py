#!/usr/bin/env python3
"""One-time instance YAML update; preserve credentials, paths and existing targets."""
import copy
import json
import os
from pathlib import Path
import sys
import uuid

root = Path(sys.argv[1]).resolve()
path = Path(sys.argv[2]).absolute()
sys.path.insert(0, str(root))
from config_loader import load_config

before_bytes = path.read_bytes()
before = load_config(path).raw
after = copy.deepcopy(before)
after['environments']['dev']['branch'] = 'dev'
if 'prod' not in after['environments']:
    after['environments']['prod'] = {'branch': 'main', 'targets': ['puyu-prod'], 'spring_profile': 'prod',
        'remote_base_dir': '/opt/puyu', 'log_dir': '/var/log/puyu', 'service_config_file': '', 'config_optional': True}
else:
    after['environments']['prod']['branch'] = 'main'
after['targets'].setdefault('puyu-prod', {'ssh': None})
for spec in after['projects'].values():
    assert all(spec.get('branches', {}).get(env, branch) == branch for env, branch in [('dev', 'dev'), ('prod', 'main')]), 'existing-project-branch-override-requires-review'
assert after['mcp'] == before['mcp'] and after['paths'] == before['paths']
assert all(after['targets'][key] == value for key, value in before['targets'].items())
assert after['mcp']['environment'] == 'dev' and after['mcp']['jobs']['deploy-services']['enabled'] is False
changed = before != after
if changed:
    import yaml
    backup = path.with_name(path.name + '.before-standard-modes-20261110')
    if backup.exists():
        assert backup.read_bytes() == before_bytes, 'existing-mode-backup-differs'
    else:
        fd = os.open(backup, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'wb') as stream:
            stream.write(before_bytes)
    assert path.read_bytes() == before_bytes, 'private-config-CAS-drift'
    temporary = path.with_name(path.name + '.' + uuid.uuid4().hex)
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w') as stream:
        yaml.safe_dump(after, stream, sort_keys=False, allow_unicode=True)
    os.replace(temporary, path)
verified = load_config(path)
assert verified.branch('dev') == 'dev' and verified.branch('prod') == 'main'
assert verified.mcp == before['mcp'] and verified.paths == load_config(path).paths
print(json.dumps({'changed': changed, 'mode_branch_map': {'prod': 'main', 'dev': 'dev'},
                  'MCP_environment': verified.mcp['environment'], 'MCP_key_and_other_settings_preserved': True,
                  'dev_targets_preserved': True, 'prod_target_configured': bool(verified.targets['puyu-prod']['ssh']),
                  'deployment_enabled': verified.mcp['jobs']['deploy-services']['enabled'],
                  'config_mode': oct(path.stat().st_mode & 0o777), 'credentials_output': False}))
