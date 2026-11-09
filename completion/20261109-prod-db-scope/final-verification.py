#!/usr/bin/env python3
"""Final read-only scope/health checks; no SQL, credential or archive content export."""
import concurrent.futures,json,sys,datetime
from pathlib import Path
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts'));import control
HOST=r'''import json,subprocess,pathlib,datetime
read=lambda a:subprocess.check_output(a,text=True,timeout=30)
job=json.loads(read(['pvesh','get','/cluster/backup/dell-local-nightly','--output-format','json']))
v=json.loads(read(['pvesh','get','/cluster/resources','--output-format','json']));v=[{'vmid':x['vmid'],'status':x.get('status'),'template':x.get('template',0)}for x in v if x['type']in['qemu','lxc']]
timer=dict(l.split('=',1)for l in read(['systemctl','show','dell-prod-db-backup.timer','--property=ActiveState,SubState,UnitFileState,NextElapseUSecRealtime']).splitlines()if '='in l)
u=dict(l.split('=',1)for l in read(['systemctl','show','dell-prod-db-backup.service','--property=ActiveState,SubState,Result,ExecMainStatus']).splitlines()if '='in l)
s=json.loads(pathlib.Path('/var/lib/dell-prod-db-backup/status.json').read_text())
print(json.dumps({'at':datetime.datetime.now().astimezone().isoformat(),'old_whole_VM_job_enabled':job['enabled'],'new_timer':timer,'new_unit':u,'new_status':s,'running_VMIDs':sorted(x['vmid']for x in v if not x['template']and x['status']=='running'),'stopped_templates':sorted(x['vmid']for x in v if x['template']and x['status']=='stopped'),'failed_units':read(['systemctl','--failed','--plain','--no-legend','--no-pager']).splitlines(),'forwarding_all0':all(p.read_text().strip()=='0'for p in pathlib.Path('/proc/sys/net').glob('ipv[46]/conf/*/forwarding')),'EDAC_all0':all(p.read_text().strip()=='0'for p in pathlib.Path('/sys/devices/system/edac/mc').glob('mc*/[cu]e_count'))}))'''
OPS=r'''import json,urllib.request,urllib.parse,subprocess,datetime
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def get(port,path):
 with op.open('http://192.168.19.70:'+str(port)+path,timeout=8)as r:return json.load(r)
m={}
for n in ['enabled','state_valid','running','last_run_success','last_success_timestamp_seconds','archive_bytes']:
 m[n]=[float(v['value'][1])for v in get(9090,'/api/v1/query?'+urllib.parse.urlencode({'query':'dell_prod_db_backup_'+n}))['data']['result']]
t=get(9090,'/api/v1/targets')['data']['activeTargets'];groups=get(9090,'/api/v1/rules')['data']['groups'];backup=[{'name':g['name'],'rules':[{'name':r['name'],'health':r['health'],'state':r.get('state')}for r in g['rules']]}for g in groups if 'backup'in g['name']]
print(json.dumps({'at':datetime.datetime.now().astimezone().isoformat(),'metrics':m,'backup_groups':backup,'targets_count':len(t),'targets_UP':sum(x['health']=='up'for x in t),'Prom_alerts':len(get(9090,'/api/v1/alerts')['data']['alerts']),'AM_alerts':len(get(9093,'/api/v2/alerts')),'Lark_unit_active':subprocess.run(['systemctl','is-active','--quiet','dell-lark-notify.service']).returncode==0,'notification_test_sent':False}))'''
info=json.loads((ROOT/'completion/20261109/ops-audit.json').read_text())['target']
def ops():
 r=control.guest(270,'sudo -n python3 -I -B -',data=OPS.encode(),info=info,timeout=70);assert r['exit_code']==0;return json.loads(r['stdout'])
with concurrent.futures.ThreadPoolExecutor(max_workers=2)as pool:
 hp=pool.submit(control.pve,'python3 -I -B -',data=HOST.encode(),timeout=70);op=pool.submit(ops);h=json.loads(hp.result());o=op.result()
m=o['metrics'];source=json.loads((ROOT/'completion/20261109-prod-db-scope/source-postcheck.json').read_text())
checks={'whole_VM_job_disabled':h['old_whole_VM_job_enabled']==0,'new_DB_timer_active_enabled':h['new_timer']['ActiveState']=='active'and h['new_timer']['UnitFileState']=='enabled','new_DB_task_success_exit0':h['new_unit']['Result']=='success'and h['new_unit']['ExecMainStatus']=='0'and h['new_status']['status']=='success','source_exactly_VM200_nacos_prod':h['new_status']['source_vmid']==200 and h['new_status']['databases']==['nacos_prod'],'12running3templates':h['running_VMIDs']==[100,190,200,201,210,220,221,230,240,250,260,270]and h['stopped_templates']==[9001,9010,9011],'no_failed_host_units':not h['failed_units'],'forward0_and_EDAC0':h['forwarding_all0']and h['EDAC_all0'],'DB_metrics_valid_success':all(m[n]==[v]for n,v in {'enabled':1,'state_valid':1,'running':0,'last_run_success':1,'archive_bytes':3301}.items()),'one_DB_only_backup_rule_group':len(o['backup_groups'])==1 and o['backup_groups'][0]['name']=='dell-prod-db-backup'and len(o['backup_groups'][0]['rules'])==3 and all(r['health']=='ok'and r['state']=='inactive'for r in o['backup_groups'][0]['rules']),'targets15UP_noalerts':o['targets_count']==o['targets_UP']==15 and o['Prom_alerts']==o['AM_alerts']==0,'Lark_active_no_test_send':o['Lark_unit_active']and not o['notification_test_sent'],'source_postcheck':source['all_passed']}
d={'at':datetime.datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),'scope':'production DB/Nacos logical backup only; no restore/migration/external SQL export','status':'passed'if all(checks.values())else'failed','checks':checks,'PVE':h,'Ops':o};(ROOT/'completion/20261109-prod-db-scope/final-verification.json').write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'status':d['status'],'checks':checks},indent=2));raise SystemExit(not all(checks.values()))
