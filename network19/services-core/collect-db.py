#!/usr/bin/env python3
"""Only root metadata SELECT/SHOW on200/210; no auth hash/secret/config bodies exported."""
import concurrent.futures,json,sys,shlex,datetime
from pathlib import Path
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];sys.path.insert(0,str(ROOT/'scripts'));import control
if (HERE/'database-inventory.json').exists():raise SystemExit('Initial snapshot already exists; preserve old evidence and request a separately versioned collection')
PROGRAM=r'''import sys,json,subprocess,re,hashlib
from pathlib import Path
v=json.loads(sys.stdin.read());name=v['container'];db=v['nacos_db'];D=['docker','--host','unix:///var/run/docker.sock']
def sql(statement):
 shell='export MYSQL_PWD="$(cat /run/secrets/mysql-root-password)"; exec mysql --user=root --protocol=socket --batch --raw --skip-column-names'
 p=subprocess.run(D+['exec','-i',name,'sh','-c',shell],input=statement.encode(),capture_output=True,timeout=30)
 if p.returncode:raise RuntimeError('readonly metadata SQL failed; raw output withheld')
 return p.stdout.decode().strip()
users=['nacos_prod','nacos_test','finger_auth_test','finger_system_test','finger_coms_test'];rows=[]
for line in sql("SELECT user,host,plugin,account_locked FROM mysql.user WHERE user IN ("+','.join("'"+u+"'" for u in users)+") ORDER BY user,host;").splitlines():
 user,host,plugin,locked=line.split('\t');grants=sql("SHOW GRANTS FOR '"+user+"'@'"+host.replace("'","''")+"';").splitlines()
 if any('IDENTIFIED' in g.upper() or 'PASSWORD' in g.upper() for g in grants):raise RuntimeError('unexpected sensitive GRANT representation; withheld')
 rows.append({'user':user,'host':host,'plugin':plugin,'account_locked':locked,'grants':grants})
configs=[]
raw=sql('SELECT data_id,group_id,tenant_id,HEX(content) FROM `'+db+'`.config_info ORDER BY data_id,group_id,tenant_id;')
import yaml
for line in raw.splitlines() if raw else []:
 dataid,group,namespace,hextext=line.split('\t');content=bytes.fromhex(hextext);safe=[]
 try:model=yaml.safe_load(content)
 except Exception:model=None
 def walk(x,path):
  if isinstance(x,dict):
   for k,val in x.items():
    if not any(s in str(k).lower() for s in ['password','secret','token','credential','private-key']):walk(val,path+[str(k)])
  elif isinstance(x,list):
   for i,val in enumerate(x):walk(val,path+[str(i)])
  elif isinstance(x,str) and re.search(r'(?:10\.63\.|192\.168\.21\.22|172\.18\.)',x) and not re.search(r'(?:password|secret|token|authorization)=',x,re.I):safe.append({'path':path,'value':x})
 walk(model,[])
 configs.append({'data_id':dataid,'group_id':group,'namespace_sha256':hashlib.sha256(namespace.encode()).hexdigest(),'content_sha256':hashlib.sha256(content).hexdigest(),'safe_internal_endpoint_values':safe,'all_other_values_withheld':True})
print(json.dumps({'vmid':v['vmid'],'mysql_accounts':rows,'Nacos_database':db,'Nacos_configs':configs,'SQL_scope':'SELECT mysql.user selected metadata and Nacos config_info + SHOW GRANTS only','writes':0,'auth_hash_password_or_config_bodies_exported':False}))'''
def one(vmid):
 rows=json.loads((ROOT/'evidence/implementation/private-guest-access.json').read_text())['roles'];row=next(x for x in rows if x['target']['vmid']==vmid)
 payload={'vmid':vmid,'container':'dell-data-prod-db-mysql-1' if vmid==200 else 'dell-data-test-data-mysql-1','nacos_db':'nacos_prod' if vmid==200 else 'nacos_test'}
 r=control.guest(vmid,'sudo -n python3 -I -B -c '+shlex.quote(PROGRAM),data=json.dumps(payload).encode(),timeout=90,info=row['target'])
 if r['exit_code']:return {'vmid':vmid,'status':'read-failed-values-withheld'}
 return json.loads(r['stdout'])
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as p:results=list(p.map(one,[200,210]))
(HERE/'database-inventory.json').write_text(json.dumps({'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'results':results},indent=2)+'\n')
for r in results:print(json.dumps({'vmid':r['vmid'],'status':r.get('status','collected'),'accounts':r.get('mysql_accounts'),'Nacos_dataIds':[x['data_id'] for x in r.get('Nacos_configs',[])]}))
