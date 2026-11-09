#!/usr/bin/python3
"""VM210-only, two-schema Puyu MySQL import. No application or Nacos changes."""
from __future__ import annotations

import argparse, datetime as dt, fcntl, gzip, hashlib, importlib.util, json, os, re
import secrets, socket, stat, subprocess, sys, time
from pathlib import Path

BASE = Path('/root/dell-puyu-db-migration')
FINGERPRINT = Path('/usr/local/libexec/dell-puyu-db-migration/fingerprint.py')
MYSQL = 'dell-data-test-data-mysql-1'
MYSQL_IMAGE = 'sha256:a0f6c7786c75739bd76a37b4b85e0f47b7c5d5a17a094bdd522412fb464d5cbe'
MOUNT_UUID = 'dd1773f9-aa48-4401-a9c8-caf0f66845f3'
DATABASES = ('puyu_auth_local', 'puyu_erp_local')
COUNTS = {'puyu_auth_local': 4, 'puyu_erp_local': 47}
RUN = re.compile(r'[0-9a-f]{32}\Z')
SHA = re.compile(r'[0-9a-f]{64}\Z')
MAX_SQL = 64 * 1024 * 1024
DUMP_FLAGS = ['--single-transaction', '--order-by-primary', '--skip-extended-insert', '--complete-insert',
              '--hex-blob', '--skip-comments', '--skip-dump-date', '--no-tablespaces',
              '--set-gtid-purged=OFF', '--default-character-set=utf8mb4', '--tz-utc', '--databases', *DATABASES]
DOCKER = ['/usr/bin/docker', '--host', 'unix:///var/run/docker.sock']
ENV = {'PATH': '/usr/sbin:/usr/bin:/sbin:/bin', 'LANG': 'C.UTF-8'}

class Rejected(RuntimeError): pass
def need(value, code):
    if not value: raise Rejected(code)
def now(): return dt.datetime.now(dt.timezone.utc).isoformat()

def run(args, *, data=None, timeout=120, limit=MAX_SQL + 1024):
    p = subprocess.run(args, input=data, capture_output=True, timeout=timeout, env=ENV)
    if p.returncode or len(p.stdout) > limit: raise Rejected('fixed-command-failed')
    return p.stdout

def safe_dir(path, create=False):
    if create and not path.exists(): path.mkdir(mode=0o700, parents=True)
    need(path.is_absolute() and path.resolve() == path and path.is_dir(), 'private-directory')
    for parent in [path, *path.parents]:
        s = parent.lstat(); need(stat.S_ISDIR(s.st_mode) and s.st_uid == 0 and not s.st_mode & 0o022, 'private-directory-owner')
    need(stat.S_IMODE(path.stat().st_mode) == 0o700, 'private-directory-mode')

def read_json(path, limit=MAX_SQL):
    s = path.lstat(); need(not path.is_symlink() and stat.S_ISREG(s.st_mode) and s.st_uid == 0 and s.st_nlink == 1 and stat.S_IMODE(s.st_mode) == 0o600 and 0 < s.st_size <= limit, 'private-json')
    def pairs(items):
        d = {}
        for k, v in items: need(k not in d, 'duplicate-json-key'); d[k] = v
        return d
    value = json.loads(path.read_bytes(), object_pairs_hook=pairs)
    need(isinstance(value, dict), 'json-object'); return value

def atom(path, value):
    safe_dir(path.parent); need(not path.exists() and not path.is_symlink(), 'private-file-exists')
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w') as f: json.dump(value, f, sort_keys=True); f.write('\n'); f.flush(); os.fsync(f.fileno())
    d = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try: os.fsync(d)
    finally: os.close(d)

def guard():
    need(os.geteuid() == 0 and socket.gethostname() == 'data-test' and not Path('/etc/pve').exists(), 'target210-only')
    raw = run(['findmnt','-J','--mountpoint','/srv/dell-data','-o','TARGET,UUID'], timeout=20)
    fs = json.loads(raw)['filesystems']; need(len(fs)==1 and fs[0]['uuid']==MOUNT_UUID, 'target-data-uuid')
    ips = json.loads(run(['ip','-j','-4','address','show','scope','global'], timeout=20))
    actual = [a['local'] for i in ips if i['ifname'] not in ('lo','docker0') and not i['ifname'].startswith(('br-','veth')) for a in i.get('addr_info',[]) if a.get('family')=='inet']
    need(actual == ['192.168.19.20'], 'target-ip')
    c = json.loads(run(DOCKER+['inspect','--format','{"Id":{{json .Id}},"Image":{{json .Image}},"State":{{json .State.Status}},"Health":{{json (index (index .State "Health") "Status")}},"RestartCount":{{json .RestartCount}},"OOM":{{json .State.OOMKilled}}}',MYSQL],timeout=20))
    need(c['Image']==MYSQL_IMAGE and c['State']=='running' and c['Health']=='healthy' and not c['OOM'], 'target-mysql-identity')
    return c

def root_sql(sql):
    shell='export MYSQL_PWD="$(cat /run/secrets/mysql-root-password)"; exec mysql --protocol=socket --user=root --batch --raw --skip-column-names --default-character-set=utf8mb4'
    return run(DOCKER+['exec','-i',MYSQL,'sh','-ec',shell], data=sql.encode(), timeout=90).decode().strip()

def collations():
    rows = root_sql('SELECT CONCAT(COLLATION_NAME,"\\t",CHARACTER_SET_NAME) FROM information_schema.COLLATIONS;').splitlines()
    out = {}
    for row in rows:
        name, sep, charset = row.partition('\t'); need(bool(sep) and name not in out, 'target-collation-metadata'); out[name] = charset
    need(out, 'target-collation-empty'); return out

def db_metadata():
    sql = "SELECT CONCAT(TABLE_SCHEMA,'\\t',TABLE_NAME) FROM information_schema.TABLES WHERE TABLE_SCHEMA IN ('puyu_auth_local','puyu_erp_local') ORDER BY TABLE_SCHEMA,TABLE_NAME;"
    return root_sql(sql).splitlines()

def target_database_names():
    rows=root_sql('SHOW DATABASES;').splitlines()
    need(len(rows) <= 128 and all(re.fullmatch(r'[A-Za-z0-9_$-]{1,128}', row) for row in rows),
         'target-database-list')
    return rows

def module_fingerprint():
    s=FINGERPRINT.lstat(); need(not FINGERPRINT.is_symlink() and stat.S_ISREG(s.st_mode) and s.st_uid==0 and stat.S_IMODE(s.st_mode)==0o600, 'fingerprint-module')
    spec=importlib.util.spec_from_file_location('puyu_snapshot_fingerprint',FINGERPRINT); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

def gzip_sql(run_dir, manifest):
    p=run_dir/'source.sql.gz'; s=p.lstat(); need(not p.is_symlink() and stat.S_ISREG(s.st_mode) and s.st_uid==0 and s.st_nlink==1 and stat.S_IMODE(s.st_mode)==0o600 and s.st_size==manifest['source_compressed_bytes'], 'source-gzip-metadata')
    raw=p.read_bytes(); need(hashlib.sha256(raw).hexdigest()==manifest['source_sha256'], 'source-gzip-sha')
    try: sql=gzip.decompress(raw)
    except OSError: raise Rejected('source-gzip-crc') from None
    need(0<len(sql)<=MAX_SQL and len(sql)==manifest['source_expanded_bytes'], 'source-expanded-size')
    return sql

def validate_manifest(manifest):
    required={'version','run_id','source_sha256','source_compressed_bytes','source_expanded_bytes','databases','gzip_CRC_verified','fingerprint'}
    need(required.issubset(manifest) and manifest['version']==1 and RUN.fullmatch(manifest['run_id']) and SHA.fullmatch(manifest['source_sha256']), 'source-manifest-schema')
    need(type(manifest['source_compressed_bytes']) is int and 0<manifest['source_compressed_bytes']<=1024**3 and type(manifest['source_expanded_bytes']) is int and 0<manifest['source_expanded_bytes']<=MAX_SQL and manifest['gzip_CRC_verified'] is True, 'source-manifest-size')
    db=manifest['databases']; need(isinstance(db,list) and {x.get('name'):x.get('table_count') for x in db if isinstance(x,dict)}==COUNTS, 'source-manifest-databases')
    need(isinstance(manifest['fingerprint'],dict), 'source-fingerprint-missing')

def validate_fingerprint(fp):
    need(fp.get('version')==1 and isinstance(fp.get('databases'),dict) and set(fp['databases'])==set(DATABASES), 'fingerprint-schema')
    for name,count in COUNTS.items():
        db=fp['databases'][name]; need(isinstance(db,dict) and isinstance(db.get('create_database'),str) and isinstance(db.get('tables'),dict) and len(db['tables'])==count, 'fingerprint-database')
        for table,row in db['tables'].items():
            empty_columns = row.get('row_count') == 0 and row.get('insert_columns') is None
            need(isinstance(table,str) and isinstance(row,dict) and isinstance(row.get('create_table'),str)
                 and (isinstance(row.get('insert_columns'),list) or empty_columns)
                 and type(row.get('row_count')) is int and row['row_count']>=0
                 and isinstance(row.get('row_multiset_sha256'),str) and SHA.fullmatch(row['row_multiset_sha256']), 'fingerprint-table')

def rewrite_database_create(sql):
    text=sql.decode('utf8')
    pattern=re.compile(r'(?im)^(\s*CREATE\s+DATABASE\s+)(?:/\*!32312\s+IF\s+NOT\s+EXISTS\s*\*/|IF\s+NOT\s+EXISTS)\s+')
    rewritten,n=pattern.subn(r'\1',text)
    need(n==2, 'create-database-if-not-exists-shape')
    return rewritten.encode('utf8')

def importer_name(run_id): return 'puyu_import_'+run_id[:12]
def importer_dir(run_id): return '/tmp/dell-puyu-import-'+run_id
def importer_cnf(run_id): return importer_dir(run_id)+'/client.cnf'

def create_importer(run_id):
    user=importer_name(run_id); password=secrets.token_urlsafe(32)
    need(root_sql("SELECT COUNT(*) FROM mysql.user WHERE user='"+user+"' AND host='localhost';") == '0',
         'target-importer-name-collision')
    created = False
    try:
        root_sql("CREATE USER '"+user+"'@'localhost' IDENTIFIED BY '"+password+"';")
        created = True
        partial=root_sql('SELECT @@partial_revokes;'); need(partial in ('0','1'), 'target-partial-revokes')
        grants=[]
        for db in DATABASES:
            # With partial revokes disabled, schema grants are patterns; backtick
            # quote the escaped underscores so this is still a literal two-schema
            # grant.  The enabled form uses the literal database identifier.
            scope=('`'+db+'`.*') if partial=='1' else ('`'+db.replace('_','\\_')+'`.*')
            grants.append('GRANT ALL PRIVILEGES ON '+scope+" TO '"+user+"'@'localhost';")
        root_sql(''.join(grants)+'FLUSH PRIVILEGES;')
        shown=root_sql("SHOW GRANTS FOR '"+user+"'@'localhost';").splitlines()
        db_rows=[x for x in shown if any(db in x or db.replace('_','\\_') in x for db in DATABASES)]
        need(len(db_rows)==2 and sum('USAGE ON *.*' in x for x in shown)==1
             and len(shown)==3 and all('GRANT OPTION' not in x and 'FILE' not in x and 'SUPER' not in x for x in shown),
             'target-importer-grants')
        cnf='[client]\nuser='+user+'\npassword='+password+'\nprotocol=socket\ndefault-character-set=utf8mb4\n'
        command='umask 077; mkdir "$1"; chmod 700 "$1"; test ! -e "$1/client.cnf"; cat > "$1/client.cnf"; chmod 600 "$1/client.cnf"'
        run(DOCKER+['exec','-i',MYSQL,'sh','-ec',command,'cnf',importer_dir(run_id)],data=cnf.encode(),timeout=30)
        return user, created
    except Exception:
        if created:
            cleanup_importer(run_id,user,created=True)
        raise

def cleanup_importer(run_id, user, *, created):
    try:
        if created:
            root_sql("DROP USER '"+user+"'@'localhost'; FLUSH PRIVILEGES;")
            need(root_sql("SELECT COUNT(*) FROM mysql.user WHERE user='"+user+"' AND host='localhost';") == '0',
                 'target-importer-removal-unconfirmed')
    finally:
        run(DOCKER+['exec',MYSQL,'sh','-ec','if [ -f "$1/client.cnf" ]; then rm -f -- "$1/client.cnf"; fi; rmdir "$1" 2>/dev/null || true','rm',importer_dir(run_id)],timeout=30)

def import_sql(run_id, sql):
    command='exec mysql --defaults-file="$1" --no-login-paths --binary-mode --local-infile=0 --protocol=socket'
    run(DOCKER+['exec','-i',MYSQL,'sh','-ec',command,'mysql',importer_cnf(run_id)],data=sql,timeout=900,limit=1024)

def target_dump_readonly():
    """Post-import verification uses the existing root secret only for SELECT/dump.

    The temporary importer and its cnf have already been removed by `apply`.
    This does not reset, alter, or expose the target root password.
    """
    shell='export MYSQL_PWD="$(cat /run/secrets/mysql-root-password)"; exec mysqldump --protocol=socket --user=root --single-transaction --order-by-primary --skip-extended-insert --complete-insert --hex-blob --skip-comments --skip-dump-date --no-tablespaces --set-gtid-purged=OFF --default-character-set=utf8mb4 --tz-utc --databases puyu_auth_local puyu_erp_local'
    return run(DOCKER+['exec','-i',MYSQL,'sh','-ec',shell],timeout=900).rstrip(b'\n')+b'\n'

def prepare(run_id):
    guard(); safe_dir(BASE,create=True); d=BASE/run_id; safe_dir(d); need({x.name for x in d.iterdir()}=={'source.sql.gz','manifest.json'},'run-upload-contract')
    manifest=read_json(d/'manifest.json'); validate_manifest(manifest); need(manifest['run_id']==run_id,'run-manifest-id')
    sql=gzip_sql(d,manifest); fpmod=module_fingerprint(); actual=fpmod.fingerprint(sql,collations=collations()); validate_fingerprint(actual); need(actual==manifest['fingerprint'],'source-fingerprint-drift')
    need(not set(DATABASES).intersection(target_database_names()) and db_metadata()==[], 'target-database-collision')
    snapshot={'version':1,'run_id':run_id,'target_mysql':guard(),'existing_database_tables':db_metadata(),'source_manifest':manifest}
    atom(d/'target-before.json',snapshot); atom(d/'prepared.json',{'phase':'prepared','source_table_counts':COUNTS,'target_existing_puyu_databases':0,'SQL_or_hashes_emitted':False})
    return {'status':'prepared-no-target-write','run_id':run_id,'source_tables':sum(COUNTS.values()),'target_collisions':0}

def apply(run_id):
    guard();d=BASE/run_id;safe_dir(d); manifest=read_json(d/'manifest.json');validate_manifest(manifest);before=read_json(d/'target-before.json');need(before['run_id']==run_id and before['existing_database_tables']==[],'target-backup-required')
    sql=gzip_sql(d,manifest);fpmod=module_fingerprint();source_fp=fpmod.fingerprint(sql,collations=collations());need(source_fp==manifest['fingerprint'],'source-fingerprint-drift');need(not set(DATABASES).intersection(target_database_names()) and db_metadata()==[],'target-database-collision')
    user=importer_name(run_id); created=False
    try:
        user,created=create_importer(run_id)
        import_sql(run_id,rewrite_database_create(sql))
    finally: cleanup_importer(run_id,user,created=created)
    atom(d/'applied.json',{'phase':'applied','run_id':run_id,'importer_removed':True,'databases_created':list(DATABASES),'automatic_rollback_or_database_drop':False})
    return {'status':'target-two-databases-imported-pending-verify','run_id':run_id,'databases':list(DATABASES),'temporary_importer_removed':True}

def verify(run_id):
    guard();d=BASE/run_id;safe_dir(d);manifest=read_json(d/'manifest.json');validate_manifest(manifest);need((d/'applied.json').is_file(),'apply-required')
    source=gzip_sql(d,manifest);coll=collations();fpmod=module_fingerprint();source_fp=fpmod.fingerprint(source,collations=coll);target_fp=fpmod.fingerprint(target_dump_readonly(),collations=coll)
    validate_fingerprint(target_fp);need(source_fp==manifest['fingerprint'] and target_fp==source_fp,'target-fingerprint-mismatch')
    for db,tables in target_fp['databases'].items():
        for table in tables['tables']:
            out=root_sql('CHECK TABLE `'+db+'`.`'+table+'`;');need(out.endswith('\tstatus\tOK'),'target-check-table')
    user=importer_name(run_id);need(root_sql("SELECT COUNT(*) FROM mysql.user WHERE user='"+user+"';")=='0','target-importer-remains')
    atom(d/'verified.json',{'phase':'verified','run_id':run_id,'databases':list(DATABASES),'table_counts':COUNTS,'target_fingerprint_equals_source':True,'temporary_importer_removed':True})
    return {'status':'target-puyu-snapshot-verified','run_id':run_id,'databases':list(DATABASES),'table_counts':COUNTS,'SQL_or_data_hash_emitted':False}

def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','apply','verify']);p.add_argument('--run-id',required=True);a=p.parse_args();need(RUN.fullmatch(a.run_id),'run-id');os.umask(0o077);safe_dir(BASE,create=True)
    fd=os.open(BASE/'.worker.lock',os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW,0o600)
    try:
        s=os.fstat(fd);need(stat.S_ISREG(s.st_mode) and s.st_uid==0 and stat.S_IMODE(s.st_mode)==0o600,'worker-lock');fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        print(json.dumps({'prepare':prepare,'apply':apply,'verify':verify}[a.action](a.run_id),sort_keys=True))
    finally: os.close(fd)
if __name__=='__main__':
    try: main()
    except Exception as e:
        code=str(e) if isinstance(e,Rejected) and re.fullmatch('[a-z0-9-]{1,80}',str(e)) else None
        print(json.dumps({'status':'puyu-target-import-not-confirmed','error_type':type(e).__name__,'failure_code':code,'automatic_rollback_or_database_drop':False}),file=sys.stderr);raise SystemExit(1)
