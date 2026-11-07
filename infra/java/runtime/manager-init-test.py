#!/usr/bin/env python3
"""Manager: apply reviewed target-only fresh SQL and six namespace configs after infra ready."""
import io,json,tarfile,sys,datetime
from pathlib import Path
BASE=Path(__file__).resolve().parents[3];sys.path.insert(0,str(BASE/'scripts'));import control
ready=json.loads((BASE/'evidence/implementation/test-data-deployment.json').read_text());assert ready['status']=='test-data-ready-authenticated-persistence-restart-verified-fixture-cleaned'
m=json.loads((BASE/'evidence/implementation/private-guest-access.json').read_text());target=next(x['target'] for x in m['roles'] if x['target']['vmid']==210)
package=BASE/'private/java/test-chain';buf=io.BytesIO()
with tarfile.open(fileobj=buf,mode='w') as tar:
 for name in ['metadata.json','sql-package-manifest.json']:tar.add(package/name,arcname=name)
 for folder in ['sql','nacos-configs']:
  for f in (package/folder).rglob('*'):
   if f.is_file():tar.add(f,arcname=str(f.relative_to(package)))
 for name in ['apply-test-sql.py','publish-test-nacos.py']:tar.add(BASE/'infra/java/runtime'/name,arcname=name)
remote='''sudo python3 -c 'import sys,os,socket,tarfile,subprocess,json;from pathlib import Path
assert socket.gethostname()=="data-test" and not Path("/etc/pve").exists()
p=Path("/root/dell-java-test-init");assert not p.exists();p.mkdir(mode=0o700)
with tarfile.open(fileobj=sys.stdin.buffer,mode="r|*") as t:
 for m in t:
  assert m.isfile() and not m.issym() and not m.islnk() and not Path(m.name).is_absolute() and ".." not in Path(m.name).parts
  t.extract(m,path=p,filter="data")
for f in p.rglob("*"):os.chmod(f,0o700 if f.is_dir() else 0o600)
sha=json.loads((p/"sql-package-manifest.json").read_text())["package_sha256"]
subprocess.run(["python3",str(p/"apply-test-sql.py"),"--package",str(p),"--data-bundle","/opt/dell/data/test-data","--expected-package-sha256",sha,"--apply","--reviewed-structure","--output",str(p/"sql-result.json")],check=True)
subprocess.run(["python3",str(p/"publish-test-nacos.py"),"--package",str(p),"--data-bundle","/opt/dell/data/test-data","--apply","--output",str(p/"nacos-result.json")],check=True)
' '''
r=control.guest(210,remote,data=buf.getvalue(),info=target,timeout=240)
(BASE/'evidence/implementation/java-test-init.json').write_text(json.dumps({'at':datetime.datetime.now().isoformat(),'structure_review':'fresh 18 named tables, source/entity differences reviewed; no source DML; independent host-bound accounts','result':r},indent=2)+'\n');print(json.dumps(r));sys.exit(r['exit_code'])
