"""Manager SSH helpers. Keys stay on the client; host keys come from trusted PVE QGA."""
from pathlib import Path
import subprocess,json,shlex,ipaddress,hashlib,base64,datetime
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parents[1]
KEY=Path.home()/'.ssh/yang_local_rsa'
KNOWN=ROOT/'private/known_hosts'
BASE=['ssh','-i',str(KEY),'-o','IdentitiesOnly=yes','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','UserKnownHostsFile='+str(KNOWN),'-o','ConnectTimeout=8']

def pve(command, data=None, timeout=120):
    result=subprocess.run(BASE+['root@192.168.21.22',command],input=data,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=timeout)
    if result.returncode:
        raise RuntimeError(f'PVE command failed ({result.returncode}): '+result.stderr.decode()[-600:])
    return result.stdout


def qga(vmid,args):
    command=shlex.join(['qm','guest','exec',str(int(vmid)),'--']+args)
    value=json.loads(pve(command,timeout=40))
    if value.get('exitcode')!=0:raise RuntimeError('Guest command failed: '+str(value.get('exitcode')))
    return value.get('out-data','')


def trust_guest(vmid, *, expected_ip=None, allow_reprovisioned_key=False, reason=None):
    vmid=int(vmid)
    interfaces=json.loads(pve(shlex.join(['qm','agent',str(vmid),'network-get-interfaces'])))
    candidates=[]
    for interface in interfaces:
        if interface.get('name') in ['lo','docker0'] or interface.get('name','').startswith(('br-','veth')):continue
        for address in interface.get('ip-addresses',[]):
            if address.get('ip-address-type')=='ipv4':
                ip=ipaddress.ip_address(address['ip-address'])
                if not ip.is_loopback and not ip.is_link_local:candidates.append(str(ip))
    if len(candidates)!=1:raise RuntimeError('Expected one unambiguous guest IPv4: '+str(candidates))
    if expected_ip is not None and candidates[0]!=expected_ip:raise RuntimeError('Guest has not reached its assigned address')
    public=qga(vmid,['cat','/etc/ssh/ssh_host_ed25519_key.pub']).strip().split()
    if len(public)<2 or public[0]!='ssh-ed25519':raise RuntimeError('Unexpected guest host key')
    alias='dell-vm'+str(vmid)
    entry=alias+' '+public[0]+' '+public[1]
    current=KNOWN.read_text() if KNOWN.exists() else ''
    prior=[line for line in current.splitlines() if line.startswith(alias+' ')]
    changed=prior and any(line!=entry for line in prior)
    if changed:
        if not allow_reprovisioned_key or not reason:raise RuntimeError('Guest host key changed; requires explicit verified reprovisioning reason')
        plan=json.loads((ROOT/'plan.json').read_text())
        matches=[r for r in plan['roles'] if r.get('vmid',r.get('planned_vmid'))==vmid]
        if len(matches)!=1 or qga(vmid,['hostname']).strip()!=matches[0]['name']:raise RuntimeError('Reprovisioned guest identity mismatch')
        now=datetime.datetime.now(ZoneInfo('Asia/Shanghai')).isoformat()
        backup=KNOWN.with_name('known_hosts.before-'+now.replace(':','-'));backup.write_text(current);backup.chmod(0o600)
        current='\n'.join(line for line in current.splitlines() if not line.startswith(alias+' '))+'\n'
        ledger=ROOT/'evidence/implementation/host-key-rotations.json'
        rows=json.loads(ledger.read_text()) if ledger.exists() else []
        rows.append({'at':now,'vmid':vmid,'assigned_ip':candidates[0],'reason':reason,'trust_source':'PVE QGA over unchanged trusted PVE SSH host','global_known_hosts_changed':False})
        ledger.write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
    if not prior or changed:KNOWN.write_text(current.rstrip()+'\n'+entry+'\n');KNOWN.chmod(0o600)
    fingerprint='SHA256:'+base64.b64encode(hashlib.sha256(base64.b64decode(public[1])).digest()).decode().rstrip('=')
    return {'vmid':vmid,'ip':candidates[0],'host_key_alias':alias,'host_key_fingerprint':fingerprint,'trust_source':'PVE QGA over known SSH host'}


def guest(vmid,command,data=None,timeout=120,info=None):
    info=info or trust_guest(vmid)
    proxy=shlex.join(BASE+['-W','%h:%p','root@192.168.21.22'])
    args=BASE+['-o','HostKeyAlias='+info['host_key_alias'],'-o','ProxyCommand='+proxy,'ub@'+info['ip'],command]
    result=subprocess.run(args,input=data,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=timeout)
    return {'exit_code':result.returncode,'stdout':result.stdout.decode(),'stderr':result.stderr.decode(),'target':info}
