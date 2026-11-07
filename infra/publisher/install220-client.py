#!/usr/bin/python3 -I
"""Prepared manager-only client install; uses existing private key only on220."""
import argparse,base64,hashlib,json,os,socket,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent

def put(path,data,mode=0o644):
 if path.resolve(strict=False)!=path:raise RuntimeError('client installation symlink rejected')
 path.parent.mkdir(parents=True,exist_ok=True,mode=0o755);path.write_bytes(data);os.chown(path,0,0);path.chmod(mode)

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--apply-reviewed220-client-window',action='store_true');args=p.parse_args()
 if not args.apply_reviewed220_client_window or os.geteuid()!=0 or socket.gethostname().split('.')[0]!='publish-service' or Path('/etc/pve').exists():raise RuntimeError('publisher220 manager client window required')
 data=sys.stdin.buffer.read(4097)
 if len(data)>4096:raise ValueError('trusted public host-key input too large')
 key=json.loads(data)['trusted240_host_public_key'].strip().split()
 if len(key)<2 or key[0]!='ssh-ed25519':raise ValueError('trusted240 Ed25519 host key required')
 # Public key is installed, never echoed; fingerprint only.
 blob=base64.b64decode(key[1],validate=True);fingerprint='SHA256:'+base64.b64encode(hashlib.sha256(blob).digest()).decode().rstrip('=')
 put(Path('/usr/local/bin/dell-publish'),(HERE/'publisher_client220.py').read_bytes(),0o755)
 put(Path('/usr/local/libexec/dell-publisher/publisher_protocol.py'),(HERE/'publisher_protocol.py').read_bytes())
 put(Path('/etc/dell-publisher/client-test240.json'),json.dumps({'target_host':'10.63.20.20','target_user':'deployer','host_key_alias':'dell-test240-publisher','source_ip':'10.63.30.10'}).encode())
 put(Path('/etc/dell-publisher/known_hosts'),('dell-test240-publisher '+key[0]+' '+key[1]+'\n').encode())
 print(json.dumps({'status':'client-installed-not-published','target':'test240','trusted_host_fingerprint':fingerprint,'private_key_read_or_exported':False,'remote240_modified':False}))

if __name__=='__main__':
 try:main()
 except Exception:print(json.dumps({'status':'failed','message':'publisher client install rejected; host public key not emitted'}));sys.exit(1)
