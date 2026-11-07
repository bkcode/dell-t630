#!/usr/bin/python3
"""VM190-only reviewed package preparation. No routing/DHCP/firewall activation."""
import argparse,contextlib,datetime,hashlib,json,os,platform,socket,subprocess,sys,uuid
from pathlib import Path
MAC={'WAN':'02:63:19:01:90:00','LAN':'02:63:19:01:90:01'}
def cmd(args,check=True,timeout=180,env=None):
 r=subprocess.run(args,capture_output=True,timeout=timeout,env=env)
 if check and r.returncode:raise RuntimeError('standby native command failed; raw output withheld')
 return r

def guard():
 if os.geteuid()!=0 or Path('/etc/pve').exists() or socket.gethostname().split('.')[0]!='network-gateway' or platform.system()!='Linux' or platform.machine() not in ('x86_64','amd64'):raise RuntimeError('dedicated gateway190 root only')
 fields=dict(line.split('=',1) for line in Path('/etc/os-release').read_text().splitlines() if '='in line)
 if fields.get('ID','').strip('"')!='debian' or fields.get('VERSION_ID','').strip('"')!='13':raise RuntimeError('Debian13 required')
 if Path('/etc/dell-gateway19/config.json').exists():raise RuntimeError('standby cannot alter an already configured gateway')
 rows=json.loads(cmd(['ip','-j','addr']).stdout);mapped={}
 for role,mac in MAC.items():
  matches=[r for r in rows if r.get('address','').lower()==mac]
  if len(matches)!=1:raise RuntimeError('unique reviewed WAN/LAN MAC required')
  row=matches[0];expected='192.168.21.23' if role=='WAN' else '192.168.19.1'
  if not any(a.get('local')==expected and a.get('prefixlen')==24 for a in row.get('addr_info',[])):raise RuntimeError('reviewed bootstrap IP not present on matching MAC')
  mapped[role]=row['ifname']
 if mapped['WAN']==mapped['LAN']:raise RuntimeError('different NICs required')
 return mapped

@contextlib.contextmanager
def block_daemon_starts():
 path=Path('/usr/sbin/policy-rc.d')
 if path.is_symlink():raise RuntimeError('existing policy hook symlink requires review')
 old=path.read_bytes() if path.exists() else None;oldstat=path.stat() if path.exists() else None
 if oldstat and (oldstat.st_uid!=0 or oldstat.st_mode&0o022):raise RuntimeError('existing policy hook not root-trusted')
 wrapper=b'#!/bin/sh\n# Temporary VM190 standby: prevent package daemon starts/restarts.\nexit 101\n';digest=hashlib.sha256(wrapper).hexdigest()
 fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_TRUNC|os.O_NOFOLLOW,0o755)
 with os.fdopen(fd,'wb') as out:out.write(wrapper)
 os.chown(path,0,0);path.chmod(0o755)
 try:yield
 finally:
  if path.is_symlink() or not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest()!=digest:raise RuntimeError('temporary policy changed concurrently; refuses blind restoration')
  if old is None:path.unlink()
  else:path.write_bytes(old);os.chown(path,oldstat.st_uid,oldstat.st_gid);path.chmod(oldstat.st_mode&0o7777)

def mask_defaults():
 for service in ['dnsmasq.service','nftables.service']:
  cmd(['systemctl','mask',service])
  if cmd(['systemctl','is-active','--quiet',service],check=False).returncode==0:cmd(['systemctl','stop',service])

def main():
 p=argparse.ArgumentParser();p.add_argument('--reviewed-vm190-standby',action='store_true');args=p.parse_args()
 if not args.reviewed_vm190_standby:raise RuntimeError('explicit reviewed standby window required')
 interfaces=guard();before_forward=Path('/proc/sys/net/ipv4/ip_forward').read_text().strip();cmd(['sysctl','-q','-w','net.ipv4.ip_forward=0']);mask_defaults()
 env=dict(os.environ,DEBIAN_FRONTEND='noninteractive',NEEDRESTART_MODE='l')
 with block_daemon_starts():
  cmd(['apt-get','-o','DPkg::Lock::Timeout=120','update'],timeout=240,env=env)
  cmd(['apt-get','-o','DPkg::Lock::Timeout=120','install','--yes','--no-install-recommends','nftables','dnsmasq'],timeout=300,env=env)
 mask_defaults();cmd(['sysctl','-q','-w','net.ipv4.ip_forward=0']);cmd(['dnsmasq','--test','--conf-file=/dev/null'])
 units={name:{'active':cmd(['systemctl','is-active','--quiet',name],check=False).returncode==0,'masked':cmd(['systemctl','is-enabled',name],check=False).stdout.decode().strip()=='masked'} for name in ['dnsmasq.service','nftables.service']}
 sockets=cmd(['ss','-H','-lntup']).stdout.decode();unsafe=[]
 for line in sockets.splitlines():
  parts=line.split()
  if len(parts)>4 and parts[4].rsplit(':',1)[-1] in ('53','67') and not parts[4].startswith(('127.','[::1]')):unsafe.append(parts[4])
 result={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'packages-installed-standby-no-activation','interfaces_matched_by_MAC':interfaces,'packages':cmd(['dpkg-query','-W','-f=${Package} ${Version}\n','nftables','dnsmasq','dnsmasq-base']).stdout.decode().splitlines(),'forward_before':before_forward,'forward_after':Path('/proc/sys/net/ipv4/ip_forward').read_text().strip(),'default_units':units,'unsafe_DNS_DHCP_listeners':unsafe,'policy_hook_restored':True,'gateway_firewall_or_DNS_DHCP_activated':False,'no_PVE_OW_or_other_guests_modified':True,'network_owners':{name:cmd(['systemctl','is-active',name],check=False).stdout.decode().strip() for name in ['networking.service','systemd-networkd.service','NetworkManager.service','systemd-resolved.service']},'UTC':cmd(['date','-u','+%Y-%m-%dT%H:%M:%SZ']).stdout.decode().strip(),'IPv6_kernel_parameters':Path('/proc/cmdline').read_text().strip().split()}
 if result['forward_after']!='0' or unsafe or not all(not row['active'] and row['masked'] for row in units.values()):raise RuntimeError('standby safety checks failed')
 store=Path('/var/lib/dell-gateway19');store.mkdir(mode=0o700,exist_ok=True);file=store/'standby.json';file.write_text(json.dumps(result,indent=2)+'\n');file.chmod(0o600);print(json.dumps(result))
if __name__=='__main__':
 try:main()
 except Exception:print(json.dumps({'status':'failed','message':'fixed gateway190 standby rejected/failed; raw output withheld'}));sys.exit(1)
