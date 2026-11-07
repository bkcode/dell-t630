#!/usr/bin/env python3
"""Manager: transport only fresh target config, reuse checksum-verified read-only ISO jars."""
import io,json,tarfile,sys,datetime,argparse,re
from pathlib import Path
BASE=Path(__file__).resolve().parents[3];sys.path.insert(0,str(BASE/'scripts'));import control
m=json.loads((BASE/'evidence/implementation/private-guest-access.json').read_text());target=next(x['target'] for x in m['roles'] if x['target']['vmid']==240)
parser=argparse.ArgumentParser();parser.add_argument('--release-id',default='20261106T061002');args=parser.parse_args();assert re.fullmatch(r'[0-9]{8}T[0-9]{6}',args.release_id)
release=BASE/'private/java/releases'/args.release_id;buf=io.BytesIO()
current=json.loads((release/'manifest.json').read_text());iso=json.loads((BASE/'private/java/releases/20261106T061002/manifest.json').read_text());iso_hash={r['name']:r['jar_sha256'] for r in iso['services']}
with tarfile.open(fileobj=buf,mode='w') as tar:
 tar.add(release/'manifest.json',arcname='manifest.json')
 for d in release.iterdir():
  if d.is_dir():tar.add(d/'application.yaml',arcname=d.name+'/application.yaml')
 for row in current['services']:
  if row['jar_sha256']!=iso_hash[row['name']]:tar.add(release/row['name']/'app.jar',arcname=row['name']+'/app.jar')
 tar.add(BASE/'infra/java/runtime/deploy-test-chain.py',arcname='deploy-test-chain.py')
remote='''sudo python3 -c 'import sys,os,socket,tarfile,subprocess,hashlib,json,shutil;from pathlib import Path
assert socket.gethostname()=="java-test-01" and not Path("/etc/pve").exists()
import re
payload_id=sys.argv[1];assert re.fullmatch(r"[0-9]{8}T[0-9]{6}",payload_id)
p=Path("/root/dell-java-test-incoming-"+payload_id);assert not p.exists();p.mkdir(mode=0o700)
with tarfile.open(fileobj=sys.stdin.buffer,mode="r|*") as t:
 for m in t:
  assert m.isfile() and not m.issym() and not m.islnk() and not Path(m.name).is_absolute() and ".." not in Path(m.name).parts
  t.extract(m,path=p,filter="data")
manifest=json.loads((p/"manifest.json").read_text());assert manifest["release_id"]==payload_id
for row in manifest["services"]:
 target=p/row["name"]/"app.jar"
 if target.exists():assert hashlib.sha256(target.read_bytes()).hexdigest()==row["jar_sha256"]
 else:
  f=Path("/mnt/dell-artifacts/java")/(row["name"]+".jar");assert hashlib.sha256(f.read_bytes()).hexdigest()==row["jar_sha256"]
  shutil.copyfile(f,target)
for f in p.rglob("*"):
 os.chmod(f,0o700 if f.is_dir() else 0o600)
subprocess.run(["python3",str(p/"deploy-test-chain.py"),"check","--bundle",str(p)],check=True)
subprocess.run(["python3",str(p/"deploy-test-chain.py"),"stage","--bundle",str(p)],check=True)
' '''
remote=remote.rstrip()+" "+args.release_id
r=control.guest(240,remote,data=buf.getvalue(),info=target,timeout=240)
receipt={'at':datetime.datetime.now().isoformat(),'action':'check-and-stage-no-app-start','result':r}
(BASE/'evidence/implementation/java-test-stage.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(r));sys.exit(r['exit_code'])
