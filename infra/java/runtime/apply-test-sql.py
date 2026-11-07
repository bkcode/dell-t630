#!/usr/bin/env python3
"""Target data-test only: explicit admin application of reviewed fresh *_test SQL."""
import argparse,hashlib,json,os,re,socket,subprocess,sys
from pathlib import Path
SCHEMAS=['finger_auth_test','finger_system_test','finger_coms_test']
FILES=['databases-admin.sql','auth-structure.sql','system-structure.sql','coms-structure.sql','accounts-admin.sql','synthetic-admin.sql']

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def emit(value):print(json.dumps(value,ensure_ascii=False))
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--package',type=Path,required=True);p.add_argument('--data-bundle',type=Path,required=True);p.add_argument('--apply',action='store_true');p.add_argument('--reviewed-structure',action='store_true');p.add_argument('--expected-package-sha256',required=True);p.add_argument('--output',type=Path);a=p.parse_args()
 meta=json.loads((a.package/'metadata.json').read_text());assert meta['target']['data_ip']=='10.63.20.10'
 items=[]
 for name in FILES:
  f=a.package/'sql'/name;assert f.is_file() and not f.is_symlink() and not f.stat().st_mode&0o077
  items.append({'name':name,'sha256':digest(f)})
 package_sha=hashlib.sha256(json.dumps(items,sort_keys=True,separators=(',',':')).encode()).hexdigest()
 assert package_sha==a.expected_package_sha256,'Reviewed SQL package hash mismatch'
 for role in ['auth','system','coms']:
  assert digest(a.package/'sql'/(role+'-structure.sql'))==meta['structures'][role]['ddl_sha256']
 if not a.apply:emit({'status':'review-package-verified-no-sql-executed','schema_count':3,'object_count':18,'package_sha256':package_sha});return
 assert a.reviewed_structure,'Explicit review of live-schema/entity differences required'
 assert os.geteuid()==0 and not Path('/etc/pve').exists(),'Target guest root only'
 assert socket.gethostname().split('.')[0] in ['data-test','test-data'],'Only test data guest supported'
 addresses=json.loads(subprocess.check_output(['ip','-j','addr'],text=True))
 assert any(x.get('local')=='10.63.20.10' for n in addresses for x in n.get('addr_info',[])),'Wrong data target IP'
 config={}
 for line in (a.data_bundle/'.env').read_text().splitlines():
  if '=' in line and not line.startswith('#'):k,v=line.split('=',1);config[k]=v
 assert config['ENVIRONMENT']=='test' and config['SERVICE_IP']=='10.63.20.10'
 base=['docker','compose','--project-directory',str(a.data_bundle),'--env-file',str(a.data_bundle/'.env'),'-f',str(a.data_bundle/'compose.yaml'),'exec','-T','mysql','sh','-c','MYSQL_PWD="$(cat "${MYSQL_ROOT_PASSWORD_FILE:-/run/secrets/mysql-root-password}")" exec mysql --user=root --batch --skip-column-names --raw --binary-mode']
 def sql(content):
  result=subprocess.run(base,input=content,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=90)
  if result.returncode:
   code=re.search(r'ERROR\s+(\d+)',result.stderr)
   raise RuntimeError('Target SQL failed; error code '+(code.group(1) if code else 'withheld'))
  return result.stdout.strip()
 registry=sql("SELECT COUNT(*) FROM information_schema.TABLES WHERE TABLE_SCHEMA='finger_system_test' AND TABLE_NAME='dell_init_history_test';")=='1'
 schema_hash=hashlib.sha256(''.join(meta['structures'][r]['ddl_sha256'] for r in ['auth','system','coms']).encode()).hexdigest()
 if registry:
  saved=sql("SELECT structure_sha256 FROM finger_system_test.dell_init_history_test WHERE init_key='dell-java-minimal-v1';")
  assert saved==schema_hash,'Existing initialization structure changed; use a reviewed migration, not reinitialization'
 else:
  count=sql("SELECT COUNT(*) FROM information_schema.TABLES WHERE TABLE_SCHEMA IN ('finger_auth_test','finger_system_test','finger_coms_test');")
  assert count=='0','Pre-existing unmarked schema objects; inspect rather than overwrite or blindly resume'
 sql((a.package/'sql/databases-admin.sql').read_text())
 if not registry:
  for name in ['auth-structure.sql','system-structure.sql','coms-structure.sql']:sql((a.package/'sql'/name).read_text())
 sql((a.package/'sql/accounts-admin.sql').read_text())
 seed=(a.package/'sql/synthetic-admin.sql').read_text()
 prepared_hash=re.search(r'\{bcrypt\}\$2[aby]\$\d\d\$[./A-Za-z0-9]{53}',seed)
 assert prepared_hash,'Expected delegating bcrypt seed hash missing'
 assert sql('SELECT @@GLOBAL.general_log;') in ['0','OFF'],'Do not emit credential seed into an active general query log'
 sql(seed)
 expected=set()
 for role,structure in meta['structures'].items():
  if role=='auth':names=['oauth2_registered_client','oauth2_authorization','oauth2_authorization_consent']
  else:names=[t['table'] for t in structure['tables']]
  expected.update(('finger_'+role+'_test',name) for name in names)
 actual=sql("SELECT TABLE_SCHEMA,TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA IN ('finger_auth_test','finger_system_test','finger_coms_test');")
 actual={tuple(line.split('\t')) for line in actual.splitlines() if line}
 assert expected.issubset(actual),'Expected structure incomplete'
 valid=sql("SELECT COUNT(*) FROM finger_system_test.user WHERE id=900000000001 AND user_number='FNTEST0001' AND type=0 AND status=0 AND role_id=900000000002 AND gmt_delete IS NULL AND SHA2(password,256)='"+hashlib.sha256(prepared_hash.group(0).encode()).hexdigest()+"';")
 assert valid=='1','Synthetic administrator collision or mismatch; no source/real record overwrite permitted'
 sql("CREATE TABLE IF NOT EXISTS finger_system_test.dell_init_history_test (init_key varchar(64) PRIMARY KEY,structure_sha256 char(64) NOT NULL,created_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP);\nINSERT INTO finger_system_test.dell_init_history_test (init_key,structure_sha256) VALUES ('dell-java-minimal-v1','"+schema_hash+"') ON DUPLICATE KEY UPDATE structure_sha256=structure_sha256;")
 result={'status':'target-test-structure-and-synthetic-seed-initialized','target_ip':'10.63.20.10','application_table_count':len(expected),'dba_registry_tables':1,'schema_sha256':schema_hash,'sql_package_sha256':package_sha,'accounts_host':'10.63.20.20','runtime_privileges':['SELECT','INSERT','UPDATE','DELETE'],'source_rows_copied':False,'source_sql_writes':False,'runtime_started':False,'nacos_configs_ready':False}
 if a.output:
  a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');a.output.chmod(0o600)
 emit(result)
if __name__=='__main__':
 try:main()
 except Exception as e:emit({'status':'failed','error_category':type(e).__name__,'message':str(e)});sys.exit(1)
