#!/usr/bin/env python3
"""Only fresh9011 image hygiene; no shutdown/reboot/PVE operations."""
import argparse,datetime,glob,hashlib,json,os,pwd,shutil,socket,subprocess,sys
from pathlib import Path
MAC='bc:24:11:a4:d3:4d';IP='192.168.19.197';NAME='java-acceptance-build'
def run(args,check=True):
 r=subprocess.run(args,capture_output=True,timeout=90)
 if check and r.returncode:raise RuntimeError('fixed clean validation failed; raw output withheld')
 return r

def main():
 p=argparse.ArgumentParser();p.add_argument('--reviewed-9011-clean',action='store_true');args=p.parse_args()
 if not args.reviewed_9011_clean or os.geteuid()!=0 or Path('/etc/pve').exists() or socket.gethostname().split('.')[0]!=NAME:raise RuntimeError('explicit fresh9011 clean only')
 links=json.loads(run(['ip','-j','addr']).stdout);rows=[x for x in links if x.get('address','').lower()==MAC]
 if len(rows)!=1 or not any(x.get('local')==IP for x in rows[0].get('addr_info',[])):raise RuntimeError('9011 exact MAC/IP guard')
 business=['/opt/finger','/etc/nacos','/var/lib/mysql','/opt/dell/ops','/etc/penpot','/etc/nexus.env','/var/lib/dell-gateway19']
 if any(Path(x).exists() for x in business):raise RuntimeError('business/role contamination; refuse cleanup')
 help=run(['cloud-init','clean','--help']).stdout.decode()
 if not all(x in help for x in ['--logs','--machine-id','--seed','--configs','network']):raise RuntimeError('required clean options not supported; stop before changes')
 for home in [Path('/root'),Path('/home/ub')]:
  if any((home/'.ssh').glob('id_*')):raise RuntimeError('unexpected client SSH key material; root review rather than copy/delete silently')
 before_machine=hashlib.sha256(Path('/etc/machine-id').read_bytes()).hexdigest();verify=Path('/usr/local/libexec/dell-java-acceptance/verify.py');verify_sha=hashlib.sha256(verify.read_bytes()).hexdigest();java=pwd.getpwnam('java')
 acceptance=run(['runuser','--user','java','--','/usr/bin/python3',str(verify),'--smoke']);checked=json.loads(acceptance.stdout)
 for unit in ['prometheus-node-exporter.service','prometheus-node-exporter.socket']:
  run(['systemctl','mask',unit])
  if run(['systemctl','is-active','--quiet',unit],False).returncode==0:run(['systemctl','stop',unit])
 identity=Path('/etc/cloud/cloud.cfg.d/90-java-template-identity.cfg');identity.write_text('ssh_deletekeys: true\nssh_genkeytypes: [ed25519, rsa]\nssh_pwauth: false\n');identity.chmod(0o644)
 run(['cloud-init','clean','--logs','--machine-id','--seed','--configs','network'])
 netplan=Path('/etc/netplan/50-cloud-init.yaml');removed=[]
 if netplan.exists():
  text=netplan.read_text()
  if IP in text or ('generated' in text.lower() and 'cloud-init' in text.lower()):netplan.unlink();removed.append(str(netplan))
  else:raise RuntimeError('unexpected non-generated netplan file; do not delete')
 # Instance hostname is supplied by next clone metadata; keep only generic image placeholders.
 Path('/etc/hostname').write_text('localhost\n');hosts=Path('/etc/hosts')
 if hosts.exists():hosts.write_text('\n'.join(line.replace(NAME,'localhost') for line in hosts.read_text().splitlines() if IP not in line)+'\n')
 for pattern in ['/var/lib/dhcp/*.leases','/var/lib/dhcp/*.leases~','/var/lib/NetworkManager/*.lease']:
  for raw in glob.glob(pattern):
   file=Path(raw)
   if file.is_file() and not file.is_symlink():file.unlink();removed.append(str(file))
 for home in [Path('/root'),Path('/home/ub')]:
  for relative in ['.ssh/authorized_keys','.bash_history','.zsh_history','.python_history']:
   file=home/relative
   if file.is_file() or file.is_symlink():file.unlink();removed.append(str(file))
 for file in Path('/etc/ssh').glob('ssh_host_*'):
  if file.is_file() or file.is_symlink():file.unlink();removed.append(str(file))
 # Only our own smoke prefix and owner; no sweep of arbitrary /tmp or /opt data.
 for file in Path('/tmp').glob('java-acceptance-*'):
  if not file.is_symlink() and file.stat().st_uid==java.pw_uid and file.is_dir():shutil.rmtree(file);removed.append(str(file))
 dbus=Path('/var/lib/dbus/machine-id')
 if dbus.exists() and not dbus.is_symlink():dbus.unlink();dbus.symlink_to('/etc/machine-id')
 run(['apt-get','clean'])
 stale=[]
 for folder in ['/etc/netplan','/etc/systemd/network','/etc/network/interfaces.d']:
  for file in Path(folder).glob('*'):
   if file.is_file() and IP in file.read_text(errors='replace'):stale.append(str(file))
 machine=Path('/etc/machine-id').read_text().strip();seed=Path('/var/lib/cloud/seed');seedgone=not seed.exists() or not any(seed.iterdir());hostkeys=list(Path('/etc/ssh').glob('ssh_host_*'));authorized=[str(x) for x in [Path('/root/.ssh/authorized_keys'),Path('/home/ub/.ssh/authorized_keys')] if x.exists()]
 result={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'9011-cleaned-do-not-reboot-await-root-template','machine_id_before_sha256':before_machine,'machine_id_nextboot_reset':machine in ('','uninitialized'),'host_SSH_keys_absent':not hostkeys,'root_ub_authorized_keys_absent':not authorized,'CI_seed_gone':seedgone,'CI_instances_gone':not Path('/var/lib/cloud/instances').exists() or not any(Path('/var/lib/cloud/instances').iterdir()),'business_dirs_absent':not any(Path(x).exists() for x in business),'static_19_197_disk_config_paths':stale,'generic_hostname_on_disk':Path('/etc/hostname').read_text().strip()=='localhost','ssh_deletekeys_nextclone':True,'verify_code_preserved':hashlib.sha256(verify.read_bytes()).hexdigest()==verify_sha,'exporter_still_parked':run(['systemctl','is-enabled','prometheus-node-exporter.service'],False).stdout.decode().strip()=='masked','remaining_opt_top_level':[x.name for x in Path('/opt').iterdir()],'removed_paths':removed,'no_reboot_or_shutdown_performed':True,'runtime_builder_IP_kept_until_root_shutdown':True,'preclean_nonroot_smoke':checked['status']}
 if not all([result['machine_id_nextboot_reset'],result['host_SSH_keys_absent'],result['root_ub_authorized_keys_absent'],result['CI_seed_gone'],result['CI_instances_gone'],result['business_dirs_absent'],not stale,result['generic_hostname_on_disk'],result['verify_code_preserved'],result['exporter_still_parked']]):raise RuntimeError('image hygiene validation failed; do not convert until root reviews')
 print(json.dumps(result))
if __name__=='__main__':
 try:main()
 except Exception:print(json.dumps({'status':'failed','message':'9011 hygiene failed; root QGA review needed, do not reboot/convert'}));sys.exit(1)
