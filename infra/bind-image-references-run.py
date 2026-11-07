#!/usr/bin/env python3
"""Bind already-preloaded public digest references on explicitly assigned guests."""
from pathlib import Path
import datetime
import importlib.util
import json
import re
import shlex
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('dell_control', ROOT / 'scripts/control.py')
control = importlib.util.module_from_spec(spec)
spec.loader.exec_module(control)
ASSIGNED = [(200, 'data-prod-db'), (201, 'data-prod-infra'), (221, 'artifact-service'),
            (250, 'penpot-service'), (270, 'ops-service')]
ALLOWED = {'mysql', 'redis', 'rabbitmq', 'nacos/nacos-server', 'sonatype/nexus3', 'nginx',
           'penpotapp/frontend', 'penpotapp/backend', 'penpotapp/exporter',
           'penpotapp/admin-console', 'penpotapp/mcp', 'postgres', 'valkey/valkey',
           'adguard/dnsproxy', 'axllent/mailpit', 'prom/prometheus', 'grafana/grafana',
           'prom/alertmanager', 'prom/blackbox-exporter', 'jellyfin/jellyfin'}

def clock():
    return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat()

def read(relative):
    return json.loads((ROOT / relative).read_text())

REMOTE = r'''
from pathlib import Path
import argparse,datetime,json,os,re,socket,subprocess,time
p=argparse.ArgumentParser();p.add_argument('--role',required=True);p.add_argument('--reference',required=True);p.add_argument('--expected-id',required=True);a=p.parse_args()
r={'role':a.role,'reference':a.reference,'expected_config_id':a.expected_id,'started_at':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),'status':'in-progress','pull_performed':False,'raw_pull_output_saved':False,'containers_started':False}
allowed={'mysql','redis','rabbitmq','nacos/nacos-server','sonatype/nexus3','nginx','penpotapp/frontend','penpotapp/backend','penpotapp/exporter','penpotapp/admin-console','penpotapp/mcp','postgres','valkey/valkey','adguard/dnsproxy','axllent/mailpit','prom/prometheus','grafana/grafana','prom/alertmanager','prom/blackbox-exporter','jellyfin/jellyfin'}
begin=time.monotonic();docker=['docker','--host','unix:///var/run/docker.sock']
def info():return json.loads(subprocess.check_output(docker+['info','--format','{{json .}}'],text=True,timeout=20))
def inspect(ref):
 f='{"id":{{json .Id}},"architecture":{{json .Architecture}},"os":{{json .Os}}}'
 q=subprocess.run(docker+['image','inspect','--format',f,ref],text=True,capture_output=True,timeout=20)
 if q.returncode==0:return q.returncode,json.loads(q.stdout),None
 return q.returncode,None,('missing-local-reference' if 'No such image' in q.stderr or 'No such object' in q.stderr else 'local-inspect-failed')
try:
 assert os.geteuid()==0 and socket.gethostname()==a.role and not Path('/etc/pve').exists()
 assert re.fullmatch(r'[a-z0-9./_-]+@sha256:[0-9a-f]{64}',a.reference) and a.reference.split('@')[0] in allowed
 assert re.fullmatch(r'sha256:[0-9a-f]{64}',a.expected_id)
 before=info();assert before['Name']==a.role and before['Driver']=='overlay2' and before['Containers']==0
 assert not before.get('RegistryConfig',{}).get('Mirrors'), 'Registry mirror configured; stop before public network access'
 r['containers_before']=before['Containers'];r['registry_mirrors_empty']=True
 cache_code,cache,_=inspect(a.expected_id);assert cache_code==0 and cache['id']==a.expected_id and cache['architecture']=='amd64' and cache['os']=='linux'
 code,current,kind=inspect(a.reference);r['initial_reference_inspect_exit_code']=code
 if code==0:
  assert current['id']==a.expected_id and current['architecture']=='amd64' and current['os']=='linux'
  r['status']='already-associated-skip-pull';r['pull_exit_code']=None;r['actual_config_id']=current['id'];r['architecture']=current['architecture']
 else:
  assert kind=='missing-local-reference', 'Unexpected local inspect failure'
  config=Path('/run/dell-public-registry-empty-config')
  if config.exists():assert config.is_dir() and not config.is_symlink() and not any(config.iterdir()), 'Public-only CLI config is not empty'
  else:config.mkdir(mode=0o700)
  r['pull_performed']=True;pull_begin=time.monotonic()
  try:
   q=subprocess.run(['docker','--config',str(config),'--host','unix:///var/run/docker.sock','pull','--platform','linux/amd64',a.reference],text=True,capture_output=True,timeout=180)
   r['pull_elapsed_seconds']=round(time.monotonic()-pull_begin,3);r['pull_exit_code']=q.returncode
   r['new_layer_download_observed']=bool(re.search(r'Pulling fs layer|Downloading',q.stdout))
   if q.returncode:
    text=q.stdout+q.stderr
    r['failure_category']='rate-limit' if '429' in text or 'toomanyrequests' in text.lower() else ('public-registry-auth-error' if 'unauthorized' in text.lower() else ('network-timeout' if re.search(r'timeout|timed out',text,re.I) else 'public-registry-or-cli-error'))
    raise RuntimeError('Public digest association pull failed; raw output deliberately omitted')
  except subprocess.TimeoutExpired:
   r['pull_exit_code']=None;r['pull_elapsed_seconds']=round(time.monotonic()-pull_begin,3);r['failure_category']='180-second-timeout';raise
  final_code,final,_=inspect(a.reference);r['final_reference_inspect_exit_code']=final_code
  assert final_code==0 and final['id']==a.expected_id and final['architecture']=='amd64' and final['os']=='linux'
  r['actual_config_id']=final['id'];r['architecture']=final['architecture'];r['status']='associated-verified'
 after=info();r['containers_after']=after['Containers'];r['driver_after']=after['Driver'];assert after['Containers']==0 and after['Driver']=='overlay2'
except Exception as exc:
 r['status']='failed-stopped-no-retry';r['error_type']=type(exc).__name__
 if 'failure_category' not in r:r['failure_category']='guard-or-verification-failed'
 try:r['containers_after']=info()['Containers']
 except Exception:r['containers_after']=None
r['elapsed_seconds']=round(time.monotonic()-begin,3);r['completed_at']=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat()
print(json.dumps(r))
'''

def main():
    assert len(sys.argv) == 1
    output = ROOT / 'evidence/implementation/image-reference-binding.json'
    if output.exists():
        raise RuntimeError('Existing evidence retained; manager review required before another run')
    cache = read('evidence/implementation/amd64-image-cache.json')['images'] + read('evidence/implementation/amd64-extras-cache.json')['images']
    expected = {x['reference']: x['inspect']['id'] for x in cache}
    staging = read('evidence/implementation/guest-staging-storage.json')['roles']
    report = {'schema_version': 1, 'started_at': clock(), 'scope': 'assigned-new-guests-public-digest-name-association-only', 'status': 'in-progress', 'roles': [], 'source_mac_docker_touched': False, 'pve_host_mutated': False, 'application_started': False, 'private_registry_access': False}
    def save():
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n');output.chmod(0o600)
    save()
    try:
        for vmid, name in ASSIGNED:
            assigned = next(x for x in staging if x['target']['vmid'] == vmid)
            assert assigned['name'] == name
            pre = read('evidence/implementation/preload-' + name + '.json')
            assert pre['status'] == 'software-preloaded-no-containers' and pre['target']['vmid'] == vmid
            refs = [ref for archive in pre['archives'] for ref in archive['result'].get('registry_reference_available', {})]
            assert len(refs) == len(set(refs))
            role = {'vmid': vmid, 'name': name, 'target': assigned['target'], 'started_at': clock(), 'status': 'in-progress', 'references': []};report['roles'].append(role);save()
            for ref in refs:
                assert ref in expected and ref.split('@')[0] in ALLOWED
                print('BIND_START ' + name + ' ' + ref.split('@')[0] + ' ' + clock(), flush=True)
                args = ['sudo', '-n', 'python3', '-', '--role', name, '--reference', ref, '--expected-id', expected[ref]]
                result = control.guest(vmid, shlex.join(args), data=REMOTE.encode(), timeout=230, info=assigned['target'])
                assert result['exit_code'] == 0, 'Remote association script did not return its structured result'
                value = json.loads([x for x in result['stdout'].splitlines() if x.strip()][-1]);role['references'].append(value);save()
                assert value['status'] in ['associated-verified', 'already-associated-skip-pull'], 'Public association failed; queue stopped'
                assert value['actual_config_id'] == expected[ref] and value['architecture'] == 'amd64' and value['containers_after'] == 0
                print('BIND_RESULT ' + name + ' ' + ref.split('@')[0] + ' ' + value['status'] + ' ' + str(value.get('pull_elapsed_seconds')) + 's', flush=True)
            role['status'] = 'public-references-associated-no-containers';role['completed_at'] = clock();save()
        report['status'] = 'public-references-associated-no-containers'
    except Exception as exc:
        report['status'] = 'failed-stopped-no-retry';report['error_type'] = type(exc).__name__;save();raise
    finally:
        report['completed_at'] = clock();save()
    print('FINAL ' + json.dumps({'status': report['status'], 'roles': len(report['roles']), 'references': sum(len(x['references']) for x in report['roles']), 'pulls': sum(v['pull_performed'] for x in report['roles'] for v in x['references'])}), flush=True)

if __name__ == '__main__':
    main()
