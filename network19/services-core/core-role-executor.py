#!/usr/bin/env python3
"""Prepared Data/Ops per-role window executor; default inspect, no OS/PVE or bootstrap."""
import argparse,datetime,hashlib,json,os,socket,stat,subprocess,sys,time,urllib.request
from pathlib import Path
ROLES={200:('data-prod-db','dell-data-prod-db.service',['mysql'],'192.168.19.10'),201:('data-prod-infra','dell-data-prod-infra.service',['nacos','redis','rabbitmq'],'192.168.19.11'),210:('data-test','dell-data-test-data.service',['mysql','nacos','redis','rabbitmq'],'192.168.19.20'),270:('ops-service','dell-ops.service',['prometheus','grafana','alertmanager','blackbox'],'192.168.19.70')}
D=['docker','--host','unix:///var/run/docker.sock']
class Refused(RuntimeError):pass

def run(args,check=True,timeout=30):
 p=subprocess.run(args,capture_output=True,text=True,timeout=timeout)
 if check and p.returncode:raise Refused('fixed-role-operation-failed:'+args[0])
 return p

def rootfile(path):
 if path.resolve()!=path or not path.is_file() or path.stat().st_uid!=0 or path.stat().st_mode&0o077:raise Refused('root600-window-required')
 return json.loads(path.read_text())
def state(unit):
 p=run(['systemctl','show',unit,'--property=ActiveState,SubState,MainPID'],check=False);return dict(l.split('=',1) for l in p.stdout.splitlines() if '=' in l)
def containers(vmid,services):
 prefix={200:'dell-data-prod-db',201:'dell-data-prod-infra',210:'dell-data-test-data',270:'dell-ops'}[vmid];rows=[]
 fmt='{"id":{{json .Id}},"name":{{json .Name}},"running":{{json .State.Running}},"status":{{json .State.Status}},"health":{{if (index .State "Health")}}{{json .State.Health.Status}}{{else}}null{{end}},"image":{{json .Image}}}'
 for service in services:
  name=prefix+'-'+service+'-1';p=run(D+['inspect','--format',fmt,name],check=False)
  if p.returncode:rows.append({'name':'/'+name,'running':False,'missing':True})
  else:rows.append(json.loads(p.stdout))
 return rows

def main():
 p=argparse.ArgumentParser();p.add_argument('--vmid',type=int,choices=ROLES,required=True);p.add_argument('--action',choices=['inspect','quiesce','commit-start','health','rollback-after-old-OS'],default='inspect');p.add_argument('--contract-dir',type=Path,required=True);p.add_argument('--root-receipt',type=Path);a=p.parse_args();role,unit,services,newip=ROLES[a.vmid]
 if os.geteuid()!=0 or Path('/etc/pve').exists() or socket.gethostname().split('.')[0]!=role:raise Refused('assigned-role-root-only')
 folder=a.contract_dir;recipe=next(x for x in json.loads((folder/'data-ops-patch-contract.json').read_text())['files'] if x['vmid']==a.vmid and x['path'].endswith('/.env'));active=Path(recipe['path']);oldip=recipe['exact_env_keys']['SERVICE_IP']['old']
 if a.action=='inspect':print(json.dumps({'status':'inspected-no-write','vmid':a.vmid,'unit':unit,'unit_state':state(unit),'containers':containers(a.vmid,services),'expected_services':services,'network_migrated_by_this_tool':False}));return
 if a.root_receipt is None:raise Refused('explicit-role-window-required')
 receipt=rootfile(a.root_receipt)
 if receipt.get('migration')!='network19' or receipt.get('vmid')!=a.vmid or receipt.get('action')!=a.action or receipt.get('parent_window_open') is not True:raise Refused('root-role-action-window-mismatch')
 if a.action=='quiesce':
  run(['systemctl','stop',unit],timeout=200)
  rows=containers(a.vmid,services)
  if any(x['running'] for x in rows) or state(unit).get('ActiveState')=='active':raise Refused('role-not-fully-quiesced')
  print(json.dumps({'status':'quiesced','vmid':a.vmid,'unit':unit,'expected_containers_stopped':len(rows),'data_deleted_or_OS_changed':False,'Nacos_bootstrap_or_notifications_run':False}));return
 if a.action=='rollback-after-old-OS':
  addresses=json.loads(run(['ip','-j','addr']).stdout)
  if not any(x.get('local')==oldip for r in addresses for x in r.get('addr_info',[])):raise Refused('root-old-OS-address-rollback-required-first')
  if state(unit).get('ActiveState')=='active' or any(x['running'] for x in containers(a.vmid,services)):raise Refused('quiesce-before-rollback')
  old=Path('/root/dell-network19/service-env')/str(a.vmid)/'old.env'
  if hashlib.sha256(old.read_bytes()).hexdigest()!=recipe['source_sha256']:raise Refused('old-env-backup-integrity')
  tmp=active.with_name('.network19-env-rollback');tmp.write_bytes(old.read_bytes());tmp.chmod(0o600);os.replace(tmp,active)
 elif a.action=='commit-start':
  if state(unit).get('ActiveState')=='active' or any(x['running'] for x in containers(a.vmid,services)):raise Refused('root-must-quiesce-before-commit')
  # Reuse the narrowly gated env committer. Receipt is private, contains no secrets.
  gate=folder/('env-commit-'+str(a.vmid)+'.json');gate.write_text(json.dumps({'migration':'network19','vmid':a.vmid,'phase':'commit-active','parent_window_open':True}));gate.chmod(0o600)
  p=run(['python3','-I','-B',str(folder/'stage-commit-env.py'),'--vmid',str(a.vmid),'--contract-dir',str(folder),'--mode','commit-active','--root-receipt',str(gate)],timeout=45)
  result=json.loads(p.stdout)
  if result.get('status')!='env-committed-role-still-quiesced':raise Refused('private-env-commit-not-confirmed')
 if a.action in ['commit-start','rollback-after-old-OS']:
  run(['systemctl','reset-failed',unit],check=False);run(['systemctl','start',unit],timeout=60)
 expected_ip=oldip if a.action=='rollback-after-old-OS' else newip;deadline=time.monotonic()+360
 while time.monotonic()<deadline:
  rows=containers(a.vmid,services)
  if len(rows)==len(services) and all(x.get('running') and x.get('health')=='healthy' for x in rows):break
  if state(unit).get('ActiveState')=='failed':raise Refused('role-supervisor-failed')
  time.sleep(3)
 else:raise Refused('role-health-deadline')
 if a.vmid in [201,210]:
  with urllib.request.build_opener(urllib.request.ProxyHandler({})).open('http://'+expected_ip+':8848/nacos/v1/console/health/readiness',timeout=5) as response:
   if response.status!=200:raise Refused('native-Nacos-readiness-not200')
 result={'status':'role-restored-healthy','vmid':a.vmid,'unit':unit,'all_containers_healthy':len(rows),'service_endpoint_new_network':a.action!='rollback-after-old-OS','Nacos_password_namespace_vhost_or_percent_accounts_modified':False,'formal_business_apps_started':False,'bootstrap_Nacos_run':False,'notifications_sent':False,'OS_PVE_or_other_guests_changed':False}
 path=folder/('role-'+str(a.vmid)+'-last-result.json');path.write_text(json.dumps(result,indent=2));path.chmod(0o600);print(json.dumps(result))
if __name__=='__main__':
 try:main()
 except Exception as e:print(json.dumps({'status':'refused-or-failed','error_category':type(e).__name__,'reason':str(e) if isinstance(e,Refused) else 'details-withheld','coordinated_root_rollback_may_be_required':True}));sys.exit(1)
