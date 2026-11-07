#!/usr/bin/env python3
"""270 no-send verification only; reads owned local APIs/target config/bridge metadata."""
import argparse,json,time,socket,os,urllib.request,urllib.parse,hashlib,subprocess
from pathlib import Path
HOST='http://192.168.19.70';BASE=Path('/opt/dell/ops')
class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,*args,**kwargs):return None
O=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
def get(path):
 with O.open(HOST+path,timeout=6) as r:return r.status,r.read(4*1024*1024)
def query(value):return json.loads(get(':9090/api/v1/query?'+urllib.parse.urlencode({'query':value}))[1])['data']['result']
def main():
 if os.geteuid()!=0 or socket.gethostname().split('.')[0]!='ops-service' or Path('/etc/pve').exists():raise SystemExit('only270')
 targets=json.loads((BASE/'config/prometheus/targets/guest-node.json').read_text());expected={x['targets'][0]:x['labels']['vmid'] for x in targets}
 if len(expected)!=12 or any(not ip.startswith('192.168.19.') for ip in expected):raise SystemExit('exact12 new target model required')
 p=argparse.ArgumentParser();p.add_argument('--wait-seconds',type=int,default=90);a=p.parse_args();deadline=time.monotonic()+min(max(a.wait_seconds,0),180);active=[]
 while True:
  code,data=get(':9090/api/v1/targets');active=json.loads(data)['data']['activeTargets'];nodes=[x for x in active if x.get('scrapePool')=='guest-node'];up=sum(x.get('health')=='up' for x in nodes)
  if len(nodes)==12 and up==12 or time.monotonic()>=deadline:break
  time.sleep(3)
 node_actual={urllib.parse.urlsplit(x['scrapeUrl']).netloc:x.get('health') for x in nodes};checks={'exact12new_model_and_actual_targets':set(node_actual)==set(expected),'all12nodeUP':len(nodes)==12 and all(x.get('health')=='up' for x in nodes),'all_Ops_own_5_targets_UP':all(x.get('health')=='up' for x in active if x.get('scrapePool')!='guest-node')}
 version=get(':3000/api/health');graph=json.loads(version[1]);checks['Grafana_database_ok']=version[0]==200 and graph.get('database')=='ok'
 pve=query('dell_pve_collector_timestamp_seconds');age=time.time()-float(pve[0]['value'][1]) if len(pve)==1 else None;checks['PVE_QGA_textfile_fresh']=age is not None and 0<=age<180
 services=query('dell_guest_service_active{role="java-test-01",instance="192.168.19.45:9100"}');http=query('dell_guest_http_up{role="java-test-01",instance="192.168.19.45:9100"}');names={x['metric'].get('service') for x in services};checks['Java240_base3_only']=names=={'ssh.service','qemu-guest-agent.service','prometheus-node-exporter.service'} and all(x['value'][1]=='1' for x in services);checks['Java240_active_HTTP_none']=http==[]
 policy=json.loads(Path('/etc/dell-lark-notify/policy.json').read_text());marker=json.loads((BASE/'lark-notify-state.json').read_text());state=subprocess.run(['systemctl','show','dell-lark-notify.service','--property=ActiveState,SubState,MainPID,NRestarts'],capture_output=True,text=True,timeout=10);bridge=dict(l.split('=',1) for l in state.stdout.splitlines() if '=' in l);checks['Lark_active_fixed172_policy']=policy=={'mode':'active','bind_host':'172.18.0.1','bind_port':19093,'allowed_source':'172.18.0.3'} and marker.get('mode')=='active' and bridge.get('ActiveState')=='active'
 report={'status':'passed' if all(checks.values()) else 'not-all-up-or-verified','checks':checks,'node_targets':12,'reported_nodes_UP':up,'actual_Ops_target_count':len(active),'nodes_down_vmids':[expected.get(ip) for ip,health in node_actual.items() if health!='up'],'PVE_metric_age_seconds':round(age,3) if age is not None else None,'native_bridge_state':bridge,'Lark_send_or_vendor_connectivity_tested':False,'HTTP_bodies_credentials_or_hook_read_or_emitted':False,'writes':0}
 print(json.dumps(report));raise SystemExit(0 if all(checks.values()) else 1)
if __name__=='__main__':main()
