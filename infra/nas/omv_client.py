"""Call actual local-root OMV RPC through stdin on the assigned NAS guest only."""
import json
import remote

def rpc(service,method,params=None,timeout=60,phase=None):
    data=json.dumps({'service':service,'method':method,'params':params},ensure_ascii=False).encode()
    result=remote.guest('sudo -n /usr/bin/php8.4 -c /etc/openmediavault /opt/dell/nas-stage/omv-rpc-stdin.php',data=data,timeout=timeout,phase=phase)
    try:decoded=json.loads(result['stdout'])
    except ValueError:raise RuntimeError('OMV RPC returned non-JSON; private transport output withheld')
    if result['exit_code'] or decoded.get('status')!='ok':
        raise RuntimeError('OMV '+service+'.'+method+' failed: '+decoded.get('message','details withheld'))
    return decoded.get('response')
