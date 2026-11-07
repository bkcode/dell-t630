#!/usr/bin/env python3
"""Real local auth and isolated synthetic persistence fixtures; never handles source business data."""
import argparse,base64,importlib.util,json,os,re,socket,subprocess,sys,time,urllib.error,urllib.parse,urllib.request,uuid
from pathlib import Path
sys.dont_write_bytecode=True
BUNDLE=Path(__file__).resolve().parent.parent
spec=importlib.util.spec_from_file_location('data_manager',BUNDLE/'scripts/manage.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
STATE=BUNDLE/'acceptance-fixture.json'

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None

class Redis:
    def __init__(self,c,auth=True):
        self.socket=socket.create_connection((c['SERVICE_IP'],6379),timeout=10)
        self.file=self.socket.makefile('rb')
        if auth and self.call('AUTH',m.read_secret('redis-password'))!='OK':raise RuntimeError('Redis authentication failed')
    def call(self,*values):
        raw=[str(x).encode() for x in values];wire=b'*'+str(len(raw)).encode()+b'\r\n'+b''.join(b'$'+str(len(x)).encode()+b'\r\n'+x+b'\r\n' for x in raw)
        self.socket.sendall(wire);file=self.file
        kind=file.read(1);line=file.readline().rstrip(b'\r\n')
        if kind==b'-':raise RuntimeError('Redis command rejected: '+line.split(b' ',1)[0].decode())
        if kind==b'+':return line.decode()
        if kind==b':':return int(line)
        if kind==b'$':
            length=int(line)
            if length==-1:return None
            data=file.read(length);file.read(2);return data.decode()
        raise RuntimeError('unexpected Redis protocol response')
    def close(self):self.file.close();self.socket.close()

class Rabbit:
    def __init__(self,c):self.base='http://'+c['SERVICE_IP']+':15672';self.c=c
    def api(self,method,path,data=None,auth=True,missing=False):
        headers={}
        if auth:headers['Authorization']='Basic '+base64.b64encode((self.c['RABBIT_ADMIN_USER']+':'+m.read_secret('rabbit-admin-password')).encode()).decode()
        if data is not None:headers['Content-Type']='application/json'
        request=urllib.request.Request(self.base+path,data=json.dumps(data).encode() if data is not None else None,method=method,headers=headers)
        try:
            with urllib.request.build_opener(NoRedirect).open(request,timeout=15) as response:body=response.read()
        except urllib.error.HTTPError as error:
            code=error.code;error.close()
            if missing and code==404:return None
            raise RuntimeError('Rabbit management API HTTP '+str(code)) from None
        return json.loads(body) if body else None

def mysql(c,sql,admin=True,allow_error=False):
    password='/run/secrets/mysql-root-password' if admin else '/run/secrets/nacos-db-password'
    login='--protocol=socket --user=root' if admin else '--protocol=TCP --host=127.0.0.1 --user="$MYSQL_USER" --database="$MYSQL_DATABASE"'
    shell='export MYSQL_PWD="$(cat '+password+')"; exec mysql '+login+' --batch --skip-column-names'
    args=['docker','--host','unix:///var/run/docker.sock','compose','--env-file',str(BUNDLE/'.env'),'-f',str(BUNDLE/'compose.yaml'),'exec','-T','mysql','sh','-c',shell]
    p=subprocess.run(args,input=sql,text=True,capture_output=True,timeout=45)
    if p.returncode and not allow_error:raise RuntimeError('MySQL authenticated query failed; server output suppressed')
    return p.returncode,p.stdout.strip()

def auth(c):
    result={}
    if c['ROLE'] in ('prod-db','test-data'):
        _,version=mysql(c,'SELECT VERSION();')
        if not version.startswith('8.4.5'):raise RuntimeError('MySQL version mismatch')
        _,one=mysql(c,'SELECT 1;')
        if one!='1':raise RuntimeError('MySQL root authentication failed')
        _,tables=mysql(c,'SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=DATABASE();',False)
        if tables!='12':raise RuntimeError('Nacos DB application account schema check failed')
        denied,_=mysql(c,'SELECT user FROM mysql.user LIMIT 1;',False,True)
        if denied==0:raise RuntimeError('Nacos DB application user has unexpected system DB access')
        result['mysql']={'version':version,'root_authenticated':True,'nacos_db_user_authenticated':True,'nacos_db_user_system_database_denied':True}
    if c['ROLE'] in ('prod-infra','test-data'):
        client=Redis(c)
        try:
            if client.call('PING')!='PONG':raise RuntimeError('Redis PING failed')
        finally:client.close()
        anon=Redis(c,False)
        try:
            try:anon.call('PING')
            except RuntimeError as error:
                if 'NOAUTH' not in str(error):raise
            else:raise RuntimeError('anonymous Redis access unexpectedly allowed')
        finally:anon.close()
        result['redis']={'authenticated':True,'anonymous_denied':True}
        result['nacos']=m.Nacos(c).verify()
        result['rabbitmq']=m.amqp_probe(c)
        rabbit=Rabbit(c);who=rabbit.api('GET','/api/whoami')
        if who.get('name')!=c['RABBIT_ADMIN_USER']:raise RuntimeError('Rabbit management identity mismatch')
        result['rabbitmq']['management_authenticated']=True
    return result

def fixture(c):
    state=json.loads(STATE.read_text())
    if state['role']!=c['ROLE'] or state['environment']!=c['ENVIRONMENT'] or not re.fullmatch('[a-f0-9]{32}',state['nonce']):raise RuntimeError('fixture ownership mismatch')
    nonce=state['nonce'];env=c['ENVIRONMENT']
    if state['database']!='dell_acceptance_'+env+'_'+nonce[:8] or state['redis_key']!='dell:acceptance:'+env+':'+nonce or state['rabbit_vhost']!='/dell-acceptance-'+env+'-'+nonce[:8] or state['nacos_data_id']!='dell_acceptance_'+nonce:raise RuntimeError('fixture object name mismatch')
    return state

def nacos(c):
    n=m.Nacos(c);n.token=n.login(c['NACOS_CLIENT_USER'],m.read_secret('nacos-client-password'));return n

def prepare(c):
    if STATE.exists():raise RuntimeError('fixture already exists; verify/clean owned fixture before preparing another')
    nonce=uuid.uuid4().hex;env=c['ENVIRONMENT']
    state={'role':c['ROLE'],'environment':env,'nonce':nonce,'database':'dell_acceptance_'+env+'_'+nonce[:8],'redis_key':'dell:acceptance:'+env+':'+nonce,'rabbit_vhost':'/dell-acceptance-'+env+'-'+nonce[:8],'queue':'dell.acceptance.persist','nacos_data_id':'dell_acceptance_'+nonce,'nacos_group':'DELL_ACCEPTANCE','payload':'synthetic-infrastructure-acceptance:'+nonce,'real_business_message':False}
    STATE.write_text(json.dumps(state,indent=2)+'\n');STATE.chmod(0o600)
    if c['ROLE'] in ('prod-db','test-data'):
        db=state['database'];mysql(c,'CREATE DATABASE `'+db+'`; CREATE TABLE `'+db+'`.persistence_fixture (id VARCHAR(64) PRIMARY KEY, value VARCHAR(128) NOT NULL); INSERT INTO `'+db+'`.persistence_fixture VALUES (\''+nonce+'\',\''+state['payload']+'\');')
    if c['ROLE'] in ('prod-infra','test-data'):
        client=Redis(c)
        try:
            if client.call('SET',state['redis_key'],state['payload'])!='OK':raise RuntimeError('Redis isolated fixture write failed')
        finally:client.close()
        n=nacos(c)
        if n.request('POST','/v1/cs/configs',{'tenant':c['NACOS_NAMESPACE_ID'],'dataId':state['nacos_data_id'],'group':state['nacos_group'],'content':state['payload'],'type':'text'}) is not True:raise RuntimeError('Nacos isolated config write failed')
        rabbit=Rabbit(c);v=urllib.parse.quote(state['rabbit_vhost'],safe='');admin=urllib.parse.quote(c['RABBIT_ADMIN_USER'],safe='');queue=urllib.parse.quote(state['queue'],safe='')
        rabbit.api('PUT','/api/vhosts/'+v,{})
        rabbit.api('PUT','/api/permissions/'+v+'/'+admin,{'configure':'.*','write':'.*','read':'.*'})
        rabbit.api('PUT','/api/queues/'+v+'/'+queue,{'durable':True,'auto_delete':False,'arguments':{}})
        published=rabbit.api('POST','/api/exchanges/'+v+'/amq.default/publish',{'properties':{'delivery_mode':2,'content_type':'text/plain'},'routing_key':state['queue'],'payload':state['payload'],'payload_encoding':'string'})
        if not published.get('routed'):raise RuntimeError('synthetic fixture message did not route to dedicated vhost')
        time.sleep(2)
    return {'fixture_created':True,'nonce':nonce,'scope':'isolated disposable objects; no business data or real business messages'}

def verify(c):
    state=fixture(c);result={}
    if c['ROLE'] in ('prod-db','test-data'):
        _,value=mysql(c,'SELECT value FROM `'+state['database']+'`.persistence_fixture WHERE id=\''+state['nonce']+'\';')
        if value!=state['payload']:raise RuntimeError('MySQL persistence fixture mismatch')
        result['mysql_fixture_persisted']=True
    if c['ROLE'] in ('prod-infra','test-data'):
        client=Redis(c)
        try:
            if client.call('GET',state['redis_key'])!=state['payload']:raise RuntimeError('Redis persistence fixture mismatch')
        finally:client.close()
        n=nacos(c)
        value=n.request('GET','/v1/cs/configs',{'tenant':c['NACOS_NAMESPACE_ID'],'dataId':state['nacos_data_id'],'group':state['nacos_group']})
        if value!=state['payload']:raise RuntimeError('Nacos persistence fixture mismatch')
        v=urllib.parse.quote(state['rabbit_vhost'],safe='');queue=urllib.parse.quote(state['queue'],safe='')
        response=Rabbit(c).api('POST','/api/queues/'+v+'/'+queue+'/get',{'count':1,'ackmode':'ack_requeue_true','encoding':'auto','truncate':10000})
        if not response or response[0].get('payload')!=state['payload'] or response[0].get('properties',{}).get('delivery_mode')!=2:raise RuntimeError('Rabbit durable synthetic fixture mismatch')
        result.update(redis_fixture_persisted=True,nacos_fixture_persisted=True,rabbit_durable_fixture_persisted=True,real_business_messages_sent=False)
    return result

def cleanup(c):
    state=fixture(c)
    if c['ROLE'] in ('prod-db','test-data'):mysql(c,'DROP DATABASE IF EXISTS `'+state['database']+'`;')
    if c['ROLE'] in ('prod-infra','test-data'):
        client=Redis(c)
        try:client.call('DEL',state['redis_key'])
        finally:client.close()
        n=nacos(c);n.request('DELETE','/v1/cs/configs?'+urllib.parse.urlencode({'tenant':c['NACOS_NAMESPACE_ID'],'dataId':state['nacos_data_id'],'group':state['nacos_group']}))
        Rabbit(c).api('DELETE','/api/vhosts/'+urllib.parse.quote(state['rabbit_vhost'],safe=''),missing=True)
    STATE.unlink();return {'owned_fixture_cleaned':True,'business_objects_modified':False}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['auth','prepare','verify','cleanup']);args=p.parse_args();c=m.cfg();m.preflight(c)
    m.require_complete_health(set(m.compose('config','--services').split()),m.states())
    if args.action=='auth':result=auth(c)
    elif args.action=='prepare':result=prepare(c)
    elif args.action=='verify':result=verify(c)
    else:result=cleanup(c)
    print(json.dumps({'role':c['ROLE'],'action':args.action,'result':result,'source_business_data_imported':False,'secrets_values_emitted':False}))

if __name__=='__main__':
    try:main()
    except Exception as error:raise SystemExit('DATA ACCEPTANCE ERROR: '+str(error))
