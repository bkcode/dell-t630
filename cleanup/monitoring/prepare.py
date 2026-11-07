#!/usr/bin/env python3
"""Local-only exact monitoring cleanup candidates. No SSH or deployed-source writes."""
import ast,copy,difflib,hashlib,importlib.util,json,sys
from pathlib import Path
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];DROP={221,231,232};KEEP={200,201,210,220,230,240,250,260,270}
def sha(b):return hashlib.sha256(b).hexdigest()
def load(path,name):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def put(path,b):path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b);return sha(b)
def change_once(text,old,new):
 assert text.count(old)==1,('exact source anchor mismatch',old[:70]);return text.replace(old,new,1)
inv=json.loads((HERE/'live-source-inventory.json').read_text());common=HERE/'baselines/vm220/opt/dell/guest-monitoring';collector=load(common/'collect-guest-health.py','actual_live_collector');original_catalog=json.loads((common/'guest-targets.json').read_text());assert len(original_catalog['roles'])==12
catalog=copy.deepcopy(original_catalog);catalog['roles']=[r for r in catalog['roles'] if r['vmid'] not in DROP];assert {r['vmid'] for r in catalog['roles']}==KEEP;row220=next(r for r in catalog['roles'] if r['vmid']==220);row220['service_aliases']=['192.168.19.31'];catalog['scope']='9 retained Debian13 exporter guests;CF100/GW190 remain PVE-QGA metadata paths';catalog['topology_revision']='cleanup-9-exporters-14-total';catbytes=(json.dumps(catalog,indent=2)+'\n').encode()
def roster(text):
 line=next(l for l in text.splitlines() if l.startswith('ROLES='));roles=ast.literal_eval(line.split('=',1)[1]);assert len(roles)==12;roles-= {'artifact-service','java-prod-02','java-prod-03'};assert len(roles)==9;text=change_once(text,line,'ROLES={'+','.join(repr(r) for r in sorted(roles))+'}');text=change_once(text,"if len(catalog['roles'])!=12 or {x['role'] for x in catalog['roles']}!=ROLES:","if len(catalog['roles'])!=len(ROLES) or {x['role'] for x in catalog['roles']}!=ROLES:");return text
# Live installer is older than current source: patch its own bytes, never overwrite source with it.
live_old=(common/'install-guest-baseline.py').read_text();live_new=roster(live_old);assert 'def role_health_profile(' not in live_new
live_new=change_once(live_new,"'artifact-service':['docker.service']","'publish-service':['docker.service','dell-nexus.service']")
live_new=change_once(live_new,"'artifact-service':(8081,'/service/rest/v1/status','nexus-status')","'publish-service':(8081,'/service/rest/v1/status','nexus-status')")
live_new=change_once(live_new,"'url':'http://'+ip+':'+str(port)+path","'url':'http://'+(row.get('service_aliases',[ip])[0] if role=='publish-service' else ip)+':'+str(port)+path")
live_new=change_once(live_new,"    if role.startswith('java-'):\n        checks=[{'name':'actuator-example-not-enabled','url':'http://127.0.0.1:9999/actuator/health/readiness'}]\n",'')
ast.parse(live_new);source_path=ROOT/'infra/ops/guest-baseline/install-guest-baseline.py';source_old=source_path.read_text();source_new=roster(source_old);assert 'def role_health_profile(' in source_new
source_new=change_once(source_new,"'artifact-service':['dell-nexus.service']","'publish-service':['dell-nexus.service']")
source_new=change_once(source_new,"'artifact-service':[(8081,'/service/rest/v1/status','nexus-status')]","'publish-service':[(8081,'/service/rest/v1/status','nexus-status')]")
source_new=change_once(source_new,"'url':'http://'+ip+':'+str(port)+path","'url':'http://'+(row.get('service_aliases',[ip])[0] if role=='publish-service' else ip)+':'+str(port)+path")
source_new=change_once(source_new,"docker_roles={'data-prod-db','data-prod-infra','data-test','artifact-service','penpot-service','nas-media','ops-service'}","docker_roles={'data-prod-db','data-prod-infra','data-test','publish-service','penpot-service','nas-media','ops-service'}");ast.parse(source_new)
for label,text in [('live-common',live_new),('source-common',source_new)]:
 d=HERE/'candidates'/label;put(d/'guest-targets.json',catbytes);put(d/'install-guest-baseline.py',text.encode());put(d/'collect-guest-health.py',(common/'collect-guest-health.py').read_bytes())
# Health profiles remain fixed-path/no credentials. No HTTP alias activation until actual original MAC owns31.
oldhealth=json.loads((HERE/'baselines/vm220/etc/dell-guest-monitoring/health.json').read_text());unit=copy.deepcopy(oldhealth)
if 'dell-nexus.service' not in unit['services']:unit['services'].append('dell-nexus.service')
unit['candidate_service_units']=['docker.service','dell-nexus.service'];unit['candidate_http_checks']=[];unit['notes']='Merged publisher/Nexus role; active Nexus unit only. Alias31 HTTP requires exact approved local-MAC readiness; no Java apps.'
full=copy.deepcopy(unit);check={'name':'nexus-status','url':'http://192.168.19.31:8081/service/rest/v1/status'};assert not any(x['name']==check['name'] and x!=check for x in full['http_checks']);full['http_checks']+=[check] if check not in full['http_checks'] else [];full['candidate_http_checks']=[check];full['notes']='Merged publisher/Nexus role; Nexus HTTP uses approved alias31 on original MAC; no broad CIDR/headers or Java apps.'
for name,c in [('unit-only',unit),('full',full)]:put(HERE/'candidates/profiles'/name/'health.json',(json.dumps(c,indent=2)+'\n').encode())
oldtargetpath=HERE/'baselines/vm270/opt/dell/ops/config/prometheus/targets/guest-node.json';oldtargets=json.loads(oldtargetpath.read_text());targets=[x for x in oldtargets if int(x['labels']['vmid']) not in DROP];assert len(targets)==9 and {int(x['labels']['vmid']) for x in targets}==KEEP;assert sum(x['targets']==['192.168.19.30:9100'] for x in targets)==1 and all('192.168.19.31:9100' not in x['targets'] for x in targets)
newtargetbytes=(json.dumps(targets,indent=2)+'\n').encode();put(HERE/'candidates/ops/guest-node.json',newtargetbytes)
# Prepare authoritative local source candidates separately, preserving newer profile/Lark semantics.
sync=[]
for dest,new in [('infra/ops/guest-baseline/guest-targets.json',catbytes),('infra/ops/guest-baseline/install-guest-baseline.py',source_new.encode())]:
 p=ROOT/dest;put(HERE/'source-candidates'/dest,new);sync.append({'path':dest,'expected_old_SHA256':sha(p.read_bytes()),'new_SHA256':sha(new),'candidate':'source-candidates/'+dest})
src_targets_path=ROOT/'infra/ops/config/candidates/guest-node.json';src_targets=json.loads(src_targets_path.read_text());assert isinstance(src_targets,list) and len(src_targets)==12;newsrc=[x for x in src_targets if int(x['labels']['vmid']) not in DROP];newsrcbytes=(json.dumps(newsrc,indent=2)+'\n').encode();put(HERE/'source-candidates/infra/ops/config/candidates/guest-node.json',newsrcbytes);sync.append({'path':'infra/ops/config/candidates/guest-node.json','expected_old_SHA256':sha(src_targets_path.read_bytes()),'new_SHA256':sha(newsrcbytes),'candidate':'source-candidates/infra/ops/config/candidates/guest-node.json'})
# Local tests reuse ACTUAL live validator, never fake-ready absent alias.
actual220=next(x for x in inv['roles'] if x['vmid']==220);actual_addresses=set(actual220['Nexus_alias_validation']['approved_local_intersection'])|{'127.0.0.1','::1'};collector.validate(unit,actual_addresses);full_live_ready=True
try:collector.validate(full,actual_addresses)
except ValueError:full_live_ready=False
assert not full_live_ready if not actual220['Nexus_alias_validation']['alias31_on_original_MAC'] else full_live_ready
collector.validate(full,{'192.168.19.30','192.168.19.31','127.0.0.1','::1'})
for url in ['http://192.168.19.20:8848/health','http://1.1.1.1/health','http://user:pass@192.168.19.31/health','http://192.168.19.31/health?token=synthetic']:
 c=copy.deepcopy(unit);c['http_checks']=[{'name':'must-reject','url':url}]
 try:collector.validate(c,{'192.168.19.30','192.168.19.31','127.0.0.1','::1'})
 except ValueError:pass
 else:raise AssertionError('forbidden HTTP target accepted')
# Test live/source paired catalogs and preserve all retained nonpublisher newer profile behavior.
a=load(HERE/'candidates/live-common/install-guest-baseline.py','candidate_live_installer');b=load(HERE/'candidates/source-common/install-guest-baseline.py','candidate_source_installer');oldsrc=load(source_path,'current_source_installer')
assert a.target_for('publish-service','publish-service')['vmid']==220 and a.candidates(row220)['candidate_http_checks']==[check];assert b.role_health_profile(row220)=={'services':['dell-nexus.service'],'http_checks':[check]}
for r in catalog['roles']:
 if r['role']!='publish-service':assert b.role_health_profile(r)==oldsrc.role_health_profile(r)
assert not b.role_health_profile(next(r for r in catalog['roles'] if r['vmid']==240))['http_checks'];assert 'dell-lark-notify.service' in b.role_health_profile(next(r for r in catalog['roles'] if r['vmid']==270))['services'];assert b.candidates(row220)['http_checks']==[]
for kind,old,new in [('live-installer',live_old,live_new),('source-installer',source_old,source_new),('health-full',json.dumps(oldhealth,indent=2)+'\n',json.dumps(full,indent=2)+'\n')]:put(HERE/'diffs'/(kind+'.patch'),''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile=kind+'-before',tofile=kind+'-candidate')).encode())
files=[]
for vm in inv['roles']:
 mapping={'/opt/dell/guest-monitoring/guest-targets.json':'candidates/live-common/guest-targets.json','/opt/dell/guest-monitoring/install-guest-baseline.py':'candidates/live-common/install-guest-baseline.py'}
 if vm['vmid']==270:mapping['/opt/dell/ops/config/prometheus/targets/guest-node.json']='candidates/ops/guest-node.json'
 for f in vm['files']:
  if f['path'] in mapping:files.append({'vmid':vm['vmid'],'target_path':f['path'],'expected_old_SHA256':f['sha256'],'new_SHA256':sha((HERE/mapping[f['path']]).read_bytes()),'candidate':mapping[f['path']],'mode':f['mode'],'uid':f['uid'],'gid':f['gid']})
meta220=next(f for f in actual220['files'] if f['path']=='/etc/dell-guest-monitoring/health.json');health={'vmid':220,'target_path':meta220['path'],'expected_old_SHA256':meta220['sha256'],'profiles':{x:{'candidate':'candidates/profiles/'+x+'/health.json','new_SHA256':sha((HERE/'candidates/profiles'/x/'health.json').read_bytes())} for x in ['unit-only','full']},'mode':meta220['mode'],'uid':0,'gid':meta220['gid']}
manifest={'status':'prepared-not-applied','exporter_VMIDs':sorted(KEEP),'removed_VMIDs':sorted(DROP),'permanent_role_count':11,'future_guest_node_count':9,'unchanged_Ops_other_target_count':5,'future_total_target_count':14,'live_target_count_at_capture':17,'files':files,'health220':health,'source_sync':sync,'unchanged_collector_SHA256':sha((common/'collect-guest-health.py').read_bytes()),'prometheus_config_SHA256':sha((HERE/'baselines/vm270/opt/dell/ops/config/prometheus/prometheus.yml').read_bytes()),'rules_SHA256':json.loads((HERE/'rules-baseline.json').read_text())['sha256'],'guards':{'vm220_original_MAC':'bc:24:11:2a:01:ad','primary_IP':'192.168.19.30','approved_alias_IP':'192.168.19.31','full_profile_requires_alias_on_original_MAC':True,'Nexus_unit_must_be_active_even_unit_only':True,'new_proxy_listener':False,'no_generic_installer_install_activate_mask_or_restart':True,'no_WireGuard_host_forward_or_data_auth_modification':True},'readiness':{'alias31_live_at_capture':actual220['Nexus_alias_validation']['alias31_on_original_MAC'],'Nexus_active_at_capture':actual220['service_state']['dell-nexus.service']['ActiveState']=='active','full_profile_ready_live':full_live_ready},'local_tests':{'paired_catalogs9':True,'native_live_collector_unchanged':True,'actual_alias_absence_rejected_full':not full_live_ready,'approved_expected_alias_model_accepts_full':True,'external_otherVM_auth_query_URLs_rejected':True,'newer_source_nonpublisher_profiles_preserved':True,'Java_scope_no_business_HTTP':True,'OpsLark_source_preserved':True},'deployment_not_performed':True}
(HERE/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps({'status':manifest['status'],'future_targets':14,'guest_nodes':9,'alias31_live_ready':full_live_ready,'Nexus_active_live':manifest['readiness']['Nexus_active_at_capture'],'collector_unchanged':True,'live_file_candidates':len(files)+1,'source_candidates':len(sync),'local_tests':'passed'}))
