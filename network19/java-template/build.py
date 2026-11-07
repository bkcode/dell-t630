#!/usr/bin/env python3
"""9011 fresh guest builder only. No PVE operation or template seal."""
import argparse,contextlib,datetime,hashlib,json,os,platform,pwd,re,socket,subprocess,sys
from pathlib import Path
MAC='bc:24:11:a4:d3:4d';IP='192.168.19.197'
def run(args,check=True,timeout=300,env=None):
 r=subprocess.run(args,capture_output=True,timeout=timeout,env=env)
 if check and r.returncode:raise RuntimeError('fixed build command failed; raw output withheld')
 return r

def guard():
 if os.geteuid()!=0 or Path('/etc/pve').exists() or platform.system()!='Linux' or platform.machine() not in ('x86_64','amd64') or socket.gethostname().split('.')[0]!='java-acceptance-build':raise RuntimeError('fresh9011 root only')
 v=dict(line.split('=',1) for line in Path('/etc/os-release').read_text().splitlines() if '='in line)
 if v.get('ID','').strip('"')!='debian' or v.get('VERSION_ID','').strip('"')!='13':raise RuntimeError('Debian13 required')
 links=json.loads(run(['ip','-j','addr']).stdout);matches=[x for x in links if x.get('address','').lower()==MAC]
 if len(matches)!=1 or not any(x.get('local')==IP and x.get('prefixlen')==24 for x in matches[0].get('addr_info',[])):raise RuntimeError('root-assigned9011 MAC/IP required')
 for value in ['/opt/finger','/etc/nacos','/var/lib/mysql','/opt/dell/ops','/etc/penpot','/etc/nexus.env','/var/lib/dell-gateway19']:
  if Path(value).exists():raise RuntimeError('business/role state contamination; do not mutate this guest')
 if run(['systemctl','is-active','--quiet','docker.service'],False).returncode==0:raise RuntimeError('Docker workload forbidden')

@contextlib.contextmanager
def block_starts():
 file=Path('/usr/sbin/policy-rc.d')
 if file.is_symlink():raise RuntimeError('existing policy hook symlink requires review')
 old=file.read_bytes() if file.exists() else None;st=file.stat() if file.exists() else None
 if st and(st.st_uid!=0 or st.st_mode&0o022):raise RuntimeError('policy hook ownership invalid')
 temporary=b'#!/bin/sh\n# Fresh Java9011 build: keep installed daemon parked.\nexit 101\n';file.write_bytes(temporary);os.chown(file,0,0);file.chmod(0o755)
 try:yield
 finally:
  if file.is_symlink() or file.read_bytes()!=temporary:raise RuntimeError('policy hook changed concurrently; no blind restore')
  if old is None:file.unlink()
  else:file.write_bytes(old);os.chown(file,st.st_uid,st.st_gid);file.chmod(st.st_mode&0o7777)

def park_exporter():
 for unit in ['prometheus-node-exporter.service','prometheus-node-exporter.socket']:
  run(['systemctl','mask',unit])
  if run(['systemctl','is-active','--quiet',unit],False).returncode==0:run(['systemctl','stop',unit])

def main():
 p=argparse.ArgumentParser();p.add_argument('--reviewed-9011-build',action='store_true');args=p.parse_args()
 if not args.reviewed_9011_build:raise RuntimeError('explicit9011 build window required')
 guard();raw=sys.stdin.buffer.read(32769)
 if len(raw)>32768:raise RuntimeError('bounded public acceptance tool required')
 compile(raw,'generic-java-acceptance','exec');park_exporter();env=dict(os.environ,DEBIAN_FRONTEND='noninteractive',NEEDRESTART_MODE='l')
 with block_starts():
  run(['apt-get','-o','DPkg::Lock::Timeout=120','update'],env=env)
  run(['apt-get','-o','DPkg::Lock::Timeout=120','install','--yes','--no-install-recommends','openjdk-21-jdk-headless','prometheus-node-exporter'],env=env,timeout=420)
 park_exporter()
 try:user=pwd.getpwnam('java')
 except KeyError:run(['useradd','--system','--user-group','--home-dir','/var/lib/java','--create-home','--shell','/usr/sbin/nologin','java']);user=pwd.getpwnam('java')
 if user.pw_uid==0 or user.pw_shell not in ('/usr/sbin/nologin','/bin/false'):raise RuntimeError('dedicated unprivileged java identity required')
 home=Path('/var/lib/java')
 if home.resolve()!=home:raise RuntimeError('java home symlink refused')
 home.mkdir(exist_ok=True,mode=0o700);os.chown(home,user.pw_uid,user.pw_gid);home.chmod(0o700)
 dest=Path('/usr/local/libexec/dell-java-acceptance');dest.mkdir(parents=True,exist_ok=True,mode=0o755)
 if dest.resolve()!=dest:raise RuntimeError('trusted destination required')
 file=dest/'verify.py';file.write_bytes(raw);os.chown(file,0,0);file.chmod(0o644)
 acceptance=run(['runuser','--user','java','--','/usr/bin/python3',str(file),'--smoke'],timeout=90);result=json.loads(acceptance.stdout)
 result.update(builder='9011 fresh9010 clone',build_only=True,template_sealed=False,policy_hook_restored=True,packages=run(['dpkg-query','-W','-f=${Package} ${Version}\n','openjdk-21-jdk-headless','openjdk-21-jre-headless','prometheus-node-exporter']).stdout.decode().splitlines(),acceptance_code_sha256=hashlib.sha256(raw).hexdigest(),no_business_or_credentials_copied=True)
 print(json.dumps(result))
if __name__=='__main__':
 try:main()
 except Exception:print(json.dumps({'status':'failed','message':'fresh9011 build failed; raw output withheld, no seal performed'}));sys.exit(1)
