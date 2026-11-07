#!/usr/bin/env python3
"""Read-only public monitoring source capture. Never writes either guest or PVE."""
import sys,json,shlex,base64,hashlib,datetime
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT/'scripts'));import control
T={x['target']['vmid']:x['target'] for x in json.loads((ROOT/'evidence/implementation/private-guest-access.json').read_text())['roles']}
CODE=r'''
import pathlib,json,sys,socket,subprocess,base64,hashlib,urllib.request,urllib.parse,re,stat
p=json.load(sys.stdin);assert socket.gethostname()==p['hostname'] and not pathlib.Path('/etc/pve').exists()
paths=['/opt/dell/guest-monitoring/guest-targets.json','/opt/dell/guest-monitoring/collect-guest-health.py','/opt/dell/guest-monitoring/install-guest-baseline.py','/etc/dell-guest-monitoring/health.json','/etc/systemd/system/dell-guest-health.service','/etc/systemd/system/dell-guest-health.timer','/etc/systemd/system/prometheus-node-exporter.service.d/10-private-only.conf']
if p['vmid']==270:paths+=['/opt/dell/ops/config/prometheus/prometheus.yml','/opt/dell/ops/config/prometheus/targets/guest-node.json']
rows=[]
for text in paths:
 f=pathlib.Path(text);assert f.is_file() and not f.is_symlink();b=f.read_bytes();st=f.stat();assert st.st_uid==0 and not st.st_mode&0o022
 if f.name=='health.json':
  c=json.loads(b);assert not set(c)-{'role','private_ip','textfile_directory','services','http_checks','candidate_service_units','candidate_http_checks','notes'}
  for item in c.get('http_checks',[])+c.get('candidate_http_checks',[]):
   u=urllib.parse.urlsplit(item['url']);assert not(u.username or u.password or u.query or u.fragment) and set(item)=={'name','url'}
 if f.suffix in ['.yaml','.yml']:assert not re.search(rb'(?mi)^\s*(basic_auth|authorization|bearer_token(?:_file)?|password|credentials|oauth2|http_headers)\s*:',b),'auth-bearing config not exported'
 rows.append({'path':text,'uid':st.st_uid,'gid':st.st_gid,'mode':oct(stat.S_IMODE(st.st_mode)),'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b),'body_b64':base64.b64encode(b).decode()})
net=json.loads(subprocess.run(['ip','-j','addr'],capture_output=True,text=True,check=True).stdout)
service={}
for unit in ['dell-nexus.service','dell-ops.service','prometheus-node-exporter.service','dell-guest-health.timer']:
 r=subprocess.run(['systemctl','show',unit,'-p','ActiveState','-p','SubState','-p','MainPID'],capture_output=True,text=True);service[unit]=dict(x.split('=',1) for x in r.stdout.splitlines() if '=' in x)
out={'vmid':p['vmid'],'hostname':socket.gethostname(),'files':rows,'network_interfaces':[{'name':x['ifname'],'MAC':x.get('address'),'IPv4':[a['local'] for a in x.get('addr_info',[]) if a['family']=='inet']} for x in net],'service_state':service,'read_only':True,'credential_Env_user_data_or_logs_read':False}
if p['vmid']==220:
 expected='bc:24:11:2a:01:ad';iface=next(x for x in net if x.get('address','').lower()==expected);actual={a['local'] for a in iface.get('addr_info',[]) if a['family']=='inet'};approved={'192.168.19.30','192.168.19.31'};out['Nexus_alias_validation']={'original_MAC':expected,'interface':iface['ifname'],'actual_IPv4':sorted(actual),'approved_local_intersection':sorted(actual&approved),'alias31_on_original_MAC': '192.168.19.31' in actual,'unapproved_other_interface_addresses_not_used':True}
 if '192.168.19.31' in actual:
  try:
   with urllib.request.build_opener(urllib.request.ProxyHandler({})).open('http://192.168.19.31:8081/service/rest/v1/status',timeout=5) as r:out['Nexus_local_status_http']=r.status;r.read(1024)
  except Exception as e:out['Nexus_local_status_http']=getattr(e,'code',None);out['Nexus_http_error_class']=type(e).__name__
 else:out['Nexus_http_skipped']='alias31 not yet on own approved MAC; do not probe otherVM221'
else:
 op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
 with op.open('http://192.168.19.70:9090/api/v1/targets',timeout=8) as r:data=json.loads(r.read(2000000))
 out['Prometheus_targets']=[{'labels':x.get('labels',{}),'health':x.get('health')} for x in data['data']['activeTargets']]
 ids=subprocess.run(['docker','ps','--quiet','--filter','label=com.docker.compose.service=prometheus'],capture_output=True,text=True,check=True).stdout.split();assert len(ids)==1;out['Prometheus_container_id']=ids[0]
 r=subprocess.run(['docker','inspect','--format','{{json .Mounts}}',ids[0]],capture_output=True,text=True,check=True);out['Prometheus_public_mounts']=[{'source':x['Source'],'destination':x['Destination'],'RW':x['RW']} for x in json.loads(r.stdout) if x['Destination']=='/etc/prometheus']
 for key,args in {'native_config_check':['docker','exec',ids[0],'/bin/promtool','check','config','/etc/prometheus/prometheus.yml'],'native_SD_help':['docker','exec',ids[0],'/bin/promtool','check','service-discovery','--help']}.items():
  r=subprocess.run(args,capture_output=True,text=True,timeout=20);out[key]={'exit':r.returncode,'stdout':r.stdout,'stderr':r.stderr}
print(json.dumps(out))
'''
D={'captured_at':datetime.datetime.now().astimezone().isoformat(),'roles':[],'live_changes':False}
for vmid,hostname in [(220,'publish-service'),(270,'ops-service')]:
 r=control.guest(vmid,'sudo -n python3 -B -c '+shlex.quote(CODE),data=json.dumps({'vmid':vmid,'hostname':hostname}).encode(),timeout=100,info=T[vmid]);assert r['exit_code']==0,('readonly capture failed',vmid,r['exit_code']);j=json.loads(r['stdout'])
 for f in j['files']:
  b=base64.b64decode(f.pop('body_b64'));assert hashlib.sha256(b).hexdigest()==f['sha256'];p=HERE/'baselines'/('vm'+str(vmid))/f['path'].lstrip('/');p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b);f['local_baseline']=str(p.relative_to(HERE))
 D['roles'].append(j);print(json.dumps({'vmid':vmid,'file_SHAs':{x['path']:x['sha256'] for x in j['files']},'Nexus_alias':j.get('Nexus_alias_validation'),'NexusHTTP':j.get('Nexus_local_status_http'),'Prometheus_target_count':len(j.get('Prometheus_targets',[]))}),flush=True)
(HERE/'live-source-inventory.json').write_text(json.dumps(D,ensure_ascii=False,indent=2)+'\n')
