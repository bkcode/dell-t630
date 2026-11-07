#!/usr/bin/env python3
"""Explicit190-only persistence test. Never bypass changed SSH host keys."""
import argparse,datetime,hashlib,importlib.util,json,shlex,time
from pathlib import Path
HERE=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('transport',HERE/'manager.py');transport=importlib.util.module_from_spec(s);s.loader.exec_module(transport)
s=importlib.util.spec_from_file_location('audit_source',HERE/'audit.py');audit=importlib.util.module_from_spec(s);s.loader.exec_module(audit)
EXTRA=r'''
out['boot_id']=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
key=subprocess.run(['ssh-keygen','-lf','/etc/ssh/ssh_host_ed25519_key.pub'],capture_output=True,text=True,check=True).stdout.split();out['ED25519_fingerprint']=key[1]
import hashlib
out['file_sha256']={name:hashlib.sha256(Path(raw).read_bytes()).hexdigest() for name,raw in {'config':'/etc/dell-gateway19/config.json','policy':'/usr/local/libexec/dell-gateway19/policy.py','manage':'/usr/local/libexec/dell-gateway19/manage.py'}.items()}
def clean(value):
 if isinstance(value,list):return [clean(x) for x in value]
 if isinstance(value,dict):return {k:({} if k=='counter' else clean(v)) for k,v in value.items() if k not in ('handle','metainfo')}
 return value
out['normalized_nft_sha256']=hashlib.sha256(json.dumps(clean([x for x in nf['nftables'] if 'metainfo'not in x]),sort_keys=True).encode()).hexdigest()
out['unit_timing']={}
for name in ['dell-gateway19-firewall.service','systemd-networkd.service','dell-gateway19-ready.service','dell-gateway19-dnsmasq.service']:
 raw=subprocess.run(['systemctl','show',name,'-p','ActiveState','-p','ExecMainStartTimestampMonotonic','-p','ExecMainExitTimestampMonotonic','-p','ActiveEnterTimestampMonotonic','-p','UnitFileState'],capture_output=True,text=True,check=True).stdout
 out['unit_timing'][name]=dict(x.split('=',1) for x in raw.splitlines() if '='in x)
out['NTP']=subprocess.run(['timedatectl','show','-p','NTPSynchronized','-p','NTP'],capture_output=True,text=True).stdout.splitlines()
rows=json.loads(subprocess.run(['ip','-j','addr'],capture_output=True,text=True,check=True).stdout);out['MAC_addresses']={}
for role,mac in [('WAN','02:63:19:01:90:00'),('LAN','02:63:19:01:90:01')]:
 matches=[x for x in rows if x.get('address','').lower()==mac]
 if len(matches)!=1:raise SystemExit('MAC mismatch')
 row=matches[0];out['MAC_addresses'][role]={'ifname':row['ifname'],'MAC':mac,'ipv4':[x['local']+'/'+str(x['prefixlen']) for x in row.get('addr_info',[]) if x.get('family')=='inet']}
print(json.dumps(out))
'''
COLLECT=audit.CODE.replace('print(json.dumps(out))',EXTRA)
def collect(target):
 r=transport.ssh(target,'sudo -n python3 -c '+shlex.quote(COLLECT),timeout=45)
 if r['exit_code']:raise RuntimeError('strict read-only reboot snapshot failed')
 return json.loads(r['stdout'])
def main():
 p=argparse.ArgumentParser();p.add_argument('--reviewed-190-reboot-after-CF',action='store_true');args=p.parse_args()
 if not args.reviewed_190_reboot_after_CF:raise RuntimeError('parent CF-complete signal and reboot window required')
 target=json.loads((HERE.parent/'evidence/gateway-initial-access.json').read_text())['target'];before=collect(target)
 if before['pending_transaction'] or before['ED25519_fingerprint']!=target['host_key_fingerprint']:raise RuntimeError('pending transaction or key mismatch before reboot')
 report={'at':datetime.datetime.now().astimezone().isoformat(),'scope':'gateway190-only-normal-reboot','before':before,'host_key_verification_bypassed':False,'other_guest_or_PVE_writes':False,'status':'reboot-requested'};path=HERE/'reboot-evidence.json';path.write_text(json.dumps(report,indent=2)+'\n')
 reboot=transport.ssh(target,'sudo -n systemctl reboot',timeout=20);report['reboot_command_exit']=reboot['exit_code'];end=time.monotonic()+180;seen=False
 while time.monotonic()<end:
  time.sleep(3);r=transport.ssh(target,'cat /proc/sys/kernel/random/boot_id',timeout=14)
  if any(text in r['stderr'] for text in ['HOST IDENTIFICATION HAS CHANGED','Host key verification failed']):
   report.update(status='blocked-hostkey-verification-QGA-required');path.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'status':report['status'],'automatic_trust_used':False}));return 1
  if r['exit_code']==0 and r['stdout'].strip()!=before['boot_id']:seen=True;break
 if not seen:raise RuntimeError('new bootID not observed via strict SSH; QGA required')
 # Allow existing boot/network-online jobs to finish; no unit restart or config repair.
 after=None
 for _ in range(12):
  try:
   after=collect(target)
   if all(x=='1' for x in after['forwarding'].values()) and all(x['ActiveState']=='active' for x in after['unit_timing'].values()):break
  except RuntimeError:pass
  time.sleep(2)
 if after is None:raise RuntimeError('postboot snapshot unavailable')
 report['after']=after;timing=after['unit_timing'];number=lambda unit,key:int(timing[unit][key]);fw='dell-gateway19-firewall.service';net='systemd-networkd.service';ready='dell-gateway19-ready.service';dns='dell-gateway19-dnsmasq.service'
 checks={'new_bootID':after['boot_id']!=before['boot_id'],'same_hostkey':after['ED25519_fingerprint']==before['ED25519_fingerprint']==target['host_key_fingerprint'],'code_and_config_sha_unchanged':before['file_sha256']==after['file_sha256'],'nft_policy_structure_unchanged':before['normalized_nft_sha256']==after['normalized_nft_sha256'],'same_MAC_and_IPs':before['MAC_addresses']==after['MAC_addresses'],'same_routes':before['routes']==after['routes'],'forwarding_all_three_1':set(after['forwarding'].values())=={'1'},'only_lo_IPv6':len(after['IPv6_addresses'])==1 and after['IPv6_addresses'][0]['ifname']=='lo' and after['IPv6_addresses'][0]['addr_info'][0]['local']=='::1','DNS_UDP_TCP_static_A':all(after['DNS_short_queries'][proto].get('matches_migration_plan') for proto in ['udp','tcp']),'no_NAT':after['no_NAT'],'all_units_active':all(x['ActiveState']=='active' for x in timing.values()),'firewall_before_networkd':number(fw,'ActiveEnterTimestampMonotonic')<=number(net,'ExecMainStartTimestampMonotonic'),'networkd_before_ready':number(net,'ActiveEnterTimestampMonotonic')<=number(ready,'ExecMainStartTimestampMonotonic'),'ready_before_DNS':number(ready,'ActiveEnterTimestampMonotonic')<=number(dns,'ExecMainStartTimestampMonotonic'),'no_pending_or_rollback':not after['pending_transaction'] and not after['rollback_timer_active'],'no_failed_units':not after['failed_units']}
 report['checks']=checks;report['status']='reboot-persistence-verified' if all(checks.values()) else 'postboot-check-failed-no-blind-repair';path.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'status':report['status'],'checks':checks,'same_hostkey_fingerprint':after['ED25519_fingerprint'],'new_bootID':after['boot_id'],'NTP':after['NTP']}));return 0 if all(checks.values()) else 1
if __name__=='__main__':
 try:raise SystemExit(main())
 except Exception:print(json.dumps({'status':'reboot-check-failed','message':'strict verification/QGA required; no key bypass or network repair attempted'}));raise
