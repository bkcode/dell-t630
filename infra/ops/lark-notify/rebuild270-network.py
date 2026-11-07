#!/usr/bin/python3 -I
"""Reviewed first-install Ops-only static-network/secret transaction; never PVE."""
import argparse,base64,contextlib,hashlib,importlib.util,io,json,os,platform,socket,subprocess,sys,time,urllib.request,uuid
from pathlib import Path
OPS=Path('/opt/dell/ops');SERVICE='dell-ops.service';NAMES={'prometheus','alertmanager','grafana','blackbox'};IP={'prometheus':'172.18.0.2','alertmanager':'172.18.0.3','blackbox':'172.18.0.4','grafana':'172.18.0.5'}
EXPECTED_UUID='01b1f302-27be-4fbd-b4af-b8e782d85dea'
def call(args,timeout=120):
 r=subprocess.run(args,capture_output=True,timeout=timeout)
 if r.returncode:raise RuntimeError('fixed native action failed; output withheld')
 return r.stdout

def compose(*args,file=None):
 return call(['docker','--host','unix:///var/run/docker.sock','compose','--project-directory',str(OPS),'--env-file',str(OPS/'.env'),'-f',str(file or OPS/'compose.yaml'),*args])
def load_manager():
 file=OPS/'scripts/manage.py'
 if file.is_symlink() or file.stat().st_uid!=0 or file.stat().st_mode&0o022:raise RuntimeError('trusted root Ops manager required')
 s=importlib.util.spec_from_file_location('fixed_ops_manager_'+uuid.uuid4().hex,file);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def network(required=True):
 r=subprocess.run(['docker','--host','unix:///var/run/docker.sock','network','inspect','dell-ops_default'],capture_output=True,timeout=20)
 if r.returncode:
  if required:raise RuntimeError('Ops network missing')
  return None
 result=json.loads(r.stdout)
 if len(result)!=1:raise RuntimeError('Ops network ambiguous')
 n=result[0]
 if n['Driver']!='bridge' or n['IPAM']['Config']!=[{'Subnet':'172.18.0.0/16','Gateway':'172.18.0.1'}] or {x['Name'] for x in n.get('Containers',{}).values()}!={'dell-ops-'+name+'-1' for name in NAMES}:raise RuntimeError('network must contain exactly the four owned existing Ops endpoints')
 return n

def ready():
 m=load_manager();m.verify_data_mount(m.cfg());m.wait_healthy();op=urllib.request.build_opener(urllib.request.ProxyHandler({}));end=time.monotonic()+120
 while time.monotonic()<end:
  try:
   with op.open('http://10.63.30.40:9090/api/v1/targets',timeout=5) as r:targets=json.loads(r.read(4*1024*1024))['data']['activeTargets']
   with op.open('http://10.63.30.40:3000/api/health',timeout=5) as r:grafana=json.loads(r.read(4096))
   if len(targets)==17 and all(t.get('health')=='up' for t in targets) and grafana.get('database')=='ok':
    with contextlib.redirect_stdout(io.StringIO()):m.health(m.cfg())
    return {'containers':4,'targets_up':17,'targets_total':17,'grafana_database':'ok','grafana_admin_login':'passed'}
  except Exception:pass
  time.sleep(2)
 raise RuntimeError('four-service/17-target/Grafana readiness not restored')

def put(path,data,mode=0o600,uid=0,gid=0):
 if path.is_symlink() or path.resolve(strict=False)!=path:raise RuntimeError('symlink destination refused')
 temp=path.with_name(path.name+'.notify-new')
 if temp.is_symlink():raise RuntimeError('symlink temporary refused')
 fd=os.open(temp,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,mode)
 try:
  os.fchown(fd,uid,gid);os.fchmod(fd,mode)
  with os.fdopen(fd,'wb') as out:out.write(data);out.flush();os.fsync(out.fileno())
  os.replace(temp,path)
 finally:temp.unlink(missing_ok=True)

def validate_delta(before,after):
 if set(before['services'])!=NAMES or set(after['services'])!=NAMES:raise RuntimeError('exact four services required')
 old_global={k:v for k,v in before.items() if k not in ('services','secrets','networks')};new_global={k:v for k,v in after.items() if k not in ('services','secrets','networks')}
 if old_global!=new_global:raise RuntimeError('unapproved Compose global changes')
 for name in NAMES:
  old=dict(before['services'][name]);new=dict(after['services'][name]);old.pop('networks',None);links=new.pop('networks',None)
  if links!={'default':{'ipv4_address':IP[name]}}:raise RuntimeError('fixed existing address required')
  if name=='alertmanager':
   entries=new.pop('secrets',None)
   if entries not in ([{'source':'lark-bridge-token','target':'lark-bridge-token'}],[{'source':'lark-bridge-token','target':'/run/secrets/lark-bridge-token'}]) or old.get('secrets'):raise RuntimeError('only single new AM secret allowed')
  if old!=new or old.get('pids_limit')!=1024:raise RuntimeError('service image/resource/ports/volume/settings drift refused')
 n=after['networks']['default']
 if n.get('name')!='dell-ops_default' or n.get('driver')!='bridge' or n.get('ipam',{}).get('config')!=[{'subnet':'172.18.0.0/16','gateway':'172.18.0.1'}]:raise RuntimeError('existing CIDR/gateway must remain fixed')
 old=dict(before.get('secrets',{}));new=dict(after.get('secrets',{}));token=new.pop('lark-bridge-token',None)
 if old!=new or not token or token.get('file')!=str(OPS/'secrets/lark-bridge-token'):raise RuntimeError('unapproved secret/global changes')

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--reviewed-ops270-network-window',action='store_true');args=parser.parse_args()
 if not args.reviewed_ops270_network_window or os.geteuid()!=0 or platform.system()!='Linux' or platform.machine() not in ('x86_64','amd64') or Path('/etc/pve').exists() or socket.gethostname().split('.')[0]!='ops-service':raise RuntimeError('reviewed ops270 guest window required')
 if (OPS/'lark-notify-state.json').exists() or Path('/etc/systemd/system/dell-lark-notify.service').exists():raise RuntimeError('first-install only; notification owner already exists')
 old_manager=load_manager();c=old_manager.cfg();old_manager.preflight(c);mount=old_manager.verify_data_mount(c)
 if c.get('SERVICE_IP')!='10.63.30.40' or c.get('DATA_FS_UUID')!=EXPECTED_UUID:raise RuntimeError('fixed private guest and measured data UUID required')
 network();before_health=ready();before_model=json.loads(compose('config','--format','json'));old_compose=(OPS/'compose.yaml').read_bytes();old_code=(OPS/'scripts/manage.py').read_bytes()
 raw=sys.stdin.buffer.read(262145)
 if len(raw)>262144:raise RuntimeError('bounded private plan required')
 request=json.loads(raw)
 if set(request)!={'compose_b64','manager_b64','token_b64'}:raise RuntimeError('fixed payload fields required')
 new_compose=base64.b64decode(request['compose_b64'],validate=True);new_code=base64.b64decode(request['manager_b64'],validate=True);token=base64.b64decode(request['token_b64'],validate=True)
 import re
 if not re.fullmatch(rb'[A-Za-z0-9_-]{64}\n',token):raise RuntimeError('stable private token invalid')
 secret=OPS/'secrets/lark-bridge-token'
 if secret.exists() and secret.read_bytes()!=token:raise RuntimeError('existing token differs; silent rotation refused')
 put(secret,token,0o600,65534,65534)
 backup=Path('/root')/('dell-ops-network-before-'+uuid.uuid4().hex);backup.mkdir(mode=0o700);put(backup/'compose.yaml',old_compose);put(backup/'manage.py',old_code);pending=backup/'candidate-compose.yaml';put(pending,new_compose)
 after_model=json.loads(compose('config','--format','json',file=pending));validate_delta(before_model,after_model)
 # Prove all fixed images are locally available before stopping anything.
 for row in after_model['services'].values():
  image=json.loads(call(['docker','--host','unix:///var/run/docker.sock','image','inspect',row['image']]))
  if len(image)!=1 or image[0].get('Architecture')!='amd64':raise RuntimeError('fixed cached AMD64 images required')
 result={'status':'running','scope':'ops270-four-service-network-and-secret-only','before':before_health,'source_uuid':EXPECTED_UUID,'backup_directory':str(backup),'webhook_read':False,'messages_sent':False,'pve_modified':False,'data_volumes_removed':False}
 try:
  call(['systemctl','stop',SERVICE],timeout=240);compose('down','--timeout','90')
  put(OPS/'compose.yaml',new_compose,0o644);put(OPS/'scripts/manage.py',new_code,0o700)
  call(['systemctl','start',SERVICE]);result['after']=ready();n=network()
  for name,ip in IP.items():
   info=json.loads(call(['docker','--host','unix:///var/run/docker.sock','inspect','dell-ops-'+name+'-1']))[0]['NetworkSettings']['Networks']['dell-ops_default']
   if info.get('IPAddress')!=ip or info.get('IPAMConfig',{}).get('IPv4Address')!=ip:raise RuntimeError('runtime static address not applied')
  m=load_manager()
  if m.verify_data_mount(m.cfg())!=mount:raise RuntimeError('data mount identity changed')
  result.update(status='static-ops-network-and-secret-verified',static_addresses=IP,secret_mount='read-only /run/secrets/lark-bridge-token; content withheld')
 except BaseException:
  call(['systemctl','stop',SERVICE],timeout=240)
  try:compose('down','--timeout','90')
  except Exception:pass
  put(OPS/'compose.yaml',old_compose,0o644);put(OPS/'scripts/manage.py',old_code,0o700);call(['systemctl','start',SERVICE]);result['rollback']=ready();result['status']='failed-old-compose-restored-health-verified';print(json.dumps(result));return 1
 print(json.dumps(result));return 0
if __name__=='__main__':
 try:sys.exit(main())
 except Exception:print(json.dumps({'status':'failed','message':'fixed Ops transaction rejected/failed; raw output/secrets withheld'}));sys.exit(1)
