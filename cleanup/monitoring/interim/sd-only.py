#!/usr/bin/env python3
"""Future explicit-execute SD-only12->10 transaction. Never stops any service or VM."""
import sys,json,shlex,hashlib,base64,uuid,argparse
from pathlib import Path
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];sys.path.insert(0,str(ROOT/'scripts'));import control
M=json.loads((HERE/'manifest.json').read_text());T=next(x['target'] for x in json.loads((ROOT/'evidence/implementation/private-guest-access.json').read_text())['roles'] if x['target']['vmid']==270)
REMOTE=r'''
import sys,json,pathlib,os,socket,hashlib,subprocess,urllib.request,time,stat,tempfile
p=json.load(sys.stdin);assert os.geteuid()==0 and socket.gethostname()=='ops-service' and not pathlib.Path('/etc/pve').exists();target=pathlib.Path('/opt/dell/ops/config/prometheus/targets/guest-node.json');assert p['path']==str(target) and not target.is_symlink();st=target.stat();assert st.st_uid==0 and not st.st_mode&0o022 and stat.S_IMODE(st.st_mode)==p['mode'] and st.st_gid==p['gid']
sha=lambda b:hashlib.sha256(b).hexdigest()
def ids(b):
 rows=json.loads(b);values=[int(x['labels']['vmid']) for x in rows];assert len(values)==len(set(values));return set(values)
def run(a,timeout=25):
 r=subprocess.run(a,capture_output=True,text=True,timeout=timeout)
 if r.returncode:raise RuntimeError('fixed-native-check-failed')
 return r.stdout
def prom(path):
 with urllib.request.build_opener(urllib.request.ProxyHandler({})).open('http://192.168.19.70:9090'+path,timeout=8) as r:assert r.status==200;return json.loads(r.read(2000000))['data']
def mainstate():
 id=run(['docker','ps','--quiet','--filter','label=com.docker.compose.service=prometheus']).split();assert len(id)==1
 return id[0],run(['docker','inspect','--format','{{.Id}} {{.State.Pid}} {{.State.StartedAt}} {{if .State.Health}}{{.State.Health.Status}}{{end}}',id[0]]).strip()
def write(body):
 fd,name=tempfile.mkstemp(prefix='.java-only-SD-',dir=target.parent)
 try:
  os.fchmod(fd,stat.S_IMODE(st.st_mode));os.fchown(fd,st.st_uid,st.st_gid)
  with os.fdopen(fd,'wb') as f:f.write(body);f.flush();os.fsync(f.fileno())
  os.replace(name,target)
 finally:
  if os.path.exists(name):os.unlink(name)
def validate15():
 end=time.monotonic()+120;want=set(p['ids10']);own={json.dumps(x,sort_keys=True) for x in p['own_labels']}
 while True:
  ts=prom('/api/v1/targets')['activeTargets'];nodes=[x for x in ts if x.get('labels',{}).get('job')=='guest-node'];others=[x for x in ts if x.get('labels',{}).get('job')!='guest-node'];nids={int(x['labels']['vmid']) for x in nodes};o={json.dumps(x['labels'],sort_keys=True) for x in others};retired=[a for a in prom('/api/v1/alerts')['alerts'] if a.get('labels',{}).get('vmid') in ['231','232'] or a.get('labels',{}).get('instance') in ['192.168.19.41:9100','192.168.19.42:9100']]
  if len(ts)==15 and len(nodes)==10 and nids==want and len(others)==5 and o==own and all(x['health']=='up' for x in ts) and not retired:return {'total':15,'nodes':10,'own':5,'all_UP':True,'221_kept_UP':any(x['labels']['vmid']=='221' and x['health']=='up' for x in nodes),'231232_alerts_remaining':0}
  if time.monotonic()>end:raise RuntimeError('interim15-or-retired-alerts-not-settled')
  time.sleep(2)
assert sha(pathlib.Path('/opt/dell/ops/config/prometheus/prometheus.yml').read_bytes())==p['prom_SHA'];assert sha(pathlib.Path('/opt/dell/ops/config/prometheus/rules/infra.yml').read_bytes())==p['rules_SHA'];before=target.read_bytes();current=sha(before);assert (current==p['sha12'] and ids(before)==set(p['ids12'])) or (current==p['sha10'] and ids(before)==set(p['ids10'])),'CASrefused: only exact pinned12or10'
container,state_before=mainstate();folder=pathlib.Path('/root/dell-monitor-interim-java')/p['nonce'];result={'action':p['action'],'nonce':p['nonce'],'scope':'onlyfileSDremoves231232;221preserved','Nexus_or_VM_or220_or_catalog_installer_changes':False,'Prom_restart_reload_or_service_stop':False,'maintenance_silence_changed':False};changed=False;backup=None
try:
 if p['action']=='rollback':
  meta=json.loads((folder/'journal.json').read_text());backup=folder/'guest-node.before.json';old=backup.read_bytes();assert sha(old)==p['sha12']==meta['real_old_SHA256'];assert ids(old)==set(p['ids12'])
  if current==p['sha10']:write(old);changed=True
  assert sha(target.read_bytes())==p['sha12'];result['status']='rolled-back-exact-original12';result['old_total_targets_expected']=17;result['maintenance_warning']='RetiredJava targets may be down again; parent controls maintenance.'
 else:
  ts=prom('/api/v1/targets')['activeTargets'];n221=[x for x in ts if x.get('labels',{}).get('vmid')=='221'];assert len(n221)==1 and n221[0]['health']=='up','Do not hide realNexus221nodefault'
  body=__import__('base64').b64decode(p['body']);assert sha(body)==p['sha10'] and ids(body)==set(p['ids10']);assert next(x for x in json.loads(body) if x['labels']['vmid']=='221')==p['protected221']
  if current==p['sha12']:
   assert not folder.exists();folder.mkdir(parents=True,mode=0o700);folder.parent.chmod(0o700);assert folder.resolve()==folder;backup=folder/'guest-node.before.json';backup.write_bytes(before);backup.chmod(0o600);meta={'real_old_SHA256':current,'new_SHA256':p['sha10'],'old_nodes':12,'new_nodes':10,'old_mode':stat.S_IMODE(st.st_mode),'old_uid':st.st_uid,'old_gid':st.st_gid,'only_target_path':str(target),'no_other_files_changed':True};(folder/'journal.json').write_text(json.dumps(meta));(folder/'journal.json').chmod(0o600);write(body);changed=True
  run(['docker','exec',container,'/bin/promtool','check','config','/etc/prometheus/prometheus.yml']);sd=json.loads(run(['docker','exec',container,'/bin/promtool','check','service-discovery','--timeout=1s','/etc/prometheus/prometheus.yml','guest-node']));assert len(sd)==10
  result['actual_targets']=validate15();result['status']='committed-10nodes15UP' if changed else 'already-interim10-verified-no-write';result['backup_path']=str(backup) if backup else None;result['fileSD_SHA256']=sha(target.read_bytes());result['parent_may_review_ending_own_maintenance']=True
 assert mainstate()==(container,state_before);result['Prometheus_main_identity_health_unchanged']=True
except Exception as e:
 result['status']='failed-no-blind-repeat';result['error_class']=type(e).__name__
 if p['action']=='apply' and changed and backup:
  write(backup.read_bytes());result['exact_real_old_file_restored']=sha(target.read_bytes())==p['sha12']
finally:
 if folder.exists():f=folder/'result.json';f.write_text(json.dumps(result));f.chmod(0o600)
print(json.dumps(result))
'''
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['plan','apply','rollback']);p.add_argument('--execute',action='store_true');p.add_argument('--nonce');a=p.parse_args()
 if a.action=='plan':print(json.dumps({'status':'prepared-only','guest_nodes':10,'total':15,'221_preserved':True,'mutation_modes_not_run':True}));return
 if not a.execute:p.error('futuremutation requires explicit --execute; current taskprepare-only')
 nonce=a.nonce or uuid.uuid4().hex;assert len(nonce)==32 and all(x in '0123456789abcdef' for x in nonce)
 body=(HERE/M['candidate']).read_bytes();assert hashlib.sha256(body).hexdigest()==M['interim10_SHA256'];data={'action':a.action,'nonce':nonce,'path':M['target_path'],'sha12':M['current12_SHA256'],'sha10':M['interim10_SHA256'],'ids12':M['expected12_IDs'],'ids10':M['expected10_IDs'],'own_labels':M['expected_Ops_own_labels'],'protected221':M['protected221_target_unchanged'],'prom_SHA':M['prom_SHA256'],'rules_SHA':M['rules_SHA256'],'mode':M['target_mode'],'gid':M['target_gid'],'body':base64.b64encode(body).decode()};r=control.guest(270,'sudo -n python3 -B -c '+shlex.quote(REMOTE),data=json.dumps(data).encode(),info=T,timeout=240);assert r['exit_code']==0,'unconfirmed; inspect ownrootjournal, neverblindlyreplaceSHAs';j=json.loads(r['stdout']);d=HERE/'deployment-evidence';d.mkdir(exist_ok=True);(d/(nonce+'.json')).write_text(json.dumps(j,indent=2)+'\n');print(json.dumps(j));assert j['status'] in ['committed-10nodes15UP','already-interim10-verified-no-write','rolled-back-exact-original12']
if __name__=='__main__':main()
