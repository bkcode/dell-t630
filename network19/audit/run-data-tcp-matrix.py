#!/usr/bin/env python3
"""Final approved 5-case TCP-only isolation matrix; never sends authentication/DML."""
import sys,json,shlex,datetime
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts'));import control
E=ROOT/'network19/audit/data-tcp-matrix.json'
def now():return datetime.datetime.now().astimezone().isoformat()
def qga(v,c):
 r=json.loads(control.pve(shlex.join(['qm','guest','exec',str(v),'--timeout','30','--','/usr/bin/python3','-c',c]),timeout=45));assert r.get('exitcode')==0,('QGA read-only TCP probe failed',v,r.get('exitcode'));return json.loads(r['out-data'])
def counters():return json.loads(control.pve("nft -j list table bridge dell19_acl",timeout=30))
assert not E.exists(),'refuse blind repeat of completed/partial matrix'
D={'started_at':now(),'scope':'5-approved-TCP3306-short-connects-only','target_listener_readback':[],'cases':[],'configuration_SQL_or_credentials_modified':False,'SQL_authentication_or_business_payload_sent':False}
def save():E.write_text(json.dumps(D,ensure_ascii=False,indent=2)+'\n')
save()
for v,hostname,ip in [(200,'data-prod-db','192.168.19.10'),(210,'data-test','192.168.19.20')]:
 code=r'''import json,socket,subprocess,pathlib
assert socket.gethostname()==HOSTNAME and not pathlib.Path('/etc/pve').exists()
ips=json.loads(subprocess.run(['ip','-j','-4','addr'],capture_output=True,text=True,check=True).stdout);assert any(a.get('local')==EXPECTED for x in ips for a in x.get('addr_info',[]));listeners=[l.split()[3] for l in subprocess.run(['ss','-lntH'],capture_output=True,text=True,check=True).stdout.splitlines() if l.split()[3].endswith(':3306')];p=subprocess.run(['docker','ps','--quiet','--filter','label=com.docker.compose.service=mysql'],capture_output=True,text=True,check=True);ids=p.stdout.split();assert len(ids)==1;h=subprocess.run(['docker','inspect','--format','{{.State.Running}} {{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}',ids[0]],capture_output=True,text=True,check=True).stdout.strip();print(json.dumps({'vmid':VMID,'hostname':socket.gethostname(),'expected_ip':EXPECTED,'tcp3306_listeners':listeners,'mysql_running_health':h,'passed':EXPECTED+':3306' in listeners and h=='true healthy','Env_or_health_logs_read':False}))'''.replace('HOSTNAME',repr(hostname)).replace('EXPECTED',repr(ip)).replace('VMID',str(v))
 row=qga(v,code);D['target_listener_readback'].append(row);save();assert row['passed']
D['counters_before']=counters();save()
for v,hostname,ip,cases in [(230,'java-prod-01','192.168.19.40',[('192.168.19.10',True),('192.168.19.20',False)]),(240,'java-test-01','192.168.19.45',[('192.168.19.20',True),('192.168.19.10',False)]),(260,'nas-media','192.168.19.60',[('192.168.19.10',False)])]:
 code=r'''import json,socket,subprocess,pathlib,time
assert socket.gethostname()==HOSTNAME and not pathlib.Path('/etc/pve').exists();ips=json.loads(subprocess.run(['ip','-j','-4','addr'],capture_output=True,text=True,check=True).stdout);assert any(a.get('local')==SOURCE for x in ips for a in x.get('addr_info',[]));out=[];begin=time.monotonic()
for ip,expected in CASES:
 s=socket.socket();s.settimeout(2);start=time.monotonic()
 try:s.connect((ip,3306));ok=True;error=None
 except OSError as e:ok=False;error=type(e).__name__
 finally:s.close()
 out.append({'source_vmid':VMID,'source_ip':SOURCE,'destination_ip':ip,'destination_port':3306,'expected_connected':expected,'TCP_connected':ok,'error_category':error,'elapsed_seconds':round(time.monotonic()-start,3),'passed':ok==expected,'payload_sent':False,'server_handshake_read':False})
print(json.dumps({'cases':out,'diagnostic_seconds':round(time.monotonic()-begin,3)}))'''.replace('HOSTNAME',repr(hostname)).replace('SOURCE',repr(ip)).replace('CASES',repr(cases)).replace('VMID',str(v));r=qga(v,code);D['cases'].extend(r['cases']);D.setdefault('process_durations',{})[str(v)]=r['diagnostic_seconds'];save();assert all(x['passed'] for x in r['cases'])
D['counters_after']=counters()
def values(n):
 out={}
 for item in n['nftables']:
  if 'rule' in item:
   r=item['rule'];c=next((x['counter']['packets'] for x in r['expr'] if 'counter' in x),None)
   if c is not None:out[(r['chain'],r['handle'],r.get('comment',''))]=c
 return out
a,b=values(D['counters_before']),values(D['counters_after']);D['counter_deltas']=[{'chain':k[0],'handle':k[1],'comment':k[2],'packets':n-a.get(k,n)} for k,n in b.items() if n-a.get(k,n)];drop=next((x['packets'] for x in D['counter_deltas'] if x['comment']=='east-west-denied'),0);allow=next((x['packets'] for x in D['counter_deltas'] if x['comment']=='explicit-role-TCP-matrix'),0);D['counter_evidence']={'east_west_drop_packets':drop,'explicit_role_TCP_allow_packets':allow,'counts_include_TCP_retransmission_and_background_not_one_per_connect':True};D['status']='passed' if len(D['cases'])==5 and all(x['passed'] for x in D['cases']) and drop>=3 and allow>=2 else 'needs-review';D['completed_at']=now();save();print(json.dumps({'status':D['status'],'cases':D['cases'],'counter_evidence':D['counter_evidence']}))
