#!/bin/bash
set -euo pipefail
umask 077
[ "$(id -u)" = 0 ] && [ ! -d /etc/pve ] && [ "$(hostname -s)" = publish-service ]
export DEBIAN_FRONTEND=noninteractive
mountpoint -q /srv/dell-build
apt-get -o DPkg::Lock::Timeout=600 update -qq
apt-get -o DPkg::Lock::Timeout=600 install -y --no-install-recommends git rsync unzip zip make gcc g++ python3-venv python3-pip jq openssh-client curl ca-certificates xz-utils fzf
install -d -m 755 /opt/dell/tools /opt/dell/publisher
install -d -o ub -g ub -m 700 /srv/dell-build/workspace /srv/dell-build/cache
python3 - <<'PY'
from pathlib import Path
import urllib.request,re,hashlib,tarfile,os,json
base='https://nodejs.org/dist/latest-v22.x/'
text=urllib.request.urlopen(base+'SHASUMS256.txt',timeout=45).read().decode()
rows=[line.split() for line in text.splitlines() if re.fullmatch('node-v22[.][0-9]+[.][0-9]+-linux-x64[.]tar[.]xz',line.split()[-1])]
assert len(rows)==1
expected,name=rows[0];target=Path('/srv/dell-build/cache')/name
if not target.exists():
 with urllib.request.urlopen(base+name,timeout=60) as src,target.open('wb') as dst:
  while True:
   block=src.read(1024*1024)
   if not block:break
   dst.write(block)
assert hashlib.sha256(target.read_bytes()).hexdigest()==expected
folder=Path('/opt/dell/tools')/name.removesuffix('.tar.xz')
if not folder.exists():
 with tarfile.open(target) as archive:archive.extractall('/opt/dell/tools',filter='data')
link=Path('/opt/dell/tools/node-current')
if link.exists() and not link.is_symlink():raise RuntimeError('Refusing unexpected node-current directory')
if link.is_symlink():link.unlink()
link.symlink_to(folder)
for tool in ['node','npm','npx']:
 p=Path('/usr/local/bin')/tool
 if p.exists() and not p.is_symlink():raise RuntimeError('Refusing existing real executable '+tool)
 if p.is_symlink():p.unlink()
 p.symlink_to(link/'bin'/tool)
Path('/opt/dell/publisher/node-source.json').write_text(json.dumps({'source':base+name,'sha256':expected,'filename':name},indent=2)+'\n')
PY
python3 - <<'NPMCONFIG'
from pathlib import Path
for name in ['npm-user.conf','npm-global.conf']:
 p=Path('/opt/dell/publisher')/name
 if p.exists() and p.read_text().strip():raise RuntimeError('Refusing to overwrite a nonempty npm configuration')
 p.touch(exist_ok=True);p.chmod(0o600)
NPMCONFIG
npm --userconfig=/opt/dell/publisher/npm-user.conf --globalconfig=/opt/dell/publisher/npm-global.conf --registry=https://registry.npmjs.org install --global --prefix /opt/dell/tools/pnpm8 --ignore-scripts --no-audit --no-fund pnpm@8.15.9
npm --userconfig=/opt/dell/publisher/npm-user.conf --globalconfig=/opt/dell/publisher/npm-global.conf --registry=https://registry.npmjs.org install --global --prefix /opt/dell/tools/pnpm10 --ignore-scripts --no-audit --no-fund pnpm@10.33.2
ln -sfn /opt/dell/tools/pnpm8/bin/pnpm /usr/local/bin/pnpm8
ln -sfn /opt/dell/tools/pnpm10/bin/pnpm /usr/local/bin/pnpm10
cat > /usr/local/bin/pnpm <<'PY'
#!/usr/bin/python3
from pathlib import Path
import json,os,sys
version='8.15.9'
for folder in [Path.cwd(),*Path.cwd().parents]:
 p=folder/'package.json'
 if p.exists():
  manager=json.loads(p.read_text()).get('packageManager','')
  if manager.startswith('pnpm@'):version=manager.split('@',1)[1].split('+',1)[0]
  break
if version not in ['8.15.9','10.33.2']:raise SystemExit('Project pnpm version not provisioned: '+version)
command='/usr/local/bin/pnpm10' if version=='10.33.2' else '/usr/local/bin/pnpm8'
os.execv(command,[command,*sys.argv[1:]])
PY
chmod 755 /usr/local/bin/pnpm
python3 -m venv /opt/dell/publisher/venv
/opt/dell/publisher/venv/bin/pip --isolated --disable-pip-version-check install --index-url https://pypi.org/simple --report /opt/dell/publisher/pip-report.json mcp==1.26.0
python3 - <<'PY'
import subprocess,json
from pathlib import Path
commands={'java':['/opt/finger/java/bin/java','-version'],'git':['git','--version'],'rsync':['rsync','--version'],'python':['python3','--version'],'node':['node','--version'],'pnpm8':['pnpm8','--version'],'pnpm10':['pnpm10','--version'],'mcp':['/opt/dell/publisher/venv/bin/python','-c','import importlib.metadata; print(importlib.metadata.version("mcp"))']}
result={}
for k,a in commands.items():
 p=subprocess.run(a,capture_output=True,text=True,check=True);result[k]=(p.stdout or p.stderr).splitlines()[0]
result['applications_started']=False;result['git_credentials_installed']=False
Path('/opt/dell/publisher/tools.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
PY
