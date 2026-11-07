#!/usr/bin/env python3
"""Exactly one approved250 frontend KILL; receipt makes retries fail closed."""
import importlib.util,json,os,subprocess,time,urllib.request
from pathlib import Path
HERE=Path('/opt/dell/penpot/runtime/health-supervision');spec=importlib.util.spec_from_file_location('locked_supervisor',HERE/'supervisor.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
m.guest_guard();lock=m.load_lock();m.storage_guard(lock);m.verify_files_and_images(lock)
frame=m.scan()
if not m.validate_frame(frame,lock):raise SystemExit('11 healthy required before fault')
unit=dict(line.split('=',1) for line in m.run(['systemctl','show','dell-penpot.service','--property=ActiveState,SubState,NRestarts,InvocationID']).stdout.splitlines() if '=' in line)
if unit.get('ActiveState')!='active' or unit.get('SubState')!='running':raise SystemExit('notify unit must be running')
net=json.loads(m.docker('inspect','--format','{{json .NetworkSettings.Networks}}','penpot-penpot-worker-1').stdout);ip=next(x['IPAddress'] for x in net.values() if x['IPAddress'])
with urllib.request.build_opener(urllib.request.ProxyHandler({})).open('http://'+ip+':4404/readyz',timeout=5) as response:worker=json.load(response)
if worker.get('state')!='ready' or worker.get('activeTasks')!=0:raise SystemExit('worker not idle')
jobdir=Path('/srv/penpot/docker/volumes/penpot_penpot_import_jobs/_data')
if any(json.loads(f.read_text()).get('status') in ['preparing','downloading','importing'] for f in jobdir.glob('*.json')):raise SystemExit('importer not idle')
target=frame['penpot-frontend']
if target['name']!='/penpot-penpot-frontend-1' or target['image']!=lock['services']['penpot-frontend']['image_id']:raise SystemExit('frontend exact object mismatch')
p=HERE/'evidence/frontend-fault.json';fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
receipt={'phase':'prepared','fault_object':'penpot-penpot-frontend-1','exact_container_id':target['id'],'unit_before':unit,'before_container_ids':{n:c['id'] for n,c in frame.items()},'fault_commands_issued':0,'prepared_at':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'worker_import_idle':True}
with os.fdopen(fd,'w') as f:json.dump(receipt,f)
# Never repeat this command if receipt exists, even if an SSH reply is lost.
result=m.docker('kill','--signal','KILL',target['id'],check=False)
receipt.update(phase='fault-issued' if result.returncode==0 else 'fault-command-failed-no-retry',fault_commands_issued=1,kill_exit_code=result.returncode,issued_at=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()))
p.write_text(json.dumps(receipt));p.chmod(0o600);print(json.dumps(receipt));raise SystemExit(result.returncode)
