#!/usr/bin/env python3
import json,importlib.util,subprocess,hashlib
from pathlib import Path
HERE=Path('/opt/dell/penpot/runtime/health-supervision');s=importlib.util.spec_from_file_location('final_contract_guard',HERE/'supervisor.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
m.guest_guard();lock=m.load_lock();m.storage_guard(lock);m.verify_files_and_images(lock);m.check_config(lock);frame=m.scan()
if not m.validate_frame(frame,lock):raise SystemExit('full runtime contract not healthy')
unit=dict(x.split('=',1) for x in m.run(['systemctl','show','dell-penpot.service','--property=Type,ActiveState,SubState,Restart,NRestarts,RemainAfterExit,UnitFileState,BindsTo,RequiresMountsFor']).stdout.splitlines() if '=' in x)
rows=[]
for name,c in sorted(frame.items()):
 ref=m.docker('inspect','--format','{{json .Config.Image}}',c['id']).stdout
 log=json.loads(m.docker('inspect','--format','{"driver":{{json .HostConfig.LogConfig.Type}},"max_size":{{json (index .HostConfig.LogConfig.Config "max-size")}},"max_file":{{json (index .HostConfig.LogConfig.Config "max-file")}},"privileged":{{json .HostConfig.Privileged}}}',c['id']).stdout)
 rows.append({'service':name,'id':c['id'],'image_id':c['image'],'configured_image_reference':json.loads(ref),'linux_amd64_image_lock_verified':True,'health':c['health'],'pids_limit':c['pids'],'CPU_cap_vcpu':c['nano_cpus']/1e9,'memory_cap_gib':c['memory']/1024**3,'container_restart':c['restart'],'logging_and_privileged':log,'mounts_match_approved_contract':True})
permissions={}
for name in ['.env','new-identities.json','worker-credentials.json','worker-credentials.uid1001.json','worker-credentials.uid1000.json']:
 p=Path('/etc/penpot')/name;t=p.stat();permissions[name]={'uid':t.st_uid,'gid':t.st_gid,'mode':oct(t.st_mode&0o777)}
drop=Path('/etc/systemd/system/dell-penpot.service.d/20-health-supervision.conf');drop_sha=hashlib.sha256(drop.read_bytes()).hexdigest();drop_expected=hashlib.sha256((HERE/'20-health-supervision.conf').read_bytes()).hexdigest()
failed=m.run(['systemctl','--failed','--plain','--no-legend','--no-pager'],check=False).stdout;failed_names=[x.split()[0] for x in failed.splitlines() if x.split()];state=m.run(['systemctl','is-system-running'],check=False).stdout.strip()
checks={'all_11_runtime_contracts_healthy':len(rows)==11,'notify_active_running_enabled':unit.get('Type')=='notify' and unit.get('ActiveState')=='active' and unit.get('SubState')=='running' and unit.get('UnitFileState')=='enabled','dropin_exact_SHA':drop_sha==drop_expected,'new_identity_modes600':all(x['mode']=='0o600' for x in permissions.values()),'all_logs_local_10m_3':all(x['logging_and_privileged']=={'driver':'local','max_size':'10m','max_file':'3','privileged':False} for x in rows),'three_source_built_images_use_actual_SHA_ID_in_configuration':all(x['configured_image_reference']==x['image_id'] for x in rows if x['service'] in ['penpot-frontend','penpot-worker','penpot-import'])}
print(json.dumps({'status':'passed' if all(checks.values()) else 'failed','checks':checks,'unit':unit,'containers':rows,'new_identity_file_permissions':permissions,'CPU_caps_sum':sum(x['CPU_cap_vcpu'] for x in rows),'VM_vcpu':6,'memory_caps_sum_gib':sum(x['memory_cap_gib'] for x in rows),'VM_memory_gib':16,'caps_are_not_reservations':True,'systemd_state':state,'failed_units':failed_names,'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'source_or_design_writes':0,'secret_values_emitted':False}));raise SystemExit(0 if all(checks.values()) else 1)
