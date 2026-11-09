#!/usr/bin/env python3
"""One-time final metadata/health evidence. No credentials or app payload reads."""
import concurrent.futures,datetime,json,sys
from pathlib import Path
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts'));import control
PVE=r'''import json,pathlib,subprocess
from datetime import datetime

def out(args):return subprocess.check_output(args,text=True,timeout=30)
def api(path):return json.loads(out(['pvesh','get',path,'--output-format','json']))
r=api('/cluster/resources');v=[{k:x.get(k) for k in ['vmid','type','status','template','name','maxmem','maxcpu']} for x in r if x['type']in['qemu','lxc']]
forward={str(p):p.read_text().strip() for p in pathlib.Path('/proc/sys/net').glob('ipv[46]/conf/*/forwarding')};forward['ip_forward']=pathlib.Path('/proc/sys/net/ipv4/ip_forward').read_text().strip()
print(json.dumps({'at':datetime.now().astimezone().isoformat(),'instances':v,'forwarding_all0':all(x=='0'for x in forward.values()),'nft_tables':out(['nft','list','tables']).splitlines(),'EDAC':{str(p):int(p.read_text().strip()) for p in pathlib.Path('/sys/devices/system/edac/mc').glob('mc*/[cu]e_count')},'failed_units':out(['systemctl','--failed','--plain','--no-legend','--no-pager']).splitlines(),'iperf':out(['systemctl','show','iperf3.service','--property=ActiveState,UnitFileState']).splitlines(),'storage':[{k:x.get(k) for k in ['storage','active','enabled','total','avail','used','content']}for x in api('/nodes/pve/storage')],'native_backup_job':api('/cluster/backup/dell-local-nightly'),'pvescheduler':out(['systemctl','show','pvescheduler.service','--property=ActiveState,SubState']).splitlines(),'listener5201':bool(out(['ss','-Hltn','sport = :5201']).strip())}))'''
OPS=r'''import json,subprocess,urllib.request,urllib.parse,time
from datetime import datetime
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def get(port,path):
 with op.open('http://192.168.19.70:'+str(port)+path,timeout=8)as r:return json.load(r)
def q(expr):return get(9090,'/api/v1/query?'+urllib.parse.urlencode({'query':expr}))['data']['result']
metrics={}
for n in ['enabled','state_valid','running','last_run_success','verified_guest_count','last_success_timestamp_seconds','current_run_state']:
 rows=q('dell_pve_local_backup_'+n);metrics[n]=[{'value':float(r['value'][1]),'sample_at':r['value'][0]}for r in rows]
t=get(9090,'/api/v1/targets')['data']['activeTargets'];rules=get(9090,'/api/v1/rules')['data']['groups'];names=[{'name':r['name'],'health':r.get('health'),'state':r.get('state')}for g in rules if g['name']=='dell-pve-local-backup' for r in g['rules']]
print(json.dumps({'at':datetime.now().astimezone().isoformat(),'read_only':True,'targets':{'count':len(t),'UP':sum(x['health']=='up' for x in t),'max_scrape_age_seconds':max(time.time()-__import__('datetime').datetime.fromisoformat(x['lastScrape'].replace('Z','+00:00')).timestamp() for x in t)},'backup_metrics':metrics,'backup_rules':names,'Prom_alert_count':len(get(9090,'/api/v1/alerts')['data']['alerts']),'AM_alert_count':len(get(9093,'/api/v2/alerts')),'AM_groups':len(get(9093,'/api/v2/alerts/groups')),'Lark_unit':subprocess.check_output(['systemctl','show','dell-lark-notify.service','--property=ActiveState,SubState'],text=True).splitlines(),'containers':subprocess.check_output(['docker','ps','--format','{{.Names}} {{.Status}}'],text=True).splitlines(),'real_notification_test_sent':False}))'''
ACCESS=json.loads((ROOT/'evidence/implementation/private-guest-access.json').read_text())
# The source is a list of public address/host-key metadata; never SSH trust-on-first-use.
if isinstance(ACCESS,list):ACCESS={str(x['vmid']):x for x in ACCESS}
if isinstance(ACCESS,dict) and '270'not in ACCESS:
 rows=ACCESS.get('roles',ACCESS.get('guests',ACCESS.get('targets',[])))
 if isinstance(rows,list):ACCESS={str(x.get('target',x)['vmid']):x.get('target',x) for x in rows}
def run_ops():
 row=ACCESS['270'];row=row.get('target',row)
 r=control.guest(270,'sudo -n python3 -B -',data=OPS.encode(),info=row,timeout=70)
 assert r['exit_code']==0,'Ops metadata check failed; raw output withheld'
 return json.loads(r['stdout'])
with concurrent.futures.ThreadPoolExecutor(max_workers=2)as pool:
 hp=pool.submit(control.pve,'python3 -B -',data=PVE.encode(),timeout=70);op=pool.submit(run_ops)
 result={'at':datetime.datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),'scope':'final metadata and health only; no application contents/restore/migration','PVE':json.loads(hp.result()),'Ops':op.result()}
required=[100,190,200,201,210,220,221,230,240,250,260,270];v=result['PVE']['instances'];m=result['Ops']['backup_metrics']
checks={'12running3templates':sorted(x['vmid']for x in v if not x.get('template')and x['status']=='running')==required and sorted(x['vmid']for x in v if x.get('template')and x['status']=='stopped')==[9001,9010,9011],'host_forward0':result['PVE']['forwarding_all0'],'EDAC0':all(x==0 for x in result['PVE']['EDAC'].values()),'no_failed_host_units':not result['PVE']['failed_units'],'no_iperf_listener':not result['PVE']['listener5201'],'job_enabled':result['PVE']['native_backup_job']['enabled']==1,'targets15UP':result['Ops']['targets']['count']==15 and result['Ops']['targets']['UP']==15,'backup_metrics_valid_success11':all(len(m[n])==1 and m[n][0]['value']==value for n,value in {'enabled':1,'state_valid':1,'running':0,'last_run_success':1,'verified_guest_count':11}.items()),'three_rules_loaded_healthy_inactive':len(result['Ops']['backup_rules'])==3 and all(r['health']=='ok' and r['state']=='inactive'for r in result['Ops']['backup_rules']),'no_active_alerts':result['Ops']['Prom_alert_count']==result['Ops']['AM_alert_count']==result['Ops']['AM_groups']==0}
result['checks']=checks;result['status']='passed'if all(checks.values())else'failed'
(ROOT/'completion/20261109/final-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'status':result['status'],'checks':checks},ensure_ascii=False,indent=2));raise SystemExit(result['status']!='passed')
