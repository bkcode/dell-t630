#!/usr/bin/env python3
"""Read-only real data-port zone matrix and private node-exporter checks."""
from pathlib import Path
import datetime
import importlib.util
import json
import shlex
import sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('netverify',ROOT/'infra/verify-network-independent.py');net=importlib.util.module_from_spec(spec);spec.loader.exec_module(net)
OUT=ROOT/'evidence/implementation/network-independent-verification.json'
def clock():return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat()
ENDPOINTS=[('data-prod-db',3306),('data-prod-infra',6379),('data-prod-infra',5672),('data-prod-infra',8848),('data-prod-infra',9848)]
TEST_PORTS=[3306,6379,5672,8848,9848]

def main():
 report=json.loads(OUT.read_text())
 if report.get('data_port_checks'):raise RuntimeError('Existing data matrix evidence retained; do not repeat blindly')
 pairs=[(name,net.ROLES[name]['target']['ip'],port) for name,port in ENDPOINTS]+[('data-test',net.ROLES['data-test']['target']['ip'],port) for port in TEST_PORTS]
 code='import socket,json\npairs='+repr(pairs)+'\nrows=[]\nfor role,ip,port in pairs:\n try:\n  s=socket.create_connection((ip,port),3);s.close();rows.append({"role":role,"ip":ip,"port":port,"connected":True})\n except OSError as exc:rows.append({"role":role,"ip":ip,"port":port,"connected":False,"errno":exc.errno})\nprint(json.dumps(rows))\n'
 report['known_listening_data_targets']=json.loads(net.control.pve('python3 -',data=code.encode(),timeout=45));net.save(report)
 live={(x['role'],x['port']):x['connected'] for x in report['known_listening_data_targets']}
 scenarios=[]
 for dest,port in ENDPOINTS:scenarios.append(('java-prod-01',dest,port,'allow'))
 for port in TEST_PORTS:scenarios.append(('java-test-01','data-test',port,'allow'))
 for source in ['java-test-01','nas-media','artifact-service']:
  for dest,port in ENDPOINTS:scenarios.append((source,dest,port,'deny'))
 for port in TEST_PORTS:scenarios.append(('java-prod-01','data-test',port,'deny'))
 for source,destination,port,expected in scenarios:
  case=source+'->'+destination+':'+str(port)
  if not live.get((destination,port)):
   report.setdefault('data_port_checks',[]).append({'case':case,'expected':expected,'status':'pending-target-not-confirmed-listening','business_payload_sent':False});net.save(report);continue
  before=net.counters();src=net.ROLES[source]['target'];dst=net.ROLES[destination]['target']['ip']
  command=shlex.join(['python3','-','--role',source,'--source-ip',src['ip'],'--destination',dst,'--port',str(port)])
  result=net.control.guest(src['vmid'],command,data=net.PROBE.encode(),timeout=25,info=src);assert result['exit_code']==0
  observed=json.loads([x for x in result['stdout'].splitlines() if x.strip()][-1]);after=net.counters()
  before_drop=sum(x['counter']['packets'] for x in before['rows'] if x['verdict']=='drop');after_drop=sum(x['counter']['packets'] for x in after['rows'] if x['verdict']=='drop');delta=after_drop-before_drop
  status='passed-observed-allow' if expected=='allow' and observed['result']=='connected' else ('passed-observed-deny-with-shared-counter-evidence' if expected=='deny' and observed['result']=='timeout' and delta>0 else 'failed-or-inconclusive')
  report.setdefault('data_port_checks',[]).append({'case':case,'expected':expected,'status':status,'known_target_listening':True,'observation':observed,'forward_counter_before':before,'forward_counter_after':after,'shared_drop_counter_delta':delta,'limitations':['Shared counters are not per-flow packet trace; no database authentication or business payload performed.']});report['updated_at']=clock();net.save(report);print(case,status,'delta='+str(delta),flush=True)
 ops=net.ROLES['ops-service']['target'];targets=[{'name':x['name'],'ip':x['target']['ip']} for x in net.PRIVATE['roles']]
 metric_code=r'''
import socket,json,time,re,urllib.request,urllib.error,datetime
from pathlib import Path
assert socket.gethostname()=='ops-service' and not Path('/etc/pve').exists()
class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,*args,**kwargs):return None
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
targets=TARGETS;rows=[]
for target in targets:
 begin=time.monotonic();row={'role':target['name'],'ip':target['ip'],'port':9100,'path':'/metrics','body_saved':False}
 try:
  with opener.open('http://'+target['ip']+':9100/metrics',timeout=5) as response:
   row['http_status']=response.status;body=response.read(8*1024*1024+1);assert len(body)<=8*1024*1024
  lines=body.splitlines();row['sample_count']=sum(bool(re.match(rb'^[A-Za-z_:][A-Za-z0-9_:]*(?:\{.*\})?\s+[^\s]+',line)) for line in lines if line and not line.startswith(b'#'))
  row['node_exporter_build_info_observed']=any(line.startswith(b'node_exporter_build_info{') for line in lines);row['status']='passed-http-metrics-observed' if row['http_status']==200 and row['sample_count']>0 and row['node_exporter_build_info_observed'] else 'failed-or-inconclusive'
 except urllib.error.HTTPError as exc:row['http_status']=exc.code;row['status']='failed-http';exc.close()
 except Exception as exc:row['status']='failed-or-inconclusive';row['error_type']=type(exc).__name__
 row['elapsed_seconds']=round(time.monotonic()-begin,3);rows.append(row)
print(json.dumps({'at':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),'source_role':'ops-service','source_ip':'10.63.30.40','observations':rows,'metric_bodies_saved':False}))
'''.replace('TARGETS',repr(targets))
 result=net.control.guest(ops['vmid'],'python3 -',data=metric_code.encode(),timeout=120,info=ops);assert result['exit_code']==0
 report['ops_guest_metrics_checks']=json.loads([x for x in result['stdout'].splitlines() if x.strip()][-1]);checks=report['data_port_checks'];metrics=report['ops_guest_metrics_checks']['observations']
 report['summary']['real_data_port_matrix']={'total':len(checks),'allowed_pass':sum(x['status']=='passed-observed-allow' for x in checks),'denied_pass':sum(x['status']=='passed-observed-deny-with-shared-counter-evidence' for x in checks),'inconclusive_or_failed':sum(not x['status'].startswith('passed-') for x in checks)}
 report['summary']['ops_to_guest_9100']['dynamic_runtime_acceptance']='passed' if len(metrics)==12 and all(x['status']=='passed-http-metrics-observed' for x in metrics) else 'partial-or-failed'
 report['summary']['ops_to_guest_9100']['tested_guests']=len(metrics)
 report['status']='host-ssh-data-port-and-ops-metrics-readonly-verification-completed';report['updated_at']=clock();net.save(report)
 print('METRICS',[(x['role'],x['http_status'],x.get('sample_count'),x['status']) for x in metrics],flush=True)
 print('DATA_MATRIX',report['summary']['real_data_port_matrix'],flush=True)

if __name__=='__main__':main()
