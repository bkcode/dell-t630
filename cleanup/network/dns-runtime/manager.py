#!/usr/bin/env python3
"""DNS-only190 guarded compilation, CAS execution, fresh strict SSH verification."""
import argparse,datetime,hashlib,importlib.util,json,shlex,sys
from pathlib import Path
sys.dont_write_bytecode=True;HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
transport=load('transport',ROOT/'network19/gateway/manager.py');compiler=load('active_compiler',ROOT/'network19/gateway/policy.py');gate=load('DNS_delta',HERE.parent/'dns_delta.py')
READ=r'''import json,hashlib,importlib.util
from pathlib import Path
p=Path('/usr/local/libexec/dell-gateway19/manage.py');s=importlib.util.spec_from_file_location('runtime',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);m.guard_identity();config=m.read_config();print(json.dumps({'config':config,'interfaces':m.guard(config,True),'config_sha256':hashlib.sha256(Path('/etc/dell-gateway19/config.json').read_bytes()).hexdigest(),'dns_sha256':hashlib.sha256(Path('/etc/dell-gateway19/dnsmasq.conf').read_bytes()).hexdigest(),'pending':Path('/var/lib/dell-gateway19/pending.json').exists()}))'''
def main():
 p=argparse.ArgumentParser();p.add_argument('--reviewed-190-DNS-only',action='store_true');args=p.parse_args()
 if not args.reviewed_190_DNS_only:raise RuntimeError('root DNS-only window required')
 target=json.loads((ROOT/'network19/evidence/gateway-initial-access.json').read_text())['target'];before=transport.ssh(target,'sudo -n python3 -B -c '+shlex.quote(READ),timeout=40)
 if before['exit_code']:raise RuntimeError('read-only snapshot failed')
 old=json.loads(before['stdout'])
 if old['pending']:raise RuntimeError('another gateway transaction pending')
 plan=json.loads((ROOT/'network19/migration-plan.json').read_text());new=compiler.load(plan,old['config']['WAN_MAC'],old['config']['LAN_MAC']);delta=gate.validate_dns_only_delta(old['config'],new)
 if compiler.nft(old['config'],old['interfaces'])!=compiler.nft(new,old['interfaces']):raise RuntimeError('candidate FW bytes changed')
 (HERE/'prepared-config.json').write_text(json.dumps(new,indent=2)+'\n');(HERE/'prepared-config.json').chmod(0o600);(HERE/'prepared-dnsmasq.conf').write_text(compiler.dnsmasq(new,old['interfaces']));(HERE/'preflight.json').write_text(json.dumps({'at':datetime.datetime.now().astimezone().isoformat(),'delta':delta,'old_config_sha256':old['config_sha256'],'old_dns_sha256':old['dns_sha256'],'expected_nft_bytes_unchanged':True,'WireGuard_full_unchanged':new.get('WireGuard_client_access')==old['config'].get('WireGuard_client_access')},indent=2)+'\n')
 data=json.dumps({'new_config':new,'expected_old_config_sha256':old['config_sha256'],'expected_old_dns_sha256':old['dns_sha256']}).encode();code=(HERE/'remote.py').read_text();result=transport.ssh(target,'sudo -n python3 -B -c '+shlex.quote(code)+' --reviewed-190-DNS-only',data,timeout=140)
 value={'at':datetime.datetime.now().astimezone().isoformat(),'target':'190','exit_code':result['exit_code'],'result':json.loads(result['stdout']) if result['stdout'].strip() else {'status':'missing-result'},'PVE_OW_other_guest_Nexus_writes':False};(HERE/'receipt.json').write_text(json.dumps(value,indent=2)+'\n')
 print(json.dumps({'exit_code':result['exit_code'],'status':value['result']['status'],'removed_count':len(value['result'].get('approved_removed',[])),'nonDNS_invariants_unchanged':value['result'].get('nonDNS_invariants_unchanged'),'private_backup':value['result'].get('backup_directory_190_private')}))
 if result['exit_code']:return result['exit_code']
 fresh=transport.ssh(target,'id -un; hostname; sudo -n /usr/bin/python3 -B /usr/local/libexec/dell-gateway19/manage.py check',timeout=45)
 lines=fresh['stdout'].splitlines();verified=fresh['exit_code']==0 and lines[:2]==['ub','network-gateway'];check=json.loads(lines[-1]) if verified else None
 follow={'at':datetime.datetime.now().astimezone().isoformat(),'fresh_strict_SSH_passed':verified,'result':check};(HERE/'fresh-strict-SSH-check.json').write_text(json.dumps(follow,indent=2)+'\n');print(json.dumps({'fresh_strict_SSH':verified,'forward':check.get('forwarding_all_WAN_LAN') if check else None,'WG':check.get('WireGuard_client_access') if check else None}));return 0 if verified else 1
if __name__=='__main__':raise SystemExit(main())
