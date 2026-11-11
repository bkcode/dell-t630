#!/usr/bin/env python3
"""Read completed safe stability evidence only; no workload or private data access."""
import datetime,json,socket,subprocess
from pathlib import Path
from zoneinfo import ZoneInfo
assert socket.gethostname()=='penpot-service'
root=Path('/root/dell-penpot-dns-init-fix-20261111');v=json.loads((root/'stability.json').read_text());assert v['status']=='seventy-minute-native-stability-passed'and v['elapsed_seconds']>=4200 and v['failure']is None
assert len(v['samples'])>=100 and all(s['all_eleven_healthy']and s['DNS_zombies']==0 and s['NRestarts']==v['baseline_NRestarts']for s in v['samples'])
assert subprocess.check_output(['systemctl','is-active','dell-penpot.service']).decode().strip()=='active'
print(json.dumps({'at':datetime.datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),'status':v['status'],'elapsed_seconds':v['elapsed_seconds'],'required_seconds':4200,'sample_count':v['sample_count'],'all_samples_eleven_healthy':True,'all_samples_DNS_zombies_zero':True,'DNS_PID_min':min(s['DNS_pids']for s in v['samples']),'DNS_PID_max_observed':max(s['DNS_pids']for s in v['samples']),'DNS_configured_PID_limit':128,'NRestarts_baseline':v['baseline_NRestarts'],'NRestarts_unchanged':True,'first_sample':v['samples'][0],'last_sample':v['samples'][-1],'failures':None,'workload_data_credentials_or_alert_rules_mutated_by_observer':False,'monitor_unit_active':subprocess.run(['systemctl','is-active','--quiet','dell-penpot-postfix-observe-20261111']).returncode==0,'private_design_or_identity_hashes_output':False}))
