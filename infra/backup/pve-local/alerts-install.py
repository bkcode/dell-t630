#!/usr/bin/env python3
"""PREPARED ONLY. One fixed Prometheus rule file; no Compose or notification receiver changes."""
import argparse,hashlib,json,os,socket,stat,subprocess,tempfile,time,urllib.error,urllib.parse,urllib.request
from pathlib import Path
RULE=Path('/opt/dell/ops/config/prometheus/rules/pve-local-backup.yml')
CONFIG=Path('/opt/dell/ops/config/prometheus/prometheus.yml')
BASE=Path('/root/dell-backup-alerts')
D=['/usr/bin/docker','--host','unix:///var/run/docker.sock']
PROM='dell-ops-prometheus-1'
EXPECTED_CONFIG_SHA='35b0a682e8cef2802cd871982e442614e67ae3313f39945ace2591879f508c04'
ALERTS={'PveLocalBackupFailed','PveLocalBackupStale','PveLocalBackupStateInvalid'}
ENV={'PATH':'/usr/sbin:/usr/bin:/sbin:/bin','LANG':'C','LC_ALL':'C'}


def run(args):
    p=subprocess.run(args,capture_output=True,text=True,timeout=60,env=ENV)
    if p.returncode:raise RuntimeError('native fixed validation failed; raw details withheld')
    return p.stdout


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def get(path):
    if not (path.startswith('/api/v1/query?') or path in ['/api/v1/status/runtimeinfo','/api/v1/rules','/-/ready']):raise RuntimeError('fixed Prometheus routes only')
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self,*args,**kwargs):return None
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
    req=urllib.request.Request('http://192.168.19.70:9090'+path,method='GET')
    with opener.open(req,timeout=15) as response:
        raw=response.read(1024*1024+1)
        if response.status!=200 or len(raw)>1024*1024:raise RuntimeError('bounded Prometheus response required')
        if path=='/-/ready':return {'ready':True}
        return json.loads(raw) if raw else None


def query(name):
    allowed={'enabled','last_success_timestamp_seconds','last_run_success','running','state_valid','verified_guest_count'}
    if name not in allowed:raise RuntimeError('fixed backup metrics only')
    value=get('/api/v1/query?'+urllib.parse.urlencode({'query':'dell_pve_local_backup_'+name}))
    if value.get('status')!='success':raise RuntimeError('Prometheus metric query failed')
    rows=value['data']['result']
    if len(rows)!=1:raise RuntimeError('exact one expected backup metric series required')
    return float(rows[0]['value'][1])


def ready_gate():
    v={name:query(name) for name in ['enabled','last_success_timestamp_seconds','last_run_success','running','state_valid','verified_guest_count']}
    if not(v['enabled']==1 and v['state_valid']==1 and v['last_run_success']==1 and v['running']==0 and v['verified_guest_count']==11 and 0<=time.time()-v['last_success_timestamp_seconds']<129600):
        raise RuntimeError('first eleven-guest verified success and enabled healthy job must precede rule installation')
    return v


def identity():
    if os.geteuid()!=0 or socket.gethostname().split('.')[0]!='ops-service' or Path('/etc/pve').exists():raise RuntimeError('assigned Ops270 root only')
    for path in [CONFIG.parent,RULE.parent,CONFIG]:
        if path.resolve()!=path or path.stat().st_uid!=0 or path.stat().st_mode&0o022:raise RuntimeError('trusted config hierarchy required')
    addresses=json.loads(run(['/usr/sbin/ip','-j','address','show']))
    if not any(a.get('local')=='192.168.19.70' for n in addresses for a in n.get('addr_info',[])):raise RuntimeError('assigned Ops IP missing')
    fs=json.loads(run(['/usr/bin/findmnt','--json','--mountpoint','/srv/dell-data','--output','TARGET,UUID']))['filesystems']
    if len(fs)!=1 or fs[0]['target']!='/srv/dell-data' or fs[0]['uuid']!='01b1f302-27be-4fbd-b4af-b8e782d85dea':raise RuntimeError('assigned Ops data UUID missing')
    if digest(CONFIG)!=EXPECTED_CONFIG_SHA:raise RuntimeError('current config changed since readonly review; re-review instead of overwriting')
    mounts=json.loads(run(D+['inspect','--format','{{json .Mounts}}',PROM]))
    matched=[m for m in mounts if m['Destination']=='/etc/prometheus']
    if len(matched)!=1 or matched[0]['Source']!='/opt/dell/ops/config/prometheus' or matched[0]['Type']!='bind' or matched[0]['RW'] is not False:raise RuntimeError('reviewed RO config directory bind required')
    if '/etc/prometheus/rules/*.yml' not in CONFIG.read_text().splitlines():
        # Actual YAML list has '- ' prefix; do not parse any other config/secret.
        if '- /etc/prometheus/rules/*.yml' not in CONFIG.read_text().splitlines():raise RuntimeError('owned rule wildcard missing')
    return frame(PROM)


def atomic(raw):
    fd,name=tempfile.mkstemp(prefix='.pve-local-backup-',suffix='.tmp',dir=RULE.parent)
    try:
        with os.fdopen(fd,'wb') as f:os.fchmod(f.fileno(),0o644);f.write(raw);f.flush();os.fsync(f.fileno())
        os.replace(name,RULE)
    finally:
        if os.path.exists(name):os.unlink(name)


def frame(reference):
    value=json.loads(run(D+['inspect','--type','container','--format','{"ID":{{json .Id}},"imageID":{{json .Image}},"PID":{{json .State.Pid}},"StartedAt":{{json .State.StartedAt}},"restarts":{{json .RestartCount}},"running":{{json .State.Running}}}',reference]))
    if not value['running'] or value['PID']<=0:raise RuntimeError('original Prometheus process must be running')
    return value


def validate(locked):
    if frame(locked['ID'])!=locked:raise RuntimeError('locked Prometheus identity drift before validation')
    run(D+['exec',locked['ID'],'/bin/promtool','check','rules','/etc/prometheus/rules/pve-local-backup.yml'])
    run(D+['exec',locked['ID'],'/bin/promtool','check','config','/etc/prometheus/prometheus.yml'])


def reload_and_verify(locked,present=True):
    if frame(locked['ID'])!=locked:raise RuntimeError('locked Prometheus identity drift before HUP')
    before=get('/api/v1/status/runtimeinfo')['data']['lastConfigTime']
    run(D+['kill','--signal=HUP',locked['ID']])
    deadline=time.monotonic()+30
    while time.monotonic()<deadline:
        try:
            ready=get('/-/ready')['ready']
            value=get('/api/v1/status/runtimeinfo')['data'];rules=get('/api/v1/rules')['data']['groups']
            names={r['name'] for g in rules if g['name']=='dell-pve-local-backup' for r in g['rules']}
            expected=ALERTS if present else set()
            if ready and value.get('reloadConfigSuccess') is True and value['lastConfigTime']!=before and names==expected:
                if frame(locked['ID'])!=locked:raise RuntimeError('Prometheus restarted or was recreated during reload')
                return
        except (urllib.error.URLError,ValueError,KeyError):
            pass  # Bounded transient HTTP/readiness gap; never reinterpret it as success.
        time.sleep(1)
    raise RuntimeError('fresh successful reload/readiness and exact group state unconfirmed')


def main():
    os.umask(0o077)
    p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--sha256',required=True);p.add_argument('--execute-reviewed-270-window',action='store_true');p.add_argument('--lark-whitelist-reviewed-ready',action='store_true');a=p.parse_args()
    raw=a.candidate.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=a.sha256 or len(raw)>16384:raise RuntimeError('reviewed candidate SHA/size required')
    if not a.execute_reviewed_270_window:
        print(json.dumps({'status':'local-plan-only-no-target-or-network-actions','candidate_SHA':a.sha256}));return
    if not a.lark_whitelist_reviewed_ready:raise RuntimeError('root must verify existing Lark route/bridge accepts exact three names without a new receiver')
    before=identity()
    metrics=ready_gate()
    if RULE.exists():raise RuntimeError('owned file already exists; re-review instead of blind replace')
    BASE.mkdir(mode=0o700,exist_ok=True)
    if BASE.resolve()!=BASE or BASE.stat().st_uid!=0 or stat.S_IMODE(BASE.stat().st_mode)!=0o700:raise RuntimeError('private receipt directory required')
    receipt=BASE/('install-'+str(time.time_ns())+'.json');written=False
    try:
        atomic(raw);written=True;validate(before);reload_and_verify(before)
        if identity()!=before:raise RuntimeError('Prometheus container identity changed unexpectedly')
    except Exception:
        if written:
            if RULE.is_symlink() or not RULE.is_file() or digest(RULE)!=a.sha256:raise RuntimeError('unknown rule drift; refuse automatic overwrite/removal') from None
            RULE.unlink()  # Only this newly created file; all old rules/config untouched.
            run(D+['exec',before['ID'],'/bin/promtool','check','config','/etc/prometheus/prometheus.yml'])
            reload_and_verify(before,False)
        raise RuntimeError('new rule not accepted; removed only this owned candidate when safe') from None
    result={'status':'owned-backup-rule-installed-native-validated-fresh-reloaded','rule':str(RULE),'candidate_SHA':a.sha256,'first_verified_guest_count':11,'Prometheus_container_ID_imageID_PID_startedAt_restarts_unchanged':True,'reload_method':'SIGHUP-locked-containerID','new_receiver_or_test_send':False,'old_rules_and_config_overwritten':False,'secrets_or_Env_Cmd_read':False}
    receipt.write_text(json.dumps(result,indent=2)+'\n');receipt.chmod(0o600);print(json.dumps(result))


if __name__=='__main__':
    try:main()
    except Exception:
        print(json.dumps({'status':'backup-alert-install-rejected-or-unconfirmed','raw_details_withheld':True}));raise SystemExit(1)
