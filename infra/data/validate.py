#!/usr/bin/env python3
"""Validate prepared bundles without starting any container or touching source data."""
import ast, hashlib, json, os, re, subprocess, sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
PRIVATE=HERE.parents[1]/'private'/'data'
LIMITS={'prod-db':16,'prod-infra':8,'test-data':4}

def main():
    for p in [HERE/'prepare.py',HERE/'validate.py',HERE/'test_safety.py',*HERE.joinpath('scripts').glob('*.py'),HERE/'secure-transfer.py']:
        ast.parse(p.read_text())
    for p in (HERE/'scripts').glob('*.sh'):
        subprocess.run(['bash','-n',str(p)],check=True,capture_output=True)
    lock=json.loads((HERE/'images.lock.json').read_text())
    for name,meta in lock['vendor'].items():
        assert hashlib.sha256((HERE/'vendor'/name).read_bytes()).hexdigest()==meta['sha256']
    safety=subprocess.run([sys.executable,str(HERE/'test_safety.py')],capture_output=True,text=True,timeout=30)
    if safety.returncode:
        raise RuntimeError('offline safety regression failed; no target action attempted')
    match=re.search(r'Ran (\d+) tests',safety.stderr)
    report={'scope':'static-and-compose-parse; no containers started','roles':[],'checks':[],'offline_safety':{'result':'passed','tests':int(match.group(1)) if match else None,'scope':'missing/extra/duplicate services; missing/read-only/wrong-UUID/nested mounts; traversal/symlink escape; systemd dependencies'}}
    for role,vm in LIMITS.items():
        bundle=PRIVATE/'bundles'/role
        command=['docker','compose','--env-file',str(bundle/'.env'),'-f',str(bundle/'compose.yaml'),'config','--format','json']
        p=subprocess.run(command,capture_output=True,text=True,timeout=30)
        if p.returncode:
            raise RuntimeError(role+' Compose parse failed; raw output suppressed')
        model=json.loads(p.stdout)
        total=0
        for name,s in model['services'].items():
            assert s['platform']=='linux/amd64'
            assert '@sha256:' in s['image']
            assert s.get('healthcheck')
            assert s['restart']=='no'
            total+=int(s['mem_limit'])
            for binding in s.get('ports',[]):
                assert binding.get('host_ip') not in ('0.0.0.0','::','127.0.0.1',None)
            for k in s.get('environment',{}):
                assert not ('PASSWORD' in k and not k.endswith('_FILE'))
            for volume in s.get('volumes',[]):
                assert volume['type']=='bind'
                assert volume.get('bind',{}).get('create_host_path') is False
        gib=total/(1024**3)
        assert gib<vm and vm-gib>=1, (role,'OS/engine headroom missing')
        for p in (bundle/'secrets').iterdir():
            assert p.stat().st_mode&0o777==0o600
        assert bundle.joinpath('.env').stat().st_mode&0o777==0o600
        report['roles'].append({'role':role,'services':sorted(model['services']),'container_limits_gib':gib,'guest_budget_gib':vm,'guest_os_runtime_headroom_gib':vm-gib,'compose_parse':'passed','mount_identity':json.loads((bundle/'bundle.json').read_text())['mount_identity_status']})
    prod=PRIVATE/'store'/'prod';test=PRIVATE/'store'/'test'
    for name in ['mysql-root-password','nacos-db-password','redis-password','nacos-admin-password','nacos-client-password','rabbit-app-password']:
        assert (prod/name).read_bytes()!=(test/name).read_bytes()
    assert (PRIVATE/'bundles'/'prod-db'/'secrets'/'nacos-db-password').read_bytes()==(PRIVATE/'bundles'/'prod-infra'/'secrets'/'nacos-db-password').read_bytes()
    report['checks']=['Python AST','shell syntax','official vendor checksums','Compose parse','AMD64 digest references','healthcheck/systemd-owned-restart/resource declarations','bind create_host_path=false','explicit guest bind IPs','no plain password environment entries','0600 secret files','prod/test credential separation','prod DB/Nacos credential match']
    runtime=HERE.parents[1]/'evidence/implementation/data-deployment-acceptance.json'
    if runtime.exists():
        actual=json.loads(runtime.read_text())
        report['runtime_evidence']={'status':actual['status'],'as_of':actual.get('finished_at') or actual['started_at'],'accepted_vmids':[x['vmid'] for x in actual['roles'] if x.get('status')=='deployed-authenticated-restart-persistence-verified'],'delegated_vmids':actual.get('delegated_vmids',[]),'evidence':'evidence/implementation/data-deployment-acceptance.json','current_guest_state_requeried':False}
    (HERE/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))

if __name__=='__main__':
    try:main()
    except Exception as error:
        print('VALIDATION FAILED: '+str(error),file=sys.stderr);sys.exit(1)
