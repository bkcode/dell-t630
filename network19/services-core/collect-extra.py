import concurrent.futures,json,sys,shlex,datetime
from pathlib import Path
sys.dont_write_bytecode=True
H=Path(__file__).resolve().parent;R=H.parents[1];sys.path.insert(0,str(R/'scripts'));import control
if (H/'extra-inventory.json').exists():raise SystemExit('Initial snapshot already exists; preserve old evidence and request a separately versioned collection')
P=r'''import json,subprocess,sys,hashlib
from pathlib import Path
v=json.loads(sys.stdin.read());vmid=v['vmid'];D=['docker','--host','unix:///var/run/docker.sock'];out={'vmid':vmid}
def run(a,data=None):
 p=subprocess.run(a,input=data,capture_output=True,text=True,timeout=25)
 if p.returncode:raise RuntimeError('read-only supplementary command failed')
 return p.stdout
if vmid in [200,210]:
 name='dell-data-prod-db-mysql-1' if vmid==200 else 'dell-data-test-data-mysql-1';shell='export MYSQL_PWD="$(cat /run/secrets/mysql-root-password)"; exec mysql --user=root --protocol=socket --batch --raw --skip-column-names'
 raw=run(D+['exec','-i',name,'sh','-c',shell],"SELECT USER,HOST,DB FROM information_schema.PROCESSLIST WHERE USER IN ('nacos_prod','nacos_test','finger_auth_test','finger_system_test','finger_coms_test') ORDER BY USER,HOST;")
 out['actual_DB_connection_sources']=[dict(zip(['user','host_with_ephemeral_port','database'],line.split('\t'))) for line in raw.splitlines()]
if vmid==210:
 out['test_data_network']=json.loads(run(D+['network','inspect','--format','{{json .IPAM.Config}}','dell-data-test-data_default']))
 out['test_Nacos_container_address']=json.loads(run(D+['inspect','--format','{{json .NetworkSettings.Networks}}','dell-data-test-data-nacos-1']))
if vmid==270:
 out['ops_network_IPAM']=json.loads(run(D+['network','inspect','--format','{{json .IPAM.Config}}','dell-ops_default']))
 out['AM_address']=json.loads(run(D+['inspect','--format','{{json .NetworkSettings.Networks}}','dell-ops-alertmanager-1']))
 p=Path('/etc/dell-lark-notify/policy.json');x=json.loads(p.read_text());out['Lark_nonsecret_policy']={k:x[k] for k in ['mode','bind_host','bind_port','allowed_source']}
p=Path('/etc/dell-guest-monitoring/health.json')
if p.exists():
 x=json.loads(p.read_text());out['active_guest_monitoring']={k:x.get(k) for k in ['role','private_ip','services','http_checks','textfile_directory']}
 out['candidate_checks_not_activated']=True
print(json.dumps(out))'''
access={r['target']['vmid']:r['target'] for r in json.loads((R/'evidence/implementation/private-guest-access.json').read_text())['roles']}
def one(v):
 r=control.guest(v,'sudo -n python3 -I -B -c '+shlex.quote(P),data=json.dumps({'vmid':v}).encode(),timeout=70,info=access[v]);return json.loads(r['stdout']) if r['exit_code']==0 else {'vmid':v,'read_failed':True}
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:rows=list(pool.map(one,[200,201,210,220,230,231,232,240,270]))
(H/'extra-inventory.json').write_text(json.dumps({'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'roles':rows},indent=2)+'\n')
for r in rows:print(json.dumps({'vmid':r['vmid'],'DB_sources':r.get('actual_DB_connection_sources'),'test_network':r.get('test_data_network'),'Lark_policy':r.get('Lark_nonsecret_policy'),'active_HTTP_checks':r.get('active_guest_monitoring',{}).get('http_checks')}))
