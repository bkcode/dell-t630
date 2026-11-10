#!/usr/bin/env python3
"""Extend only the private project catalog, preserving all credentials and fencing."""
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import time
import urllib.request

ROOT = Path('/opt/deploy-public')
PRIVATE = ROOT / 'config.local.yaml'
BACKUP = Path('/root/deploy-public-before-bff-admin.local.yaml')
assert os.geteuid() == 0 and not BACKUP.exists()
with sqlite3.connect('file:/srv/dell-build/deploy-public/mcp-state/jobs.sqlite?mode=ro', uri=True) as db:
    assert not any(json.loads(row[0])['status'] in ['queued', 'running'] for row in db.execute('SELECT payload FROM jobs'))
fd = os.open(BACKUP, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
with os.fdopen(fd, 'wb') as stream:
    stream.write(PRIVATE.read_bytes())
old_metadata = PRIVATE.stat()
subprocess.run(['systemctl', 'stop', 'puyu-deploy-mcp.service'], check=True, capture_output=True)
try:
    child = '''import copy,json,os,yaml,uuid
from pathlib import Path
from config_loader import load_config
p=Path('/opt/deploy-public/config.local.yaml');before=load_config(p).raw;assert before['mcp']['jobs']['deploy-services']['enabled']is False;assert'puyu-bff-admin'not in before['projects'];after=copy.deepcopy(before);after['projects']['puyu-bff-admin']={'kind':'service','url':'git@github-bkcode-puyu-bff-admin:bkcode/puyu-bff-admin.git'};order=['puyu-common-lib','puyu-auth','puyu-gateway','puyu-bff-admin','puyu-bff-web','puyu-service-core'];after['projects']={name:after['projects'][name]for name in order};assert all(after[key]==value for key,value in before.items()if key!='projects');t=p.with_name(p.name+'.'+uuid.uuid4().hex);fd=os.open(t,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
with os.fdopen(fd,'w')as f:yaml.safe_dump(after,f,sort_keys=False,allow_unicode=True)
os.replace(t,p);cfg=load_config(p).require_mcp();assert cfg.mcp['api_key']==before['mcp']['api_key'];print(json.dumps({'private_catalog_extended':True,'MCP_key_and_other_settings_unchanged':True,'deployment_still_disabled':True,'service_count':sum(v['kind']=='service'for v in cfg.projects.values())}))
'''
    result = subprocess.run(['runuser', '-u', 'ub', '--', str(ROOT / '.venv/bin/python'), '-c', child],
                            cwd=ROOT, capture_output=True, timeout=30)
    assert result.returncode == 0, 'private-catalog-update-failed'
    subprocess.run(['systemctl', 'start', 'puyu-deploy-mcp.service'], check=True, capture_output=True)
    report = json.loads(result.stdout)
except BaseException:
    subprocess.run(['systemctl', 'stop', 'puyu-deploy-mcp.service'], capture_output=True)
    temporary = PRIVATE.with_name(PRIVATE.name + '.recovery')
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    os.fchown(fd, old_metadata.st_uid, old_metadata.st_gid)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(BACKUP.read_bytes())
    os.replace(temporary, PRIVATE)
    subprocess.run(['systemctl', 'start', 'puyu-deploy-mcp.service'], capture_output=True)
    raise
print(json.dumps(report))
