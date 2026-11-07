#!/usr/bin/python3 -I
"""Root-owned forced-command front end, executed unprivileged as deployer."""
import importlib.util,json,os,pwd,select,subprocess,sys,time
from pathlib import Path
CODE=Path('/usr/local/libexec/dell-publisher')
ROOT_RPC='/usr/local/libexec/dell-publish-test240'

def protocol():
 path=CODE/'publisher_protocol.py'
 if path.is_symlink() or path.stat().st_uid!=0 or path.stat().st_mode&0o022:raise RuntimeError('untrusted protocol code')
 spec=importlib.util.spec_from_file_location('forced_protocol',path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def main():
 if len(sys.argv)!=1 or os.geteuid()!=pwd.getpwnam('deployer').pw_uid:raise RuntimeError('deployer forced command only')
 connection=os.environ.get('SSH_CONNECTION','').split()
 if len(connection)!=4 or connection[0]!='10.63.30.10' or connection[2]!='10.63.20.20' or connection[3]!='22':raise RuntimeError('publisher/test240 source tuple required')
 p=protocol();header=p.parse_ssh(os.environ.get('SSH_ORIGINAL_COMMAND',''))
 child=subprocess.Popen(['/usr/bin/sudo','-n','--',ROOT_RPC],stdin=subprocess.PIPE,stdout=sys.stdout.buffer,stderr=sys.stderr.buffer,env={'PATH':'/usr/bin:/bin','LANG':'C.UTF-8'},bufsize=0)
 try:
  child.stdin.write(json.dumps(header,separators=(',',':')).encode()+b'\n');child.stdin.flush()
  if header['action']=='stage':
   remaining=header['archive_bytes'];deadline=time.monotonic()+300
   while remaining:
    wait=min(30,max(0,deadline-time.monotonic()))
    if wait<=0 or not select.select([sys.stdin.fileno()],[],[],wait)[0]:raise RuntimeError('publisher input deadline exceeded')
    block=os.read(sys.stdin.fileno(),min(1024*1024,remaining))
    if not block:raise RuntimeError('publisher stage stream truncated')
    child.stdin.write(block);remaining-=len(block)
   if not select.select([sys.stdin.fileno()],[],[],5)[0] or os.read(sys.stdin.fileno(),1):raise RuntimeError('publisher stage has trailing or unterminated input')
  child.stdin.close();return child.wait(timeout=1600)
 except Exception:
  child.stdin.close()
  # Root helper handles bounded input and transition ownership. Do not execute another command.
  try:child.wait(timeout=10)
  except subprocess.TimeoutExpired:pass
  raise

if __name__=='__main__':
 try:sys.exit(main())
 except Exception:
  print(json.dumps({'ok':False,'message':'restricted SSH publishing request rejected; no shell/subsystem access'}));sys.exit(1)
