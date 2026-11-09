#!/usr/bin/env python3
"""PVE metadata/RAID read-only collection; push via existing QGA, no host listener/key."""
import json,subprocess,time,os,datetime
from pathlib import Path
assert Path('/etc/pve').exists() and os.geteuid()==0

def run(a,timeout=20):
 p=subprocess.run(a,capture_output=True,text=True,timeout=timeout)
 if p.returncode:raise RuntimeError('Metadata collector command failed: '+a[0])
 return p.stdout

def label(value):return json.dumps(str(value),ensure_ascii=True)
lines=['# Dell PVE metadata via existing QGA; contains no credentials or user content']
def metric(name,value,**labels):
 suffix='{'+','.join(k+'='+label(v) for k,v in sorted(labels.items()))+'}' if labels else ''
 lines.append(name+suffix+' '+str(float(value)))
metric('dell_pve_collector_timestamp_seconds',time.time())
mem={x.split(':',1)[0]:int(x.split()[1])*1024 for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith(('MemTotal:','MemAvailable:'))}
for k,v in mem.items():metric('dell_pve_'+('memory_total_bytes' if k=='MemTotal' else 'memory_available_bytes'),v)
metric('dell_pve_cpu_logical_count',os.cpu_count());metric('dell_pve_load1',os.getloadavg()[0])
for r in json.loads(run(['pvesh','get','/cluster/resources','--type','vm','--output-format','json'])):
 args={'vmid':r['vmid'],'role':r.get('name','unknown')};metric('dell_pve_guest_running',r.get('status')=='running',**args)
 metric('dell_pve_guest_memory_bytes',r.get('mem',0),**args);metric('dell_pve_guest_memory_limit_bytes',r.get('maxmem',0),**args)
for r in json.loads(run(['pvesh','get','/nodes/pve/storage','--output-format','json'])):
 for key in ['total','avail','used']:
  if key in r:metric('dell_pve_storage_'+key+'_bytes',r[key],storage=r['storage'])
program='/root/dell-bootstrap/perccli-extracted/opt/MegaRAID/perccli/perccli64'
controller=json.loads(run([program,'/c0','show','J']))['Controllers'][0]['Response Data']
for r in controller.get('VD LIST',[]):metric('dell_pve_raid_virtual_optimal',r['State']=='Optl',array=r['DG/VD'],raid=r['TYPE'])
for r in controller.get('PD LIST',[]):metric('dell_pve_raid_member_online',r['State']=='Onln',slot=r['EID:Slt'])
for r in controller.get('BBU_Info',[]):metric('dell_pve_bbu_optimal',r.get('State')=='Optimal')
p=subprocess.run(['pct','exec','100','--','systemctl','is-active','cloudflared'],capture_output=True,text=True,timeout=10);metric('dell_cf_cloudflared_active',p.returncode==0 and p.stdout.strip()=='active')
# BEGIN dell-local-backup metadata metrics (candidate; insert before text='\n'.join(lines))
# Uses only the collector's existing metric(name, value) output API.
import stat as _db_stat
import re as _db_re
import sys as _db_sys

_DB_ALLOWED = (100, 190, 200, 201, 210, 221, 230, 240, 250, 260, 270)
_DB_LIMIT = 65536
_DB_STATE = '/var/lib/dell-local-backup'
_DB_STORE = '/mnt/pve/store'
_DB_UUID = '75e5b438-5ff3-4139-83d6-b6a6847aedac'


def _db_require(ok):
    if not ok:
        raise ValueError('backup metadata rejected')


def _db_pairs(items):
    result = {}
    for key, value in items:
        _db_require(key not in result)
        result[key] = value
    return result


def _db_json(raw):
    _db_require(isinstance(raw, (bytes, str)) and len(raw) <= _DB_LIMIT)
    value = json.loads(raw, object_pairs_hook=_db_pairs,
                       parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
    _db_require(isinstance(value, dict))
    return value


def _db_read_json(path, parent_mode=0o700, optional=False):
    """Traverse trusted root-owned directories by fd; never follow symlinks."""
    value = Path(path)
    _db_require(value.is_absolute() and '..' not in value.parts
                and str(value) == path and len(value.parts) > 2)
    fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        root_stat = os.fstat(fd)
        _db_require(root_stat.st_uid == 0 and not root_stat.st_mode & 0o022)
        for index, component in enumerate(value.parts[1:-1]):
            child = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                            dir_fd=fd)
            os.close(fd)
            fd = child
            item = os.fstat(fd)
            _db_require(item.st_uid == 0 and not item.st_mode & 0o022)
            if index == len(value.parts[1:-1]) - 1:
                _db_require(_db_stat.S_IMODE(item.st_mode) == parent_mode)
        try:
            file_fd = os.open(value.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                              dir_fd=fd)
        except FileNotFoundError:
            if optional:
                return None
            raise
        try:
            item = os.fstat(file_fd)
            _db_require(_db_stat.S_ISREG(item.st_mode) and item.st_uid == 0
                        and item.st_nlink == 1
                        and _db_stat.S_IMODE(item.st_mode) == 0o600
                        and 0 < item.st_size <= _DB_LIMIT)
            chunks, size = [], 0
            while True:
                chunk = os.read(file_fd, min(8192, _DB_LIMIT + 1 - size))
                if not chunk:
                    break
                chunks.append(chunk)
                size += len(chunk)
                _db_require(size <= _DB_LIMIT)
            return _db_json(b''.join(chunks))
        finally:
            os.close(file_fd)
    finally:
        os.close(fd)


def _db_command_json(args):
    # Fixed local read-only CLI inputs only; bounded pipe reader and deadline.
    import select as _select
    child = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    try:
        fd = child.stdout.fileno()
        os.set_blocking(fd, False)
        deadline, chunks, size = time.monotonic() + 8, [], 0
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError('backup metadata CLI timeout')
            ready, _, _ = _select.select([fd], [], [], remaining)
            if not ready:
                raise TimeoutError('backup metadata CLI timeout')
            chunk = os.read(fd, min(8192, _DB_LIMIT + 1 - size))
            if not chunk:
                break
            chunks.append(chunk)
            size += len(chunk)
            _db_require(size <= _DB_LIMIT)
        _db_require(child.wait(timeout=max(0.01, deadline - time.monotonic())) == 0)
        return _db_json(b''.join(chunks))
    finally:
        child.stdout.close()
        if child.poll() is None:
            child.kill()
        child.wait()


def _db_timestamp(value, now):
    _db_require(isinstance(value, str) and len(value) <= 40
                and _db_re.fullmatch(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d{1,6})?(?:Z|\+00:00)', value))
    moment = datetime.datetime.fromisoformat(value.replace('Z', '+00:00'))
    stamp = moment.timestamp()
    _db_require(0 < stamp <= now + 60)
    return stamp


def _db_ledger(value, now):
    _db_require(isinstance(value, dict)
                and value.get('allowed_vmids') == list(_DB_ALLOWED)
                and isinstance(value.get('run_id'), str)
                and _db_re.fullmatch('[0-9a-f]{32}', value['run_id'])
                and value.get('status') in ('running', 'verified', 'failed'))
    start = _db_timestamp(value.get('started_at'), now)
    finish = None
    if value['status'] != 'running':
        finish = _db_timestamp(value.get('finished_at'), now)
        _db_require(finish >= start)
    else:
        _db_require('finished_at' not in value)
    rows = value.get('results')
    _db_require(isinstance(rows, dict) and set(rows).issubset(map(str, _DB_ALLOWED)))
    verified = 0
    for row in rows.values():
        _db_require(isinstance(row, dict) and row.get('status') in
                    ('running', 'verified', 'backup-failed', 'verification-failed'))
        if row['status'] == 'verified':
            checked = _db_timestamp(row.get('checked_at'), now)
            _db_require(row.get('zstd_verified') is True
                        and row.get('native_archive_verified') is True
                        and row.get('mode') == '0600'
                        and type(row.get('bytes')) is int and row['bytes'] > 0
                        and checked >= start and (finish is None or checked <= finish))
            verified += 1
    if value['status'] == 'verified':
        _db_require(len(rows) == len(_DB_ALLOWED) and verified == len(_DB_ALLOWED)
                    and not value.get('log_permission_error'))
    return {'status': value['status'], 'start': start, 'finish': finish,
            'verified': verified, 'run_id': value['run_id']}


def _db_collect(read_json=_db_read_json, command_json=_db_command_json, now=None,
                free_bytes=None):
    now = time.time() if now is None else now
    policy = read_json('/etc/dell-local-backup/policy.json')
    _db_require(policy.get('state_dir') == _DB_STATE
                and policy.get('job_id') == 'dell-local-nightly'
                and policy.get('allowed_vmids') == list(_DB_ALLOWED)
                and policy.get('excluded_vmids') == [220]
                and policy.get('mountpoint') == _DB_STORE
                and policy.get('filesystem_uuid') == _DB_UUID
                and policy.get('storage_id') == 'dell-local-backup'
                and policy.get('mode') == 'snapshot')
    current = _db_ledger(read_json(_DB_STATE + '/current.json'), now)
    success_value = read_json(_DB_STATE + '/last-success.json', optional=True)
    success = _db_ledger(success_value, now) if success_value is not None else None
    _db_require(success is None or success['status'] == 'verified')
    if success:
        _db_require(success['start'] <= current['start'])
    if current['status'] == 'verified':
        _db_require(success and current == success)
    # A newer hook guard failure may leave current.json from an older verified run.
    failure = read_json(_DB_STATE + '/last-failure.json', optional=True)
    failed_at = 0
    if failure is not None:
        failed_at = _db_timestamp(failure.get('failed_at'), now)
        _db_require(('error_type' in failure) or isinstance(failure.get('statuses'), dict))
    job = command_json(['pvesh', 'get', '/cluster/backup/dell-local-nightly',
                        '--output-format', 'json'])
    _db_require(job.get('id', 'dell-local-nightly') == 'dell-local-nightly'
                and type(job.get('enabled')) in (int, bool) and job['enabled'] in (0, 1)
                and job.get('mode') == 'snapshot'
                and job.get('storage') == 'dell-local-backup'
                and job.get('script') == '/usr/local/libexec/dell-local-backup/hook.py'
                and job.get('tmpdir') == '/var/tmp/dell-local-backup'
                and job.get('notification-mode') == 'legacy-sendmail' and not job.get('mailto'))
    raw_vmids = job.get('vmid')
    _db_require(isinstance(raw_vmids, str))
    ids = _db_re.split(r'[,\s]+', raw_vmids.strip())
    _db_require(len(ids) == len(_DB_ALLOWED) and all(v.isdigit() for v in ids)
                and set(map(int, ids)) == set(_DB_ALLOWED))
    mount = command_json(['findmnt', '-J', '-T', _DB_STORE,
                          '-o', 'TARGET,FSTYPE,UUID'])
    mounts = mount.get('filesystems')
    _db_require(isinstance(mounts, list) and len(mounts) == 1
                and mounts[0].get('target') == _DB_STORE
                and mounts[0].get('uuid') == _DB_UUID
                and mounts[0].get('fstype') == 'ext4')
    if free_bytes is None:
        vfs = os.statvfs(_DB_STORE)
        free = vfs.f_bavail * vfs.f_frsize
    else:
        free = free_bytes()
    _db_require(type(free) is int and free >= 0)
    newest_complete = success['finish'] if success else 0
    last_success = int(bool(success))
    if current['status'] == 'failed' and current['finish'] >= newest_complete:
        newest_complete, last_success = current['finish'], 0
    if failed_at >= newest_complete and failed_at > 0:
        last_success = 0
    state = {'verified': 0, 'running': 1, 'failed': 2}[current['status']]
    reference = current['finish'] if current['finish'] is not None else current['start']
    if failed_at >= reference and failed_at > 0:
        state = 2
    return {'last_success_timestamp_seconds': success['finish'] if success else 0,
            'current_run_state': state, 'running': int(state == 1),
            'last_run_success': last_success, 'enabled': int(job['enabled']),
            'verified_guest_count': current['verified'], 'free_bytes': free,
            'current_run_started_timestamp_seconds': current['start'],
            'hook_state_valid': 1, 'state_valid': 1, 'metric_valid': 1}


def _db_emit(emit, collect=_db_collect, report=None):
    defaults = {'last_success_timestamp_seconds': 0, 'current_run_state': 3,
                'running': 0, 'last_run_success': 0, 'enabled': 0,
                'verified_guest_count': 0, 'free_bytes': 0,
                'current_run_started_timestamp_seconds': 0,
                'hook_state_valid': 0, 'state_valid': 0, 'metric_valid': 0}
    try:
        values = collect()
    except Exception as error:
        values = defaults
        # Exception class only: never path, stdout/stderr, ledger, archive or SHA.
        metadata = {'component': 'local-backup-metrics', 'status': 'invalid-metadata',
                    'error_type': type(error).__name__}
        try:
            if report is None:
                print(json.dumps(metadata), file=_db_sys.stderr)
            else:
                report(metadata)
        except Exception:
            pass
    for name, value in values.items():
        emit('dell_pve_local_backup_' + name, value)


_db_emit(metric)
# END dell-local-backup metadata metrics

text='\n'.join(lines)+'\n'
writer='''import os,sys,socket,uuid
from pathlib import Path
assert socket.gethostname()=='ops-service' and not Path('/etc/pve').exists()
p=Path('/var/lib/prometheus/node-exporter-textfile');assert p.resolve()==p
fd=os.open(p,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
name='.dell-pve-'+uuid.uuid4().hex+'.tmp'
try:
 out=os.open(name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o644,dir_fd=fd)
 with os.fdopen(out,'wb') as f:f.write(sys.stdin.buffer.read());f.flush();os.fsync(f.fileno())
 os.replace(name,'dell-pve.prom',src_dir_fd=fd,dst_dir_fd=fd)
finally:os.close(fd)
'''
p=subprocess.run(['qm','guest','exec','270','--pass-stdin','1','--','python3','-c',writer],input=text,capture_output=True,text=True,timeout=30)
if p.returncode:raise RuntimeError('QGA metric delivery failed')
value=json.loads(p.stdout)
if value.get('exitcode')!=0:raise RuntimeError('Guest metric file write failed')
print(json.dumps({'at':datetime.datetime.now().isoformat(),'metric_lines':len(lines),'delivery':'existing-QGA-to-Ops-textfile','host_listener_created':False,'credentials_read':False}))
