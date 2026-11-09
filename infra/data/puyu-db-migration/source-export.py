#!/usr/bin/env python3
"""Owned local MySQL8.4.5 two-schema logical export. No target writes or business repo dependency."""
import argparse,datetime,gzip,hashlib,json,os,queue,re,shutil,stat,subprocess,threading,time,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
CONTAINER='mysql'
CONTAINER_ID='1fee5c4074fac7f6fe309a7ecd24ef882a1b038c1890f13aef5fa04453105788'
IMAGE_ID='sha256:b2f81adb2f3335ee77c6a74a6099bea0c5dca5b51ed01cd84c7966d826992764'
DATABASES=('puyu_auth_local','puyu_erp_local')
DUMP_FLAGS=['--single-transaction','--order-by-primary','--skip-extended-insert','--complete-insert','--hex-blob','--skip-comments','--skip-dump-date','--no-tablespaces','--set-gtid-purged=OFF','--default-character-set=utf8mb4','--tz-utc','--databases',*DATABASES]
MAX_SECONDS=1200
MAX_COMPRESSED=1024**3
AUTH='if [ -n "${MYSQL_ROOT_PASSWORD_FILE:-}" ]; then IFS= read -r MYSQL_PWD < "$MYSQL_ROOT_PASSWORD_FILE"; export MYSQL_PWD; elif [ "${MYSQL_ROOT_PASSWORD+x}" = x ]; then MYSQL_PWD="$MYSQL_ROOT_PASSWORD"; export MYSQL_PWD; else exit 90; fi; '
MYSQL=AUTH+'exec mysql --protocol=socket --user=root --batch --raw --skip-column-names --default-character-set=utf8mb4 "$@"'
DUMP=AUTH+'start=$(awk \'{print $22}\' /proc/$$/stat); printf \'DUMP_PID:%s:%s\\n\' "$$" "$start" >&2; exec mysqldump --protocol=socket --user=root "$@"'
ENV={'PATH':os.environ.get('PATH','/usr/bin:/bin'),'LANG':'C','LC_ALL':'C'}


class Rejected(RuntimeError):pass


def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()


def query(sql,allow_error=False):
    p=subprocess.run(['docker','exec','-i',CONTAINER,'sh','-c',MYSQL,'query'],input=sql.encode(),stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,timeout=35,env=ENV)
    if p.returncode and not allow_error:raise Rejected('source-metadata-query-failed')
    return p.returncode,p.stdout.decode('utf8')


def scalar(sql):
    _,raw=query(sql);return raw.strip()


def rows(sql):
    _,raw=query(sql);return [json.loads(x) for x in raw.splitlines() if x]


def metadata():
    quoted=','.join("'"+x+"'" for x in DATABASES)
    schemas=rows('SELECT JSON_ARRAY(schema_name,default_character_set_name,default_collation_name) FROM information_schema.schemata WHERE schema_name IN ('+quoted+') ORDER BY schema_name;')
    tables=rows("SELECT JSON_ARRAY(table_schema,table_name,table_type,COALESCE(engine,''),COALESCE(table_collation,'')) FROM information_schema.tables WHERE table_schema IN ("+quoted+') ORDER BY table_schema,table_name;')
    columns=rows("SELECT JSON_ARRAY(table_schema,table_name,ordinal_position,column_name,column_type,is_nullable,column_default,extra,character_set_name,collation_name,generation_expression) FROM information_schema.columns WHERE table_schema IN ("+quoted+') ORDER BY table_schema,table_name,ordinal_position;')
    indexes=rows("SELECT JSON_ARRAY(table_schema,table_name,index_name,non_unique,seq_in_index,column_name,expression,sub_part,collation,index_type,is_visible) FROM information_schema.statistics WHERE table_schema IN ("+quoted+') ORDER BY table_schema,table_name,index_name,seq_in_index;')
    objects={}
    for label,sql in [('routines','SELECT COUNT(*) FROM information_schema.routines WHERE routine_schema IN ('+quoted+');'),('triggers','SELECT COUNT(*) FROM information_schema.triggers WHERE trigger_schema IN ('+quoted+');'),('events','SELECT COUNT(*) FROM information_schema.events WHERE event_schema IN ('+quoted+');')]:objects[label]=int(scalar(sql))
    return {'schemas':schemas,'tables':tables,'columns':columns,'indexes':indexes,'object_counts':objects}


def validate_metadata(value):
    if [x[0] for x in value['schemas']]!=list(DATABASES):raise Rejected('exact-source-schema-set-required')
    tables=value['tables']
    if len(tables)>500 or not tables or any(t[2]!='BASE TABLE' or t[3]!='InnoDB' for t in tables):raise Rejected('only-bounded-InnoDB-base-tables-supported')
    pk={(r[0],r[1]) for r in value['indexes'] if r[2]=='PRIMARY'}
    if any((t[0],t[1]) not in pk for t in tables):raise Rejected('every-exported-table-requires-primary-key')
    if any(value['object_counts'].values()):raise Rejected('views-routines-triggers-events-require-separate-review')


def independent_release_counts(connection_id):
    if type(connection_id)is not int or connection_id<=0:raise Rejected('owned-connection-id-required')
    connection=int(scalar('SELECT COUNT(*) FROM performance_schema.threads WHERE PROCESSLIST_ID='+str(connection_id)+';'))
    locks=int(scalar("SELECT COUNT(*) FROM performance_schema.metadata_locks WHERE OBJECT_TYPE='BACKUP LOCK' AND OWNER_THREAD_ID IN (SELECT THREAD_ID FROM performance_schema.threads WHERE PROCESSLIST_ID="+str(connection_id)+');'))
    return {'owned_lock_connection_count':connection,'owned_backup_lock_count':locks}


class BackupLock:
    def __init__(self):
        self.nonce=uuid.uuid4().hex;self.connection_id=None;self.process=None;self.queue=queue.Queue();self.release_proof=None;self.fallback_kill_used=False
    def __enter__(self):
        self.process=subprocess.Popen(['docker','exec','-i',CONTAINER,'sh','-c',MYSQL,'lock','--skip-reconnect','--unbuffered'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,env=ENV)
        threading.Thread(target=self._reader,daemon=True).start()
        try:
            self._send("SELECT 'CONNECTED:"+self.nonce+"',CONNECTION_ID();\n")
            line=self._expect('CONNECTED:',10);parts=line.split('\t')
            if len(parts)!=2 or not parts[1].isdigit():raise Rejected('source-lock-session-handshake-invalid')
            self.connection_id=int(parts[1])
            self._send("SET SESSION lock_wait_timeout=15; SET SESSION wait_timeout=1250; LOCK INSTANCE FOR BACKUP; SELECT 'LOCKED:"+self.nonce+"';\n")
            self._expect('LOCKED:',25)
            if self.process.poll()is not None:raise Rejected('lock-session-exited-before-dump')
            return self
        except Exception:
            self.release();raise
    def _reader(self):
        for line in self.process.stdout:self.queue.put(line.decode('utf8','replace').rstrip('\r\n'))
        self.queue.put(None)
    def _send(self,text):
        if self.process.poll()is not None:raise Rejected('owned-lock-session-not-running')
        self.process.stdin.write(text.encode());self.process.stdin.flush()
    def _expect(self,prefix,timeout):
        deadline=time.monotonic()+timeout
        while time.monotonic()<deadline:
            try:line=self.queue.get(timeout=min(1,max(.01,deadline-time.monotonic())))
            except queue.Empty:
                if self.process.poll()is not None:raise Rejected('owned-lock-session-ended-unexpectedly')
                continue
            if line is None:raise Rejected('owned-lock-session-output-closed')
            if line.startswith(prefix+self.nonce):return line
            raise Rejected('unexpected-owned-lock-session-output')
        raise Rejected('owned-lock-session-handshake-timeout')
    def alive(self):return self.process is not None and self.process.poll()is None
    def release(self):
        if self.release_proof is not None:return self.release_proof
        acknowledged=False
        try:
            if self.alive():
                try:
                    self._send("UNLOCK INSTANCE; SELECT 'RELEASED:"+self.nonce+"';\n")
                    self._expect('RELEASED:',15);acknowledged=True;self.process.stdin.close();self.process.wait(timeout=10)
                except Exception:pass
            if self.connection_id is not None:
                counts=independent_release_counts(self.connection_id)
                if counts['owned_lock_connection_count'] or counts['owned_backup_lock_count']:
                    self.fallback_kill_used=True;query('KILL CONNECTION '+str(self.connection_id)+';',allow_error=True)
                    deadline=time.monotonic()+15
                    while time.monotonic()<deadline:
                        counts=independent_release_counts(self.connection_id)
                        if counts=={'owned_lock_connection_count':0,'owned_backup_lock_count':0}:break
                        time.sleep(.3)
                if counts!={'owned_lock_connection_count':0,'owned_backup_lock_count':0}:raise Rejected('owned-source-lock-release-unconfirmed')
                self.release_proof={'UNLOCK_marker_acknowledged':acknowledged,'independent_counts':counts,'owned_connection_KILL_fallback_used':self.fallback_kill_used,'session_idle_safety_bound_seconds':1250}
            else:
                self.release_proof={'UNLOCK_marker_acknowledged':False,'no_LOCK_command_sent':True,'owned_connection_KILL_fallback_used':False}
            return self.release_proof
        finally:
            # Always close/dispose the owned CLI, even if the independent proof query itself fails.
            if self.process is not None:
                try:
                    if not self.process.stdin.closed:self.process.stdin.close()
                except Exception:pass
                if self.process.poll()is None:
                    self.process.terminate()
                    try:self.process.wait(timeout=5)
                    except subprocess.TimeoutExpired:self.process.kill();self.process.wait(timeout=5)
    def __exit__(self,*args):self.release()


def guard_container():
    fmt='{"Name":{{json .Name}},"ID":{{json .Id}},"ImageID":{{json .Image}},"State":{{json .State.Status}}}'
    p=subprocess.run(['docker','inspect','--type','container','--format',fmt,CONTAINER],capture_output=True,text=True,timeout=15,env=ENV)
    if p.returncode:raise Rejected('fixed-source-container-inspect-failed')
    actual=json.loads(p.stdout)
    if actual!={'Name':'/mysql','ID':CONTAINER_ID,'ImageID':IMAGE_ID,'State':'running'}:raise Rejected('fixed-source-container-identity-changed')
    if scalar('SELECT VERSION();')!='8.4.5':raise Rejected('fixed-source-MySQL-version-changed')
    return actual


def private_directory():
    base=ROOT/'private/puyu-db-migration/20261109'
    for path in [ROOT/'private',ROOT/'private/puyu-db-migration',base]:
        if not path.exists():path.mkdir(mode=0o700)
        s=path.lstat()
        if path.resolve()!=path or not stat.S_ISDIR(s.st_mode) or s.st_uid!=os.getuid() or stat.S_IMODE(s.st_mode)!=0o700:raise Rejected('private-output-directory-owner-or-mode')
    if shutil.disk_usage(base).free<2*1024**3:raise Rejected('minimum-two-GiB-free-output-space-required')
    run_id=uuid.uuid4().hex;folder=base/run_id;folder.mkdir(mode=0o700)
    return run_id,folder


def private_json(path,value):
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'w') as f:json.dump(value,f,ensure_ascii=False,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())


def dispose_dump_process(pid,start):
    if not re.fullmatch('[0-9]+',str(pid)) or not re.fullmatch('[0-9]+',str(start)):raise Rejected('owned-dump-process-marker-invalid')
    probe='p="$1"; expected="$2"; [ -r "/proc/$p/stat" ] || exit 0; IFS= read -r comm < "/proc/$p/comm"; [ "$comm" = mysqldump ] || exit 91; actual=$(awk \'{print $22}\' "/proc/$p/stat"); [ "$actual" = "$expected" ] || exit 92; exit 10'
    def state():
        p=subprocess.run(['docker','exec',CONTAINER,'sh','-c',probe,'probe',str(pid),str(start)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=10,env=ENV)
        if p.returncode not in (0,10):raise Rejected('owned-dump-process-identity-or-probe-unconfirmed')
        return p.returncode
    for signal in ['TERM','KILL']:
        if state()==0:return True
        command=probe.replace('exit 10', 'kill -'+signal+' "$p"')
        p=subprocess.run(['docker','exec',CONTAINER,'sh','-c',command,'dispose',str(pid),str(start)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=10,env=ENV)
        if p.returncode:raise Rejected('owned-dump-process-disposal-unconfirmed')
        deadline=time.monotonic()+5
        while time.monotonic()<deadline:
            if state()==0:return True
            time.sleep(.2)
    raise Rejected('owned-dump-process-still-present')


class CompressedBound:
    def __init__(self,raw):self.raw=raw
    def write(self,data):
        if self.raw.tell()+len(data)>MAX_COMPRESSED:raise Rejected('compressed-output-size-bound-exceeded')
        return self.raw.write(data)
    def flush(self):return self.raw.flush()
    def tell(self):return self.raw.tell()


def dump(folder,lock):
    path=folder/'source.sql.gz';fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    process=subprocess.Popen(['docker','exec','-i',CONTAINER,'sh','-c',DUMP,'dump',*DUMP_FLAGS],stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=ENV)
    deadline=time.monotonic()+MAX_SECONDS;failed=[];markers=queue.Queue(maxsize=1);owned=None
    def stderr_reader():
        for line in process.stderr:
            value=line.decode('ascii','ignore').strip()
            if re.fullmatch(r'DUMP_PID:[0-9]+:[0-9]+',value) and markers.empty():
                try:markers.put_nowait(value)
                except queue.Full:pass
    threading.Thread(target=stderr_reader,daemon=True).start()
    def watchdog():
        while process.poll()is None:
            if not lock.alive():failed.append('owned-DDL-lock-session-lost');process.kill();return
            if time.monotonic()>deadline:failed.append('dump-1200second-bound-exceeded');process.kill();return
            time.sleep(.2)
    threading.Thread(target=watchdog,daemon=True).start()
    total=0
    try:
        try:
            marker=markers.get(timeout=10).split(':');owned=(int(marker[1]),int(marker[2]))
        except queue.Empty:raise Rejected('owned-dump-process-marker-timeout') from None
        with os.fdopen(fd,'wb') as output:
            fd=None
            with gzip.GzipFile(filename='',fileobj=CompressedBound(output),mode='wb',mtime=0) as zipped:
                while True:
                    chunk=process.stdout.read(1024*1024)
                    if not chunk:break
                    zipped.write(chunk);total+=len(chunk)
                    if output.tell()>MAX_COMPRESSED:failed.append('compressed-output-size-bound-exceeded');process.kill();break
            output.flush();os.fsync(output.fileno())
        rc=process.wait(timeout=10)
        if failed or rc or not lock.alive():raise Rejected(failed[0] if failed else 'dump-client-failed-or-lock-lost')
        if path.stat().st_size>MAX_COMPRESSED:raise Rejected('compressed-output-size-bound-exceeded')
        return path,total
    finally:
        if fd is not None:os.close(fd)
        if process.poll()is None:process.kill();process.wait(timeout=10)
        # Killing only the host docker CLI cannot prove container exec termination.
        if owned is not None:dispose_dump_process(*owned)


def verify_gzip(path):
    digest=hashlib.sha256();uncompressed=0
    with path.open('rb') as raw:
        for chunk in iter(lambda:raw.read(1024*1024),b''):digest.update(chunk)
    with gzip.open(path,'rb') as raw:
        for chunk in iter(lambda:raw.read(1024*1024),b''):uncompressed+=len(chunk)
    if not uncompressed:raise Rejected('empty-gzip-stream')
    return digest.hexdigest(),uncompressed


def execute():
    started=time.monotonic();report={'version':1,'started_at':now(),'status':'source-export-unconfirmed','selected_databases':list(DATABASES),'dump_flags':DUMP_FLAGS,'source_rows_count_claim':'Exportpoint is one singletransaction dump; preflight1291 isnotasserted asdumpcount.','target_writes_or_application_stop':False,'data_hashes_SQL_or_credentials_in_public_evidence':False,'code_SHA256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()};folder=None;lock=None
    try:
        source=guard_container();pre=metadata();validate_metadata(pre);run_id,folder=private_directory();lock=BackupLock()
        with lock:
            locked=metadata();validate_metadata(locked)
            if locked!=pre:raise Rejected('source-schema-changed-before-lock')
            report['DDL_lock_acquired_at']=now();path,plainbytes=dump(folder,lock)
        report['DDL_lock_released_at']=now();report['session_release_proof']=lock.release_proof
        post=metadata();validate_metadata(post)
        if post!=locked:raise Rejected('source-schema-metadata-changed-after-export')
        digest,actualbytes=verify_gzip(path)
        if plainbytes!=actualbytes:raise Rejected('uncompressed-gzip-byte-count-mismatch')
        manifest={'version':1,'run_id':run_id,'source_container':source,'source_mysql_version':'8.4.5','databases':[{'name':db,'table_count':sum(t[0]==db for t in locked['tables'])} for db in DATABASES],'source_sha256':digest,'source_compressed_bytes':path.stat().st_size,'source_expanded_bytes':actualbytes,'dump_flags':DUMP_FLAGS,'export_started_at':report['started_at'],'export_finished_at':now(),'compressed_bytes':path.stat().st_size,'uncompressed_bytes':actualbytes,'source_sql_gzip_SHA256':digest,'gzip_CRC_verified':True,'schema_before_lock_and_after_metadata':locked,'schema_stable_before_after':True,'session_release_proof':lock.release_proof,'snapshot_rows':'Determine fromexportedSQL snapshot,fingerprint privately; no preflightrowcount equivalence claim','DML_continued_allowed':True,'target_import_performed':False}
        private_json(folder/'manifest.json',manifest)
        report.update(status='source-two-puyu-databases-exported-private-only',run_id=run_id,database_count=2,table_counts={db:sum(t[0]==db for t in locked['tables']) for db in DATABASES},gzip_CRC_verified=True,private_SHA_verified=True,schema_metadata_stable_before_after=True,compressed_bytes=path.stat().st_size,uncompressed_bytes=actualbytes,private_directory_reference=str(folder.relative_to(ROOT)),private_files_mode600=True,private_directory_mode700=True,source_container_not_restarted=True)
    except Exception as error:
        report.update(status='source-export-not-confirmed-no-target-write',error_class=type(error).__name__,reason=str(error) if isinstance(error,Rejected) else 'raw-details-withheld')
        if lock is not None:report['session_release_proof']=lock.release_proof
        if folder is not None:
            report['private_partial_directory_reference']=str(folder.relative_to(ROOT))
            private_json(folder/'failure.json',report)
    report['finished_at']=now();report['elapsed_seconds']=round(time.monotonic()-started,3)
    dest=ROOT/'completion/20261109-puyu-db-migration/source-export.json';dest.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))
    return 0 if report['status']=='source-two-puyu-databases-exported-private-only' else 1


if __name__=='__main__':
    os.umask(0o077);p=argparse.ArgumentParser();p.add_argument('--execute-source-private-export',action='store_true');args=p.parse_args()
    if not args.execute_source_private_export:print(json.dumps({'status':'plan-only-no-database-or-target-actions','databases':list(DATABASES),'dump_flags':DUMP_FLAGS}));raise SystemExit(0)
    raise SystemExit(execute())
