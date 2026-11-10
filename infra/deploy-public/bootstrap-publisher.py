#!/usr/bin/env python3
"""One assigned VM220 installation: publisher infrastructure and source reads only."""
import datetime
import json
import os
from pathlib import Path
import pwd
import secrets
import socket
import subprocess
import sys
from zoneinfo import ZoneInfo

ROOT = Path('/opt/deploy-public')
DATA = Path('/srv/dell-build/deploy-public')
STATUS = Path('/root/deploy-public-bootstrap-status.json')
LOG = Path('/root/deploy-public-bootstrap-private.log')
GIT_SSH = '/usr/bin/ssh -F /home/ub/.ssh/deploy-keys/bkcode/all-repos.conf'
NAMES = ['puyu-common-lib', 'puyu-auth', 'puyu-gateway', 'puyu-bff-web', 'puyu-service-core']
EXPECTED = '5be397f1e5a0d07e272bb4d87b7599cf1279d2c4'


def need(value, code):
    if not value:
        raise RuntimeError(code)


def phase(name):
    STATUS.write_text(json.dumps({'phase': name, 'at': datetime.datetime.now(ZoneInfo('Asia/Shanghai')).isoformat()}))
    STATUS.chmod(0o600)


def user(args, timeout=90, data=None, capture=True):
    account = pwd.getpwnam('ub')
    env = {k: v for k, v in os.environ.items() if k not in ['PYTHONPATH', 'PYTHONHOME', 'GIT_SSH_COMMAND',
           'GIT_CONFIG_COUNT', 'PIP_INDEX_URL', 'PIP_EXTRA_INDEX_URL', 'PIP_TRUSTED_HOST']}
    env.update(HOME=account.pw_dir, USER='ub', LOGNAME='ub', PIP_CONFIG_FILE='/dev/null',
               PIP_DISABLE_PIP_VERSION_CHECK='1', GIT_TERMINAL_PROMPT='0')
    with LOG.open('ab') as log:
        result = subprocess.run(['runuser', '-u', 'ub', '--', *map(str, args)], cwd=ROOT,
            env=env, input=data, stdout=subprocess.PIPE if capture else log, stderr=log, timeout=timeout)
    need(result.returncode == 0, 'publisher-fixed-operation-failed')
    return result.stdout if capture else b''


def main():
    need(os.geteuid() == 0 and socket.gethostname() == 'publish-service', 'assigned-VM220-only')
    os.umask(0o077)
    fs = json.loads(subprocess.check_output(['findmnt', '--json', '--mountpoint', '/srv/dell-build',
                                            '--output', 'UUID,FSTYPE']))['filesystems']
    need(len(fs) == 1 and fs[0]['uuid'] == '16dc6067-56ef-4687-a314-edc6421f9ed4' and fs[0]['fstype'] == 'ext4',
         'existing-build-disk-UUID-required')
    need(user(['git', 'rev-parse', 'HEAD']).decode().strip() == EXPECTED, 'fixed-source-HEAD-required')
    need(not user(['git', 'status', '--porcelain']).strip(), 'clean-source-required')
    need(not (ROOT / 'config.local.yaml').exists(), 'existing-private-config-requires-review')
    need(not Path('/etc/systemd/system/puyu-deploy-mcp.service').exists(), 'existing-unit-requires-review')
    account = pwd.getpwnam('ub')
    for path in [DATA, DATA / 'repos', DATA / 'build', DATA / 'mcp-state']:
        need(not path.exists(), 'fresh-dedicated-data-path-required')
        path.mkdir(mode=0o700)
        os.chown(path, account.pw_uid, account.pw_gid)
    phase('python-environment')
    need(not (ROOT / '.venv').exists(), 'fresh-Python-environment-required')
    user(['/usr/bin/python3', '-m', 'venv', ROOT / '.venv'], timeout=90, capture=False)
    phase('dependencies')
    user([ROOT / '.venv/bin/python', '-m', 'pip', 'install', '--index-url', 'https://pypi.org/simple',
          '-r', ROOT / 'requirements.txt'], timeout=600, capture=False)
    phase('Linux-local-tests-no-business-build')
    user([ROOT / '.venv/bin/python', '-m', 'unittest', 'discover', '-s', 'tests'], timeout=120, capture=False)
    phase('managed-Puyu-Git-source-reads')
    user(['git', 'config', 'core.sshCommand', GIT_SSH])
    user(['git', 'config', 'remote.origin.pushurl', 'no-push://disabled'])
    sources = {}
    for name in NAMES:
        target = DATA / 'repos' / name
        need(not target.exists(), 'fresh-managed-source-path-required')
        url = 'git@github-bkcode-' + name + ':bkcode/' + name + '.git'
        try:
            user(['git', '-c', 'core.sshCommand=' + GIT_SSH, 'clone', '--branch', 'main',
                  '--single-branch', url, target], timeout=180, capture=False)
            user(['git', '-C', target, 'config', 'core.sshCommand', GIT_SSH])
            user(['git', '-C', target, 'config', 'remote.origin.pushurl', 'no-push://disabled'])
            head = user(['git', '-C', target, 'rev-parse', 'HEAD']).decode().strip()
            sources[name] = {'status': 'cloned-main', 'Git_HEAD': head}
        except RuntimeError:
            sources[name] = {'status': 'Git-read-or-checkout-unconfirmed-no-retry'}
    phase('private-YAML-configuration')
    config = {'paths': {'repos': str(DATA / 'repos'), 'builds': str(DATA / 'build'),
                        'state': str(DATA / 'mcp-state')}, 'projects': NAMES,
              'port': 18765, 'target': 'deployer@192.168.19.45'}
    child = '''import sys,json,os,secrets,yaml
from pathlib import Path
from config_loader import load_config
request=json.load(sys.stdin);p=Path('config.local.yaml');assert not p.exists()
data=yaml.safe_load(Path('config.example.yaml').read_text());data['paths']=request['paths'];data['projects']={name:data['projects'][name]for name in request['projects']}
for name in data['projects']:data['projects'][name]['url']='git@github-bkcode-'+name+':bkcode/'+name+'.git'
data['targets']['puyu-test']['ssh']=request['target'];data['mcp']['host']='127.0.0.1';data['mcp']['port']=request['port'];data['mcp']['api_key']=secrets.token_urlsafe(40);data['mcp']['jobs']['deploy-services']['enabled']=False
fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
with os.fdopen(fd,'w')as f:yaml.safe_dump(data,f,sort_keys=False,allow_unicode=True)
load_config(p).require_mcp();print(json.dumps({'private_YAML_created':True,'config_mode':'0600','server_generated_MCP_key_not_output':True}))
'''
    config_receipt = json.loads(user([ROOT / '.venv/bin/python', '-c', child], data=json.dumps(config).encode()))
    phase('mount-guard-and-systemd')
    guard_dir = Path('/opt/dell/deploy-public')
    guard_dir.mkdir(mode=0o755, exist_ok=True)
    guard_dir.chmod(0o755)
    guard = guard_dir / 'check-build-mount.py'
    need(not guard.exists(), 'fresh-guard-path-required')
    guard.write_text("import subprocess\nfrom pathlib import Path\np=Path('/srv/dell-build')\nassert p.resolve()==p\nassert subprocess.check_output(['findmnt','--noheadings','--output','UUID','--mountpoint',str(p)]).decode().strip()=='16dc6067-56ef-4687-a314-edc6421f9ed4'\n")
    guard.chmod(0o644)
    unit = (ROOT / 'mcp/puyu-deploy-mcp.service').read_text()
    unit = unit.replace('After=network-online.target', 'After=network-online.target\nRequiresMountsFor=/srv/dell-build\nConditionPathIsMountPoint=/srv/dell-build')
    unit = unit.replace('UMask=0077', 'UMask=0077\nExecStartPre=/usr/bin/python3 /opt/dell/deploy-public/check-build-mount.py')
    path = Path('/etc/systemd/system/puyu-deploy-mcp.service')
    path.write_text(unit)
    path.chmod(0o644)
    probe = socket.socket()
    probe.bind(('127.0.0.1', 18765))
    probe.close()
    result = subprocess.run(['systemd-analyze', 'verify', str(path)], capture_output=True, timeout=30)
    need(result.returncode == 0, 'unit-native-validation-failed')
    subprocess.run(['systemctl', 'daemon-reload'], check=True, capture_output=True, timeout=30)
    subprocess.run(['systemctl', 'enable', '--now', 'puyu-deploy-mcp.service'], check=True,
                   capture_output=True, timeout=40)
    need(user(['git', 'check-ignore', 'config.local.yaml']).strip() == b'config.local.yaml', 'private-YAML-not-ignored')
    need(not user(['git', 'status', '--porcelain']).strip(), 'runtime-writes-changed-source')
    record = {'captured_at': datetime.datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),
        'status': 'publisher-code-config-and-MCP-installed-awaiting-protocol-check',
        'Git_HEAD': EXPECTED, 'source_path': str(ROOT), 'source_owner': 'ub',
        'GitHub_readonly_identity': 'deploy-public_ed25519', 'source_and_artifacts_on_build_disk': str(DATA),
        'data_disk_UUID': '16dc6067-56ef-4687-a314-edc6421f9ed4', 'Linux_unit_tests': 60,
        'backend_sources': sources, 'excluded_project': 'puyu-bff-admin', 'configuration': config_receipt,
        'MCP_listener': '127.0.0.1:18765', 'MCP_unit': 'puyu-deploy-mcp.service',
        'actual_deployment_enabled': False, 'runtime_target_binding_preview_only': config['target'],
        'original_publisher_chain_or_key_modified': False, 'business_build_or_Java_start': False}
    Path('/root/deploy-public-bootstrap-result.json').write_text(json.dumps(record, indent=2))
    Path('/root/deploy-public-bootstrap-result.json').chmod(0o600)
    phase('installed-awaiting-protocol-verification')
    print(json.dumps(record))


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        message = str(error)
        record = {'status': 'publisher-bootstrap-not-confirmed', 'error_type': type(error).__name__,
                  'code': message if all(c.isalnum() or c == '-' for c in message) and len(message) < 100 else 'private-details-withheld'}
        STATUS.write_text(json.dumps(record))
        STATUS.chmod(0o600)
        print(json.dumps(record))
        sys.exit(1)
