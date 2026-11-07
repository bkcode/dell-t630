#!/usr/bin/env python3
"""Read only local unit/health state, atomically emit non-secret textfile metrics."""
import argparse,ipaddress,json,os,re,subprocess,tempfile,time,urllib.error,urllib.request
from pathlib import Path
from urllib.parse import urlsplit
TEXTFILE_DIR=Path('/var/lib/prometheus/node-exporter-textfile')
CONFIG=Path('/etc/dell-guest-monitoring/health.json')
ALLOWED_PATHS={'/','/actuator/health','/actuator/health/readiness','/readyz','/health','/-/ready','/api/health','/service/rest/v1/status','/nacos/v1/console/health/readiness'}

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None

def local_addresses():
    p=subprocess.run(['ip','-j','address','show'],capture_output=True,text=True,timeout=5)
    if p.returncode:raise ValueError('cannot read local interface addresses')
    return {x['local'] for a in json.loads(p.stdout) for x in a.get('addr_info',[]) if x.get('local')}

def validate(c,addresses):
    if set(c)-{'role','private_ip','textfile_directory','services','http_checks','candidate_service_units','candidate_http_checks','notes'}:raise ValueError('unknown config fields; do not put secrets or headers in health config')
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,62}',c.get('role','')):raise ValueError('invalid role label')
    if c.get('textfile_directory')!=str(TEXTFILE_DIR):raise ValueError('unexpected textfile directory')
    if c.get('private_ip') not in addresses:raise ValueError('assigned private address is not configured')
    services=c.get('services',[]);checks=c.get('http_checks',[])
    if len(services)>32 or len(checks)>8:raise ValueError('collector limits exceeded')
    if len(set(services))!=len(services):raise ValueError('duplicate unit')
    for unit in services:
        if not re.fullmatch(r'[A-Za-z0-9_.@:-]+\.service',unit):raise ValueError('invalid service unit')
    for check in checks+c.get('candidate_http_checks',[]):
        if set(check)!={'name','url'}:raise ValueError('health checks accept only name and credential-free URL')
        if not re.fullmatch(r'[A-Za-z0-9_.-]{1,80}',check.get('name','')):raise ValueError('invalid health-check label')
        u=urlsplit(check.get('url',''))
        if u.scheme not in ('http','https') or not u.hostname or u.username or u.password or u.query or u.fragment:raise ValueError('credential/query-bearing health URL rejected')
        if u.hostname!='localhost':
            try:ipaddress.ip_address(u.hostname)
            except ValueError:raise ValueError('literal local address required') from None
            if u.hostname not in addresses:raise ValueError('health endpoint must be on this guest')
        if (u.path or '/') not in ALLOWED_PATHS:raise ValueError('only health/root read paths are allowed')
        try:port=u.port or (443 if u.scheme=='https' else 80)
        except ValueError:raise ValueError('invalid local health port') from None
        if not 1<=port<=65535:raise ValueError('invalid local health port')
    return c

def unit_state(unit):
    try:p=subprocess.run(['systemctl','show','--no-pager','--property=LoadState','--property=ActiveState',unit],capture_output=True,text=True,timeout=5)
    except subprocess.TimeoutExpired:return 0,0,False
    if p.returncode:return 0,0,False
    values=dict(x.split('=',1) for x in p.stdout.splitlines() if '=' in x)
    if set(values)!={'LoadState','ActiveState'}:return 0,0,False
    return int(values['LoadState']=='loaded'),int(values['ActiveState']=='active'),True

def http_state(url):
    try:
        request=urllib.request.Request(url,method='GET',headers={'User-Agent':'dell-local-health/1'})
        with urllib.request.build_opener(NoRedirect).open(request,timeout=3) as response:
            response.read(1024)
            return int(response.status==200),response.status
    except urllib.error.HTTPError as error:
        code=error.code;error.close();return 0,code
    except (OSError,ValueError):return 0,0

def label(value):return value.replace('\\','\\\\').replace('"','\\"').replace('\n','\\n')

def collect(c):
    role='role="'+label(c['role'])+'"';lines=[];read_ok=True
    lines+=['# TYPE dell_guest_service_present gauge','# TYPE dell_guest_service_active gauge']
    for unit in c.get('services',[]):
        present,active,readable=unit_state(unit);read_ok=read_ok and readable
        tags=role+',service="'+label(unit)+'"'
        lines+=['dell_guest_service_present{'+tags+'} '+str(present),'dell_guest_service_active{'+tags+'} '+str(active)]
    lines+=['# TYPE dell_guest_http_up gauge','# TYPE dell_guest_http_status_code gauge']
    for check in c.get('http_checks',[]):
        up,code=http_state(check['url']);tags=role+',check="'+label(check['name'])+'"'
        lines+=['dell_guest_http_up{'+tags+'} '+str(up),'dell_guest_http_status_code{'+tags+'} '+str(code)]
    lines+=['# TYPE dell_guest_health_collection_success gauge','dell_guest_health_collection_success{'+role+'} '+str(int(read_ok)),'# TYPE dell_guest_health_collection_timestamp_seconds gauge','dell_guest_health_collection_timestamp_seconds{'+role+'} '+format(time.time(),'.3f')]
    return '\n'.join(lines)+'\n',read_ok

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--config',type=Path,default=CONFIG);p.add_argument('--check',action='store_true');args=p.parse_args()
    if args.config.is_symlink():raise ValueError('collector config symlink rejected')
    st=args.config.stat()
    if st.st_uid!=0 or st.st_mode&0o022:raise ValueError('collector config must be root-owned and not group/world writable')
    c=validate(json.loads(args.config.read_text()),local_addresses());body,read_ok=collect(c)
    if args.check:
        if not read_ok:raise ValueError('unit status read access unavailable for this account')
        print(json.dumps({'role':c['role'],'read_access':'passed','metrics_written':False,'services':len(c.get('services',[])),'local_http_checks':len(c.get('http_checks',[]))}));return
    if not TEXTFILE_DIR.is_dir() or TEXTFILE_DIR.resolve()!=TEXTFILE_DIR:raise ValueError('textfile directory must exist and not resolve through symlinks')
    fd,name=tempfile.mkstemp(prefix='.dell-guest-health-',suffix='.tmp',dir=TEXTFILE_DIR)
    try:
        with os.fdopen(fd,'w') as out:out.write(body)
        os.chmod(name,0o644);os.replace(name,TEXTFILE_DIR/'dell_guest_health.prom')
    finally:
        if os.path.exists(name):os.unlink(name)
    print(json.dumps({'role':c['role'],'metrics_written':True,'collection_success':read_ok,'notifications_sent':False}))

if __name__=='__main__':
    try:main()
    except (ValueError,OSError,KeyError,subprocess.TimeoutExpired) as error:raise SystemExit('LOCAL HEALTH ERROR: '+str(error))
