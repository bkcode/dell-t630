#!/usr/bin/env python3
"""NAS260 network recognition only; exact VPN append, private backup and guarded rollback."""
import argparse,hashlib,importlib.util,json,os,re,stat,sys,time,urllib.request
from pathlib import Path
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent

def load(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

changes=load('vpn_changes',HERE/'changes.py')
BASE=Path('/opt/dell/network19/services-media')
tx=load('media_tx',BASE/'guest_transaction.py')
smb=load('smb_adapter',BASE/'nas-smb-allowlist-apply.py')
XML=Path('/srv/dev-disk-by-uuid-5b19837c-128c-498a-b79d-563db810c34a/appdata/jellyfin/config/config/network.xml')


def guard():
    if HERE!=Path('/opt/dell/network19/wireguard/media'):raise RuntimeError('fixed owned tool directory required')
    for p in [Path('/opt/dell/network19/wireguard'),HERE,HERE/'changes.py',HERE/'transaction.py',BASE/'nas-smb-allowlist-apply.py']:
        if p.resolve()!=p or p.stat().st_uid!=0 or p.stat().st_mode&0o022:raise RuntimeError('trusted root tool ownership required')
    return tx.guard(260,'new')


def metadata():
    fields='--property=ActiveState,SubState,MainPID'
    return {name:dict(x.split('=',1) for x in tx.command(['/usr/bin/systemctl','show',name,fields]).stdout.decode().splitlines() if '='in x) for name in ['dell-nas-jellyfin.service','docker.service','smbd.service','openmediavault-engined.service']}


def smb_clients():
    value=json.loads(tx.command(['/usr/bin/smbstatus','--json']).stdout)
    return {k:len(value.get(k,{}) or {}) for k in ['sessions','tcons','open_files']}


def jf_get(token,path):
    if not re.fullmatch('[A-Za-z0-9._~-]{16,512}',token) or path not in ['/Sessions','/System/Configuration/network']:raise RuntimeError('fixed authenticated read only')
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self,*args,**kwargs):return None
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
    header='MediaBrowser Client="DellVPNRecognition", Device="NASLocal", DeviceId="dell-vpn-admin", Version="1.0", Token="'+token+'"'
    req=urllib.request.Request('http://192.168.19.60:8096'+path,headers={'Authorization':header,'Accept':'application/json; profile="PascalCase"'},method='GET')
    with opener.open(req,timeout=15) as response:
        raw=response.read(1024*1024+1)
        if len(raw)>1024*1024:raise RuntimeError('bounded API read required')
        return json.loads(raw)


def fixture_hashes():
    root=Path('/srv/dev-disk-by-uuid-5b19837c-128c-498a-b79d-563db810c34a')
    paths=[root/n/('dell-acceptance-'+n+'.bin') for n in ['media','games','incoming']]+[root/'media/movies/DellAcceptance/dell-acceptance-fixture.mp4']
    return {str(p):hashlib.sha256(tx.read(p)).hexdigest() for p in paths if p.is_file()}


def stage(folder,r):
    if folder.exists():raise RuntimeError('nonce already staged; do not overwrite')
    objects=smb.read_objects();effective=smb.effective()
    model=json.loads(tx.read('/usr/share/openmediavault/datamodels/rpc.smb.json'));model=model if isinstance(model,list) else [model]
    schemas=[v for v in model if v.get('id')=='rpc.smb.setshare'];assert len(schemas)==1
    props=schemas[0]['params']['properties'];old={};new={}
    for name,obj in objects.items():
        if not all(k in obj for k,v in props.items() if v.get('required')):raise RuntimeError('installed RPC required field absent')
        old[name]={k:obj[k] for k in props if k in obj};new[name]=changes.smb_parameters(old[name])
        if effective[name]['hosts allow']!=changes.SMB_OLD:raise RuntimeError('runtime share and persisted policy disagree')
    raw=tx.read(XML);changed=changes.xml_append(raw);s=XML.stat();frame=tx.state(r)
    if not all(x['running'] and x['health']=='healthy' for x in frame):raise RuntimeError('healthy JF baseline required')
    parent=folder.parent;parent.mkdir(mode=0o700,exist_ok=True)
    if parent.resolve()!=parent or parent.stat().st_uid!=0 or stat.S_IMODE(parent.stat().st_mode)!=0o700:raise RuntimeError('root700 backup parent required')
    folder.mkdir(mode=0o700);tx.atomic(folder/'network.old.xml',raw);tx.atomic(folder/'network.new.xml',changed)
    j={'role':260,'phase':'staged','created_at':time.time(),'old_smb':old,'new_smb':new,'effective_before':effective,'xml_old_sha':tx.patch.sha(raw),'xml_new_sha':tx.patch.sha(changed),'xml_metadata':{'mode':stat.S_IMODE(s.st_mode),'uid':s.st_uid,'gid':s.st_gid},'protected_hashes':tx.protected(r),'fixture_hashes':fixture_hashes(),'containers_before':frame,'units_before':metadata(),'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip()}
    tx.save(folder/'journal.json',j)


def validate(folder,j,r,forward):
    if tx.protected(r)!=j['protected_hashes'] or fixture_hashes()!=j['fixture_hashes']:raise RuntimeError('identity/data changed; do not overwrite')
    for filename,key in [('network.old.xml','xml_old_sha'),('network.new.xml','xml_new_sha')]:
        if tx.patch.sha(tx.read(folder/filename))!=j[key]:raise RuntimeError('private backup/candidate hash differs')
    if tx.patch.sha(tx.read(XML)) not in ({j['xml_old_sha']} if forward else {j['xml_old_sha'],j['xml_new_sha']}):raise RuntimeError('third-party XML drift; no overwrite')
    current=smb.read_objects()
    for name,obj in current.items():
        expected=j['old_smb'][name]
        actual={k:obj[k] for k in expected}
        if forward and actual!=expected:raise RuntimeError('share model drift; no overwrite')
        if not forward and actual not in (expected,j['new_smb'][name]):raise RuntimeError('third-party share policy drift; no overwrite')


def wait_ready(r):
    deadline=time.monotonic()+180
    while time.monotonic()<deadline:
        try:
            rows=tx.state(r);unit=metadata()['dell-nas-jellyfin.service']
            if len(rows)==1 and rows[0]['running'] and rows[0]['health']=='healthy' and unit['ActiveState']=='active' and unit['SubState']=='running':return rows
        except tx.patch.Rejected:pass
        time.sleep(2)
    raise RuntimeError('original JF unit did not become healthy within180s')


def apply(folder,j,r,token):
    validate(folder,j,r,True)
    sessions=jf_get(token,'/Sessions');playing=sum(bool(x.get('NowPlayingItem')) for x in sessions);transcoding=sum(bool(x.get('TranscodingInfo')) for x in sessions);clients=smb_clients()
    if playing or transcoding or any(clients.values()):raise RuntimeError('active family client/stream; defer without mutation')
    j['clients_before']={'JF_active_or_paused_playback':playing,'JF_transcoding':transcoding,'SMB':clients};j['phase']='applying';tx.save(folder/'journal.json',j)
    stopped=False;changed=[];xml_written=False
    try:
        tx.command(['/usr/bin/systemctl','stop','dell-nas-jellyfin.service'],timeout=120);stopped=True
        validate(folder,j,r,True)
        # Check again before the official module's watched service may restart/reload.
        if any(smb_clients().values()):raise RuntimeError('new SMB client appeared; defer without model changes')
        for name in smb.SHARES:smb.rpc(j['new_smb'][name]);changed.append(name)
        tx.atomic(XML,tx.read(folder/'network.new.xml'),**j['xml_metadata']);xml_written=True
        tx.command(['/usr/sbin/omv-salt','deploy','run','samba'],timeout=240)
        current=smb.read_objects();effective=smb.effective()
        for name in smb.SHARES:
            if {k:current[name][k] for k in j['new_smb'][name]}!=j['new_smb'][name]:raise RuntimeError('unexpected OMV share field change')
            if any(effective[name][k]!=v for k,v in j['effective_before'][name].items() if k!='hosts allow') or effective[name]['hosts allow']!=changes.SMB_NEW:raise RuntimeError('effective auth/permission drift')
        tx.command(['/usr/bin/systemctl','start','--no-block','dell-nas-jellyfin.service']);rows=wait_ready(r)
        runtime=jf_get(token,'/System/Configuration/network')
        if runtime['LocalNetworkSubnets']!=changes.JF_NEW or runtime['EnableRemoteAccess'] is not False or runtime['EnableUPnP'] is not False:raise RuntimeError('running JF network policy differs')
        if tx.protected(r)!=j['protected_hashes'] or fixture_hashes()!=j['fixture_hashes']:raise RuntimeError('identity/data changed')
        after=metadata()
        if after['docker.service']['MainPID']!=j['units_before']['docker.service']['MainPID'] or Path('/proc/sys/kernel/random/boot_id').read_text().strip()!=j['boot_id']:raise RuntimeError('VM or Docker restarted unexpectedly')
        if rows[0]['image']!=j['containers_before'][0]['image']:raise RuntimeError('JF image changed')
        j['phase']='committed-verified';tx.save(folder/'journal.json',j)
        return {'role':260,'status':'VPN-source-recognition-committed-verified','VPN_CIDR':changes.VPN,'SMB_old':changes.SMB_OLD,'SMB_new':changes.SMB_NEW,'JF_old':changes.JF_OLD,'JF_new':changes.JF_NEW,'all_non_network_share_fields_and_effective_permissions_unchanged':True,'EnableRemoteAccess':False,'EnableUPnP':False,'root_shadow_key_guard_bytes_and_original_fixture_hashes_unchanged':True,'data_uuid':r['uuid'],'JF_required_restart_completed':True,'Docker_or_VM_restarted':False,'SMB_clients_before':clients,'JF_active_or_paused_playback_before':playing,'JF_transcoding_before':transcoding,'SMBD_PID_changed_by_official_Salt':after['smbd.service']['MainPID']!=j['units_before']['smbd.service']['MainPID'],'JF_running_healthy':True,'credential_values_or_private_hashes_emitted':False}
    except Exception:
        try:
            validate(folder,j,r,False)
            if xml_written:tx.command(['/usr/bin/systemctl','stop','dell-nas-jellyfin.service'],timeout=120);tx.atomic(XML,tx.read(folder/'network.old.xml'),**j['xml_metadata'])
            for name in changed:smb.rpc(j['old_smb'][name])
            if changed:tx.command(['/usr/sbin/omv-salt','deploy','run','samba'],timeout=240)
            if stopped:tx.command(['/usr/bin/systemctl','start','--no-block','dell-nas-jellyfin.service']);wait_ready(r)
            j['phase']='rolled-back-after-failure';tx.save(folder/'journal.json',j)
        except Exception:j['phase']='unconfirmed-drift-or-rollback-failure';tx.save(folder/'journal.json',j)
        raise RuntimeError('apply unconfirmed; inspect guest-private journal, no raw secrets') from None


def main():
    os.umask(0o077);p=argparse.ArgumentParser();p.add_argument('action',choices=['stage','commit']);p.add_argument('--nonce',required=True);a=p.parse_args()
    if not re.fullmatch('[a-f0-9]{32}',a.nonce):raise RuntimeError('fixed nonce format required')
    r=guard();folder=Path('/root/dell-wireguard-media')/a.nonce
    if a.action=='stage':stage(folder,r);result={'role':260,'status':'VPN-recognition-staged-no-active-change'}
    else:
        if folder.resolve()!=folder or folder.stat().st_uid!=0 or stat.S_IMODE(folder.stat().st_mode)!=0o700:raise RuntimeError('private staged directory required')
        j=json.loads(tx.read(folder/'journal.json'));assert j['phase']=='staged' and j['role']==260
        private=json.load(sys.stdin);assert set(private)=={'adminToken'}
        result=apply(folder,j,r,private['adminToken']);tx.save(folder/'result.json',result)
    print(json.dumps(result))

if __name__=='__main__':
    try:main()
    except Exception:
        print(json.dumps({'role':260,'status':'VPN-recognition-rejected-or-unconfirmed','private_journal_retained':True}));raise SystemExit(1)
