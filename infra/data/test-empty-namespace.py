#!/usr/bin/python3
"""VM210 empty Nacos namespace only. No migrations, config publication or Java start."""
import argparse,datetime,time,hashlib,importlib.util,json,os,pathlib,socket,stat,subprocess,urllib.error,urllib.parse,urllib.request
BUNDLE=pathlib.Path('/opt/dell/data/test-data')
NEW_ID='23836f2e-9553-5948-84cd-431b2f241bd6'
NEW_NAME='finger-test-empty'
OLD_ID='10719261-2641-590a-b821-c8484ca955ac'
BASE='http://192.168.19.20:8848/nacos'
ROLE='finger-test-client'
CLIENT='finger_test'

def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def need(v):
 if not v:raise RuntimeError('fixed test foundation guard rejected')
def native(a):
 p=subprocess.run(a,capture_output=True,text=True,timeout=35);need(p.returncode==0);return p.stdout

def guard():
 need(os.geteuid()==0 and socket.gethostname()=='data-test'and not pathlib.Path('/etc/pve').exists())
 fs=json.loads(native(['findmnt','-J','--mountpoint','/srv/dell-data','-o','TARGET,UUID']))['filesystems'];need(len(fs)==1 and fs[0]['uuid']=='dd1773f9-aa48-4401-a9c8-caf0f66845f3')
 ips=[a['local']for i in json.loads(native(['ip','-j','-4','address']))if i['ifname']not in ['lo','docker0']and not i['ifname'].startswith(('br-','veth'))for a in i.get('addr_info',[])];need(ips==['192.168.19.20'])
 selected={}
 for line in (BUNDLE/'.env').open():
  if '='in line:
   k,v=line.rstrip('\n').split('=',1)
   if k in ['ROLE','ENVIRONMENT','SERVICE_IP','NACOS_NAMESPACE_ID','NACOS_CLIENT_USER','NACOS_CLIENT_ROLE']:selected[k]=v
 need(selected=={'ROLE':'test-data','ENVIRONMENT':'test','SERVICE_IP':'192.168.19.20','NACOS_NAMESPACE_ID':OLD_ID,'NACOS_CLIENT_USER':CLIENT,'NACOS_CLIENT_ROLE':ROLE})

def secret(name):
 p=BUNDLE/'secrets'/name;s=p.lstat();need(p.resolve()==p and stat.S_ISREG(s.st_mode)and s.st_nlink==1 and stat.S_IMODE(s.st_mode)==0o600)
 return p.read_text().strip()

class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,*a,**kw):return None
class API:
 def __init__(self):self.token=None;self.op=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
 def req(self,method,path,values=None,missing=False):
  allowed={'GET':{'/v1/console/namespaces','/v1/auth/permissions','/v1/auth/roles','/v1/ns/catalog/services','/v1/cs/configs'},'POST':{'/v1/auth/users/login','/v1/console/namespaces','/v1/auth/permissions'}}
  need(path in allowed.get(method,set()));body=None;headers={}
  if self.token:headers['Authorization']='Bearer '+self.token
  if values is not None:
   v=urllib.parse.urlencode(values)
   if method=='GET':path+='?'+v
   else:body=v.encode();headers['Content-Type']='application/x-www-form-urlencoded'
  try:
   with self.op.open(urllib.request.Request(BASE+path,data=body,method=method,headers=headers),timeout=15)as r:
    raw=r.read(1048577);need(len(raw)<=1048576)
    if not raw:return r.status,None
    try:value=json.loads(raw)
    except ValueError:
     need(method=='POST'and path.split('?')[0]in('/v1/console/namespaces','/v1/auth/permissions')and len(raw)<256);value=raw.decode('utf-8')
    return r.status,value
  except urllib.error.HTTPError as e:
   code=e.code;e.close()
   if missing and code in (403,404):return code,None
   raise RuntimeError('fixed Nacos API request rejected')from None
 def login(self,user,name):
  self.token=None;code,d=self.req('POST','/v1/auth/users/login',{'username':user,'password':secret(name)});need(code==200 and isinstance(d,dict)and d.get('accessToken'));self.token=d['accessToken']

def namespaces(api):
 _,d=api.req('GET','/v1/console/namespaces');rows=d['data'];need(isinstance(rows,list));return rows

def permission_rows(api):
 _,d=api.req('GET','/v1/auth/permissions',{'search':'accurate','pageNo':1,'pageSize':100,'role':ROLE});need(d['totalCount']<=100)
 return sorted((x['role'],x['resource'],x['action'])for x in d['pageItems'])

def role_rows(api):
 _,d=api.req('GET','/v1/auth/roles',{'search':'accurate','pageNo':1,'pageSize':100,'username':CLIENT});need(d['totalCount']<=100)
 rows=sorted((x['role'],x['username'])for x in d['pageItems']);need((ROLE,CLIENT)in rows);return rows

def metadata():
 spec=importlib.util.spec_from_file_location('test_readonly_mysql',BUNDLE/'scripts/acceptance.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 queries=["SELECT JSON_ARRAY(table_schema,table_name,COALESCE(engine,''),table_type) FROM information_schema.tables WHERE table_schema NOT IN ('mysql','sys','performance_schema','information_schema') ORDER BY table_schema,table_name;", "SELECT JSON_ARRAY(data_id,group_id,tenant_id,md5,type) FROM nacos_test.config_info ORDER BY tenant_id,group_id,data_id;",'SELECT COUNT(*) FROM nacos_test.his_config_info;']
 return [m.mysql({},q)[1]for q in queries]

def containers():
 ids=native(['docker','ps','--filter','label=com.docker.compose.project=dell-data-test-data','--quiet','--no-trunc']).split();need(len(ids)==4)
 fmt='{"ID":{{json .Id}},"Image":{{json .Image}},"PID":{{json .State.Pid}},"StartedAt":{{json .State.StartedAt}},"Status":{{json .State.Status}},"Health":{{json (index (index .State "Health") "Status")}},"RestartCount":{{json .RestartCount}},"OOM":{{json .State.OOMKilled}}}'
 rows=[json.loads(native(['docker','inspect','--format',fmt,cid]))for cid in ids];need(all(c['Status']=='running'and c['Health']=='healthy'and not c['OOM']for c in rows));return sorted(rows,key=lambda x:x['ID'])

def main():
 p=argparse.ArgumentParser();p.add_argument('--apply-empty-namespace',action='store_true');a=p.parse_args();os.umask(0o077);guard();api=API();api.login('nacos','nacos-admin-password');before_ns=namespaces(api);need(any(x['namespace']==OLD_ID for x in before_ns));perms=permission_rows(api);old_resource=(ROLE,OLD_ID+':*:*','rw');new_resource=(ROLE,NEW_ID+':*:*','rw');need(old_resource in perms and set(perms)<={old_resource,new_resource})
 before_roles=role_rows(api);before_meta=metadata();before_containers=containers();need(not any(x.get('namespaceShowName')==NEW_NAME and x['namespace']!=NEW_ID for x in before_ns));existing=next((x for x in before_ns if x['namespace']==NEW_ID),None)
 if existing:need(existing['namespaceShowName']==NEW_NAME and existing['configCount']==0)
 if not a.apply_empty_namespace:
  print(json.dumps({'status':'plan-only-no-mutations','new_namespace':{'id':NEW_ID,'name':NEW_NAME},'exists':existing is not None,'configuration_body_read':False}));return
 created=False;permission_added=False
 if existing is None:
  code,d=api.req('POST','/v1/console/namespaces',{'customNamespaceId':NEW_ID,'namespaceName':NEW_NAME,'namespaceDesc':'Empty test foundation only; no business imports or Java applications'});need(code==200 and d is True);created=True
  created_row=next((x for x in namespaces(api)if x['namespace']==NEW_ID),None);need(created_row and created_row['namespaceShowName']==NEW_NAME and created_row['configCount']==0)
 if new_resource not in perms:
  code,d=api.req('POST','/v1/auth/permissions',{'role':ROLE,'resource':NEW_ID+':*:*','action':'rw'});need(code==200);permission_added=True
 after_ns=namespaces(api);row=next(x for x in after_ns if x['namespace']==NEW_ID);need(row['namespaceShowName']==NEW_NAME and row['configCount']==0)
 for old in before_ns:need(next(x for x in after_ns if x['namespace']==old['namespace'])==old)
 need(permission_rows(api)==sorted(set(perms)|{new_resource}));need(role_rows(api)==before_roles);need(metadata()==before_meta);need(containers()==before_containers)
 code,services=api.req('GET','/v1/ns/catalog/services',{'pageNo':1,'pageSize':1,'namespaceId':NEW_ID,'groupNameParam':'','serviceNameParam':'','withInstances':'false'});need(code==200 and services['count']==0 and not services['serviceList'])
 api.login(CLIENT,'nacos-client-password')
 for attempt in range(16):
  own,_=api.req('GET','/v1/cs/configs',{'dataId':'__empty_namespace_readonly_probe__','group':'INFRA_ACCEPTANCE','tenant':NEW_ID},missing=True)
  if own==404:break
  need(own==403);time.sleep(2)
 need(own==404)
 denied,_=api.req('GET','/v1/cs/configs',{'dataId':'__empty_namespace_readonly_probe__','group':'INFRA_ACCEPTANCE','tenant':'00000000-0000-4000-8000-000000000000'},missing=True);need(denied==403)
 result={'at':now(),'status':'empty-test-Nacos-foundation-ready','namespace_id':NEW_ID,'namespace_name':NEW_NAME,'namespace_created':created,'scoped_permission_added':permission_added,'config_count':0,'registered_service_count':0,'application_user':CLIENT,'own_namespace_read_missing404':True,'unrelated_namespace_denied403':True,'existing_config_metadata_history_count_and_schema_metadata_unchanged':True,'original4_container_frames_unchanged':True,'migration_or_business_SQL_or_config_publication':False,'Java_started':False,'passwords_or_user_role_associations_reset':False,'production_touched':False,'test_backup_added':False}
 out=pathlib.Path('/root/dell-test-empty-foundation');out.mkdir(mode=0o700,exist_ok=True);need(out.resolve()==out and stat.S_IMODE(out.stat().st_mode)==0o700);f=out/'receipt.json';need(not f.exists());fd=os.open(f,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
 with os.fdopen(fd,'w')as h:json.dump(result,h,indent=2);h.write('\n')
 print(json.dumps(result))
if __name__=='__main__':
 try:main()
 except Exception as e:print(json.dumps({'status':'empty-foundation-not-confirmed','error_type':type(e).__name__,'no_automatic_delete_or_reset':True}),file=__import__('sys').stderr);raise SystemExit(1)
