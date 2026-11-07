#!/usr/bin/env python3
"""Read-only10guest source capture; local12->10 catalog/ROLES-only candidates."""
import ast,base64,copy,datetime,difflib,hashlib,importlib.util,json,re,shlex,sys
from pathlib import Path
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];sys.path.insert(0,str(ROOT/'scripts'));import control
IDS=[200,201,210,220,221,230,240,250,260,270];DROP={'java-prod-02','java-prod-03'};T={x['target']['vmid']:x['target'] for x in json.loads((ROOT/'evidence/implementation/private-guest-access.json').read_text())['roles']}
def sha(b):return hashlib.sha256(b).hexdigest()
CODE=r'''
import socket,pathlib,json,sys,hashlib,base64,stat
p=json.load(sys.stdin);assert socket.gethostname()==p['hostname'] and not pathlib.Path('/etc/pve').exists();out={'vmid':p['vmid'],'hostname':socket.gethostname(),'files':[]}
for text in ['/opt/dell/guest-monitoring/guest-targets.json','/opt/dell/guest-monitoring/install-guest-baseline.py','/opt/dell/guest-monitoring/collect-guest-health.py','/etc/dell-guest-monitoring/health.json']:
 f=pathlib.Path(text);st=f.stat();assert f.is_file() and not f.is_symlink() and st.st_uid==0 and not st.st_mode&0o022;b=f.read_bytes();r={'path':text,'sha256':hashlib.sha256(b).hexdigest(),'mode':stat.S_IMODE(st.st_mode),'uid':st.st_uid,'gid':st.st_gid}
 if f.name=='health.json':
  c=json.loads(b);r['health_metadata']={'role':c['role'],'private_ip':c['private_ip'],'service_count':len(c['services']),'http_count':len(c['http_checks'])}
 else:r['body_b64']=base64.b64encode(b).decode()
 out['files'].append(r)
print(json.dumps(out))
'''
D={'captured_at':datetime.datetime.now().astimezone().isoformat(),'read_only':True,'roles':[]};rows=[]
plan=json.loads((ROOT/'plan.json').read_text());names={r.get('vmid',r.get('existing_ctid')):r['name'] for r in plan['roles']}
for v in IDS:
 r=control.guest(v,'sudo -n python3 -B -c '+shlex.quote(CODE),data=json.dumps({'vmid':v,'hostname':names[v]}).encode(),info=T[v],timeout=40);assert r['exit_code']==0,('readonlysourcecapturefailed',v,r['exit_code']);j=json.loads(r['stdout'])
 for f in j['files']:
  if 'body_b64' in f:
   b=base64.b64decode(f.pop('body_b64'));assert sha(b)==f['sha256'];p=HERE/'baselines'/('vm'+str(v))/Path(f['path']).name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b);f['baseline']=str(p.relative_to(HERE))
 D['roles'].append(j);print(json.dumps({'captured':v,'SHAs':{x['path'].split('/')[-1]:x['sha256'] for x in j['files']}}),flush=True)
(HERE/'live-source-inventory.json').write_text(json.dumps(D,indent=2)+'\n')
# Each actual live variant is patched independently; no new profile logic is imported/downgraded.
def patch_installer(b):
 s=b.decode();line=next(l for l in s.splitlines() if l.startswith('ROLES='));roles=ast.literal_eval(line.split('=',1)[1]);assert len(roles)==12 and DROP<=roles;newroles=roles-DROP;replacement='ROLES={'+','.join(repr(x) for x in sorted(newroles))+'}';assert s.count(line)==1;s=s.replace(line,replacement,1);needle="if len(catalog['roles'])!=12 or {x['role'] for x in catalog['roles']}!=ROLES:";assert s.count(needle)==1;s=s.replace(needle,"if len(catalog['roles'])!=len(ROLES) or {x['role'] for x in catalog['roles']}!=ROLES:",1);ast.parse(s);return s.encode()
def patch_catalog(b):
 c=json.loads(b);assert len(c['roles'])==12;c['roles']=[r for r in c['roles'] if r['vmid'] not in [231,232]];assert {r['vmid'] for r in c['roles']}==set(IDS);c['scope']='10 active Debian13 exporter guests;221 retained,no Nexusmerge;CF100/GW190 use PVE/QGA';c['topology_revision']='cleanup-Java-only-10-exporters-15-targets';return (json.dumps(c,indent=2)+'\n').encode()
def load(p,n):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
for j in D['roles']:
 v=j['vmid'];metas={x['path'].split('/')[-1]:x for x in j['files']};base=HERE/'baselines'/('vm'+str(v));candidate=HERE/'candidates'/('vm'+str(v));candidate.mkdir(parents=True,exist_ok=True)
 for name,fn in [('guest-targets.json',patch_catalog),('install-guest-baseline.py',patch_installer)]:
  old=(base/name).read_bytes();new=fn(old);(candidate/name).write_bytes(new);rows.append({'vmid':v,'target_path':metas[name]['path'],'expected_old_SHA256':sha(old),'new_SHA256':sha(new),'mode':metas[name]['mode'],'uid':metas[name]['uid'],'gid':metas[name]['gid'],'candidate':str((candidate/name).relative_to(HERE))})
  diff=HERE/'diffs'/('vm'+str(v)+'-'+name+'.patch');diff.parent.mkdir(exist_ok=True);diff.write_text(''.join(difflib.unified_diff(old.decode().splitlines(True),new.decode().splitlines(True),fromfile=name+'-actual-before',tofile=name+'-ten-role-candidate')))
 m=load(candidate/'install-guest-baseline.py','candidate_'+str(v));role=metas['health.json']['health_metadata']['role'];assert m.target_for(role,role)['vmid']==v and len(m.ROLES)==10
 original_ast=ast.parse((base/'install-guest-baseline.py').read_text());candidate_ast=ast.parse((candidate/'install-guest-baseline.py').read_text());functions=lambda t:{n.name:ast.dump(n,include_attributes=False) for n in t.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))};a,b=functions(original_ast),functions(candidate_ast);assert all(a[k]==b[k] for k in a if k!='target_for'),'unrelated function changed'
# Current newer SOURCE is a separate baseline, never replaced by any older deployed copy.
source=ROOT/'infra/ops/guest-baseline';out=HERE/'source-candidates';out.mkdir(exist_ok=True);source_rows=[]
for name,fn in [('guest-targets.json',patch_catalog),('install-guest-baseline.py',patch_installer)]:
 old=(source/name).read_bytes();new=fn(old);(out/name).write_bytes(new);source_rows.append({'path':'infra/ops/guest-baseline/'+name,'old_SHA256':sha(old),'new_SHA256':sha(new),'candidate':'source-candidates/'+name})
oldsrc=load(source/'install-guest-baseline.py','actual_current_source');newsrc=load(out/'install-guest-baseline.py','source_ten_candidate');cat=json.loads((out/'guest-targets.json').read_text());assert hasattr(newsrc,'role_health_profile')
for r in cat['roles']:assert oldsrc.role_health_profile(r)==newsrc.role_health_profile(r)
pub=next(r for r in cat['roles'] if r['vmid']==220);nex=next(r for r in cat['roles'] if r['vmid']==221);assert not newsrc.role_health_profile(pub)['services'] and newsrc.role_health_profile(nex)['http_checks'][0]['url']=='http://192.168.19.31:8081/service/rest/v1/status';assert 'service_aliases' not in pub
manifest={'status':'prepared-not-applied','physical_permanent_roles':12,'exporter_ids':IDS,'exporters':10,'Ops_other_targets':5,'actual_fileSD_target_total':15,'Nexus221_kept':True,'Nexus220_profile_added':False,'files':rows,'unchanged_guards':{str(r['vmid']):{f['path']:f['sha256'] for f in r['files'] if f['path'].endswith(('/health.json','/collect-guest-health.py'))} for r in D['roles']},'source_files':source_rows,'allowed_live_changes':['ROLES removejava-prod-02/java-prod-03','catalog removetwo rows+scope metadata','catalog count guard len(ROLES)'],'no_profile_function_or_collector_health_change':True,'source_all_retained_role_profiles_equal':True,'runtime_other_functions_equal':True,'Nexus_stop_authorization_pending':True,'current_source_overwritten':False,'guest_files_written':False,'interimSD_receipt':'../interim/deployment-evidence/940e757ea48c4fc59e4413cd20a04b07.json'};(HERE/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps({'status':'prepare-complete','guests':10,'paired_candidates':len(rows),'health_collector_bytes_preserved':True,'source_role_health_profiles_unchanged':True,'Nexus221_preserved':True,'source_or_guest_writes':False}))
