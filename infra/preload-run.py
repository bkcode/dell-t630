#!/usr/bin/env python3
"""Assigned guest software preload only; no host mutations or app starts."""
from pathlib import Path
import datetime
import hashlib
import importlib.util
import json
import shlex
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('dell_control', ROOT / 'scripts/control.py')
control = importlib.util.module_from_spec(spec)
spec.loader.exec_module(control)
ASSIGNED = [(200, 'data-prod-db', ['data']), (201, 'data-prod-infra', ['data']),
            (221, 'artifact-service', ['nexus', 'extras']),
            (250, 'penpot-service', ['penpot', 'custom']),
            (270, 'ops-service', ['extras'])]

def clock():
    return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat()

def read(relative):
    return json.loads((ROOT / relative).read_text())

def archive_specs():
    public = read('evidence/implementation/amd64-image-cache.json')
    extra = read('evidence/implementation/amd64-extras-cache.json')
    custom = read('private/images/custom-penpot-amd64-images.json')
    archives = {}
    for record in read('evidence/implementation/pve-image-archives.json')['records']:
        group = record['group']
        entries = [x for x in public['images'] if x['group'] == group]
        archives[group] = {'archive': Path(record['path']).name, 'sha256': record['sha256'],
                           'expected_ids': [x['inspect']['id'] for x in entries],
                           'references': [x['reference'] for x in entries]}
    records = read('evidence/implementation/pve-extra-archives.json')['records']
    for group, filename, entries in [('extras', 'target-amd64-extras-images.tar', extra['images'])]:
        record = next(x for x in records if x['file'] == filename)
        archives[group] = {'archive': filename, 'sha256': record['sha256'],
                           'expected_ids': [x['inspect']['id'] for x in entries],
                           'references': [x['reference'] for x in entries]}
    record = next(x for x in records if x['file'] == 'custom-penpot-amd64-images.tar')
    assert record['sha256'] == custom['sha256']
    archives['custom'] = {'archive': record['file'], 'sha256': record['sha256'],
                          'expected_ids': [x['id'] for x in custom['images'].values()],
                          'references': [],
                          'tags': {x['tag']: x['id'] for x in custom['images'].values()}}
    return archives

PREFLIGHT = r'''
import json,subprocess,socket,os,sys
from pathlib import Path
role=sys.argv[1]
assert os.geteuid()==0 and not Path('/etc/pve').exists() and socket.gethostname()==role
info=json.loads(subprocess.check_output(['docker','--host','unix:///var/run/docker.sock','info','--format','{{json .}}'],text=True))
assert info['Name']==role and info['Containers']==0
assert info['OSType']=='linux' and info['Architecture'] in ['x86_64','amd64']
root=Path(info['DockerRootDir'])
v=os.statvfs(root)
print(json.dumps({'role':role,'driver':info['Driver'],'docker_root':str(root),'containers':info['Containers'],'images':info['Images'],'live_restore':info['LiveRestoreEnabled'],'filesystem_free_bytes':v.f_bavail*v.f_frsize,'filesystem_total_bytes':v.f_blocks*v.f_frsize,'artifact_device_exists':Path('/dev/disk/by-label/DELL_ARTIFACTS').exists()}))
'''

def run_guest(vmid, info, code, args, timeout=120):
    command = shlex.join(['sudo', '-n', 'python3', '-'] + args)
    result = control.guest(vmid, command, data=code.encode(), timeout=timeout, info=info)
    if result['exit_code']:
        raise RuntimeError('guest command failed: ' + json.dumps({'exit_code': result['exit_code'], 'stderr': result['stderr'][-1200:], 'stdout': result['stdout'][-600:]}))
    lines = [line for line in result['stdout'].splitlines() if line.strip()]
    return json.loads(lines[-1])

def main():
    assert len(sys.argv) == 1, 'This runner has a fixed assigned guest set'
    staging = read('evidence/implementation/guest-staging-storage.json')
    specs = archive_specs()
    profile = (ROOT / 'infra/docker-runtime-profile.py').read_text()
    preload = (ROOT / 'infra/preload-images.py').read_text()
    for vmid, role, groups in ASSIGNED:
        record = next(x for x in staging['roles'] if x['target']['vmid'] == vmid)
        assert record['name'] == role and record['status'] == 'prepared'
        info = record['target']
        assert info['host_key_alias'] == 'dell-vm' + str(vmid)
        target = ROOT / 'evidence/implementation' / ('preload-' + role + '.json')
        if target.exists():
            raise RuntimeError('Prior evidence exists; manager review required before any repeat: ' + str(target))
        evidence = {'schema_version': 1, 'role': role, 'target': info, 'started_at': clock(),
                    'scope': 'assigned-new-guest-software-preload-only', 'status': 'in-progress',
                    'runtime_profile_script_sha256': hashlib.sha256(profile.encode()).hexdigest(),
                    'preload_script_sha256': hashlib.sha256(preload.encode()).hexdigest(),
                    'archives': [], 'applications_started': False, 'host_network_applied': False}
        def persist():
            target.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + '\n')
            target.chmod(0o600)
        persist()
        print('ROLE_START ' + role + ' ' + clock(), flush=True)
        try:
            evidence['before'] = run_guest(vmid, info, PREFLIGHT, [role])
            assert evidence['before']['artifact_device_exists'], 'Artifacts ISO device missing'
            assert evidence['before']['filesystem_free_bytes'] > 12 * 1024**3, 'Insufficient image-cache filesystem reserve'
            evidence['runtime_profile'] = run_guest(vmid, info, profile, ['--role', role], 180)
            assert evidence['runtime_profile']['driver'] == 'overlay2'
            assert evidence['runtime_profile']['live_restore'] is False
            assert evidence['runtime_profile']['containers'] == 0
            persist()
            for group in groups:
                archive = specs[group]
                entry = {'group': group, 'archive': archive['archive'], 'started_at': clock(), 'status': 'in-progress'}
                evidence['archives'].append(entry); persist()
                print('LOAD_START ' + role + ' ' + group + ' ' + clock(), flush=True)
                args = ['--role', role, '--archive', archive['archive'], '--sha256', archive['sha256']]
                for image_id in archive['expected_ids']:
                    args += ['--expected-id', image_id]
                for reference in archive['references']:
                    args += ['--reference', reference]
                result = run_guest(vmid, info, preload, args, 1800)
                assert result['applications_started'] is False
                assert sorted(result['verified_image_ids']) == sorted(archive['expected_ids'])
                entry.update({'status': 'verified-preloaded', 'completed_at': clock(), 'result': result})
                persist(); print('LOAD_VERIFIED ' + role + ' ' + group + ' ' + clock(), flush=True)
            evidence['after'] = run_guest(vmid, info, PREFLIGHT, [role])
            assert evidence['after']['containers'] == 0 and evidence['after']['driver'] == 'overlay2'
            assert evidence['after']['live_restore'] is False
            assert evidence['after']['filesystem_free_bytes'] / evidence['after']['filesystem_total_bytes'] >= .20, 'Filesystem below 20 percent reserve after preload'
            evidence['status'] = 'software-preloaded-no-containers'
            evidence['limitations'] = ['No docker pull or compose invoked; registry manifest aliases may remain unavailable pending manager-approved metadata pull.', 'No application target_guard, application IP, host network, source machine or unassigned guest changed.', 'Old containerd cache retained by runtime profile; no data removed.']
            evidence['completed_at'] = clock(); persist()
            print('ROLE_COMPLETE ' + role + ' ' + clock(), flush=True)
        except Exception as exc:
            evidence['status'] = 'failed-stopped-no-retry'
            evidence['error'] = type(exc).__name__ + ': ' + str(exc)
            evidence['failed_at'] = clock(); persist()
            print('FAILED_STOP ' + role + ' ' + evidence['error'], flush=True)
            raise

if __name__ == '__main__':
    main()
