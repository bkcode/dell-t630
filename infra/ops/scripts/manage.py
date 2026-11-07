#!/usr/bin/env python3
"""Assigned ops guest only; local Docker, precise mount UUID and systemd recovery."""
import argparse, base64, datetime, ipaddress, json, math, os, platform, re, subprocess, sys, time, urllib.error, urllib.parse, urllib.request, uuid
from pathlib import Path
BUNDLE=Path(__file__).resolve().parent.parent

def cfg():
    result = {}
    for line in (BUNDLE/'.env').read_text().splitlines():
        if line and not line.startswith('#'):
            k,v=line.split('=',1);result[k]=v
    return result

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
    if c['ROLE']!='ops-service':raise RuntimeError('unknown assigned role')
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

def wait_healthy():
    expected=set(compose('config','--services').split())
    end=time.monotonic()+360
    while time.monotonic()<end:
        current=states()
        try:return require_complete_health(expected,current)
        except RuntimeError:pass
        if any(x['state'] in ('dead','exited') for x in current):raise RuntimeError('target container exited; inspect private logs')
        time.sleep(3)
    raise RuntimeError('target health deadline exceeded; inspect private logs')

def systemd_unit(c,mount_unit):
    command='/usr/bin/python3 '+str(BUNDLE/'scripts'/'manage.py')
    return ('[Unit]\nDescription=Dell ops '+c['ROLE']+'\n'
            'Requires=docker.service\nBindsTo=docker.service '+mount_unit+'\n'
            'After=docker.service network-online.target '+mount_unit+'\n'
            'Wants=network-online.target\nRequiresMountsFor='+c['DATA_MOUNTPOINT']+'\n'
            'StartLimitIntervalSec=600\nStartLimitBurst=5\n\n'
            '[Service]\nType=simple\nUser=root\nWorkingDirectory='+str(BUNDLE)+'\n'
            'ExecStartPre='+command+' check\nExecStart='+command+' supervise\n'
            'ExecStop='+command+' stop\nRestart=on-failure\nRestartSec=10\n'
            'TimeoutStopSec=180\nUMask=0077\n\n[Install]\nWantedBy=multi-user.target\n')

def install_supervisor(c):
    mount_unit=run(['systemd-escape','--path','--suffix=mount',c['DATA_MOUNTPOINT']],'resolve data mount unit').strip()
    target=Path('/etc/systemd/system')/unit_name(c)
    content=systemd_unit(c,mount_unit)
    if not target.exists() or target.read_text()!=content:
        target.write_text(content);target.chmod(0o644)
        run(['systemctl','daemon-reload'],'reload target service units')
    if subprocess.run(['systemctl','is-failed','--quiet',unit_name(c)],capture_output=True).returncode==0:
        run(['systemctl','reset-failed',unit_name(c)],'reset explicit deployment retry state')
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

def data_paths(c):
    mount=canonical_path(c['DATA_MOUNTPOINT']);root=canonical_path(c['DATA_ROOT'])
    if mount==Path('/') or root==mount or not root.is_relative_to(mount):
        raise RuntimeError('data-root must resolve strictly below its dedicated mountpoint')
    paths=[root]+[root/name for name in ('prometheus','grafana','alertmanager')]
    for path in paths:canonical_path(str(path))
    return mount,root,paths

def unit_name(c):return 'dell-ops.service'

def protect_bridge_token():
    file=BUNDLE/'secrets'/'lark-bridge-token'
    if file.is_symlink() or file.resolve(strict=False)!=file or not file.is_file():
        raise RuntimeError('stable bridge token missing/symlink; generic deployment refuses rotation')
    if not re.fullmatch(rb'[A-Za-z0-9_-]{64}\n',file.read_bytes()):
        raise RuntimeError('stable bridge token format invalid')
    owner(file,(65534,65534),0o600)

def prepare_files(c):
    verify_data_mount(c)
    images=json.loads((BUNDLE/'images.lock.json').read_text())['images']
    root=Path(c['DATA_ROOT']);root.mkdir(parents=True,exist_ok=True,mode=0o750)
    for name in ('prometheus','grafana','alertmanager'):
        ids=image_uid(images[name]['reference'])
        p=root/name;p.mkdir(exist_ok=True,mode=0o750);owner(p,ids,0o750)
        if name=='grafana':owner(BUNDLE/'secrets'/'grafana-admin-password',ids)
    protect_bridge_token()
    # Credential files belong in Compose secrets, never in this public config tree.
    for p in (BUNDLE/'config').rglob('*'):
        if p.name in ('bridge-auth','lark-bridge-token'):
            raise RuntimeError('credential in public config directory refused')
        p.chmod(0o755 if p.is_dir() else 0o644)

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None

def get_http(url,authorization=None):
    headers={'Authorization':authorization} if authorization else {}
    request=urllib.request.Request(url,headers=headers,method='GET')
    try:
        with urllib.request.build_opener(NoRedirect).open(request,timeout=10) as response:
            data=response.read(1024*1024)
            if response.status!=200:raise RuntimeError('unexpected HTTP health status')
            return data
    except urllib.error.HTTPError as error:
        error.read();raise RuntimeError('HTTP health failed with status '+str(error.code)) from None

def notification_metadata():
    path=BUNDLE/'lark-notify-state.json'
    base={'health_check_sends_notifications':False,'supplier_reachability':'not-probed-by-this-health-check'}
    if not path.exists() and not path.is_symlink():return dict(base,status='not-configured-not-tested',mode=None,unit_active=False)
    try:
        if path.is_symlink() or path.resolve()!=path or path.stat().st_uid!=os.geteuid() or path.stat().st_mode&0o777!=0o600:raise ValueError()
        state=json.loads(path.read_text())
        if not isinstance(state,dict):raise ValueError()
        mode=state.get('mode')
        if mode not in ('acceptance','active') or state!={'mode':mode,'owner':'native-lark-notify','generic_prepare':'refuse-reset'}:raise ValueError()
        result=subprocess.run(['systemctl','is-active','--quiet','dell-lark-notify.service'],capture_output=True,timeout=10)
        active=result.returncode==0
        status=('lark-active' if mode=='active' else 'acceptance-only') if active else 'lark-unit-inactive'
        return dict(base,status=status,mode=mode,unit_active=active)
    except (OSError,ValueError,TypeError,subprocess.TimeoutExpired):
        return dict(base,status='invalid-notification-state',mode=None,unit_active=False)

def pve_collector_metadata(c):
    try:
        query=urllib.parse.urlencode({'query':'time() - dell_pve_collector_timestamp_seconds'})
        result=json.loads(get_http('http://'+c['SERVICE_IP']+':9090/api/v1/query?'+query))
        if result.get('status')!='success':return {'status':'query-failed','fresh':False}
        values=result.get('data',{}).get('result',[])
        if not values:return {'status':'missing','fresh':False}
        if len(values)!=1:return {'status':'ambiguous','fresh':False}
        age=float(values[0]['value'][1])
        if not math.isfinite(age):return {'status':'invalid','fresh':False}
        fresh=0<=age<=180
        return {'status':'fresh' if fresh else 'stale-or-clock-skew','fresh':fresh,'age_seconds':round(age,3),'initial_threshold_seconds':180,'query_scope':'read-only-current-Prometheus-vector'}
    except (RuntimeError,ValueError,KeyError,IndexError,OverflowError,TypeError,OSError):return {'status':'query-failed','fresh':False}

def archive_legacy_health(path,notification):
    if not path.exists() or notification['status']=='not-configured-not-tested':return
    try:old=json.loads(path.read_text())
    except (ValueError,OSError):return
    if old.get('external_notifications')!='not-configured-not-tested':return
    archive=BUNDLE/'health-history';archive.mkdir(mode=0o700,exist_ok=True);archive.chmod(0o700)
    backup=archive/('health-before-notification-metadata-'+uuid.uuid4().hex+'.json')
    fd=os.open(backup,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'wb') as out:out.write(path.read_bytes())

def health(c):
    current=require_complete_health(set(compose('config','--services').split()),states())
    host='http://'+c['SERVICE_IP']
    get_http(host+':9090/-/ready');get_http(host+':9093/-/ready')
    grafana=json.loads(get_http(host+':3000/api/health'))
    if grafana.get('database')!='ok':raise RuntimeError('Grafana database health failed')
    password=(BUNDLE/'secrets'/'grafana-admin-password').read_text().strip()
    auth='Basic '+base64.b64encode((c['GRAFANA_ADMIN_USER']+':'+password).encode()).decode()
    user=json.loads(get_http(host+':3000/api/user',auth))
    if user.get('login')!=c['GRAFANA_ADMIN_USER'] or not user.get('isGrafanaAdmin'):
        raise RuntimeError('Grafana configured administrator login failed')
    targets=json.loads(get_http(host+':9090/api/v1/targets')).get('data',{}).get('activeTargets',[])
    notification=notification_metadata();pve_metrics=pve_collector_metadata(c)
    result={'timestamp':datetime.datetime.now(datetime.timezone.utc).isoformat(),'role':'ops-service','service_ip':c['SERVICE_IP'],'containers':current,'http_readiness':'passed','grafana_admin_login':'passed','prometheus_reported_targets':len(targets),'reported_up':sum(x.get('health')=='up' for x in targets),'reported_down':sum(x.get('health')=='down' for x in targets),'coverage':'guest metrics/HTTP require separate endpoint and ACL acceptance','pve_host_metrics':pve_metrics,'external_notifications':notification['status'],'notification_metadata':notification,'readiness_scope':'ops-components-only'}
    path=BUNDLE/'health.json';archive_legacy_health(path,notification);path.write_text(json.dumps(result,indent=2)+'\n');path.chmod(0o600)
    print(json.dumps(result))

def validate_native_config():
    images=json.loads((BUNDLE/'images.lock.json').read_text())['images']
    for name,tool,target in [('prometheus','/bin/promtool','/etc/prometheus'),('alertmanager','/bin/amtool','/etc/alertmanager'),('blackbox','/bin/blackbox_exporter','/etc/blackbox_exporter')]:
        source=BUNDLE/'config'/name
        args=['docker','--host','unix:///var/run/docker.sock','run','--rm','--pull=never','--platform=linux/amd64','--network','none','--read-only','--user','65534:65534','--cap-drop=ALL','--security-opt=no-new-privileges:true','--cpus=0.5','--memory=256m','--memory-swap=256m','--pids-limit=128','--mount','type=bind,src='+str(source)+',dst='+target+',readonly','--entrypoint',tool,images[name]['reference']]
        if name=='prometheus':args+=['check','config',target+'/prometheus.yml']
        elif name=='alertmanager':
            secret=BUNDLE/'secrets'/'lark-bridge-token'
            args=args[:args.index('--entrypoint')]+['--mount','type=bind,src='+str(secret)+',dst=/run/secrets/lark-bridge-token,readonly']+args[args.index('--entrypoint'):]
            args+=['check-config',target+'/alertmanager.yml']
        else:args+=['--config.file='+target+'/blackbox.yml','--config.check']
        run(args,'native '+name+' configuration validation')

def main():
    os.umask(0o077)
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=['check','deploy','health','supervise','stop'])
    args=p.parse_args();c=cfg()
    if args.action=='stop':
        preflight(c,require_mount=False,require_ip=False);compose('stop','--timeout','90');return
    preflight(c)
    if args.action=='check':print(json.dumps({'role':'ops-service','preflight':'passed','deployment':'not-run'}));return
    if args.action=='supervise':supervise(c);return
    if args.action=='deploy':
        active=subprocess.run(['systemctl','is-active','--quiet',unit_name(c)],capture_output=True)
        if active.returncode==0:run(['systemctl','stop',unit_name(c)],'stop target ops supervisor')
        compose('stop','--timeout','90');compose('pull');prepare_files(c);validate_native_config();compose('create')
        install_supervisor(c);wait_healthy()
    health(c)

if __name__=='__main__':
    try:main()
    except Exception as error:
        print('ERROR: '+str(error),file=sys.stderr);sys.exit(1)
