#!/usr/bin/env python3
"""Prepare private target-test configs, synthetic secrets and structure-only SQL; never executes SQL."""
import argparse,datetime as dt,hashlib,json,os,re,secrets,stat,subprocess,sys,urllib.parse,zipfile
from pathlib import Path
from zoneinfo import ZoneInfo
import yaml
BASE=Path(__file__).resolve().parents[3];OUT=BASE/'private/java';BUILD=BASE/'private/java-build'
BUNDLE=BASE/'private/data/bundles/test-data';SOURCE=Path('/Users/yangzhaohui/work/www/finger/finger-master')
SERVICES={'finger-gateway-mobile':9999,'finger-auth':10000,'finger-service-system':10210,'finger-service-coms':10202,'finger-bff-system':10104}
DBS={r:'finger_'+r+'_test' for r in ['auth','system','coms']}

def write(path,value):
 path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
 fd=os.open(path,os.O_CREAT|os.O_TRUNC|os.O_WRONLY,0o600)
 with os.fdopen(fd,'w') as f:f.write(value)
 os.chmod(path,0o600)

def private_read(path):
 s=path.lstat();assert stat.S_ISREG(s.st_mode) and not path.is_symlink() and not stat.S_IMODE(s.st_mode)&0o077,'Private regular 600 file required'
 return path.read_text().strip()

def stable_secret(name):
 path=OUT/'secrets'/name
 if not path.exists():write(path,secrets.token_urlsafe(36)+'\n')
 value=private_read(path);assert re.fullmatch(r'[A-Za-z0-9_-]{32,64}',value)
 return value,path

def sql_lit(value):return "'"+str(value).replace("'","''")+"'"
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def env_file(path):
 data={}
 for l in private_read(path).splitlines():
  if l and not l.startswith('#') and '=' in l:k,v=l.split('=',1);data[k]=v
 return data

def annotations(text,name):
 for m in re.finditer(r'@(?:field:)?'+re.escape(name)+r'\s*\(',text):
  start=m.end();i=start;depth=1;quote=False;escape=False
  while i<len(text) and depth:
   c=text[i]
   if quote:
    if escape:escape=False
    elif c=='\\':escape=True
    elif c=='"':quote=False
   elif c=='"':quote=True
   elif c=='(':depth+=1
   elif c==')':depth-=1
   i+=1
  assert depth==0
  yield text[start:i-1],i

def string_arg(args,key=None):
 pattern=r'^\s*"((?:[^"\\]|\\.)*)"' if key is None else re.escape(key)+r'\s*=\s*"((?:[^"\\]|\\.)*)"'
 m=re.search(pattern,args)
 return json.loads('"'+m.group(1)+'"') if m else None

def create_blocks(text):
 # DDL came from --no-data, not a business SQL script. Column semicolons inside quotes are respected.
 result={}
 for match in re.finditer(r'CREATE TABLE\s+`?([A-Za-z0-9_]+)`?\s*\(',text,re.I):
  i=match.start();j=match.end();quote=None;escape=False
  while j<len(text):
   c=text[j]
   if quote:
    if escape:escape=False
    elif c=='\\':escape=True
    elif c==quote:quote=None
   elif c in ["'",'"','`']:quote=c
   elif c==';':break
   j+=1
  assert j<len(text)
  block=text[i:j+1];assert not re.search(r'\b(?:DEFINER|TRIGGER|PROCEDURE)\b',block,re.I)
  result[match.group(1)]=block
 return result

def normalized_type(value):
 return re.sub(r'\b(tinyint|smallint|mediumint|int|bigint)\(\d+\)',r'\1',value.lower().strip())

def schema_proposal(role):
 source_path=OUT/'schema-source'/(role+'-source-no-data.sql');blocks=create_blocks(source_path.read_text()) if source_path.exists() else {}
 if role=='auth':
  expected={}
  for name in ['oauth2_registered_client','oauth2_authorization','oauth2_authorization_consent']:
   expected.update(create_blocks((SOURCE/'db'/(name+'.sql')).read_text()))
  assert set(expected)==set(blocks)
  return '\n\n'.join(re.sub(r'CREATE TABLE', 'CREATE TABLE IF NOT EXISTS',blocks[n],count=1,flags=re.I) for n in sorted(blocks)),{'source_tables':len(blocks),'target_tables':len(blocks),'entity_comparison':'OAuth DDL table set matches current source structure scripts; no source DML copied','differences':[]}
 project=SOURCE/'projects'/('finger-service-'+role)/(role+'-boot')/'src/main/kotlin/com/sargia/finger/service'/role/'entity'
 output=[];differences=[];details=[]
 for file in sorted(project.glob('*.kt')):
  text=file.read_text();table_args=next(annotations(text,'Table'),None)
  if not table_args:continue
  table=string_arg(table_args[0]);columns=[];prop_to_col={};primary=[]
  source_cols={m.group(1):m.group(2).rstrip(',') for m in re.finditer(r'^\s*`([^`]+)`\s+(.+?)[,]?$',blocks.get(table,''),re.M)}
  for args,end in annotations(text,'Column'):
   prop=re.match(r'\s*(?:var|val)\s+([A-Za-z0-9_]+)\s*:\s*([A-Za-z0-9_<>?.]+)',text[end:])
   if not prop:continue
   name=string_arg(args);dtype=string_arg(args,'dbType');assert name and dtype
   assert re.fullmatch(r'[a-zA-Z]+(?:\([0-9, ]+\))?(?: unsigned)?',dtype), 'Review unsupported dbType'
   pkey=bool(re.search(r'primaryKey\s*=\s*true',args));generated=bool(re.search(r'generatedKey\s*=\s*true',args))
   old=source_cols.get(name);old_type=re.match(r'[A-Za-z]+(?:\([^)]*\))?(?: unsigned)?',old or '')
   if old and old_type and normalized_type(dtype)!=normalized_type(old_type.group(0)):differences.append({'table':table,'column':name,'kind':'entity-type-differs-from-source','entity_type':dtype,'source_type':old_type.group(0)})
   if not old:differences.append({'table':table,'column':name,'kind':'not-in-source-structure'})
   notnull=pkey or bool(old and re.search(r'\bNOT NULL\b',old,re.I)) or re.search(r'nullable\s*=\s*false',args)
   default=string_arg(args,'dbDefault')
   if default is None and old:
    d=re.search(r"\bDEFAULT\s+((?:'(?:[^'\\]|\\.)*')|(?:b'[01]')|NULL|CURRENT_TIMESTAMP(?:\(\d*\))?|[-0-9.]+)",old,re.I)
    default=d.group(1) if d else None
   clause='`'+name+'` '+dtype+(' NOT NULL' if notnull else ' NULL')
   if generated:clause+=' AUTO_INCREMENT'
   elif default is not None:clause+=' DEFAULT '+default
   columns.append(clause);prop_to_col[prop.group(1)]=name
   if pkey:primary.append(name)
  assert columns and primary
  extras=sorted(set(source_cols)-set(prop_to_col.values()))
  if extras:differences.append({'table':table,'kind':'source-only-columns-not-carried-to-fresh-test-model','columns':extras})
  columns.append('PRIMARY KEY ('+', '.join('`'+c+'`' for c in primary)+')')
  for args,_ in annotations(text,'TableIndex'):
   name=string_arg(args,'name');fields=re.search(r'fields\s*=\s*\[([^]]+)\]',args)
   assert name and fields
   props=re.findall(r'"([A-Za-z0-9_]+)"',fields.group(1));assert props and all(x in prop_to_col for x in props)
   columns.append(('UNIQUE KEY ' if re.search(r'unique\s*=\s*true',args) else 'KEY ')+'`'+name+'` ('+', '.join('`'+prop_to_col[x]+'`' for x in props)+')')
  output.append('CREATE TABLE IF NOT EXISTS `'+table+'` (\n  '+',\n  '.join(columns)+'\n) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;')
  details.append({'table':table,'entity_source':str(file),'entity_sha256':digest(file),'columns':list(prop_to_col.values()),'has_source_structure':table in blocks})
 assert len(output)==(5 if role=='system' else 10)
 return '\n\n'.join(output),{'source_tables':len(blocks),'target_tables':len(output),'tables':details,'differences':differences,'nullability_basis':'Retain source NOT NULL for matching columns; primary keys NOT NULL; other model fields nullable unless explicitly declared. Fresh-test proposal requires manager review.'}

def hash_admin(raw):
 target=OUT/'secrets/admin-password-hash'
 build=json.loads((BASE/'infra/java/build-status.json').read_text());jar=Path(next(r['artifact']['path'] for r in build['services'] if r['service']=='finger-auth'))
 libs=OUT/'tools/password-encoder';libs.mkdir(parents=True,exist_ok=True,mode=0o700);paths=[]
 with zipfile.ZipFile(jar) as z:
  for prefix in ['spring-security-crypto-','spring-core-','spring-jcl-']:
   entries=[n for n in z.namelist() if n.startswith('BOOT-INF/lib/'+prefix) and n.endswith('.jar')];assert len(entries)==1
   data=z.read(entries[0]);path=libs/entries[0].split('/')[-1]
   if path.exists():assert path.read_bytes()==data
   else:path.write_bytes(data);path.chmod(0o600)
   paths.append(str(path))
 java=Path.home()/'.local/share/mise/installs/java/temurin-21/bin/java'
 env={'PATH':'/usr/bin:/bin','LANG':'en_US.UTF-8'}
 existing=private_read(target) if target.exists() else None
 command=[str(java),'-Xmx128m','-cp',os.pathsep.join(paths),str(Path(__file__).with_name('HashPassword.java'))]+(['--verify'] if existing else [])
 r=subprocess.run(command,input=raw+'\n'+existing if existing else raw,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env,timeout=30)
 assert r.returncode==0,'PasswordEncoder helper failed; output withheld'
 if existing:
  assert r.stdout=='verified';return existing
 encoded=r.stdout.strip();assert re.fullmatch(r'\{bcrypt\}\$2[aby]\$\d\d\$[./A-Za-z0-9]{53}',encoded) and len(encoded)<=76
 write(target,encoded+'\n');return encoded

def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--issuer',required=True,help='Explicit candidate/test issuer; must be validated at actual target entrypoint');parser.add_argument('--refresh-config',action='store_true',help='Refresh only an unexecuted prepared package; stable secrets are retained');a=parser.parse_args()
 url=urllib.parse.urlsplit(a.issuer);assert url.scheme in ['http','https'] and url.hostname and not(url.username or url.password or url.query or url.fragment)
 assert url.hostname=='192.168.21.22' and url.port==19999 and url.path in ['', '/'],'Test LAN issuer must use approved gateway port 19999; 9999 is reserved for prod'
 issuer=a.issuer.rstrip('/');meta_path=OUT/'test-chain/metadata.json'
 if meta_path.exists():
  old=json.loads(meta_path.read_text());assert a.refresh_config and old['status']=='prepared-not-executed' and old['sql_execution']=='not-executed' and old['runtime_started'] is False,'Only an unexecuted package may be refreshed'
 OUT.mkdir(parents=True,exist_ok=True,mode=0o700);env=env_file(BUNDLE/'.env');assert env['ENVIRONMENT']=='test' and env['SERVICE_IP']=='10.63.20.10'
 ns=env['NACOS_NAMESPACE_ID'];nacos_user=env['NACOS_CLIENT_USER'];nacos_password=private_read(BUNDLE/'secrets/nacos-client-password')
 redis_password=private_read(BUNDLE/'secrets/redis-password');rabbit_password=private_read(BUNDLE/'secrets/rabbit-app-password')
 mysql={}
 for role in DBS:
  secret,path=stable_secret('db-'+role+'-password');mysql[role]={'schema':DBS[role],'user':DBS[role],'password':secret,'password_file':str(path),'client_host':'10.63.20.20'}
 admin_password,admin_secret=stable_secret('admin-password');admin_hash=hash_admin(admin_password)
 clients={};client_meta=[]
 for client in ['finger-admin','finger-merchant','finger-app','finger-web']:
  value,path=stable_secret('oauth-'+client+'-secret');clients[client]={'secret':value,'redirect-uris':[issuer+'/dell-test/callback'],'post-logout-redirect-uris':[issuer+'/dell-test/logout']};client_meta.append({'client_id':client,'secret_file':str(path)})
 root=OUT/'test-chain';group='DELL_TEST';services=[]
 common={'redis':{'host':'10.63.20.10','port':6379,'database':0,'password':redis_password},'gateway':{'endpoint':issuer},'nacos':{'server-addr':'10.63.20.10:8848'},'spring':{'autoconfigure':{'exclude':['com.sargia.finger.common.apidoc.OpenApiConfig']},'data':{'redis':{'host':'10.63.20.10','port':6379,'database':0,'password':redis_password,'timeout':'3s','connect-timeout':'2s'}},'rabbitmq':{'host':'10.63.20.10','port':5672,'username':env['RABBIT_APP_USER'],'password':rabbit_password,'virtual-host':env['RABBIT_VHOST']},'security':{'oauth2':{'resourceserver':{'jwt':{'issuer-uri':issuer,'jwk-set-uri':'http://10.63.20.20:10000/oauth2/jwks'}}}},'sql':{'init':{'mode':'never'}},'servlet':{'multipart':{'max-file-size':'5MB','max-request-size':'5MB'}}},'easy-query':{'database':'mysql','name-conversion':'underlined','print-sql':False,'auto-create':False,'update':False},'management':{'endpoints':{'web':{'exposure':{'include':'health,info'}}},'endpoint':{'health':{'show-details':'never','show-components':'never'}}},'logging':{'level':{'root':'INFO','com.easy.query':'WARN'}},'sms':{'aws':{'access-key-id':'','access-key-secret':''},'aliyun':{'access-key-id':'','access-key-secret':''}}}
 write(root/'nacos-configs'/group/'finger-common.yaml',yaml.safe_dump(common,allow_unicode=True,sort_keys=False))
 for service,port in SERVICES.items():
  runtime={'spring':{'application':{'name':service},'profiles':{'active':'dell-test'},'config':{'import':['nacos:finger-common.yaml?group='+group+'&refreshEnabled=false','nacos:'+service+'.yaml?group='+group+'&refreshEnabled=false']},'cloud':{'nacos':{'server-addr':'10.63.20.10:8848','username':nacos_user,'password':nacos_password,'discovery':{'server-addr':'10.63.20.10:8848','namespace':ns,'group':group,'ip':'10.63.20.20','register-enabled':True},'config':{'server-addr':'10.63.20.10:8848','namespace':ns,'group':group,'refresh-enabled':False}}}},'server':{'address':'10.63.20.20','port':port}}
  specific={}
  runtime['snowflake']={'data-center-id':1,'worker-id':list(SERVICES).index(service)+1}
  role='auth' if service=='finger-auth' else 'system' if service=='finger-service-system' else 'coms' if service=='finger-service-coms' else None
  if role:
   account=mysql[role];runtime['spring']['datasource']={'driver-class-name':'com.mysql.cj.jdbc.Driver','url':'jdbc:mysql://10.63.20.10:3306/'+account['schema']+'?useUnicode=true&characterEncoding=utf8&useSSL=false&allowPublicKeyRetrieval=true&serverTimezone=Asia/Shanghai','username':account['user'],'password':account['password'],'hikari':{'maximum-pool-size':4,'minimum-idle':0,'connection-timeout':5000,'validation-timeout':3000}}
  if service=='finger-auth':
   runtime['finger']={'auth':{'bootstrap':{'issuer':issuer,'clients':clients}}};runtime['captcha']={'type':'circle','code':{'type':'random','length':4},'font':{'name':'DejaVu Sans','weight':1,'size':24},'expire-seconds':300};runtime['sargia']={'accounts':{'oauth':{'public-url':'http://10.63.20.20:9','client-id':'disabled-in-dell-test'}}}
  if service=='finger-service-coms':
   runtime['file']={'upload':{'path':'/var/lib/finger/finger-service-coms/uploads','domain':issuer+'/finger-bff-system/dell-test-files'}}
   runtime['spring']['web']={'resources':{'static-locations':['classpath:/META-INF/resources/','classpath:/resources/','classpath:/static/','classpath:/public/','file:/var/lib/finger/finger-service-coms/uploads/']}}
  if service=='finger-gateway-mobile':
   specific={'spring':{'cloud':{'gateway':{'server':{'webflux':{'discovery':{'locator':{'enabled':False}},'routes':[{'id':'dell-test-files','uri':'lb://finger-service-coms','predicates':['Path=/finger-bff-system/dell-test-files/**','Method=GET'],'filters':['StripPrefix=2']},{'id':'dell-test-captcha','uri':'lb://finger-auth','predicates':['Path=/api/v1/auth/captcha','Method=GET']},{'id':'dell-test-oauth','uri':'lb://finger-auth','predicates':['Path=/oauth2/token,/oauth2/jwks,/.well-known/openid-configuration','Method=GET,POST']},{'id':'dell-test-system-read','uri':'lb://finger-bff-system','predicates':['Path=/finger-bff-system/sys-api/v1/role/get-list,/finger-bff-system/sys-api/v1/role/get-role-permissions,/finger-bff-system/sys-api/v1/employee/get-list','Method=POST'],'filters':['StripPrefix=1']}]}}}}},'security':{'whitelist-paths':['/api/v1/auth/captcha','/oauth2/token','/oauth2/jwks','/.well-known/openid-configuration','/actuator/health'],'jwt':{'trustedIssuers':[{'issuerUri':issuer,'jwkSetUri':'http://10.63.20.20:10000/oauth2/jwks'}],'externalClients':[]}}}
  data_id=service+'-lan-v2.yaml' if service=='finger-gateway-mobile' else service+'.yaml'
  if service=='finger-gateway-mobile':
   specific['spring']['cloud']['gateway']['server']['webflux']['routes'].append({'id':'dell-test-auth-prefix','uri':'lb://finger-auth','predicates':['Path=/finger-auth/api/v1/auth/captcha,/finger-auth/oauth2/token,/finger-auth/oauth2/jwks','Method=GET,POST'],'filters':['StripPrefix=1']})
   specific['security']['whitelist-paths']+=['/finger-auth/api/v1/auth/captcha','/finger-auth/oauth2/token','/finger-auth/oauth2/jwks']
   runtime['spring']['config']['import'][1]='nacos:'+data_id+'?group='+group+'&refreshEnabled=false'
  write(root/'nacos-configs'/group/data_id,yaml.safe_dump(specific,allow_unicode=True,sort_keys=False))
  write(root/'runtime'/service/'application.yaml',yaml.safe_dump(runtime,allow_unicode=True,sort_keys=False))
  services.append({'name':service,'port':port,'runtime_config':str(root/'runtime'/service/'application.yaml'),'nacos_data_id':data_id,'database':DBS[role] if role else None})
 structures={}
 for role in DBS:
  sql,comparison=schema_proposal(role);ddl='-- Fresh target test schema only; structure from source/entities, no source rows.\nUSE `'+DBS[role]+'`;\n'+sql+'\n';write(root/'sql'/(role+'-structure.sql'),ddl);structures[role]=dict(comparison,ddl_sha256=hashlib.sha256(ddl.encode()).hexdigest())
 accounts=[];databases=[]
 for role,account in mysql.items():
  user=sql_lit(account['user'])+'@'+sql_lit(account['client_host']);databases.append('CREATE DATABASE IF NOT EXISTS `'+account['schema']+'` CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;')
  accounts += ['CREATE USER IF NOT EXISTS '+user+' IDENTIFIED BY '+sql_lit(account['password'])+';','ALTER USER '+user+' IDENTIFIED BY '+sql_lit(account['password'])+';','REVOKE ALL PRIVILEGES, GRANT OPTION FROM '+user+';']
  tables=['oauth2_registered_client','oauth2_authorization','oauth2_authorization_consent'] if role=='auth' else [t['table'] for t in structures[role]['tables']]
  accounts += ['GRANT SELECT, INSERT, UPDATE, DELETE ON `'+account['schema']+'`.`'+table+'` TO '+user+';' for table in tables]
 write(root/'sql/databases-admin.sql','-- Admin-only schema creation, before table DDL and account grants.\n'+'\n'.join(databases)+'\n')
 write(root/'sql/accounts-admin.sql','-- Admin-only, target *_test identities; never supplied to runtime users.\n'+'\n'.join(accounts)+'\n')
 seed='''-- Only synthetic acceptance identities; never copied from source rows.
USE `finger_system_test`;
INSERT INTO `role_info` (`id`,`name`,`status`,`description`,`gmt_create`,`gmt_update`,`gmt_delete`)
SELECT 900000000002,'Dell test administrator',0,'Synthetic acceptance only',CURRENT_TIMESTAMP,CURRENT_TIMESTAMP,NULL
WHERE NOT EXISTS (SELECT 1 FROM `role_info` WHERE `id`=900000000002);
INSERT INTO `user` (`id`,`user_number`,`name`,`password`,`email`,`type`,`status`,`role_id`,`gmt_create`,`gmt_update`,`gmt_delete`)
SELECT 900000000001,'FNTEST0001','Dell acceptance administrator',__HASH__,'admin@dell-test.invalid',0,0,900000000002,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP,NULL
WHERE NOT EXISTS (SELECT 1 FROM `user` WHERE `user_number`='FNTEST0001' OR `id`=900000000001);
'''.replace('__HASH__',sql_lit(admin_hash));write(root/'sql/synthetic-admin.sql',seed)
 meta={'schema_version':1,'prepared_at':dt.datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),'status':'prepared-not-executed','target':{'java_vmid':240,'java_ip':'10.63.20.20','data_vmid':210,'data_ip':'10.63.20.10'},'issuer':issuer,'issuer_status':'explicit-candidate-not-runtime-accepted','nacos_namespace':ns,'nacos_group':group,'services':services,'accounts':[{k:v for k,v in x.items() if k!='password'} for x in mysql.values()],'oauth_clients':client_meta,'synthetic_admin':{'account':'FNTEST0001','id':900000000001,'password_file':str(admin_secret),'password_hash_file':str(OUT/'secrets/admin-password-hash'),'encoder':'Spring PasswordEncoderFactories delegating bcrypt','source_user_rows_copied':False},'structures':structures,'nacos_config_publication':'not-executed','sql_execution':'not-executed','runtime_started':False,'start_gates':['network authorization/VM start','schema review and initialization','Nacos mandatory data-id publication and permissions','target Java21 and finger permissions','explicit issuer entrypoint validation']}
 write(meta_path,json.dumps(meta,ensure_ascii=False,indent=2)+'\n')
 public={k:meta[k] for k in ['schema_version','prepared_at','status','target','issuer','issuer_status','nacos_group','accounts','oauth_clients','synthetic_admin','start_gates']}
 write(BASE/'infra/java/runtime/test-chain-metadata.json',json.dumps(public,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({'status':'prepared-not-executed','services':len(services),'schemas':list(DBS.values()),'objects':sum(v['target_tables'] for v in structures.values()),'source_dml_copied':False,'sql_executed':False,'runtime_started':False,'metadata':str(meta_path)}))
if __name__=='__main__':
 try:main()
 except Exception as e:print(json.dumps({'status':'failed','error_category':type(e).__name__,'message':str(e)}));sys.exit(1)
