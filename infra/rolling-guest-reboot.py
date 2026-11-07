#!/usr/bin/env python3
"""Fixed-scope normal guest reboot acceptance. No PVE power/config changes."""
import sys,json,time,datetime,subprocess
from pathlib import Path
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'));import control
E=ROOT/'evidence/implementation/rolling-guest-reboot-acceptance.json'
D=json.loads(E.read_text()); PRE={x['vmid']:x for x in D['preflight']}; ACCESS={x['target']['vmid']:x['target'] for x in json.loads((ROOT/'evidence/implementation/private-guest-access.json').read_text())['roles']}
def now():return datetime.datetime.now(ZoneInfo('Asia/Shanghai')).isoformat()
def save():
 p=E.with_suffix('.tmp');p.write_text(json.dumps(D,ensure_ascii=False,indent=2)+'\n');p.replace(E)
def call(v,code,timeout=65):
 r=control.guest(v,'sudo -n python3 -',data=code.encode(),timeout=timeout,info=ACCESS[v])
 if r['exit_code']:return {'probe_ok':False,'exit_code':r['exit_code'],'stderr_present':bool(r['stderr'])}
 try:return json.loads(r['stdout'])
 except Exception:return {'probe_ok':False,'exit_code':r['exit_code'],'invalid_json':True}
REMOTE=r'''
import os,json,subprocess,socket,pathlib,pwd,re,urllib.request,time,hashlib
V=VMID;P=PREVIOUS
def run(a):return subprocess.run(a,capture_output=True,text=True,timeout=35)
def unit(n):return dict(x.split('=',1) for x in run(['systemctl','show',n,'-p','LoadState','-p','ActiveState','-p','SubState','-p','MainPID']).stdout.splitlines() if '=' in x)
def get(url):
 with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(url,timeout=5) as r:return r.status,r.read(1000000)
try:
 host=socket.gethostname();assert host==P['hostname'] and not pathlib.Path('/etc/pve').exists()
 ip=[a['local'] for i in json.loads(run(['ip','-j','-4','addr']).stdout) for a in i.get('addr_info',[])];assert EXPECTED_ADDRESS in ip
 fp=run(['ssh-keygen','-lf','/etc/ssh/ssh_host_ed25519_key.pub']).stdout.split()[1];assert fp==P['host_key_fingerprint']
 fs=json.loads(run(['findmnt','-J','-t','ext4,xfs,btrfs','-o','TARGET,SOURCE,UUID,FSTYPE,OPTIONS']).stdout)['filesystems']
 def uu(rows):
  out={}
  for x in rows:out[x['target']]=x['uuid'];out.update(uu(x.get('children',[])))
  return out
 assert uu(fs)==uu(P['filesystems'])
 ntp=dict(x.split('=',1) for x in run(['timedatectl','show','-p','NTPSynchronized','-p','NTP','-p','Timezone']).stdout.splitlines() if '=' in x)
 units={n:unit(n) for n in P['units']};failed=[x.split()[0] for x in run(['systemctl','list-units','--state=failed','--no-legend','--plain','--no-pager']).stdout.splitlines() if x.strip()]
 out={'probe_ok':True,'hostname':host,'ipv4':ip,'boot_id':pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'machine_id':pathlib.Path('/etc/machine-id').read_text().strip(),'host_key_fingerprint':fp,'filesystems':fs,'ntp':ntp,'units':units,'failed_units':failed,'strict_ub_ssh':True,'health_ok':False}
 historical_preboot=(V==270 and out['boot_id']==P['boot_id'] and failed==['dell-ops-first-deploy.service'] and unit('dell-ops.service')['ActiveState']=='active')
 ok=all(x['ActiveState']=='active' for x in units.values()) and ntp['NTPSynchronized']=='yes' and (not failed or historical_preboot)
 if V in [230,231,232]:
  uid=pwd.getpwnam('finger').pw_uid;r=run(['runuser','-u','finger','--','env','-i','PATH=/usr/bin:/bin','/opt/finger/java/bin/java','-version']);act=run(['systemctl','list-units','--type=service','--state=active','--no-legend','dell-finger-*']).stdout.strip()
  out['nonroot_java']={'uid':uid,'exit_code':r.returncode,'version':re.search(r'"([^"]+)"',r.stderr).group(1) if r.returncode==0 else None};out['active_business_units']=bool(act);ok=ok and uid!=0 and r.returncode==0 and not act
 if V==220:
  k=pathlib.Path('/var/lib/dell-publisher/.ssh/test240_ed25519');st=k.stat();f=run(['ssh-keygen','-lf',str(k)+'.pub']).stdout.split()[1];r=run(['runuser','-u','publisher','--','/usr/local/bin/dell-publish','status']);fr=json.loads(r.stdout) if r.returncode==0 else {};payload=fr.get('result',fr.get('data',{}))
  out['publisher']={'status_exit_code':r.returncode,'frame_ok':fr.get('ok'),'payload':payload,'key_mode':oct(st.st_mode&0o777),'key_owner':pwd.getpwuid(st.st_uid).pw_name,'key_fingerprint':f,'private_key_contents_read':False}
  ok=ok and r.returncode==0 and fr.get('ok') and not payload.get('busy',True) and payload.get('current_release')=='20261106T121030' and all(x['health_up'] and x['systemd_active'] for x in payload.get('services',[])) and len(payload.get('services',[]))==5 and f==P['publisher']['key_fingerprint'] and oct(st.st_mode&0o777)=='0o600' and pwd.getpwuid(st.st_uid).pw_name=='publisher'
 if V in [200,201,210,270]:
  path={200:'/opt/dell/data/prod-db',201:'/opt/dell/data/prod-infra',210:'/opt/dell/data/test-data',270:'/opt/dell/ops'}[V];r=run(['python3',path+'/scripts/manage.py','health']);out['manager_health_exit_code']=r.returncode
  if r.returncode==0:out['manager_health']=json.loads(r.stdout)
  ok=ok and r.returncode==0
  if V==270 and r.returncode==0:
   targets=json.loads(get('http://10.63.30.40:9090/api/v1/targets')[1])['data']['activeTargets'];out['targets']=[{'job':x.get('labels',{}).get('job'),'instance':x.get('labels',{}).get('instance'),'health':x.get('health')} for x in targets]
   vals=json.loads(get('http://10.63.30.40:9090/api/v1/query?query=dell_pve_collector_timestamp_seconds')[1])['data']['result'];ages=[round(time.time()-float(x['value'][1]),1) for x in vals];out['pve_collector_age_seconds']=ages
   ok=ok and len(targets)==17 and all(x['health']=='up' or '10.63.30.30' in x['instance'] for x in out['targets']) and bool(ages) and all(-5<=a<=180 for a in ages)
 if V==240:
  names=['finger-service-system','finger-service-coms','finger-auth','finger-bff-system','finger-gateway-mobile'];ports=[10210,10202,10000,10104,9999];out['java_health']=[];out['current_release']=pathlib.Path('/opt/finger/current-test').resolve().name;out['config_credentials']=[]
  for name,port in zip(names,ports):
   try:status,body=get('http://10.63.20.20:'+str(port)+'/actuator/health');h=status==200 and json.loads(body).get('status')=='UP'
   except Exception:h=False
   st=(pathlib.Path('/opt/finger/releases/test/20261106T121030')/name/'application.yaml').stat();u='dell-finger-'+name+'.service';lc=run(['systemctl','show',u,'-p','LoadCredential','--value']).stdout.strip();usr=run(['systemctl','show',u,'-p','User','--value']).stdout.strip();out['java_health'].append({'service':name,'health_up':h});out['config_credentials'].append({'service':name,'mode':oct(st.st_mode&0o777),'uid':st.st_uid,'gid':st.st_gid,'loadcredential_present':bool(lc),'unit_user':usr});ok=ok and h and st.st_uid==0 and st.st_gid==0 and st.st_mode&0o777==0o600 and bool(lc) and usr=='finger'
  png=pathlib.Path('/var/lib/finger/finger-service-coms/uploads/image/2026-11/3c7ab7b6a351437db6504ef0da21856b.png');out['retained_fixture_sha256']=hashlib.sha256(png.read_bytes()).hexdigest();ok=ok and out['current_release']=='20261106T121030' and out['retained_fixture_sha256']=='45add9f27a1f9f4c770d173cec808f6772c31381b036ff136b7593796fec1989'
 if V==260:
  out['nas_http']={}
  for name,url in [('omv','http://10.63.40.10/'),('jellyfin','http://10.63.40.10:8096/health')]:
   try:s,b=get(url);out['nas_http'][name]={'status':s,'healthy':s==200 and (name=='omv' or b.strip()==b'Healthy')}
   except Exception:out['nas_http'][name]={'healthy':False}
  try:
   with socket.create_connection(('10.63.40.10',445),timeout=5):out['smb_tcp445']=True
  except Exception:out['smb_tcp445']=False
  out['smb_retained_fixtures']=[]
  for share in ['media','games','incoming']:
   r=subprocess.run(['smbclient','//127.0.0.1/'+share,'-A','/root/private/dell-nas/acceptance/reader.auth','-m','SMB3','-c','get dell-acceptance-'+share+'.bin -'],capture_output=True,timeout=20)
   expected=hashlib.sha256(bytes(range(256))*4096).hexdigest();out['smb_retained_fixtures'].append({'share':share,'read_exit_code':r.returncode,'bytes':len(r.stdout),'sha256_matches':hashlib.sha256(r.stdout).hexdigest()==expected,'writes_performed':False})
  ok=ok and all(x['healthy'] for x in out['nas_http'].values()) and out['smb_tcp445'] and all(x['read_exit_code']==0 and x['sha256_matches'] for x in out['smb_retained_fixtures'])
 out['health_ok']=bool(ok);print(json.dumps(out))
except Exception as e:print(json.dumps({'probe_ok':False,'exception_class':type(e).__name__}))
'''
def probe(v):return call(v,REMOTE.replace('VMID',str(v)).replace('PREVIOUS',repr(PRE[v])).replace('EXPECTED_ADDRESS',repr(ACCESS[v]['ip'])))
def healthy(v,budget=420):
 end=time.monotonic()+budget;tries=0;last={}
 while time.monotonic()<end:
  tries+=1
  try:last=probe(v)
  except (subprocess.TimeoutExpired,OSError) as e:last={'probe_ok':False,'exception_class':type(e).__name__}
  if last.get('health_ok'):return last,tries
  time.sleep(8)
 return last,tries
if __name__=='__main__':
 for v in map(int,sys.argv[1:]):
  assert v in [230,231,232,220,270,200,201,210,240,260]
  assert not any(x['vmid']==v for x in D['reboots']),'refuse repeat reboot'
  before=probe(v)
  if not before.get('health_ok'):
   D.update(status='stopped-pre-reboot-health',failed_vmid=v);D['last_probe']=before;save();print(json.dumps({'vmid':v,'status':D['status'],'metadata':before}),flush=True);sys.exit(1)
  row={'vmid':v,'started_at':now(),'before':before,'reboot_command':'sudo -n systemctl reboot','status':'issuing-normal-reboot'};D['reboots'].append(row);D['status']='rolling-in-progress';save()
  try:r=control.guest(v,'sudo -n systemctl reboot',timeout=25,info=ACCESS[v]);row['reboot_transport_exit_code']=r['exit_code'];row['reboot_transport_stderr_present']=bool(r['stderr'])
  except subprocess.TimeoutExpired:row['reboot_transport_timeout']=True
  save();time.sleep(6)
  after,tries=healthy(v);row['after']=after;row['health_probe_attempts']=tries
  passed=after.get('health_ok') and after.get('boot_id')!=before['boot_id'] and after.get('machine_id')==before['machine_id']
  if passed and v in [200,210]:
   dep=201 if v==200 else 240;depafter,n=healthy(dep);row['dependent_guest_health']={'vmid':dep,'attempts':n,'result':depafter};passed=bool(depafter.get('health_ok'))
  row['completed_at']=now();row['status']='passed' if passed else 'stopped-after-reboot';D['status']='batch-passed' if passed else 'stopped-after-reboot';save();print(json.dumps({'vmid':v,'status':row['status'],'boot_changed':after.get('boot_id')!=before['boot_id'],'health_probes':tries,'failed_units':after.get('failed_units')}),flush=True)
  if not passed:sys.exit(1)
