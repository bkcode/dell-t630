#!/usr/bin/env python3
"""Run on the assigned Linux guest only. Never prints credentials or API bodies."""
import argparse, base64, datetime, ipaddress, json, os, platform, re, socket, struct, subprocess, sys, time, urllib.error, urllib.parse, urllib.request, uuid
from pathlib import Path

BUNDLE = Path(__file__).resolve().parent.parent

def cfg():
    result = {}
    for line in (BUNDLE/'.env').read_text().splitlines():
        if line and not line.startswith('#'):
            k,v=line.split('=',1);result[k]=v
    return result

def read_secret(name):
    return (BUNDLE/'secrets'/name).read_text().strip()

def run(args, label=None):
    p=subprocess.run(args,cwd=BUNDLE,capture_output=True,text=True,timeout=600)
    log=BUNDLE/'deploy-private.log'
    if log.exists() and log.stat().st_size > 2*1024*1024:
        os.replace(log, BUNDLE/'deploy-private.log.1')
    fd=os.open(log,os.O_WRONLY|os.O_CREAT|os.O_APPEND,0o600)
    with os.fdopen(fd,'a') as out:
        out.write('\n'+datetime.datetime.now(datetime.timezone.utc).isoformat()+' '+(label or args[0])+'\n'+p.stdout+p.stderr)
    os.chmod(log,0o600)
    if p.returncode:
        raise RuntimeError((label or args[0])+' failed, exit '+str(p.returncode)+'; output retained in private log')
    return p.stdout

def compose(*args):
    return run(['docker','--host','unix:///var/run/docker.sock','compose','--env-file',str(BUNDLE/'.env'),'-f',str(BUNDLE/'compose.yaml'),*args], 'compose '+args[0])

def canonical_path(value):
    if not value.startswith('/') or not re.fullmatch(r'/[A-Za-z0-9_./-]+',value):
        raise RuntimeError('absolute safe-character paths required')
    if any(x in ('.','..') for x in value.split('/')) or os.path.normpath(value)!=value:
        raise RuntimeError('non-normalized or traversal path rejected')
    path=Path(value)
    if path.resolve(strict=False)!=path:
        raise RuntimeError('symlink path components rejected')
    return path

def data_paths(c):
    mount=canonical_path(c['DATA_MOUNTPOINT'])
    root=canonical_path(c['DATA_ROOT'])
    if mount==Path('/') or root==mount or not root.is_relative_to(mount):
        raise RuntimeError('data-root must resolve strictly below its dedicated mountpoint')
    paths=[root]
    if c['ROLE'] in ('prod-db','test-data'):paths.append(root/'mysql')
    if c['ROLE'] in ('prod-infra','test-data'):
        paths.extend(root/sub for sub in ['redis','rabbitmq','nacos','nacos/logs','nacos/data'])
    for path in paths:canonical_path(str(path))
    return mount,root,paths

def filesystem(path,exact_mount=False):
    flag='--mountpoint' if exact_mount else '--target'
    raw=run(['findmnt','--json',flag,str(path),'--output','TARGET,SOURCE,UUID,FSTYPE,OPTIONS'],'verify data mount identity')
    items=json.loads(raw).get('filesystems',[])
    if len(items)!=1:raise RuntimeError('data filesystem lookup was not unique')
    return items[0]

def verify_data_mount(c):
    mount,root,paths=data_paths(c)
    try:expected_uuid=str(uuid.UUID(c.get('DATA_FS_UUID','')))
    except ValueError:raise RuntimeError('DATA_FS_UUID must be the measured guest filesystem UUID') from None
    probe=subprocess.run(['mountpoint','-q',str(mount)],capture_output=True)
    if probe.returncode:raise RuntimeError('dedicated data mountpoint is not mounted')
    mounted=filesystem(mount,True)
    if mounted.get('target')!=str(mount) or str(mounted.get('uuid','')).lower()!=expected_uuid:
        raise RuntimeError('dedicated mountpoint or filesystem UUID mismatch')
    if mounted.get('fstype') not in ('ext4','xfs','btrfs') or 'rw' not in mounted.get('options','').split(','):
        raise RuntimeError('persistent writable data filesystem required')
    for path in paths:
        existing=path
        while not existing.exists():existing=existing.parent
        if existing!=mount and not existing.is_relative_to(mount):
            raise RuntimeError('data path escaped its mount')
        actual=filesystem(existing)
        if any(actual.get(key)!=mounted.get(key) for key in ('target','source','uuid')):
            raise RuntimeError('data path resolves to another or nested filesystem')
    return mounted

def preflight(c,require_mount=True,require_ip=True):
    if os.geteuid()!=0:raise RuntimeError('run as root on the assigned guest')
    if Path('/etc/pve').exists():raise RuntimeError('refusing to operate on PVE host')
    if platform.system()!='Linux' or platform.machine() not in ('x86_64','amd64'):raise RuntimeError('assigned Linux AMD64 guest required')
    if c['ROLE'] not in ('prod-db','prod-infra','test-data'):raise RuntimeError('unknown assigned role')
    if canonical_path(c['INSTALL_DIR'])!=BUNDLE:raise RuntimeError('bundle must run from its assigned install directory')
    ipaddress.IPv4Address(c['SERVICE_IP'])
    if require_ip:
        addresses=json.loads(run(['ip','-j','address','show'],'read guest addresses'))
        actual={x.get('local') for a in addresses for x in a.get('addr_info',[])}
        if c['SERVICE_IP'] not in actual:raise RuntimeError('SERVICE_IP is not assigned to this guest; refusing deployment')
    if os.environ.get('DOCKER_HOST','') not in ('','unix:///var/run/docker.sock'):
        raise RuntimeError('remote Docker host override is not allowed')
    arch=run(['docker','--host','unix:///var/run/docker.sock','info','--format','{{.Architecture}}'],'read local Docker architecture').strip()
    if arch not in ('x86_64','amd64'):raise RuntimeError('local Docker daemon is not AMD64')
    model=json.loads(compose('config','--format','json'))
    if any(service.get('restart')!='no' for service in model['services'].values()):
        raise RuntimeError('systemd must exclusively own container restart')
    if any(volume.get('type')=='bind' and volume.get('bind',{}).get('create_host_path') is not False for service in model['services'].values() for volume in service.get('volumes',[])):
        raise RuntimeError('all bind mounts must disable automatic host path creation')
    if require_mount:verify_data_mount(c)

def image_uid(image,user=None):
    base=['docker','--host','unix:///var/run/docker.sock','run','--rm','--network','none','--entrypoint','id',image]
    uid=int(run(base+['-u']+([user] if user else []),'query image uid').strip())
    gid=int(run(base+['-g']+([user] if user else []),'query image gid').strip())
    return uid,gid

def owner(path,ids,mode=0o600):
    os.chown(path,*ids);os.chmod(path,mode)

def prepare_files(c):
    verify_data_mount(c)
    lock=json.loads((BUNDLE/'images.lock.json').read_text())['images']
    role=c['ROLE']; root=Path(c['DATA_ROOT']);root.mkdir(parents=True,exist_ok=True,mode=0o750)
    if role in ('prod-db','test-data'):
        uid=image_uid(lock['mysql']['reference'],'mysql')
        p=root/'mysql';p.mkdir(exist_ok=True,mode=0o750);os.chown(p,*uid)
        for name in ['mysql-root-password','nacos-db-password']:owner(BUNDLE/'secrets'/name,uid)
        owner(BUNDLE/'config'/'mysql.cnf',uid)
        owner(BUNDLE/'vendor'/'nacos-mysql-schema-2.4.3.sql',uid)
    if role in ('prod-infra','test-data'):
        sysctl=Path('/etc/sysctl.d/60-dell-redis-overcommit.conf')
        if sysctl.is_symlink():raise RuntimeError('Redis guest sysctl path symlink rejected')
        desired='vm.overcommit_memory = 1\n'
        if not sysctl.exists() or sysctl.read_text()!=desired:
            sysctl.write_text(desired);sysctl.chmod(0o644)
        run(['sysctl','-w','vm.overcommit_memory=1'],'configure Redis guest memory overcommit')
        uid=image_uid(lock['redis']['reference'],'redis')
        p=root/'redis';p.mkdir(exist_ok=True,mode=0o750);os.chown(p,*uid)
        owner(BUNDLE/'secrets'/'redis-password',uid)
        uid=image_uid(lock['rabbitmq']['reference'],'rabbitmq')
        p=root/'rabbitmq';p.mkdir(exist_ok=True,mode=0o750);os.chown(p,*uid)
        owner(BUNDLE/'secrets'/'rabbit-definitions.json',uid)
        owner(BUNDLE/'config'/'rabbitmq.conf',uid)
        uid=image_uid(lock['nacos']['reference'])
        for sub in ['nacos','nacos/logs','nacos/data']:
            p=root/sub;p.mkdir(parents=True,exist_ok=True,mode=0o750);os.chown(p,*uid)
        for name in ['nacos-db-password','nacos-auth-token','nacos-identity-value']:owner(BUNDLE/'secrets'/name,uid)
        owner(BUNDLE/'vendor'/'nacos-application-2.4.3.properties',uid)

def states():
    names=compose('ps','--all','--quiet').split()
    if not names:return []
    raw=json.loads(run(['docker','--host','unix:///var/run/docker.sock','inspect',*names],'inspect target health'))
    return [{'service':d['Config']['Labels']['com.docker.compose.service'],'state':d['State']['Status'],'health':d['State'].get('Health',{}).get('Status'),'restart_count':d['RestartCount']} for d in raw]

def require_complete_health(expected,current):
    names=[item['service'] for item in current]
    if len(names)!=len(expected) or set(names)!=set(expected):
        raise RuntimeError('configured and actual service sets differ')
    if not all(item['state']=='running' and item['health']=='healthy' for item in current):
        raise RuntimeError('not all configured role containers are healthy')
    return current

def wait_healthy(startup_exit_grace=0):
    expected=set(compose('config','--services').split())
    started=time.monotonic();end=started+360
    while time.monotonic()<end:
        current=states()
        try:return require_complete_health(expected,current)
        except RuntimeError:pass
        if any(x['state']=='dead' for x in current):raise RuntimeError('target container is dead; inspect private logs')
        if any(x['state']=='exited' for x in current) and time.monotonic()-started>=startup_exit_grace:raise RuntimeError('target container exited; inspect private logs')
        time.sleep(3)
    raise RuntimeError('target health deadline exceeded; inspect private logs')

class Nacos:
    def __init__(self,c):self.c=c;self.base='http://'+c['SERVICE_IP']+':8848/nacos';self.token=None
    def request(self,method,path,values=None,auth=True):
        headers={}
        if auth and self.token:headers['Authorization']='Bearer '+self.token
        data=None
        if values is not None:
            payload=urllib.parse.urlencode(values)
            if method=='GET':path+='?'+payload
            else:data=payload.encode();headers['Content-Type']='application/x-www-form-urlencoded'
        request=urllib.request.Request(self.base+path,data=data,method=method,headers=headers)
        try:
            with urllib.request.urlopen(request,timeout=20) as response:body=response.read()
        except urllib.error.HTTPError as error:
            error.read()
            raise RuntimeError('Nacos '+method+' '+path.split('?')[0]+' returned HTTP '+str(error.code)) from None
        try:return json.loads(body)
        except ValueError:return body.decode()
    def login(self,user,password):
        response=self.request('POST','/v1/auth/users/login',{'username':user,'password':password},False)
        if not isinstance(response,dict) or not response.get('accessToken'):raise RuntimeError('Nacos login did not return a token')
        return response['accessToken']
    def admin(self):self.token=self.login('nacos',read_secret('nacos-admin-password'))
    def bootstrap(self):
        try:self.admin()
        except RuntimeError:
            # The official 2.4.3 API refuses initialization once a global admin exists.
            self.request('POST','/v1/auth/users/admin',{'password':read_secret('nacos-admin-password')},False)
            for attempt in range(10):
                try:self.admin();break
                except RuntimeError:
                    if attempt==9:raise
                    time.sleep(1)
        namespaces=self.request('GET','/v1/console/namespaces')
        items=namespaces.get('data',[]) if isinstance(namespaces,dict) else []
        if not any(x.get('namespace')==self.c['NACOS_NAMESPACE_ID'] for x in items):
            self.request('POST','/v1/console/namespaces',{'customNamespaceId':self.c['NACOS_NAMESPACE_ID'],'namespaceName':'finger-'+self.c['ENVIRONMENT'],'namespaceDesc':'Isolated '+self.c['ENVIRONMENT']+' environment'})
        params={'search':'accurate','pageNo':1,'pageSize':100,'username':self.c['NACOS_CLIENT_USER']}
        users=self.request('GET','/v1/auth/users',params)
        if not any(x.get('username')==self.c['NACOS_CLIENT_USER'] for x in users.get('pageItems',[])):
            self.request('POST','/v1/auth/users',{'username':self.c['NACOS_CLIENT_USER'],'password':read_secret('nacos-client-password')})
        self.login(self.c['NACOS_CLIENT_USER'],read_secret('nacos-client-password'))
        roles=self.request('GET','/v1/auth/roles',{**params,'role':self.c['NACOS_CLIENT_ROLE']})
        if not any(x.get('role')==self.c['NACOS_CLIENT_ROLE'] and x.get('username')==self.c['NACOS_CLIENT_USER'] for x in roles.get('pageItems',[])):
            self.request('POST','/v1/auth/roles',{'role':self.c['NACOS_CLIENT_ROLE'],'username':self.c['NACOS_CLIENT_USER']})
        resource=self.c['NACOS_NAMESPACE_ID']+':*:*'
        permissions=self.request('GET','/v1/auth/permissions',{'search':'accurate','pageNo':1,'pageSize':100,'role':self.c['NACOS_CLIENT_ROLE']})
        if not any(x.get('resource')==resource and x.get('action')=='rw' for x in permissions.get('pageItems',[])):
            self.request('POST','/v1/auth/permissions',{'role':self.c['NACOS_CLIENT_ROLE'],'resource':resource,'action':'rw'})
    def config_status(self,namespace):
        query=urllib.parse.urlencode({'dataId':'__dell_infra_readonly_probe__','group':'INFRA_ACCEPTANCE','tenant':namespace})
        request=urllib.request.Request(self.base+'/v1/cs/configs?'+query,headers={'Authorization':'Bearer '+self.token})
        try:
            with urllib.request.urlopen(request,timeout=20) as response:
                response.read();return response.status
        except urllib.error.HTTPError as error:
            error.read();return error.code
    def verify(self):
        self.admin()
        response=self.request('GET','/v1/console/namespaces')
        if not any(x.get('namespace')==self.c['NACOS_NAMESPACE_ID'] for x in response.get('data',[])):raise RuntimeError('Nacos namespace missing')
        self.token=self.login(self.c['NACOS_CLIENT_USER'],read_secret('nacos-client-password'))
        if self.config_status(self.c['NACOS_NAMESPACE_ID']) not in (200,404):
            raise RuntimeError('Nacos client cannot read its own namespace')
        other='00000000-0000-4000-8000-000000000000'
        if other==self.c['NACOS_NAMESPACE_ID']:other='00000000-0000-4000-8000-000000000001'
        if self.config_status(other)!=403:
            raise RuntimeError('Nacos client is not restricted to its assigned namespace')
        return {'admin_login':True,'client_login':True,'namespace_present':True,'client_namespace_read':True,'other_namespace_denied':True}

def exact(sock,size):
    out=b''
    while len(out)<size:
        data=sock.recv(size-len(out))
        if not data:raise RuntimeError('AMQP peer closed connection')
        out+=data
    return out

def frame(sock):
    kind,channel,size=struct.unpack('!BHI',exact(sock,7));payload=exact(sock,size)
    if exact(sock,1)!=b'\xce':raise RuntimeError('invalid AMQP frame')
    if kind!=1 or channel!=0:raise RuntimeError('unexpected AMQP frame')
    return payload

def send_method(sock,method,payload=b''):
    data=struct.pack('!HH',10,method)+payload
    sock.sendall(struct.pack('!BHI',1,0,len(data))+data+b'\xce')

def short(value):
    data=value.encode();return bytes([len(data)])+data

def amqp_probe(c):
    with socket.create_connection((c['SERVICE_IP'],5672),timeout=10) as sock:
        sock.sendall(b'AMQP\x00\x00\x09\x01')
        if frame(sock)[:4]!=struct.pack('!HH',10,10):raise RuntimeError('AMQP start missing')
        auth=b'\0'+c['RABBIT_APP_USER'].encode()+b'\0'+read_secret('rabbit-app-password').encode()
        send_method(sock,11,b'\0\0\0\0'+short('PLAIN')+struct.pack('!I',len(auth))+auth+short('en_US'))
        tune=frame(sock)
        if tune[:4]!=struct.pack('!HH',10,30):raise RuntimeError('AMQP authentication failed')
        channels,size,_=struct.unpack('!HIH',tune[4:])
        send_method(sock,31,struct.pack('!HIH',channels,size,0))
        send_method(sock,40,short(c['RABBIT_VHOST'])+b'\0\0')
        if frame(sock)[:4]!=struct.pack('!HH',10,41):raise RuntimeError('AMQP vhost access failed')
    return {'app_authentication':True,'vhost_access':True,'messages_published':0}

def health(c):
    current=states()
    require_complete_health(set(compose('config','--services').split()),current)
    result={'timestamp':datetime.datetime.now(datetime.timezone.utc).isoformat(),'role':c['ROLE'],'service_ip':c['SERVICE_IP'],'containers':current,'business_data_migration_status':'not-checked-by-this-health-probe','readiness_scope':'infrastructure-only'}
    if c['ROLE'] in ('prod-infra','test-data'):
        result['nacos']=Nacos(c).verify()
        result['rabbitmq']=amqp_probe(c)
    path=BUNDLE/'health.json';path.write_text(json.dumps(result,indent=2)+'\n');path.chmod(0o600)
    print(json.dumps(result))

def unit_name(c):
    return 'dell-data-'+c['ROLE']+'.service'

def systemd_unit(c,mount_unit):
    command='/usr/bin/python3 '+str(BUNDLE/'scripts'/'manage.py')
    return ('[Unit]\nDescription=Dell data '+c['ROLE']+'\n'
            'Requires=docker.service\nBindsTo=docker.service '+mount_unit+'\n'
            'After=docker.service network-online.target '+mount_unit+'\n'
            'Wants=network-online.target\nRequiresMountsFor='+c['DATA_MOUNTPOINT']+'\n'
            'StartLimitIntervalSec=600\nStartLimitBurst=5\n\n'
            '[Service]\nType=simple\nUser=root\nWorkingDirectory='+str(BUNDLE)+'\n'
            'ExecStartPre='+command+' check\nExecStart='+command+' supervise\n'
            'ExecStop='+command+' stop\nRestart=on-failure\nRestartSec=10\n'
            'TimeoutStopSec=180\nUMask=0077\n\n[Install]\nWantedBy=multi-user.target\n')

def reset_failed_unit_if_needed(c):
    failed=subprocess.run(['systemctl','is-failed','--quiet',unit_name(c)],capture_output=True)
    if failed.returncode==0:
        run(['systemctl','reset-failed',unit_name(c)],'reset explicit deployment retry state')

def install_supervisor(c):
    mount_unit=run(['systemd-escape','--path','--suffix=mount',c['DATA_MOUNTPOINT']],'resolve data mount unit').strip()
    target=Path('/etc/systemd/system')/unit_name(c)
    content=systemd_unit(c,mount_unit)
    if not target.exists() or target.read_text()!=content:
        target.write_text(content);target.chmod(0o644)
        run(['systemctl','daemon-reload'],'reload target service units')
    reset_failed_unit_if_needed(c)
    run(['systemctl','enable','--now',unit_name(c)],'enable mount-controlled data supervisor')

def supervise(c):
    # Docker has restart=no. This process and systemd own all recovery.
    try:
        verify_data_mount(c)
        compose('up','-d')
        wait_healthy()
        expected=set(compose('config','--services').split())
        while True:
            verify_data_mount(c)
            require_complete_health(expected,states())
            time.sleep(5)
    finally:
        # Keep this independent of mount/IP availability: stop writers on failure.
        compose('stop','--timeout','90')

def main():
    os.umask(0o077)
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['check','deploy','bootstrap-nacos','health','supervise','stop'])
    args=parser.parse_args(); c=cfg()
    if args.action=='stop':
        preflight(c,require_mount=False,require_ip=False)
        compose('stop','--timeout','90');return
    preflight(c)
    if args.action=='check':print(json.dumps({'role':c['ROLE'],'preflight':'passed','deployment':'not-run'}));return
    if args.action=='supervise':supervise(c);return
    if args.action=='deploy':
        active=subprocess.run(['systemctl','is-active','--quiet',unit_name(c)],capture_output=True)
        if active.returncode==0:run(['systemctl','stop',unit_name(c)],'stop previous target supervisor')
        compose('stop','--timeout','90')
        compose('pull','--policy','missing');prepare_files(c)
        compose('create')
        install_supervisor(c)
        wait_healthy(startup_exit_grace=15)
    if args.action in ('deploy','bootstrap-nacos') and c['ROLE'] in ('prod-infra','test-data'):
        Nacos(c).bootstrap()
    health(c)

if __name__=='__main__':
    try:main()
    except Exception as error:
        print('ERROR: '+str(error),file=sys.stderr);sys.exit(1)
