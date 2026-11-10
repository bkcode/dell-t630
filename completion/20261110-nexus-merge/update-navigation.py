#!/usr/bin/env python3
"""Preserve navigation code/UI, deploy only approved catalog in a new public release."""
import hashlib,importlib.util,json,os,shutil,socket,subprocess,sys,urllib.request
from pathlib import Path
assert os.geteuid()==0 and socket.gethostname()=='publish-service';x=json.load(sys.stdin)
unit=Path('/etc/systemd/system/dell-service-directory.service');before=unit.read_text();assert hashlib.sha256(before.encode()).hexdigest()==x['unit_before_sha']
old=Path('/opt/dell/service-directory/releases/d56cae553bf95ce0e2c3fe8f258a2f99389aae7c');assert old.is_dir() and all(not p.is_symlink()for p in old.rglob('*'))
old_catalog=json.loads((old/'services.json').read_text());catalog=json.loads(x['catalog']);removed='7009e2be-5847-49c9-a010-000000000011';expected=[dict(row)for row in old_catalog['services']if row['id']!=removed]
for row in expected:
 if row['id']=='7009e2be-5847-49c9-a010-000000000006':row['description']='已并入发布机VM220，保留原制品仓库访问地址。'
assert catalog['services']==expected and len(expected)==13
release=old.parent/('nfs-nexus-20261110-'+hashlib.sha256(x['catalog'].encode()).hexdigest()[:12]);assert not release.exists();shutil.copytree(old,release)
for p in [release,*release.rglob('*')]:p.chmod(0o755 if p.is_dir()else 0o644)
(release/'services.json').write_text(x['catalog']);(release/'services.json').chmod(0o644)
spec=importlib.util.spec_from_file_location('navigation_candidate',release/'server.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);assert len(m.validate_catalog(catalog)['services'])==13
new=before.replace(str(old),str(release));assert new!=before and new.count(str(release))==2
backup=Path('/root/dell-navigation-before-nfs-nexus-20261110.service');assert not backup.exists();backup.write_text(before);backup.chmod(0o600)
def run(args):return subprocess.check_output(args,stderr=subprocess.PIPE,timeout=45).decode().strip()
try:
 unit.write_text(new);unit.chmod(0o644);run(['systemd-analyze','verify',str(unit)]);run(['systemctl','daemon-reload']);run(['systemctl','restart','dell-service-directory.service'])
 opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
 import time
 for _ in range(30):
  try:
   with opener.open('http://192.168.19.30:9080/api/services',timeout=3)as response:actual=json.loads(response.read())
   assert actual==catalog;break
  except OSError:time.sleep(0.2)
 else:raise RuntimeError('navigation did not become ready')
except Exception:
 unit.write_text(before);unit.chmod(0o644);run(['systemctl','daemon-reload']);run(['systemctl','restart','dell-service-directory.service']);raise
print(json.dumps({'status':'navigation-catalog-updated','release':str(release),'services':13,'FileBrowser_entry_removed':True,'Nexus_description_consolidated':True,'HTTP_and_original_UI_preserved':True,'source_repository_commit_or_push':False,'catalog_public_SHA':hashlib.sha256(x['catalog'].encode()).hexdigest()}))
