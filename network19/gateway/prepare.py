#!/usr/bin/env python3
"""Compile only from the parent migration plan and measured190 NIC receipt."""
import argparse,datetime,hashlib,json,sys
from pathlib import Path
sys.dont_write_bytecode=True;HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE));import policy

def main():
 p=argparse.ArgumentParser();p.add_argument('--plan',type=Path,default=HERE.parent/'migration-plan.json');p.add_argument('--nic-receipt',type=Path,default=HERE.parent/'evidence/host-stage-receipt.json');args=p.parse_args()
 plan=json.loads(args.plan.read_text());nics=json.loads(args.nic_receipt.read_text())['gateway'];config=policy.load(plan,nics['WAN_MAC'],nics['LAN_MAC']);policy.validate_config(config)
 out=HERE/'bundle';out.mkdir(mode=0o700,exist_ok=True)
 for name,data in [('config.json',json.dumps(config,indent=2)+'\n'),('05-dell-gateway19-wan.network',policy.network(config,'WAN')),('05-dell-gateway19-lan.network',policy.network(config,'LAN'))]:(out/name).write_text(data);(out/name).chmod(0o600 if name=='config.json' else 0o644)
 # Names here are an observed rendering preview, not a persisted assumption.
 observed={'WAN':'eth0','LAN':'eth1'}
 standby=HERE/'standby-evidence.json'
 if standby.exists():observed=json.loads(standby.read_text())['result']['interfaces_matched_by_MAC']
 (out/'preview.nft').write_text(policy.nft(config,observed));(out/'preview-dnsmasq.conf').write_text(policy.dnsmasq(config,observed))
 report={'at':datetime.datetime.now().astimezone().isoformat(),'status':'prepared-not-applied','master_plan_sha256':config['migration_plan_sha256'],'MACs':{'WAN':config['WAN_MAC'],'LAN':config['LAN_MAC']},'interface_names':'runtime-resolved-by-MAC; preview names only observed','files':{x.name:hashlib.sha256(x.read_bytes()).hexdigest() for x in out.iterdir() if x.is_file()},'gateway_forwarding_activated_by_prepare':False};(HERE/'prepared.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
if __name__=='__main__':main()
