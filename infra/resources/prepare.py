#!/usr/bin/env python3
"""Strict local renderer only: never installs, formats, mounts or connects."""
import argparse
import copy
import json
from pathlib import Path
import uuid

HERE = Path(__file__).resolve().parent
EXAMPLE = json.loads((HERE / 'policy.example.json').read_text())


def validate(policy, allow_pending=False):
    expected = copy.deepcopy(EXAMPLE)
    supplied = copy.deepcopy(policy)
    try:
        value = supplied['server']['data_uuid']
        supplied['server']['data_uuid'] = None
    except (KeyError, TypeError):
        raise ValueError('exact-policy-required') from None
    if supplied != expected:
        raise ValueError('exact-policy-required')
    if value is None and allow_pending:
        return
    if not isinstance(value, str):
        raise ValueError('fresh-data-uuid-required')
    try:
        parsed = uuid.UUID(value)
    except (ValueError, AttributeError):
        raise ValueError('canonical-data-uuid-required') from None
    if str(parsed) != value or parsed.int == 0:
        raise ValueError('canonical-data-uuid-required')


def firewall_helper(rules):
    """Fixed owned table, atomic replace; legacy local RPC remains reachable."""
    return "#!/usr/bin/python3\nEXPECTED = " + repr(rules) + "\n" + r'''import argparse,fcntl,json,os,platform,socket,stat,subprocess
from pathlib import Path
RULES=Path('/etc/dell-resources/input.nft')
NFT='/usr/sbin/nft'
TABLE='dell_resources_input'

def transaction(body, listing):
    if body != EXPECTED or not isinstance(listing,dict) or not isinstance(listing.get('nftables'),list):
        raise ValueError('fixed-rules-required')
    own=[row['table'] for row in listing['nftables'] if 'table' in row and row['table'].get('family')=='inet' and row['table'].get('name')==TABLE]
    if len(own)>1:
        raise ValueError('owned-table-not-unique')
    return ('delete table inet '+TABLE+'\n' if own else '')+body

def run(args, body=None):
    result=subprocess.run(args,input=body,capture_output=True,text=True,timeout=15)
    if result.returncode:
        raise RuntimeError('fixed-firewall-operation-failed')
    return result.stdout

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--check',action='store_true');args=parser.parse_args()
    if os.geteuid()!=0 or Path('/etc/pve').exists() or socket.gethostname()!='resource-service' or platform.system()!='Linux':
        raise ValueError('resource-guest-root-only')
    addresses=json.loads(run(['/usr/sbin/ip','-j','-4','address','show','scope','global']))
    ips=[a['local'] for i in addresses if i['ifname'] not in ['lo','docker0'] and not i['ifname'].startswith(('br-','veth')) for a in i.get('addr_info',[]) if a.get('family')=='inet']
    if ips!=['192.168.19.80']:
        raise ValueError('resource-exact-IP-required')
    for path in [RULES,*RULES.parents]:
        item=path.lstat()
        if stat.S_ISLNK(item.st_mode) or item.st_uid!=0 or item.st_mode&0o022:
            raise ValueError('trusted-rule-path-required')
    item=RULES.stat()
    if not stat.S_ISREG(item.st_mode) or item.st_nlink!=1 or stat.S_IMODE(item.st_mode) not in [0o600,0o644]:
        raise ValueError('trusted-rule-file-required')
    lock=os.open('/run/dell-resources-firewall.lock',os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW,0o600)
    try:
        item=os.fstat(lock)
        if not stat.S_ISREG(item.st_mode) or item.st_uid!=0 or item.st_nlink!=1 or stat.S_IMODE(item.st_mode)!=0o600:
            raise ValueError('trusted-lock-required')
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        body=transaction(RULES.read_text(),json.loads(run([NFT,'--json','list','tables'])))
        run([NFT,'--check','--file','-'],body)
        if not args.check:
            run([NFT,'--file','-'],body)
        print(json.dumps({'status':'owned-firewall-checked' if args.check else 'owned-firewall-atomically-applied','other_tables_flushed':False}))
    finally:
        os.close(lock)
if __name__=='__main__':
    try:main()
    except Exception:raise SystemExit('resource-firewall-failed') from None
'''


def render(policy):
    validate(policy)
    data_uuid = policy['server']['data_uuid']
    files = {'server/policy.json': json.dumps(policy, indent=2) + '\n'}
    files['server/dell-resources.exports'] = (
        '/srv/resources '
        '192.168.19.40(rw,sync,root_squash,no_subtree_check,fsid=0,mountpoint,sec=sys,secure) '
        '192.168.19.45(rw,sync,root_squash,no_subtree_check,fsid=0,mountpoint,sec=sys,secure)\n')
    files['server/90-dell-resources.conf'] = '''[nfsd]
host=192.168.19.80
port=2049
threads=4
vers2=n
vers3=n
vers4=y
vers4.0=n
vers4.1=y
vers4.2=n
tcp=y
udp=n
rdma=n

[mountd]
port=20048
manage-gids=n
'''
    files['server/srv-resources.mount'] = f'''[Unit]
Description=Dell shared resource data filesystem
Before=nfs-server.service

[Mount]
What=/dev/disk/by-uuid/{data_uuid}
Where=/srv/resources
Type=ext4
Options=rw,nodev,nosuid,noexec
DirectoryMode=0000
TimeoutSec=30

[Install]
WantedBy=multi-user.target
'''
    files['server/nfs-server.service.d/50-dell-resources.conf'] = '''[Unit]
Requires=srv-resources.mount dell-resources-firewall.service
After=srv-resources.mount dell-resources-firewall.service
BindsTo=srv-resources.mount
RequiresMountsFor=/srv/resources

[Service]
ExecStartPre=/usr/bin/python3 -I -B /opt/dell/resources/guard.py --role server
'''
    files['server/dell-resources-input.nft'] = '''# Candidate OWNED table only; parent must native nft -c and controlled install.
# Preserve other tables; direct NFS clients also need the approved parent bridge ACL.
table inet dell_resources_input {
 chain input {
  type filter hook input priority -5; policy accept;
  iifname "lo" accept
  tcp dport 2049 ip saddr { 192.168.19.40, 192.168.19.45 } accept
  tcp dport 2049 drop
  udp dport 2049 drop
  meta l4proto { tcp, udp } th dport { 111, 20048 } drop
 }
}
'''
    files['server/apply-firewall.py'] = firewall_helper(files['server/dell-resources-input.nft'])
    files['server/dell-resources-firewall.service'] = '''[Unit]
Description=Dell resource NFS input allowlist
Before=nfs-server.service

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStartPre=/usr/bin/python3 -I -B /opt/dell/resources/apply-firewall.py --check
ExecStart=/usr/bin/python3 -I -B /opt/dell/resources/apply-firewall.py
# No ExecStop: stopping this unit must not remove the protective rules.

[Install]
WantedBy=multi-user.target
'''
    for client in policy['clients']:
        name = str(client['vmid'])
        files[f'client-{name}/policy.json'] = files['server/policy.json']
        files[f'client-{name}/mnt-resources.mount'] = '''[Unit]
Description=Dell shared resources NFS4.1
Wants=network-online.target
After=network-online.target

[Mount]
What=192.168.19.80:/
Where=/mnt/resources
Type=nfs
Options=vers=4.1,proto=tcp,port=2049,rw,hard,timeo=600,retrans=2,sec=sys,resvport,nodev,nosuid,noexec
TimeoutSec=30
DirectoryMode=0000
'''
        files[f'client-{name}/mnt-resources.automount'] = '''[Unit]
Description=On-demand shared resources

[Automount]
Where=/mnt/resources
DirectoryMode=0000
TimeoutIdleSec=0

[Install]
WantedBy=multi-user.target
'''
        files[f'client-{name}/future-java-resource-dependency.conf'] = f'''# FUTURE ONLY: no current Java service is enabled or modified.
[Unit]
Requires=mnt-resources.mount
After=mnt-resources.mount
BindsTo=mnt-resources.mount
RequiresMountsFor=/mnt/resources

[Service]
ExecStartPre=+/usr/bin/python3 -I -B /opt/dell/resources/guard.py --role client-{name}
UMask=0002
ReadWritePaths=/mnt/resources
'''
    files['optional-http/NOT-ENABLED-nginx.conf'] = '''# OPTIONAL CANDIDATE ONLY. No install/start without separate approval.
server {
 listen 192.168.19.80:8080;
 server_name _;
 server_tokens off;
 access_log off;
 add_header X-Content-Type-Options nosniff always;
 add_header Content-Security-Policy "default-src 'none'; sandbox" always;
 location ^~ /images/ {
  alias /srv/resources/images/;
  autoindex off;
  disable_symlinks on;
  limit_except GET HEAD { deny all; }
 }
 location / { return 404; }
}
'''
    return files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--policy', type=Path, default=HERE / 'policy.example.json')
    parser.add_argument('--data-uuid')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    policy = json.loads(args.policy.read_text())
    if args.data_uuid is not None:
        policy['server']['data_uuid'] = args.data_uuid
    validate(policy, allow_pending=args.output is None)
    if args.output is None:
        print(json.dumps({'status': 'validated-candidate', 'data_uuid_assigned': policy['server']['data_uuid'] is not None, 'deployed': False}))
        return
    files = render(policy)
    # Refuse existing paths; no broad overwrite, symlink traversal or remote action.
    if args.output.exists() or args.output.is_symlink():
        raise ValueError('new-output-directory-required')
    args.output.mkdir(mode=0o700)
    for relative, content in files.items():
        target = args.output / relative
        target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        target.write_text(content)
        target.chmod(0o600 if relative.endswith('policy.json') else 0o644)
    print(json.dumps({'status': 'prepared-not-installed', 'files': len(files), 'deployed': False}))


if __name__ == '__main__':
    main()
