#!/usr/bin/env python3
"""Validate/repair only own candidate lock serialization and start same reviewed installation."""
import hashlib,importlib.util,json,os,subprocess
from pathlib import Path
BASE=Path('/opt/dell/penpot/runtime/health-supervision');p=BASE/'deployment-lock.json';text=p.read_text();root=Path('/root/dell-penpot-dns-init-fix-20261111');before=json.loads((root/'before-private.json').read_text());original_mode=before['files'][str(p)]['mode']
try:lock=json.loads(text);corrected=False
except json.JSONDecodeError:
 assert text.endswith(chr(92)+'n');lock=json.loads(text[:-2]);corrected=True
assert lock['services']['penpot-dns']['require_init']is True
source=(BASE/'supervisor.py').read_bytes();assert hashlib.sha256(source).hexdigest()==lock['supervision_file_sha256']['supervisor.py']
p.write_text(json.dumps(lock,indent=2));p.chmod(original_mode);assert json.loads(p.read_text())==lock
s=importlib.util.spec_from_file_location('ready_install',BASE/'supervisor.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);m.guest_guard();actual=m.load_lock();m.storage_guard(actual);m.verify_files_and_images(actual);m.check_config(actual);assert len(m.scan())==11
# Old guarded candidate failed before any container was started; clear only this unit's start limit.
subprocess.run(['systemctl','reset-failed','dell-penpot.service'],check=True,capture_output=True)
subprocess.run(['systemctl','start','--no-block','dell-penpot.service'],check=True,capture_output=True)
print(json.dumps({'status':'candidate-full-native-lock-and-scan-checked-start-requested','own_serialization_suffix_corrected':corrected,'lock_original_mode_preserved':oct(original_mode),'source_public_SHA256':hashlib.sha256(source).hexdigest(),'guards_relaxed':False,'data_or_credentials_modified':False}))
