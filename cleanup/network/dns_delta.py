#!/usr/bin/env python3
"""Offline DNS-only retirement review gate; never contacts a host or installs config."""
import copy
KEEP={('artifact-service','192.168.19.31'),('publish-service','192.168.19.30')}
REMOVALS={('data-docker-base-tpl','192.168.19.101'),('publish-legacy','192.168.19.104'),('java-prod-02','192.168.19.41'),('java-prod-03','192.168.19.42'),('dell-template-inspect','192.168.19.190'),('dell-linux-clone-test','192.168.19.191'),('dell-docker-clone-test','192.168.19.192'),('dell-docker-clone-a','192.168.19.193'),('dell-linux-clone-b','192.168.19.194'),('dell-docker-clone-b','192.168.19.195'),('dell-restore-baseline','192.168.19.196')}
def validate_dns_only_delta(old,new):
    for item in [old,new]:
        if not isinstance(item,dict) or not isinstance(item.get('hosts'),list):raise ValueError('compiled policy objects required')
    omit={'hosts','migration_plan_sha256'}
    if {k:v for k,v in old.items() if k not in omit}!={k:v for k,v in new.items() if k not in omit}:raise ValueError('DNS cleanup cannot change FW, WG, MAC, egress or management policy')
    pairs=lambda cfg:{(x['role'],x['address']) for x in cfg['hosts']}
    before,after=pairs(old),pairs(new)
    if not KEEP.issubset(before) or not KEEP.issubset(after):raise ValueError('Nexus31 and publisher30 DNS must survive ownership migration')
    if after-before or before-after!=before.intersection(REMOVALS):raise ValueError('only reviewed retired static DNS records present in current policy may be removed')
    return {'status':'offline-DNS-only-delta-approved-shape','removed':sorted(before-after),'retained_logical_aliases':sorted(KEEP),'nft_or_network_change_permitted':False,'native_dnsmasq_test_and_controlled_unit_restart':'pending-parent-window','lease_file':'preserve existing; never truncate/rotate'}
