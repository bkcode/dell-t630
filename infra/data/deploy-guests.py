#!/usr/bin/env python3
"""Deploy only data guests200/201/210, validate auth and isolated restart persistence."""
import base64,datetime,hashlib,importlib.util,json,shlex,sys,time,urllib.parse
from pathlib import Path
from zoneinfo import ZoneInfo
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[2]
E=ROOT/'evidence/implementation'
SCOPE=[('prod-infra',201,'data-prod-infra')]  # 200 accepted; 210 explicitly delegated to another agent

def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
control=load('dell_control',ROOT/'scripts/control.py')
transfer=load('data_transfer',ROOT/'infra/data/secure-transfer.py')

def now():return datetime.datetime.now(ZoneInfo('Asia/Shanghai')).isoformat()
def save(path,value):
 tmp=path.with_suffix(path.suffix+'.tmp');tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n');tmp.replace(path)

def sanitizer(role):
 bundle=ROOT/'private/data/bundles'/role
 values=[p.read_text().strip() for p in (bundle/'secrets').iterdir() if p.is_file() and p.name!='rabbit-definitions.json']
 env=dict(x.split('=',1) for x in (bundle/'.env').read_text().splitlines() if x)
 users=['root','nacos',env.get('RABBIT_ADMIN_USER',''),env.get('RABBIT_APP_USER',''),env.get('NACOS_CLIENT_USER','')]
 expanded=set(values)
 for value in values:
  expanded.add(urllib.parse.quote(value,safe=''))
  for user in users:expanded.add(base64.b64encode((user+':'+value).encode()).decode())
 def redact(value):
  if isinstance(value,str):
   for secret in sorted(expanded,key=len,reverse=True):
    if secret:value=value.replace(secret,'[REDACTED]')
   return value
  if isinstance(value,dict):return {k:redact(v) for k,v in value.items()}
  if isinstance(value,list):return [redact(v) for v in value]
  return value
 return redact

SNAPSHOT=r'''import subprocess,json,socket
from pathlib import Path
role=ROLE
base=Path('/opt/dell/data')/role
def run(a):
 p=subprocess.run(a,capture_output=True,text=True,timeout=40)
 if p.returncode:raise SystemExit('read-only data snapshot prerequisite failed')
 return p.stdout
c=['docker','--host','unix:///var/run/docker.sock','compose','--env-file',str(base/'.env'),'-f',str(base/'compose.yaml')]
ids=run(c+['ps','--all','--quiet']).split()
values=[]
if ids:
 raw=json.loads(run(['docker','--host','unix:///var/run/docker.sock','inspect',*ids]))
 for d in raw:
  values.append({'service':d['Config']['Labels']['com.docker.compose.service'],'container_id':d['Id'],'image':d['Config']['Image'],'state':d['State']['Status'],'health':d['State'].get('Health',{}).get('Status'),'started_at':d['State']['StartedAt'],'pid':d['State']['Pid'],'restart_policy':d['HostConfig']['RestartPolicy']['Name']})
print(json.dumps({'hostname':socket.gethostname().split('.')[0],'product_uuid':Path('/sys/class/dmi/id/product_uuid').read_text().strip().lower(),'mount':json.loads(run(['findmnt','--json','--mountpoint','/srv/dell-data','--output','TARGET,SOURCE,UUID,FSTYPE,OPTIONS'])),'containers':values}))'''

def main():
 if sys.argv[1:]!=['--finish-authorized-201-live']:raise SystemExit('current agent scope is only --finish-authorized-201-live; 200 accepted, 210 delegated')
 access=json.loads((E/'private-guest-access.json').read_text());rows={x['target']['vmid']:x for x in access['roles']}
 pre=json.loads((E/'data-private-preflight.json').read_text());pre={x['vmid']:x for x in pre['roles']}
 report={'started_at':now(),'scope':'data-guests-only-private-network','vmids':[201],'already_verified_vmids':[200],'delegated_vmids':[210],'source_business_data_imported':False,'source_mac_services_modified':False,'cf_backup_accessed_or_exported':False,'host_network_mutated':False,'status':'running','roles':[json.loads((E/'data-deploy-vm200.json').read_text())]}
 path=E/'data-deployment-acceptance.json';save(path,report)
 for role,vmid,guest_name in SCOPE:
  entry={'role':role,'vmid':vmid,'started_at':now(),'steps':[]};report['roles'].append(entry);redact=sanitizer(role)
  try:
   row=rows[vmid];target=row['target']
   if row['status']!='ssh-verified' or row['name']!=guest_name or target['ip']!=transfer.ROLES[role]['ip']:raise RuntimeError('private access proof does not match assigned data guest')
   def step(name,command,data=None,timeout=120):
    print(json.dumps({'role':role,'vmid':vmid,'stage':name}),flush=True)
    result=control.guest(vmid,command,data=data,timeout=timeout,info=target)
    safe=redact(result);entry['steps'].append({'name':name,'at':now(),'result':safe});save(path,report)
    if result['exit_code']:raise RuntimeError(name+' failed; sanitized guest result retained')
    return result['stdout']
   private=ROOT/'private/data/bundles'/role
   metadata=json.loads((private/'bundle.json').read_text())
   if metadata['data_filesystem_uuid']!=pre[vmid]['metadata']['mount']['filesystems'][0]['uuid']:raise RuntimeError('bundle UUID differs from measured filesystem')
   product=pre[vmid]['metadata']['product_uuid']
   entry['management_wait_fix_receipt']=json.loads((E/'data201-startup-wait-fix.json').read_text())
   entry['existing_live_stack_preserved']=True
   manager='/opt/dell/data/'+role+'/scripts/manage.py';accept='/opt/dell/data/'+role+'/scripts/acceptance.py'
   def call(name,script,action,timeout=600):return step(name,shlex.join(['sudo','-n','python3',script,action]),timeout=timeout)
   call('preflight-check',manager,'check',120)
   deployed=call('health-of-existing-live-stack',manager,'health',180);entry['initial_health']=json.loads(deployed.strip().splitlines()[-1])
   entry['auth_before_restart']=json.loads(call('real-auth-before-restart',accept,'auth',180))
   entry['existing_fixture_survived_fix']=json.loads(call('verify-existing-fixture-after-redis-fix',accept,'verify',180))
   before=json.loads(step('snapshot-before-restart','sudo -n python3 -',SNAPSHOT.replace('role=ROLE','role='+repr(role)).encode(),90));entry['before_restart']=before
   step('controlled-role-restart',shlex.join(['sudo','-n','systemctl','restart','dell-data-'+role+'.service']),timeout=240)
   # No blind redeploy: only wait for the intentionally restarted role to become healthy.
   waiter="import importlib.util,sys;sys.dont_write_bytecode=True;s=importlib.util.spec_from_file_location('m',"+repr(manager)+");m=importlib.util.module_from_spec(s);s.loader.exec_module(m);c=m.cfg();m.preflight(c);m.wait_healthy(startup_exit_grace=15);m.health(c)"
   entry['health_after_restart']=json.loads(step('health-after-controlled-restart','sudo -n python3 -c '+shlex.quote(waiter),timeout=480).strip().splitlines()[-1])
   after=json.loads(step('snapshot-after-restart','sudo -n python3 -',SNAPSHOT.replace('role=ROLE','role='+repr(role)).encode(),90));entry['after_restart']=after
   old={x['service']:x for x in before['containers']};new={x['service']:x for x in after['containers']}
   if set(old)!=set(new) or not old or any(old[n]['started_at']==new[n]['started_at'] for n in old) or any(x['restart_policy']!='no' or x['state']!='running' or x['health']!='healthy' for x in new.values()):raise RuntimeError('controlled restart/full service set evidence invalid')
   entry['auth_after_restart']=json.loads(call('real-auth-after-restart',accept,'auth',180))
   entry['persistence']=json.loads(call('verify-restart-persistence',accept,'verify',180))
   entry['cleanup']=json.loads(call('cleanup-owned-fixtures',accept,'cleanup',180))
   entry['final_health']=json.loads(call('final-infrastructure-health',manager,'health',180))
   entry.update(status='deployed-authenticated-restart-persistence-verified',finished_at=now(),source_business_data_imported=False,real_business_messages_sent=False)
   save(E/('data-deploy-vm'+str(vmid)+'.json'),redact(entry));save(path,redact(report))
   print(json.dumps({'vmid':vmid,'role':role,'status':entry['status']}),flush=True)
  except Exception as error:
   entry.update(status='failed-stopped-queue',error=redact(str(error)),finished_at=now());report.update(status='stopped-on-error',finished_at=now())
   save(E/('data-deploy-vm'+str(vmid)+'.json'),redact(entry));save(path,redact(report));print(json.dumps({'role':role,'status':entry['status'],'error':entry['error']}),flush=True);return 1
 report.update(status='prod-data200201-auth-persistence-verified-test210-delegated',finished_at=now());save(path,report)
 print(json.dumps({'status':report['status'],'vmids':[201],'already_verified_vmids':[200],'delegated_vmids':[210],'prod_business_import':False,'source_mac_modified':False}),flush=True);return 0

if __name__=='__main__':raise SystemExit(main())
