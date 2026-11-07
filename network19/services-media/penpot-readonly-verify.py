#!/usr/bin/env python3
"""Owned250 post-network original design/media, new origin and MCP/job read-only validation."""
import json,sys
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts'));import control
control.BASE+=['-o','ForwardAgent=no']
info=json.loads((ROOT/'network19/evidence/migrated-access.json').read_text())['targets']['250'];assert info['ip']=='192.168.19.50'
nonce=json.loads(Path(__file__).with_name('stage-nonces.json').read_text())['250']
mcp=(ROOT/'infra/penpot/runtime/health-supervision/mcp-readonly.mjs').read_text()
SCRIPT=r'''
import hashlib,importlib.util,json,subprocess,sys,urllib.request
from pathlib import Path
sys.dont_write_bytecode=True
B=Path('/opt/dell/penpot');s=importlib.util.spec_from_file_location('tx','/opt/dell/network19/services-media/guest_transaction.py');tx=importlib.util.module_from_spec(s);s.loader.exec_module(tx)
r=tx.guard(250,'new');folder=Path('/root/dell-network19-media/250')/NONCE;j=json.loads(tx.read(folder/'journal.json'));assert j['phase']=='runtime-ready-final-app-verification-pending';tx.prove_protected(r,j)
snapshot=tx.pen_snapshot();before=j['penpot_baseline']
for key in ['original_files','media_path_to_sha256','Git_HEAD','Git_dirty']:
 if snapshot[key]!=before[key]:raise RuntimeError('Original file/media/Git snapshot differs')
assert len(snapshot['original_files'])==3 and snapshot['media_unique_hashes']==973 and snapshot['Git_HEAD']=='ff1783e7865af7aae571c985f03e057631b7af63' and not snapshot['Git_dirty']
compose=tx.D+['compose','--env-file','/etc/penpot/.env','-f',str(B/'compose.fresh.yaml'),'-f',str(B/'runtime/health-supervision/compose.health-supervision.yaml')]
q=subprocess.run(compose+['exec','-T','penpot-worker','node','--input-type=module','-'],input=PUBLIC_MCP_SCRIPT,text=True,capture_output=True,timeout=150)
assert q.returncode==0,'MCP readonly semantics failed; private protocol details withheld'
mcp=json.loads(q.stdout);assert mcp['status']=='passed' and mcp['design_writes']==0
# Credentials only stay within the existing250/root importer status call.
sys.path.insert(0,str(B));spec=importlib.util.spec_from_file_location('acceptance',B/'application/acceptance.py');a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
key=json.loads(Path('/etc/penpot/worker-credentials.json').read_text())['mcpKey'];record=json.loads(Path('/etc/penpot/async-import-acceptance.json').read_text())
job=a.import_rpc(key,'get_import_status',{'jobId':record['job_id']})
assert job['status']=='completed' and job['jobId']==record['job_id'] and len(job['files'])==1 and job['files'][0]['id']==record['new_file_id'] and job['projectId']==record['project_id']
owner=a.api.API('owner');files=owner.call('get-project-files',{'project-id':record['project_id']});assert len(files)==1 and files[0]['id']==record['new_file_id']
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),a.api.NoRedirect())
with opener.open('http://192.168.19.50:9001/js/config.js',timeout=15) as response:config=response.read(1024*1024).decode()
assert 'http://192.168.19.50:9001' in config and 'http://192.168.21.22:9001' not in config
compose_bytes=(B/'compose.fresh.yaml').read_bytes();assert compose_bytes.count(b'--upstream=192.168.19.1:53')==1 and b'https://1.1.1.1/dns-query' not in compose_bytes and b'https://1.0.0.1/dns-query' not in compose_bytes
rows=tx.state(r);assert len(rows)==11 and all(x['running'] and x['health']=='healthy' for x in rows);tx.prove_protected(r,j)
result={'role':250,'status':'new-network-original-design-media-Git-MCP-job-origin-verified','public_uri':'http://192.168.19.50:9001','original_designs':3,'original_data_revn_stats_equal_to_pre_network_stage':True,'original_971_media_protected':True,'all_973_asset_paths_and_SHA_unchanged':True,'Git_HEAD':snapshot['Git_HEAD'],'Git_clean':True,'new_identity_IDmap_credential_bytes_unchanged':True,'worker_ready_idle':True,'MCP_authenticated_context_and_anonymous_design_denial':mcp,'existing_async_job_status':'completed','existing_async_job_id':job['jobId'],'existing_async_file_id':record['new_file_id'],'existing_async_project_one_file_only':True,'import_or_retry_requests_submitted':False,'public_config_origin_updated':True,'DNS_unified_router19_1_port53':True,'Git_or_design_writes':False,'containers_running_healthy':11,'containers':rows,'data_uuid':r['uuid'],'all_sensitive_values_and_hashes_withheld':True}
tx.save(folder/'network-semantic-verification.json',result);print(json.dumps(result))
'''
SCRIPT=SCRIPT.replace('NONCE',repr(nonce)).replace('PUBLIC_MCP_SCRIPT',repr(mcp))
res=control.guest(250,'sudo python3 -',data=SCRIPT.encode(),timeout=360,info=info)
if res['exit_code']:raise SystemExit('PEN new-network readonly semantic verification unconfirmed; raw data withheld')
value=json.loads(res['stdout']);Path(__file__).with_name('penpot-post-cutover-verification.json').write_text(json.dumps(value,indent=2)+'\n')
print(json.dumps({'role':250,'status':value['status']}))
