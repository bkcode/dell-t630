#!/usr/bin/env python3
"""Render private, role-specific deployment bundles; never deploy or read source data."""
import argparse, base64, hashlib, ipaddress, json, os, re, secrets, shutil, uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ROLES = ('prod-db', 'prod-infra', 'test-data')

def write_private(path, value):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if path.is_symlink():
        raise ValueError('refusing symlink in private output')
    path.write_text(value)
    path.chmod(0o600)

def secret(directory, name, kind='password'):
    p = directory / name
    if p.is_symlink():
        raise ValueError('refusing symlink in secret store')
    if not p.exists():
        value = base64.b64encode(secrets.token_bytes(48)).decode() if kind == 'jwt' else secrets.token_hex(4 if kind == 'salt' else 24)
        fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'w') as out:
            out.write(value + '\n')
    p.chmod(0o600)
    value = p.read_text().strip()
    if not value or '\n' in value:
        raise ValueError('empty or invalid existing secret; no automatic rotation')
    return value

def rabbit_hash(password, salt):
    raw = bytes.fromhex(salt)
    return base64.b64encode(raw + hashlib.sha256(raw + password.encode()).digest()).decode()

def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('role', choices=ROLES)
    parser.add_argument('--service-ip', required=True)
    parser.add_argument('--mysql-host', help='Required for prod-infra; use prod-db IP')
    parser.add_argument('--data-root', help='Absolute path below the verified data mount')
    parser.add_argument('--data-mountpoint', default='/srv/dell-data')
    parser.add_argument('--data-uuid', type=uuid.UUID, help='Filesystem UUID measured on the assigned guest data disk')
    parser.add_argument('--install-dir', help='Bundle directory on guest, default /opt/dell/data/ROLE')
    parser.add_argument('--namespace-id', type=uuid.UUID)
    args = parser.parse_args()
    ipaddress.IPv4Address(args.service_ip)
    if args.role == 'prod-infra':
        if not args.mysql_host:
            parser.error('--mysql-host is required for prod-infra')
        ipaddress.IPv4Address(args.mysql_host)
    env = 'test' if args.role == 'test-data' else 'prod'
    private_root = ROOT / 'private' / 'data'
    directory = private_root / 'store' / env
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    directory.chmod(0o700)
    names = ['mysql-root-password','nacos-db-password','redis-password','rabbit-admin-password','rabbit-app-password','nacos-admin-password','nacos-client-password','nacos-identity-value']
    values = {n:secret(directory,n) for n in names}
    values['nacos-auth-token'] = secret(directory, 'nacos-auth-token', 'jwt')
    salts = {n:secret(directory,n,'salt') for n in ['rabbit-admin-salt','rabbit-app-salt']}
    bundle = private_root / 'bundles' / args.role
    bundle.mkdir(parents=True, exist_ok=True, mode=0o700)
    bundle.chmod(0o700)
    for sub in ['secrets','config','scripts','vendor']:
        (bundle/sub).mkdir(exist_ok=True, mode=0o700)
    lock = json.loads((HERE/'images.lock.json').read_text())
    for name, meta in lock['vendor'].items():
        if hashlib.sha256((HERE/'vendor'/name).read_bytes()).hexdigest() != meta['sha256']:
            raise ValueError('official vendor checksum mismatch')
        shutil.copy2(HERE/'vendor'/name, bundle/'vendor'/name)
    shutil.copy2(HERE/f'compose.{args.role}.yaml', bundle/'compose.yaml')
    shutil.copy2(HERE/'images.lock.json', bundle/'images.lock.json')
    for p in (HERE/'scripts').iterdir():
        if p.is_file():
            shutil.copy2(p, bundle/'scripts'/p.name)
    needed = {'mysql-root-password','nacos-db-password'} if args.role == 'prod-db' else set(values) - ({'mysql-root-password'} if args.role == 'prod-infra' else set())
    expected = needed | ({'rabbit-definitions.json'} if args.role != 'prod-db' else set())
    known = set(values) | {'rabbit-definitions.json'}
    for existing in (bundle/'secrets').iterdir():
        if existing.name not in known:
            raise ValueError('unexpected file in generated secret bundle; inspect before rendering')
        if existing.name not in expected:
            existing.unlink()
    for n,v in values.items():
        if n in needed:
            write_private(bundle/'secrets'/n,v+'\n')
    users = [('mq_'+env+'_admin','rabbit-admin-password','rabbit-admin-salt',['administrator']),('finger_'+env+'_mq','rabbit-app-password','rabbit-app-salt',[])]
    definitions = {'users':[{'name':n,'password_hash':rabbit_hash(values[p],salts[s]),'hashing_algorithm':'rabbit_password_hashing_sha256','tags':tags} for n,p,s,tags in users], 'vhosts':[{'name':'/finger-'+env}], 'permissions':[{'user':n,'vhost':'/finger-'+env,'configure':'.*','write':'.*','read':'.*'} for n,_,_,_ in users]}
    defs_file = directory/'rabbit-definitions.json'
    write_private(defs_file,json.dumps(definitions,indent=2)+'\n')
    if args.role != 'prod-db':
        write_private(bundle/'secrets'/'rabbit-definitions.json',defs_file.read_text())
    test = env == 'test'
    mysql_config = '[mysqld]\ncharacter-set-server=utf8mb4\ncollation-server=utf8mb4_unicode_ci\ninnodb_flush_log_at_trx_commit=1\nsync_binlog=1\n'
    mysql_config += 'innodb_buffer_pool_size=192M\nmax_connections=40\ntable_open_cache=128\nperformance_schema=OFF\nskip-log-bin\nserver_id=2001\n' if test else 'innodb_buffer_pool_size=8G\nmax_connections=200\nserver_id=1001\nlog_bin=mysql-bin\nmax_binlog_size=128M\nbinlog_expire_logs_seconds=604800\n'
    (bundle/'config'/'mysql.cnf').write_text(mysql_config)
    (bundle/'config'/'rabbitmq.conf').write_text('management.load_definitions = /run/secrets/rabbit-definitions.json\nvm_memory_high_watermark.absolute = '+('256MB' if test else '768MB')+'\ndisk_free_limit.absolute = 1GB\n')
    install = args.install_dir or '/opt/dell/data/'+args.role
    data = args.data_root or args.data_mountpoint.rstrip('/')+'/'+args.role
    for value in [install,data,args.data_mountpoint]:
        if not value.startswith('/') or not re.fullmatch(r'/[A-Za-z0-9_./-]+',value):
            raise ValueError('paths must be absolute and contain safe path characters')
        if '..' in value.split('/') or '.' in value.split('/') or os.path.normpath(value) != value:
            raise ValueError('dot traversal and non-normalized paths are forbidden')
        if Path(value).resolve(strict=False) != Path(value):
            raise ValueError('existing symlink path components are forbidden')
    mount = Path(args.data_mountpoint).resolve(strict=False)
    data_path = Path(data).resolve(strict=False)
    if mount == Path('/') or not data_path.is_relative_to(mount) or data_path==mount:
        raise ValueError('data-root must resolve below a dedicated non-root data-mountpoint')
    previous = {}
    if (bundle/'.env').exists():
        previous = dict(line.split('=',1) for line in (bundle/'.env').read_text().splitlines() if line and not line.startswith('#'))
    data_uuid = str(args.data_uuid) if args.data_uuid else previous.get('DATA_FS_UUID','')
    if data_uuid:
        data_uuid = str(uuid.UUID(data_uuid))
    namespace = str(args.namespace_id or uuid.uuid5(uuid.NAMESPACE_DNS,'dell.finger.'+env))
    env_values={'ROLE':args.role,'ENVIRONMENT':env,'SERVICE_IP':args.service_ip,'MYSQL_HOST':'mysql' if test else (args.mysql_host or args.service_ip),'NACOS_DB_NAME':'nacos_'+env,'NACOS_DB_USER':'nacos_'+env,'NACOS_NAMESPACE_ID':namespace,'NACOS_CLIENT_USER':'finger_'+env,'NACOS_CLIENT_ROLE':'finger-'+env+'-client','RABBIT_ADMIN_USER':'mq_'+env+'_admin','RABBIT_APP_USER':'finger_'+env+'_mq','RABBIT_VHOST':'/finger-'+env,'DATA_ROOT':data,'DATA_MOUNTPOINT':str(mount),'DATA_FS_UUID':data_uuid,'INSTALL_DIR':install}
    write_private(bundle/'.env',''.join(k+'='+v+'\n' for k,v in env_values.items()))
    metadata={'role':args.role,'environment':env,'service_ip':args.service_ip,'install_dir':install,'data_root':data,'data_mountpoint':str(mount),'data_filesystem_uuid':data_uuid or None,'mount_identity_status':'configured' if data_uuid else 'pending-guest-filesystem-uuid','namespace_id':namespace,'status':'prepared-not-deployed','source_business_data_included':False}
    write_private(bundle/'bundle.json',json.dumps(metadata,indent=2)+'\n')
    for p in bundle.rglob('*'):
        if p.is_file() and p.parent.name != 'scripts':p.chmod(0o600)
    print(json.dumps({'role':args.role,'bundle':str(bundle),'service_ip':args.service_ip,'status':'prepared-not-deployed','secrets':'generated-or-reused; values suppressed'}))

if __name__=='__main__':
    main()
