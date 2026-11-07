#!/usr/bin/env python3
"""Read structure for exactly the minimal test chain; never exports source rows or credentials."""
import datetime as dt,hashlib,json,os,re,subprocess,sys,urllib.parse,urllib.request,urllib.error
from pathlib import Path
from zoneinfo import ZoneInfo
import yaml
BASE=Path(__file__).resolve().parents[3];OUT=BASE/'private/java/schema-source'
TABLES={'auth':['oauth2_registered_client','oauth2_authorization','oauth2_authorization_consent'],
 'system':['user','role_info','role_permission','admin_notice','admin_notice_delivery'],
 'coms':['permission_menu','permission_menu_url','permission_role','permission_role_menu','file_info','dict','country_info','country_info_i18n','city_info','city_info_i18n']}
IDS={'auth':'finger-auth.yaml','system':'finger-service-system.yaml','coms':'finger-service-coms.yaml'}
class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,*args,**kwargs):return None
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect)

def main():
 OUT.mkdir(parents=True,exist_ok=True,mode=0o700);os.chmod(OUT,0o700);rows=[]
 for role,tables in TABLES.items():
  if len(sys.argv)>1 and role!=sys.argv[1]:continue
  query=urllib.parse.urlencode({'dataId':IDS[role],'group':'DEFAULT_GROUP','tenant':'08e7191f-3ccd-411a-be00-56798d237533'})
  with opener.open('http://127.0.0.1:8848/nacos/v1/cs/configs?'+query,timeout=5) as response:
   config=yaml.safe_load(response.read(1024*1024))
  jdbc=config.get('spring',{}).get('datasource',{}).get('url','')
  match=re.search(r'jdbc:mysql://[^/]+/([a-zA-Z0-9_]+)',jdbc)
  assert match,'Cannot identify source schema without evaluating credentials'
  schema=match.group(1)
  # Read table names only; missing current-entity tables are reported, never synthesized as source facts.
  names=subprocess.run(['docker','exec','mysql','sh','-c','MYSQL_PWD="$MYSQL_ROOT_PASSWORD" exec mysql --user=root --batch --skip-column-names "$1" --execute="SHOW TABLES"','--',schema],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=15)
  assert names.returncode==0
  available=set(names.stdout.splitlines());missing=sorted(set(tables)-available)
  tables=[t for t in tables if t in available]
  assert tables,'No expected tables found in source schema'
  # Root password stays in the existing container environment and never appears in argv/stdout.
  command=['docker','exec','mysql','sh','-c','MYSQL_PWD="$MYSQL_ROOT_PASSWORD" exec mysqldump --user=root --no-data --skip-lock-tables --no-tablespaces --skip-triggers --skip-add-drop-table --skip-comments --skip-dump-date --set-gtid-purged=OFF --column-statistics=0 "$@"','--',schema,*tables]
  result=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=40)
  if result.returncode:
   rows.append({'role':role,'status':'failed','exit_code':result.returncode,'raw_error_withheld':True});continue
  ddl=result.stdout
  assert not re.search(r'^\s*(?:INSERT|REPLACE|UPDATE|DELETE|LOCK TABLES|CREATE TRIGGER|CREATE USER|GRANT)\b',ddl,re.M|re.I)
  objects=re.findall(r'CREATE TABLE\s+`?([a-zA-Z0-9_]+)`?',ddl,re.I)
  assert set(objects)==set(tables) and len(objects)==len(tables),'Unexpected/missing schema objects'
  path=OUT/(role+'-source-no-data.sql')
  if path.exists():assert path.read_text()==ddl,'Source structure changed; preserve evidence for review'
  else:path.write_text(ddl);path.chmod(0o600)
  row={'role':role,'status':'collected-no-data','source_schema':schema,'target_schema':'finger_'+role+'_test','objects':objects,'object_count':len(objects),'sha256':hashlib.sha256(ddl.encode()).hexdigest(),'path':str(path),'missing_expected_tables':missing,'source_rows_exported':False,'source_global_lock':False,'password_in_arguments':False}
  rows.append(row)
 manifest={'schema_version':1,'collected_at':dt.datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),'scope':'read-only local MySQL schema metadata','source_values_copied_from_nacos':'Only schema identifier; no source credentials or unrelated settings retained','mysqldump_flags':['--no-data','--skip-lock-tables','--no-tablespaces','--skip-triggers','--skip-add-drop-table'],'structures':rows}
 path=OUT/('manifest-'+sys.argv[1]+'.json' if len(sys.argv)>1 else 'manifest.json');path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n');path.chmod(0o600)
 print(json.dumps({'status':'collected' if all(x['status']=='collected-no-data' for x in rows) else 'partial','roles':[{'role':x['role'],'status':x['status'],'objects':x.get('object_count')} for x in rows],'source_dml_exported':False,'source_write_operations':False}))
if __name__=='__main__':
 try:main()
 except Exception as e:print(json.dumps({'status':'failed','error_category':type(e).__name__}));sys.exit(1)
