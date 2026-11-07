#!/usr/bin/env python3
"""Controlled target-only copy roundtrip and asynchronous import acceptance."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.parse
import urllib.request
import uuid
import zipfile

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))
from target_guard import DOCKER, verify_target
spec = importlib.util.spec_from_file_location('target_application', BASE / 'application/target-api.py')
api = importlib.util.module_from_spec(spec);spec.loader.exec_module(api)
PRIVATE = Path('/etc/penpot')
DATA = Path('/srv/penpot/acceptance')


def save(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n');path.chmod(0o600)


def project(owner, team, name):
    rows = owner.call('get-projects', {'team-id': team})
    matches = [p for p in rows if p['name'] == name and not api.field(p, 'deletedAt', 'deleted-at')]
    if len(matches) > 1:raise RuntimeError('Ambiguous acceptance project')
    return matches[0] if matches else owner.call('create-project', {'team-id': team, 'name': name})


def export_file(owner, file_id, destination):
    raw = owner.request('export-binfile', json.dumps({'file-id':file_id,'include-libraries':True,'embed-assets':False}).encode(), stream=True)
    uri = None
    for event in raw.decode().replace('\r\n','\n').split('\n\n'):
        lines=event.splitlines();kind=next((x.split(':',1)[1].strip() for x in lines if x.startswith('event:')),'')
        if kind=='error':raise RuntimeError('Target copy export failed')
        if kind=='end':
            value=json.loads('\n'.join(x.split(':',1)[1].lstrip() for x in lines if x.startswith('data:')))
            uri=value.get('~#uri') if isinstance(value,dict) else value
    if not uri:raise RuntimeError('Target copy export completion unconfirmed')
    parsed=urllib.parse.urlsplit(uri)
    if not parsed.path.startswith('/assets/by-id/'):raise RuntimeError('Unexpected export path')
    with owner.opener.open(api.ORIGIN+parsed.path,timeout=120) as response:body=response.read()
    destination.write_bytes(body);destination.chmod(0o600)
    return hashlib.sha256(body).hexdigest()


def roundtrip():
    verify_target(require_docker_data=True);DATA.mkdir(parents=True,exist_ok=True,mode=0o700)
    record_path=PRIVATE/'copy-roundtrip.json'
    if record_path.exists():
        print(json.dumps(json.loads(record_path.read_text())));return
    owner=api.API('owner');ledger=json.loads((PRIVATE/'application-id-map.json').read_text())
    original=ledger['files']['e519ae78-b5c8-81fe-8008-e32a81af5e27']
    before=owner.call('get-file-stats',{'id':original['target_id']})
    dedicated=project(owner,original['target_team_id'],'Dell copy roundtrip acceptance')
    candidates=[x for x in owner.call('get-project-files',{'project-id':dedicated['id']}) if x['name']=='Dell controlled roundtrip copy']
    if len(candidates)>1:raise RuntimeError('Ambiguous controlled copies; inspect before retry')
    copy=candidates[0] if candidates else owner.call('duplicate-file',{'file-id':original['target_id'],'name':'Dell controlled roundtrip copy'})
    if not candidates:owner.call('move-files',{'ids':[copy['id']],'project-id':dedicated['id']})
    full=owner.call('get-file',{'id':copy['id']});page=full['data']['pages'][0]
    new_name='Dell target acceptance page edit'
    owner.call('update-file',{'id':copy['id'],'session-id':str(uuid.uuid4()),'revn':full['revn'],'vern':full.get('vern',0),
                             'features':full.get('features',[]),'changes':[{'type':'mod-page','id':page,'name':new_name}]})
    archive=DATA/'edited-copy.penpot';sha=export_file(owner,copy['id'],archive)
    with zipfile.ZipFile(archive) as zip:
        manifest=json.loads(zip.read('manifest.json'))
        pages=[n for n in zip.namelist() if n.startswith('files/'+copy['id']+'/pages/') and n.count('/')==3 and n.endswith('.json')]
        if not any(json.loads(zip.read(n)).get('name')==new_name for n in pages):raise RuntimeError('Edited page absent from official export')
    files=owner.call('get-project-files',{'project-id':dedicated['id']});ids={x['id'] for x in files}
    owner.import_file(archive,'Dell edited roundtrip reimport',dedicated['id'])
    added=[x for x in owner.call('get-project-files',{'project-id':dedicated['id']}) if x['id'] not in ids]
    if len(added)!=1:raise RuntimeError('Roundtrip import identity ambiguous')
    reexport=DATA/'reimported-copy.penpot';sha2=export_file(owner,added[0]['id'],reexport)
    with zipfile.ZipFile(reexport) as zip:
        pages=[n for n in zip.namelist() if n.startswith('files/'+added[0]['id']+'/pages/') and n.count('/')==3 and n.endswith('.json')]
        if not any(json.loads(zip.read(n)).get('name')==new_name for n in pages):raise RuntimeError('Edited page absent after reimport')
    after=owner.call('get-file-stats',{'id':original['target_id']})
    if before!=after:raise RuntimeError('Original imported design unexpectedly changed')
    record={'controlled_copy_only':True,'original_file_id':original['target_id'],'copy_file_id':copy['id'],'reimport_file_id':added[0]['id'],
            'copy_project_id':dedicated['id'],'edited_page_name_preserved':True,'export_sha256':sha,'reexport_sha256':sha2,
            'original_imported_design_unchanged':True,'source_processes_or_designs_touched':False}
    save(record_path,record);print(json.dumps(record),flush=True)


def import_rpc(key, name, arguments):
    body={'jsonrpc':'2.0','id':1,'method':'tools/call','params':{'name':name,'arguments':arguments}}
    req=urllib.request.Request('http://127.0.0.1:9002/mcp',data=json.dumps(body).encode(),method='POST',headers={
        'Content-Type':'application/json','Accept':'application/json,text/event-stream','Authorization':'Bearer '+key})
    with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(req,timeout=30) as response:result=json.load(response)
    value=json.loads(result['result']['content'][0]['text'])
    if result['result'].get('isError'):raise RuntimeError('Import tool rejected: '+value.get('error','unknown'))
    return value


def async_import():
    verify_target(require_docker_data=True)
    record_path=PRIVATE/'async-import-acceptance.json'
    if record_path.exists():print(record_path.read_text());return
    owner=api.API('owner');profile=owner.call('get-profile',{});team=api.field(profile,'defaultTeamId','default-team-id')
    dedicated=project(owner,team,'Dell async import acceptance')
    fixture=json.loads((BASE/'application/public-fixture.json').read_text())
    key=json.loads((PRIVATE/'worker-credentials.json').read_text())['mcpKey']
    request={'url':fixture['url'],'requestId':str(uuid.uuid4()),'projectId':dedicated['id'],'name':'Dell pinned public async fixture'}
    before={x['id'] for x in owner.call('get-project-files',{'project-id':dedicated['id']})}
    first=import_rpc(key,'import_penpot_file',request);retry=import_rpc(key,'import_penpot_file',request)
    if first['jobId']!=retry['jobId']:raise RuntimeError('Retry created a different import job')
    for _ in range(180):
        state=import_rpc(key,'get_import_status',{'jobId':first['jobId']})
        if state['status']=='completed':break
        if state['status'] in ('failed','interrupted'):raise RuntimeError('Real async import did not complete: '+state.get('error','unknown'))
        time.sleep(1)
    else:raise RuntimeError('Async import deadline exceeded')
    added=[x for x in owner.call('get-project-files',{'project-id':dedicated['id']}) if x['id'] not in before]
    if len(added)!=1:raise RuntimeError('Async retry duplicated or lost files')
    compose=DOCKER+['compose','--env-file',str(PRIVATE/'.env'),'-f',str(BASE/'compose.fresh.yaml')]
    for args in [['stop','penpot-import'],['up','-d','--no-build','--pull','never','--no-deps','penpot-import']]:
        p=subprocess.run(compose+args,capture_output=True,text=True,timeout=60)
        if p.returncode:raise RuntimeError('Controlled idle importer restart failed')
    for _ in range(30):
        try:
            restored=import_rpc(key,'get_import_status',{'jobId':first['jobId']});break
        except Exception:time.sleep(1)
    else:raise RuntimeError('Import status did not recover')
    retried=import_rpc(key,'import_penpot_file',request)
    final=owner.call('get-project-files',{'project-id':dedicated['id']})
    if restored['status']!='completed' or restored.get('files')!=state.get('files') or retried['jobId']!=first['jobId'] or len({x['id'] for x in final}-before)!=1:
        raise RuntimeError('Completed async job did not persist without duplication')
    result={'fixture':fixture,'job_id':first['jobId'],'project_id':dedicated['id'],'new_file_id':added[0]['id'],
            'completed':True,'same_request_retry_same_job':True,'one_file_only':True,'completed_status_and_ids_survive_service_restart':True,
            'inflight_interruption_test':'not-run','real_source_designs_modified':False,'key_values_emitted':False}
    save(record_path,result);print(json.dumps(result),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['roundtrip','async-import']);args=p.parse_args()
    try:{'roundtrip':roundtrip,'async-import':async_import}[args.action]()
    except Exception as error:print('TARGET ACCEPTANCE ERROR: '+str(error),file=sys.stderr);sys.exit(1)
