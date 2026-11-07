#!/usr/bin/env python3
"""Owned VM221 rebuild/reboot persistence canary. No source or PVE operations."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import time

BASE=Path(__file__).resolve().parent
sys.path.insert(0,str(BASE))
from target_guard import DOCKER,verify_target
spec=importlib.util.spec_from_file_location('importer',BASE/'application-import.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
CANARY=m.STATE/'rebuild-canary.json'


def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True).encode()).hexdigest()


def ids():
    rows=json.loads(subprocess.run(DOCKER+['inspect','nexus-nexus-1','nexus-gateway-1'],capture_output=True,text=True,check=True).stdout)
    return {x['Name']:{'id':x['Id'],'state':x['State']['Status'],'pids_limit':x['HostConfig'].get('PidsLimit'),'health':x['State'].get('Health',{}).get('Status')} for x in rows}


def configuration(api):
    return {'repo':api.json('GET','/repositories/maven/hosted/imnull-releases'),
            'group':api.json('GET','/repositories/maven/group/finger-public'),
            'roles':{role:api.json('GET','/security/roles/'+role) for role in ('dell-artifact-reader','dell-artifact-publisher')}}


def secrets():
    return {name:hashlib.sha256((m.SECRET/name).read_bytes()).hexdigest() for name in ('admin-password','publisher-password','reader-password')}


def before():
    verify_target(data_path='/srv/nexus/data');api=m.API();m.ensure_repository(api)
    metadata=json.loads((m.STATE/'verification.json').read_text());assert metadata['primary_assets']==234
    marker=json.loads((BASE/'rebuild-publish-canary.json').read_text())
    _,body=api.request('GET','/repository/dell-acceptance/'+marker['jar_path']);assert hashlib.sha256(body).hexdigest()==marker['jar_sha256']
    record={'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'old_containers':ids(),
            'secret_hashes_guest_only':secrets(),'configuration_sha256':digest(configuration(api)),
            'eula_accepted':api.json('GET','/system/eula')['accepted'],'publish_canary':marker,
            'source_manifest_sha256':metadata['source_manifest_sha256'],'primary_verified':234}
    assert record['eula_accepted'] is True and all(x['state']=='running' and x['health']=='healthy' for x in record['old_containers'].values())
    m.save('rebuild-canary.json',record);print(json.dumps({'baseline_recorded':True,'boot_id':record['boot_id'],'primary_verified':234,'secret_values_emitted':False}))


def recreate():
    verify_target(data_path='/srv/nexus/data');canary=json.loads(CANARY.read_text());assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==canary['boot_id']
    subprocess.run(['systemctl','stop','dell-nexus.service'],capture_output=True,text=True,check=True,timeout=180)
    compose=DOCKER+['compose','--env-file','/etc/nexus.env','-f',str(BASE/'compose.yaml'),'-f',str(BASE/'compose.mount-gated.yaml')]
    subprocess.run(compose+['create','--force-recreate','--no-build','--pull','never','nexus','gateway'],capture_output=True,text=True,check=True,timeout=120)
    current=ids();assert all(x['state']=='created' and x['pids_limit']==1024 and x['id']!=canary['old_containers'][name]['id'] for name,x in current.items())
    canary['recreated_containers']=current;m.save('rebuild-canary.json',canary)
    print(json.dumps({'only_nexus_gateway_recreated':True,'no_volume_removed':True,'writers_running':False,'new_container_ids':{k:v['id'] for k,v in current.items()},'pids_limit':1024}))


def after():
    verify_target(data_path='/srv/nexus/data');canary=json.loads(CANARY.read_text());api=m.API()
    boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip();assert boot!=canary['boot_id']
    for _ in range(90):
        current=ids()
        if all(x['state']=='running' and x['health']=='healthy' for x in current.values()):break
        time.sleep(2)
    else:raise RuntimeError('Recreated containers did not finish bounded health warmup')
    assert all(x['id']==canary['recreated_containers'][name]['id'] and x['pids_limit']==1024 for name,x in current.items())
    assert secrets()==canary['secret_hashes_guest_only'];assert digest(configuration(api))==canary['configuration_sha256'];assert api.json('GET','/system/eula')['accepted'] is True
    marker=canary['publish_canary'];_,body=api.request('GET','/repository/dell-acceptance/'+marker['jar_path']);assert hashlib.sha256(body).hexdigest()==marker['jar_sha256']
    rows=subprocess.run(DOCKER+['stats','--no-stream','--format','{{json .}}','nexus-nexus-1','nexus-gateway-1'],capture_output=True,text=True,check=True).stdout
    pids={x['Name']:int(x['PIDs']) for x in map(json.loads,rows.splitlines())};assert all(x<1024 for x in pids.values())
    m.verify();m.permissions()
    result={'container_rebuild_and_guest_reboot':True,'boot_before':canary['boot_id'],'boot_after':boot,
            'container_ids_changed_from_baseline':True,'recreated_container_ids_preserved_after_boot':True,
            'new_identity_files_preserved':True,'eula_still_accepted':True,'repository_group_roles_preserved':True,
            'data_uuid_preserved':True,'primary_sha_verified':234,'component_gav_verified':49,'metadata_verified':35,'checksum_verified':1076,
            'other_repo_synthetic_jar_sha256_preserved':marker['jar_sha256'],'runtime_pids':pids,'pids_limit':1024,
            'old_h2_users_upstream_credentials_used':False,'external_proxy_requests':0,'source_or_pve_restarted':False}
    m.save('rebuild-acceptance.json',result);print(json.dumps(result),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['before','recreate','after']);a=p.parse_args()
    try:{'before':before,'recreate':recreate,'after':after}[a.action]()
    except Exception as e:print('REBUILD ACCEPTANCE ERROR: '+str(e),file=sys.stderr);sys.exit(1)
