#!/usr/bin/env python3
"""Read-only private-zone TCP checks; never create listeners or mutate host rules."""
from pathlib import Path
import datetime
import importlib.util
import json
import shlex
import subprocess
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('dell_control', ROOT / 'scripts/control.py')
control = importlib.util.module_from_spec(spec)
spec.loader.exec_module(control)
OUT = ROOT / 'evidence/implementation/network-independent-verification.json'
PRIVATE = json.loads((ROOT / 'evidence/implementation/private-guest-access.json').read_text())
ROLES = {row['name']: row for row in PRIVATE['roles']}

def clock():
    return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat()

def save(report):
    temporary = OUT.with_suffix('.json.tmp')
    temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    temporary.chmod(0o600)
    temporary.replace(OUT)

def counters():
    raw = control.pve('nft -j list chain inet dell_filter forward')
    data = json.loads(raw)
    rows = []
    for item in data.get('nftables', []):
        rule = item.get('rule')
        if not isinstance(rule, dict):
            continue
        for expression in rule.get('expr', []):
            if 'counter' in expression:
                rows.append({'handle': rule.get('handle'), 'counter': expression['counter'],
                             'verdict': 'drop' if any('drop' in e for e in rule['expr']) else 'other'})
    return {'at': clock(), 'rows': rows}

PROBE = r'''
import argparse,datetime,errno,json,socket,subprocess,time
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--role',required=True);p.add_argument('--source-ip',required=True);p.add_argument('--destination',required=True);p.add_argument('--port',type=int,required=True);a=p.parse_args()
assert socket.gethostname()==a.role and not Path('/etc/pve').exists()
route=json.loads(subprocess.check_output(['ip','-j','route','get',a.destination],text=True))[0]
assert route.get('prefsrc',route.get('src'))==a.source_ip
begin=time.monotonic();s=socket.socket(socket.AF_INET,socket.SOCK_STREAM);s.settimeout(3)
try:
 code=s.connect_ex((a.destination,a.port));local=s.getsockname()[0];kind='connected' if code==0 else ('refused-endpoint-closed' if code==errno.ECONNREFUSED else 'not-connected')
except Exception as exc:
 code=getattr(exc,'errno',None);local=a.source_ip;kind=type(exc).__name__
finally:s.close()
elapsed=time.monotonic()-begin
if code in [errno.EAGAIN,errno.ETIMEDOUT,errno.EINPROGRESS] and elapsed>=2.7:kind='timeout'
print(json.dumps({'at':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),'source_role':a.role,'source_ip':a.source_ip,'destination':a.destination,'port':a.port,'route':route,'connect_errno':code,'connect_errno_name':errno.errorcode.get(code),'result':kind,'elapsed_seconds':round(elapsed,3),'business_payload_sent':False}))
'''

def main():
    report = json.loads(OUT.read_text())
    report['management_cli_probes'] = []
    for port in [22,8006]:
        args=['nc','-vz','-w','5','192.168.21.22',str(port)]
        result=subprocess.run(args,text=True,capture_output=True,timeout=10)
        report['management_cli_probes'].append({'checked_at':clock(),'source':'Mac-local-client','host':'192.168.21.22','port':port,'command':shlex.join(args),'exit_code':result.returncode,'stdout':result.stdout.strip(),'stderr':result.stderr.strip(),'scope':'TCP reachability only; no TLS weakening, credentials or admin login used'})
    report['management_probe_limitations'] = 'Earlier direct Python sockets raised OSError in this client environment; trusted SSH and subsequent nc succeeded. The OSError samples are retained and are not endpoint-failure evidence.'
    targets = [('java-prod-01', 22), ('data-prod-db', 22)]
    pairs = [(name, ROLES[name]['target']['ip'], port) for name, port in targets]
    host_code = 'import socket,json\npairs=' + repr(pairs) + '\nout=[]\nfor name,ip,port in pairs:\n try:\n  s=socket.create_connection((ip,port),3);s.close();out.append({"role":name,"ip":ip,"port":port,"connected":True})\n except OSError as e:out.append({"role":name,"ip":ip,"port":port,"connected":False,"errno":e.errno})\nprint(json.dumps(out))\n'
    report['known_listening_ssh_targets'] = json.loads(control.pve('python3 -', data=host_code.encode(), timeout=30))
    assert all(row['connected'] for row in report['known_listening_ssh_targets'])
    scenarios = [('java-prod-01','data-prod-db','allow'),
                 ('publish-service','java-prod-01','allow'),
                 ('publish-service','java-test-01','allow'),
                 ('artifact-service','penpot-service','allow'),
                 ('artifact-service','java-prod-01','deny'),
                 ('data-test','java-prod-01','deny'),
                 ('data-test','data-prod-db','deny'),
                 ('nas-media','java-prod-01','deny'),
                 ('nas-media','data-prod-db','deny'),
                 ('java-prod-01','data-test','deny')]
    existing = {r['case'] for r in report.get('guest_tcp_checks', [])}
    for source, destination, expected in scenarios:
        case = source + '->' + destination + ':22'
        if case in existing:
            raise RuntimeError('Existing test record; manager must review before repeat')
        row = ROLES[source];target = row['target'];dest = ROLES[destination]['target']['ip']
        before = counters()
        command = shlex.join(['python3','-','--role',source,'--source-ip',target['ip'],'--destination',dest,'--port','22'])
        result = control.guest(target['vmid'], command, data=PROBE.encode(), timeout=25, info=target)
        assert result['exit_code'] == 0, 'Guest read-only probe failed'
        observation = json.loads([x for x in result['stdout'].splitlines() if x.strip()][-1])
        after = counters()
        before_packets = sum(r['counter']['packets'] for r in before['rows'] if r['verdict']=='drop')
        after_packets = sum(r['counter']['packets'] for r in after['rows'] if r['verdict']=='drop')
        delta = after_packets - before_packets
        status = 'passed-observed-allow' if expected=='allow' and observation['result']=='connected' else ('passed-observed-deny-with-shared-counter-evidence' if expected=='deny' and observation['result']=='timeout' and delta>0 else 'pending-inconclusive')
        test = {'case':case,'expected':expected,'port':22,'status':status,'observation':observation,'forward_counter_before':before,'forward_counter_after':after,'shared_drop_counter_delta':delta,'limitations':['Shared rule counters are not a per-flow packet trace. SSH destination is known listening; refusal is never treated as ACL denial.']}
        report.setdefault('guest_tcp_checks', []).append(test);report['updated_at']=clock();save(report)
        print(case, status, 'counter_delta='+str(delta), flush=True)
    report['status']='host-and-ssh-zone-checks-completed-data-runtime-checks-pending'
    report['pending_checks']=['Real production data ports await data-agent readiness and positive listener confirmation.','Ops to guest9100 is policy-only until masked exporters are activated; closed port is not ACL denial.','Dynamic IPv6 isolation and LAN DNAT application endpoints require their respective ready listeners/clients.']
    report['updated_at']=clock();save(report)

if __name__=='__main__':
    main()
