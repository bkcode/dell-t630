#!/usr/bin/env python3
"""PREPARED ONLY: root-reviewed NAS260 OMV setter + Salt OS switch, through QGA standby."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import platform
import socket
import stat
import sys
import time

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent

def module(name,file):
 spec=importlib.util.spec_from_file_location(name,HERE/file);value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value

tx=module('media_transaction','guest_transaction.py')
omv=module('omv_payload','omv_payload.py')
R=tx.ROLES[260]


def identity():
 if HERE!=Path('/opt/dell/network19/services-media') or os.geteuid()!=0 or Path('/etc/pve').exists() or platform.system()!='Linux' or platform.machine() not in ('x86_64','amd64') or socket.gethostname().split('.')[0]!='nas-media':raise RuntimeError('assigned NAS guest only')
 for path in [Path('/opt'),Path('/opt/dell'),Path('/opt/dell/network19'),HERE,HERE/'nas-os-network.py',HERE/'omv_payload.py']:
  if path.resolve()!=path or path.stat().st_uid!=0 or path.stat().st_mode&0o022:raise RuntimeError('trusted root package required')
 rows=json.loads(tx.command(['/usr/sbin/ip','-j','address','show']).stdout)
 selected=[x for x in rows if x.get('address','').lower()==R['mac']]
 if len(selected)!=1 or selected[0]['ifname']!='ens18':raise RuntimeError('same assigned physical NIC MAC/name required')
 # Does not depend on current IP for QGA rollback after a failed network deployment.
 return selected[0]


def schema():
 value=json.loads(tx.read('/usr/share/openmediavault/datamodels/rpc.network.json'))
 values=value if isinstance(value,list) else [value]
 matches=[x for x in values if x.get('id')=='rpc.network.setethernetiface']
 if len(matches)!=1:raise RuntimeError('exact installed OMV RPC model required')
 return matches[0]


def current():
 data=json.loads(tx.command(['/usr/sbin/omv-confdbadm','read','--prettify','conf.system.network.interface']).stdout)
 values=data if isinstance(data,list) else [data]
 found=[x for x in values if x.get('uuid')=='f5ea6395-ec2e-47ca-9e5e-4d541eeb9f5f' and x.get('devicename')=='ens18' and x.get('type')=='ethernet']
 if len(found)!=1:raise RuntimeError('existing wired OMV object required')
 return {k:found[0][k] for k in omv.FIELDS}


def ipv6():
 keys=['ens18/disable_ipv6','ens18/accept_ra','ens18/autoconf','all/disable_ipv6','default/disable_ipv6','lo/disable_ipv6']
 return {k:Path('/proc/sys/net/ipv6/conf',k).read_text().strip() for k in keys}


def private(folder):
 for d in [folder.parent.parent,folder.parent,folder]:
  if d.resolve()!=d or d.stat().st_uid!=0 or stat.S_IMODE(d.stat().st_mode)!=0o700:raise RuntimeError('existing root700 application transaction required')
 p=folder/'journal.json'
 if p.stat().st_uid!=0 or stat.S_IMODE(p.stat().st_mode)!=0o600:raise RuntimeError('existing root600 application journal required')
 app=json.loads(tx.read(p))
 if app['role']!=260:raise RuntimeError('wrong app transaction')
 return app


def set_network(params):
 helper=Path('/opt/dell/nas-stage/omv-rpc-stdin.php')
 if helper.resolve()!=helper or helper.stat().st_uid!=0 or helper.stat().st_mode&0o022:raise RuntimeError('existing local-root OMV helper ownership differs')
 request=json.dumps({'service':'Network','method':'setEthernetIface','params':params}).encode()
 p=__import__('subprocess').run(['/usr/bin/php8.4','-c','/etc/openmediavault',str(helper)],input=request,capture_output=True,timeout=90,env=tx.ENV)
 try:reply=json.loads(p.stdout)
 except ValueError:raise RuntimeError('OMV setter returned unconfirmed response') from None
 if p.returncode or reply.get('status')!='ok':raise RuntimeError('OMV setter failed; private details withheld')
 tx.command(['/usr/sbin/omv-salt','deploy','run','systemd-networkd'],timeout=240)


def verify_phase(new,params,proof):
 deadline=time.monotonic()+45
 while True:
  try:tx.guard(260,'new' if new else 'old');break
  except Exception:
   if time.monotonic()>=deadline:raise RuntimeError('bounded IP/gateway/Docker/data guard remains unconfirmed') from None
   time.sleep(2)
 if current()!=params:raise RuntimeError('OMV wired configuration persistence differs')
 if ipv6()!=proof['ipv6']:raise RuntimeError('NAS original IPv6 policy changed; no automatic broad policy override')
 if tx.protected(R)!=proof['protected_hashes']:raise RuntimeError('SSH key/shadow/root data guard bytes changed')
 ssh=tx.command(['/usr/sbin/sshd','-T']).stdout.decode().splitlines()
 if not {'permitrootlogin no','passwordauthentication no','pubkeyauthentication yes'}<=set(ssh):raise RuntimeError('SSH authentication policy changed')


def main():
 os.umask(0o077)
 p=argparse.ArgumentParser();p.add_argument('action',choices=['check','stage','apply','rollback']);p.add_argument('--window',required=True);p.add_argument('--qga-console-standby',action='store_true');p.add_argument('--smb-clients-drained',action='store_true');a=p.parse_args()
 if not __import__('re').fullmatch('[a-f0-9]{32}',a.window):raise RuntimeError('exact existing app transaction nonce required')
 identity();folder=Path('/root/dell-network19-media/260')/a.window;app=private(folder);path=folder/'network-journal.json'
 if a.action in ('check','stage'):
  tx.guard(260,'old');before=current();payload=omv.build(before,schema())
  policy=ipv6()
  if policy!={'ens18/disable_ipv6':'1','ens18/accept_ra':'0','ens18/autoconf':'0','all/disable_ipv6':'0','default/disable_ipv6':'0','lo/disable_ipv6':'0'}:raise RuntimeError('review actual NAS IPv6 policy before network switch')
  if a.action=='stage':
   if path.exists() or app['phase'] not in ('staged','quiesced'):raise RuntimeError('network stage exists or invalid app phase')
   tx.save(path,{'phase':'network-staged','role':260,'payload':payload,'ipv6':policy,'protected_hashes':tx.protected(R),'created_at':time.time()})
 else:
  if not(a.qga_console_standby and a.smb_clients_drained):raise RuntimeError('explicit QGA standby and drained SMB clients required')
  if not path.is_file() or path.stat().st_uid!=0 or stat.S_IMODE(path.stat().st_mode)!=0o600:raise RuntimeError('private network journal required')
  record=json.loads(tx.read(path));payload=record['payload'];old=payload['old_RPC']['params'];new=payload['new_RPC']['params']
  if current() not in (old,new):raise RuntimeError('third-party wired config drift; refuse overwrite')
  if app['phase'] not in ('quiesced','rolled-back-files-await-old-network'):raise RuntimeError('Jellyfin app transaction must remain stopped before OS switch')
  tx.require_stopped(R)
  if tx.protected(R)!=record['protected_hashes']:raise RuntimeError('protected NAS bytes changed')
  forward=a.action=='apply'
  if forward:
   tx.guard(260,'old')
   if record['phase']!='network-staged' or current()!=old:raise RuntimeError('old network stage required')
  elif record['phase'] not in ('network-applying','network-new-ready','network-transition-unconfirmed','network-rollback-unconfirmed'):
   raise RuntimeError('no applied/interrupted network transition to rollback')
  record['phase']='network-applying' if forward else 'network-rolling-back';tx.save(path,record)
  try:
   set_network(new if forward else old);verify_phase(forward,new if forward else old,record)
   record['phase']='network-new-ready' if forward else 'network-old-restored'
   tx.save(path,record)
  except Exception:
   record['phase']='network-transition-unconfirmed' if forward else 'network-rollback-unconfirmed';tx.save(path,record)
   raise RuntimeError('network switch unconfirmed; use QGA journal and explicit rollback, do not start writers') from None
 print(json.dumps({'role':260,'status':'NAS-OS-network-'+a.action+'-completed','secret_values_or_hashes_emitted':False}))


if __name__=='__main__':
 try:main()
 except Exception:
  print(json.dumps({'role':260,'status':'NAS-OS-network-rejected-or-unconfirmed','private_journal':'existing root transaction directory'}));raise SystemExit(1)
