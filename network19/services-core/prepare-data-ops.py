#!/usr/bin/env python3
"""Public exact diff recipes only; never stages secret env contents or writes targets."""
import copy,json,hashlib
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parents[1]
i=json.loads((H/'inventory.json').read_text());rows={r['vmid']:r for r in i['roles']};mp=json.loads((R/'network19/migration-plan.json').read_text());mapping={r['old_ip']:r['new_ip'] for r in mp['guest_addresses'] if r['old_ip'].startswith('10.63.')}
recipes=[]
for vmid,role in [(200,'prod-db'),(201,'prod-infra'),(210,'test-data')]:
 bundle='/opt/dell/data/'+role;old=rows[vmid]['env_safe'];new=mapping[old['SERVICE_IP']]
 fields={'SERVICE_IP':{'old':old['SERVICE_IP'],'new':new}}
 if vmid in [200,201]:fields['MYSQL_HOST']={'old':'10.63.10.10','new':'192.168.19.10'}
 recipes.append({'vmid':vmid,'path':bundle+'/.env','source_sha256':rows[vmid]['files'][bundle+'/.env']['sha256'],'exact_env_keys':fields,'other_lines_preserve_bytes':True,'mode':'0600 root/owner unchanged','MYSQL_HOST_mysql_unchanged':vmid==210,'Nacos_percent_ownDB_accounts_password_namespace_vhost_unchanged':True})
recipes.append({'vmid':270,'path':'/opt/dell/ops/.env','source_sha256':rows[270]['files']['/opt/dell/ops/.env']['sha256'],'exact_env_keys':{'SERVICE_IP':{'old':'10.63.30.40','new':'192.168.19.70'}},'other_lines_preserve_bytes':True})
ops=rows[270];out=H/'prepared/ops';out.mkdir(parents=True,exist_ok=True)
for path,value in ops['selected_JSON'].items():
 if path.endswith('/targets/guest-node.json'):
  target=copy.deepcopy(value)
  for item in target:
   if len(item['targets'])!=1:raise RuntimeError('target-array-size-differs')
   host,port=item['targets'][0].split(':')
   if host not in mapping or port!='9100':raise RuntimeError('unknown-old-metrics-target')
   item['targets'][0]=mapping[host]+':9100'
  p=out/'guest-node.json';p.write_text(json.dumps(target,indent=2)+'\n');recipes.append({'vmid':270,'path':path,'source_sha256':ops['files'][path]['sha256'],'prepared_public_path':str(p.relative_to(H)),'new_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'only_target_host_changed':True})
 elif path.endswith('/targets/http-services.json'):
  # Existing actual set only internal service-DNS health URLs. Keep bytes, do not invent direct targets.
  recipes.append({'vmid':270,'path':path,'source_sha256':ops['files'][path]['sha256'],'action':'unchanged; grafana/alertmanager/prometheus Docker service names remain','no_new_external_probe':True})
(H/'data-ops-patch-contract.json').write_text(json.dumps({'status':'recipes-not-applied','files':recipes,'Data_guards':'manage preflight reads env SERVICE_IP dynamically; mount UUID/paths unchanged. No generic deploy/bootstrap-Nacos rerun.','Ops_guards':'SERVICE_IP dynamic; existing Lark marker, renderer and token checks preserved. Do not rerun prepare/install/send.','PVE_textfile':{'source':'/root/dell-bootstrap/pve-push-metrics.py','delivery':'QGA VMID270, not old IP','destination':'/var/lib/prometheus/node-exporter-textfile/dell-pve.prom','known_source_IP_literals':0,'action':'root verify actual installed source hash and next QGA timestamp; no address replacement inferred'},'Lark_invariants':{'bind':'172.18.0.1:19093','allowed_source':'172.18.0.3','network':'172.18.0.0/16','fixed_service_IPs':{'prometheus':'172.18.0.2','alertmanager':'172.18.0.3','blackbox':'172.18.0.4','grafana':'172.18.0.5'},'all_credentials_mode_and_active_renderer_unchanged':True,'outbound_test_send':False,'maintenance_silence':'root-owned network19/evidence/maintenance-silence.json'}},indent=2)+'\n')
print(json.dumps({'Data_env_recipes':3,'Ops_env_recipe':1,'metrics_targets':12,'all_stage_only':True}))
