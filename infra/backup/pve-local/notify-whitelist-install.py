#!/usr/bin/env python3
"""PREPARED ONLY: append three fixed alert names to existing native bridge/AM renderer."""
import argparse,ast,copy,hashlib,importlib.util,json,os,re,socket,stat,subprocess,sys,tempfile,time,types,urllib.error,urllib.request
from pathlib import Path
sys.dont_write_bytecode=True
BRIDGE=Path('/usr/local/libexec/dell-lark-notify/bridge.py')
AM=Path('/opt/dell/ops/config/alertmanager/alertmanager.yml')
POLICY=Path('/etc/dell-lark-notify/policy.json')
UNIT='dell-lark-notify.service'
D=['/usr/bin/docker','--host','unix:///var/run/docker.sock']
CONTAINER='dell-ops-alertmanager-1'
OLD_BRIDGE_SHA='e4b251653d0ae9822351928d3f04b6d4a0833edbe50ce3e6057edc7de7182f80'
OLD_AM_SHA='ace6e36ff16e86b487523d141859f0bd150883d9e73e05a86c06d0d38a38cd53'
ADDED=" 'PveLocalBackupFailed':'PVE本机备份失败',\n 'PveLocalBackupStale':'PVE本机备份成功已超过36小时',\n 'PveLocalBackupStateInvalid':'PVE本机备份任务关闭或状态无效',\n"
NEW_NAMES={'PveLocalBackupFailed','PveLocalBackupStale','PveLocalBackupStateInvalid'}
RENDERER_SOURCE='"""No dependencies, no credential values. JSON is valid Alertmanager YAML."""\nimport json\nfrom bridge import ALERTS,BIND,SOURCE\nAUTH=\'/run/secrets/lark-bridge-token\'\ndef policy(mode):\n if mode not in (\'acceptance\',\'active\'):raise ValueError(\'invalid mode\')\n return {\'mode\':mode,\'bind_host\':BIND[0],\'bind_port\':BIND[1],\'allowed_source\':SOURCE}\ndef render(mode):\n policy(mode)\n test={\'receiver\':\'lark-acceptance\',\'matchers\':[\'alertname="DellLarkNotificationAcceptance"\',\'dell_acceptance="lark-notify"\'],\'group_by\':[\'alertname\',\'acceptance_run\'],\'group_wait\':\'1s\',\'group_interval\':\'15s\',\'repeat_interval\':\'24h\'}\n routes=[test]\n if mode==\'active\':routes.append({\'receiver\':\'lark-live\',\'matchers\':[\'alertname=~"\'+(\'|\'.join(sorted(set(ALERTS)-{\'DellLarkNotificationAcceptance\'})))+\'"\',\'severity=~"warning|critical"\'],\'group_by\':[\'alertname\',\'role\'],\'group_wait\':\'30s\',\'group_interval\':\'5m\',\'repeat_interval\':\'4h\'})\n webhook={\'url\':\'http://172.18.0.1:19093/v1/alertmanager\',\'send_resolved\':True,\'max_alerts\':16,\'timeout\':\'12s\',\'http_config\':{\'authorization\':{\'type\':\'Bearer\',\'credentials_file\':AUTH},\'follow_redirects\':False}}\n receivers=[{\'name\':\'local-only\'},{\'name\':\'lark-acceptance\',\'webhook_configs\':[webhook]}]\n if mode==\'active\':receivers.append({\'name\':\'lark-live\',\'webhook_configs\':[webhook]})\n return {\'global\':{\'resolve_timeout\':\'5m\'},\'route\':{\'receiver\':\'local-only\',\'group_by\':[\'alertname\',\'role\'],\'group_wait\':\'30s\',\'group_interval\':\'5m\',\'repeat_interval\':\'4h\',\'routes\':routes},\'receivers\':receivers}\ndef dump(mode):return json.dumps(render(mode),indent=2)+\'\\n\'\nif __name__==\'__main__\':\n import argparse\n p=argparse.ArgumentParser();p.add_argument(\'mode\',choices=[\'acceptance\',\'active\']);a=p.parse_args();print(dump(a.mode),end=\'\')\n'
ENV={'PATH':'/usr/sbin:/usr/bin:/sbin:/bin','LANG':'C','LC_ALL':'C'}


def sha(raw):return hashlib.sha256(raw).hexdigest()


def run(args):
    p=subprocess.run(args,capture_output=True,text=True,timeout=60,env=ENV)
    if p.returncode:raise RuntimeError('fixed native operation failed; raw output withheld')
    return p.stdout


def get(port,path,raw=False):
    allowed={9090:{'/api/v1/alerts'},9093:{'/api/v2/alerts','/api/v2/alerts/groups','/metrics','/-/ready'}}
    if path not in allowed[port]:raise RuntimeError('fixed read-only Ops route required')
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self,*args,**kwargs):return None
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
    with opener.open('http://192.168.19.70:'+str(port)+path,timeout=15) as response:
        data=response.read(4*1024*1024+1)
        if response.status!=200 or len(data)>4*1024*1024:raise RuntimeError('bounded Ops HTTP read required')
        return data.decode() if raw else json.loads(data)


def unit_state():
    return dict(line.split('=',1) for line in run(['/usr/bin/systemctl','show',UNIT,'--property=ActiveState,SubState,MainPID,TasksCurrent,NRestarts']).splitlines() if '='in line)


def quiescent():
    # No durable bridge queue/status API exists; do not inspect process memory or message contents.
    for sample in range(2):
        if len(get(9093,'/api/v2/alerts')) or len(get(9093,'/api/v2/alerts/groups')) or len(get(9090,'/api/v1/alerts')['data']['alerts']):raise RuntimeError('active/pending alert groups; defer without mutation')
        state=unit_state()
        if state.get('ActiveState')!='active' or state.get('SubState')!='running' or int(state.get('MainPID','0'))<=0 or state.get('TasksCurrent')!='1':raise RuntimeError('bridge active/quiescent single-task state required')
        if run(['/usr/bin/ss','-Htn','state','established','sport = :19093']).strip():raise RuntimeError('bridge has an in-flight inbound connection')
        if sample==0:time.sleep(2)
    return state


def module(raw,name):
    value=types.ModuleType(name);exec(compile(raw,name,'exec'),value.__dict__);return value


def render(bridge):
    previous=sys.modules.get('bridge');sys.modules['bridge']=bridge
    try:return module(RENDERER_SOURCE,'fixed_public_renderer').render('active')
    finally:
        if previous is None:sys.modules.pop('bridge',None)
        else:sys.modules['bridge']=previous


def exact_delta(old,new):
    # Only one live route's alertname regex changes; receivers/auth/grouping/retries remain byte-semantic equal.
    expected=copy.deepcopy(old)
    routes=expected['route']['routes']
    matches=[r for r in routes if r['receiver']=='lark-live']
    if len(matches)!=1:raise RuntimeError('exact existing live route required')
    route=matches[0];oldmatch=route['matchers'][0]
    if not(oldmatch.startswith('alertname=~"') and oldmatch.endswith('"')):raise RuntimeError('unknown live alert matcher')
    names=set(oldmatch[len('alertname=~"'):-1].split('|'))
    route['matchers'][0]='alertname=~"'+'|'.join(sorted(names|NEW_NAMES))+'"'
    if new!=expected or new['receivers']!=old['receivers']:raise RuntimeError('renderer changes outside exact three names')


def frame(reference):
    v=json.loads(run(D+['inspect','--type','container','--format','{"ID":{{json .Id}},"imageID":{{json .Image}},"PID":{{json .State.Pid}},"StartedAt":{{json .State.StartedAt}},"restarts":{{json .RestartCount}},"running":{{json .State.Running}}}',reference]))
    if not v['running'] or v['PID']<=0:raise RuntimeError('existing AM process must be running')
    return v


def safe(path,directory=False):
    p=Path(path)
    if p.resolve()!=p or p.stat().st_uid!=0 or p.stat().st_mode&0o022 or (directory and not p.is_dir()):raise RuntimeError('trusted root public path required')


def identity():
    if os.geteuid()!=0 or socket.gethostname().split('.')[0]!='ops-service' or Path('/etc/pve').exists():raise RuntimeError('assigned270 root only')
    for p in [BRIDGE.parent,AM.parent,POLICY.parent]:safe(p,True)
    for p in [BRIDGE,AM,POLICY]:safe(p)
    addr=json.loads(run(['/usr/sbin/ip','-j','address']))
    if not any(a.get('local')=='192.168.19.70' for n in addr for a in n.get('addr_info',[])):raise RuntimeError('assigned Ops IP missing')
    fs=json.loads(run(['/usr/bin/findmnt','--json','--mountpoint','/srv/dell-data','--output','TARGET,UUID']))['filesystems']
    if len(fs)!=1 or fs[0]['target']!='/srv/dell-data' or fs[0]['uuid']!='01b1f302-27be-4fbd-b4af-b8e782d85dea':raise RuntimeError('assigned data UUID missing')
    mounts=json.loads(run(D+['inspect','--format','{{json .Mounts}}',CONTAINER]))
    found=[x for x in mounts if x['Destination']=='/etc/alertmanager']
    if len(found)!=1 or found[0]['Source']!='/opt/dell/ops/config/alertmanager' or found[0]['RW'] is not False:raise RuntimeError('actual RO AM source-directory bind required')
    # Secret path/ownership remain native; never open token/webhook or credential directory.
    return frame(CONTAINER)


def atomic(path,data,mode):
    safe(path.parent,True)
    fd,tmp=tempfile.mkstemp(prefix='.backup-whitelist-',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as out:os.fchmod(out.fileno(),mode);out.write(data);out.flush();os.fsync(out.fileno())
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)


def native_check(locked):
    if frame(locked['ID'])!=locked:raise RuntimeError('AM locked identity drift')
    run(D+['exec',locked['ID'],'/bin/amtool','check-config','/etc/alertmanager/alertmanager.yml'])
    for name in sorted(NEW_NAMES):
        run(D+['exec',locked['ID'],'/bin/amtool','config','routes','test','--config.file=/etc/alertmanager/alertmanager.yml','--verify.receivers=lark-live','alertname='+name,'severity=warning','role=pve','site=dell-t630'])


def reload_timestamp():
    values={}
    for line in get(9093,'/metrics',True).splitlines():
        if line.startswith('#'):continue
        name=line.split(' ',1)[0]
        if name in ['alertmanager_config_last_reload_successful','alertmanager_config_last_reload_success_timestamp_seconds']:values[name]=float(line.rsplit(' ',1)[1])
    if len(values)!=2:raise RuntimeError('actual AM reload metrics missing')
    return values


def hup(locked):
    if frame(locked['ID'])!=locked:raise RuntimeError('AM locked identity drift before HUP')
    before=reload_timestamp()['alertmanager_config_last_reload_success_timestamp_seconds']
    run(D+['kill','--signal=HUP',locked['ID']]);deadline=time.monotonic()+30
    while time.monotonic()<deadline:
        try:
            get(9093,'/-/ready',True);v=reload_timestamp()
            if v['alertmanager_config_last_reload_successful']==1 and v['alertmanager_config_last_reload_success_timestamp_seconds']>before:
                if frame(locked['ID'])!=locked:raise RuntimeError('AM restarted/recreated during HUP')
                return
        except (urllib.error.URLError,ValueError):
            pass  # Only bounded transient readiness gaps; never convert an error to success.
        time.sleep(1)
    raise RuntimeError('AM fresh successful HUP unconfirmed')


def bridge_ready():
    deadline=time.monotonic()+30
    while time.monotonic()<deadline:
        unit=unit_state()
        endpoints=[line.split()[3] for line in run(['/usr/bin/ss','-Hltn','sport = :19093']).splitlines() if len(line.split())>=4]
        if unit.get('ActiveState')=='active' and unit.get('SubState')=='running' and int(unit.get('MainPID','0'))>0 and endpoints==['172.18.0.1:19093']:return unit
        time.sleep(1)
    raise RuntimeError('existing native bridge bind/readiness unconfirmed')


def main():
    os.umask(0o077);p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--sha256',required=True);p.add_argument('--execute-reviewed-270-window',action='store_true');a=p.parse_args()
    candidate=a.candidate.read_bytes()
    if sha(candidate)!=a.sha256 or len(candidate)>65536:raise RuntimeError('exact candidate SHA/size required')
    ast.parse(candidate.decode())
    if not a.execute_reviewed_270_window:print(json.dumps({'status':'local-notify-whitelist-plan-only','candidate_SHA':a.sha256,'target_actions':False}));return
    locked=identity();oldbridge=BRIDGE.read_bytes();oldam=AM.read_bytes()
    if sha(oldbridge)!=OLD_BRIDGE_SHA or sha(oldam)!=OLD_AM_SHA:raise RuntimeError('actual source SHA differs from readonly review')
    expected=oldbridge.replace(b'ALERTS={\n',b'ALERTS={\n'+ADDED.encode(),1)
    if candidate!=expected:raise RuntimeError('only exact three fixed ALERTS descriptions may change')
    previous=module(oldbridge,'old_bridge');future=module(candidate,'new_bridge');old=render(previous);new=render(future)
    if json.loads(oldam)!=old or json.loads(POLICY.read_text())!={'mode':'active','bind_host':'172.18.0.1','bind_port':19093,'allowed_source':'172.18.0.3'}:raise RuntimeError('existing active AM/policy contract differs')
    exact_delta(old,new);before=quiescent()
    parent=Path('/root/dell-backup-notify-whitelist');parent.mkdir(mode=0o700,exist_ok=True);safe(parent,True)
    if stat.S_IMODE(parent.stat().st_mode)!=0o700:raise RuntimeError('root700 backup directory required')
    backup=parent/str(time.time_ns());backup.mkdir(mode=0o700)
    for name,data in [('bridge.before.py',oldbridge),('alertmanager.before.json',oldam)]:
        f=backup/name;f.write_bytes(data);f.chmod(0o600)
    changed=False;newam=(json.dumps(new,indent=2)+'\n').encode()
    try:
        if sha(BRIDGE.read_bytes())!=OLD_BRIDGE_SHA or sha(AM.read_bytes())!=OLD_AM_SHA:raise RuntimeError('source drift before CAS')
        changed=True
        atomic(BRIDGE,candidate,0o644);atomic(AM,newam,0o644)
        native_check(locked);quiescent()
        run(['/usr/bin/systemctl','restart',UNIT]);bridge_ready();hup(locked)
        if sha(BRIDGE.read_bytes())!=a.sha256 or json.loads(AM.read_text())!=new or new['receivers']!=old['receivers']:raise RuntimeError('post-install code/receiver drift')
        after=quiescent()
    except Exception:
        if changed:
            if sha(BRIDGE.read_bytes()) not in {OLD_BRIDGE_SHA,a.sha256} or sha(AM.read_bytes()) not in {OLD_AM_SHA,sha(newam)}:raise RuntimeError('third party source drift; refuse overwrite rollback') from None
            atomic(BRIDGE,oldbridge,0o644);atomic(AM,oldam,0o644)
            run(D+['exec',locked['ID'],'/bin/amtool','check-config','/etc/alertmanager/alertmanager.yml'])
            run(['/usr/bin/systemctl','restart',UNIT]);bridge_ready();hup(locked)
        raise RuntimeError('notification whitelist update unconfirmed; public backups retained') from None
    result={'status':'three-backup-alert-whitelist-committed-native-checked-no-test-send','candidate_SHA':a.sha256,'AM_locked_ID_image_PID_start_restarts_unchanged':frame(locked['ID'])==locked,'native_bridge_MainPID_changed':before['MainPID']!=after['MainPID'],'three_synthetic_label_routes_lark_live':True,'receiver_auth_token_paths_unchanged':True,'ALERTS_only_three_names_added':True,'all_alert_group_counts_zero':True,'no_durable_bridge_queue_and_single_task_no_inbound_confirmed':True,'secret_values_read_or_new_receiver_or_test_send':False}
    f=backup/'result.json';f.write_text(json.dumps(result,indent=2)+'\n');f.chmod(0o600);print(json.dumps(result))


if __name__=='__main__':
    try:main()
    except Exception:print(json.dumps({'status':'notify-whitelist-rejected-or-unconfirmed','private_public-code-backup-retained':True}));raise SystemExit(1)
