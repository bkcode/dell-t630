#!/usr/bin/env python3
"""One manual Nexus UI-native metadata rebuild, scoped only to imported hosted repo."""
import importlib.util
import json
from pathlib import Path
import sys
import time

BASE=Path(__file__).resolve().parent
sys.path.insert(0,str(BASE))
from target_guard import verify_target
spec=importlib.util.spec_from_file_location('importer',BASE/'application-import.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
NAME='Dell imported imnull metadata one-shot'
TYPE='repository.maven.rebuild-metadata'


def ui(api,method,data):
    _,raw=api.request('POST','/service/extdirect',{'action':'coreui_Task','method':method,'data':data,'type':'rpc','tid':1})
    response=json.loads(raw)
    if response.get('type')=='exception' or not response.get('result',{}).get('success',True):
        raise RuntimeError('Official UI task operation failed; details suppressed')
    return response['result'].get('data')


def main():
    verify_target(data_path='/srv/nexus/data');api=m.API();m.ensure_repository(api)
    types=ui(api,'readTypes',[])
    kind=next((x for x in types if x.get('id')==TYPE),None)
    if not kind or not {'repositoryName','rebuildChecksums','cascadeRebuild'}.issubset({x['id'] for x in kind['formFields']}):
        raise RuntimeError('Installed Nexus UI task type/fields differ from reviewed schema')
    rows=ui(api,'read',[])
    candidates=[x for x in rows if x.get('name')==NAME]
    if len(candidates)>1:raise RuntimeError('Ambiguous managed metadata tasks')
    properties={'repositoryName':'imnull-releases','groupId':'','artifactId':'','baseVersion':'','rebuildChecksums':'true','cascadeRebuild':'true'}
    if candidates:task=candidates[0]
    else:
        task=ui(api,'create',[{'typeId':TYPE,'enabled':True,'name':NAME,'alertEmail':'','notificationCondition':'FAILURE','schedule':'manual','properties':properties,'recurringDays':[],'startDate':None,'timeZoneOffset':'+00:00'}])
    # Read the persisted task before running: wildcard/all-repository scopes are forbidden.
    rows=ui(api,'read',[]);task=next(x for x in rows if x.get('id')==task['id'])
    if task.get('typeId')!=TYPE or task.get('schedule')!='manual' or task.get('properties',{}).get('repositoryName')!='imnull-releases':
        raise RuntimeError('Persisted task scope is not exact imported repository; not executed')
    m.save('metadata-task-scope.json',{'task_id':task['id'],'type':TYPE,'schedule':'manual','repository':'imnull-releases','properties':task['properties'],'schema_origin':'installed Nexus3.84 UI readTypes + extdirect API declaration'})
    api.request('POST','/service/rest/v1/tasks/'+task['id']+'/run',body=b'',content_type='application/json')
    for _ in range(120):
        status=api.json('GET','/tasks/'+task['id'])
        if status.get('lastRun') and status.get('currentState')=='WAITING':
            if status.get('lastRunResult')!='OK':raise RuntimeError('Scoped metadata rebuild did not finish OK')
            m.save('metadata-task-result.json',status);print(json.dumps({'task_id':task['id'],'scope':'imnull-releases only','last_run_result':'OK','source_or_other_repositories_touched':False}));return
        time.sleep(1)
    raise RuntimeError('Scoped metadata task deadline exceeded')


if __name__=='__main__':
    try:main()
    except Exception as error:print('METADATA REBUILD ERROR: '+str(error),file=sys.stderr);sys.exit(1)
