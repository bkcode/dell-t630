#!/usr/bin/env python3
"""Readonly270 capture/native check, local interim SD-only candidates; no deployment."""
import sys,json,copy,base64,hashlib,shlex,datetime
from pathlib import Path
import yaml
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;PARENT=HERE.parent;ROOT=HERE.parents[2];sys.path.insert(0,str(ROOT/'scripts'));import control
T=next(x['target'] for x in json.loads((ROOT/'evidence/implementation/private-guest-access.json').read_text())['roles'] if x['target']['vmid']==270)
def sha(b):return hashlib.sha256(b).hexdigest()
CAPTURE=r'''
import sys,json,socket,pathlib,hashlib,base64,subprocess,urllib.request,re
assert socket.gethostname()=='ops-service' and not pathlib.Path('/etc/pve').exists();out={'files':[]}
for path in ['/opt/dell/ops/config/prometheus/targets/guest-node.json','/opt/dell/ops/config/prometheus/prometheus.yml','/opt/dell/ops/config/prometheus/rules/infra.yml']:
 p=pathlib.Path(path);st=p.stat();assert not p.is_symlink() and st.st_uid==0 and not st.st_mode&0o022;b=p.read_bytes();assert not re.search(rb'(?mi)^\s*(basic_auth|authorization|bearer_token(?:_file)?|password|credentials|oauth2|http_headers)\s*:',b);out['files'].append({'path':path,'sha256':hashlib.sha256(b).hexdigest(),'mode':st.st_mode&0o777,'uid':st.st_uid,'gid':st.st_gid,'body':base64.b64encode(b).decode()})
with urllib.request.build_opener(urllib.request.ProxyHandler({})).open('http://192.168.19.70:9090/api/v1/targets',timeout=8) as r:ts=json.loads(r.read(2000000))['data']['activeTargets']
out['live_targets']=[{'labels':x.get('labels',{}),'health':x['health']} for x in ts];print(json.dumps(out))
'''
r=control.guest(270,'sudo -n python3 -B -c '+shlex.quote(CAPTURE),info=T,timeout=35);assert r['exit_code']==0;live=json.loads(r['stdout']);contents={}
for f in live['files']:
 b=base64.b64decode(f.pop('body'));assert sha(b)==f['sha256'];contents[f['path']]=b;p=HERE/'baseline'/Path(f['path']).name;p.parent.mkdir(exist_ok=True);p.write_bytes(b)
full=json.loads((PARENT/'manifest.json').read_text());reference=PARENT/'baselines/vm270/opt/dell/ops/config/prometheus/targets/guest-node.json';old12=reference.read_bytes();refmeta=next(x for x in full['files'] if x['vmid']==270 and x['target_path'].endswith('/guest-node.json'));assert sha(old12)==refmeta['expected_old_SHA256']
rows12=json.loads(old12);IDS12={200,201,210,220,221,230,231,232,240,250,260,270};IDS10=IDS12-{231,232};assert {int(x['labels']['vmid']) for x in rows12}==IDS12 and len(rows12)==12
rows10=[x for x in rows12 if int(x['labels']['vmid']) not in {231,232}];new10=(json.dumps(rows10,indent=2)+'\n').encode();assert len(rows10)==10 and next(x for x in rows10 if x['labels']['vmid']=='221')==next(x for x in rows12 if x['labels']['vmid']=='221')
current=contents['/opt/dell/ops/config/prometheus/targets/guest-node.json'];ids={int(x['labels']['vmid']) for x in json.loads(current)}
if sha(current)==sha(old12) and ids==IDS12:source_state='original12-pinned'
elif sha(current)==sha(new10) and ids==IDS10:source_state='already-interim10-pinned'
else:raise RuntimeError('sourceCASrefused: exact12or10 IDs and pinnedbytes required; no arbitrarySHA substitution')
(HERE/'guest-node.interim.json').write_bytes(new10);(HERE/'original12-pinned.json').write_bytes(old12)
conf=yaml.safe_load(contents['/opt/dell/ops/config/prometheus/prometheus.yml']);guest=next(x for x in conf['scrape_configs'] if x['job_name']=='guest-node');assert guest['file_sd_configs']==[{'files':['/etc/prometheus/targets/guest-node.json']}];guest.pop('file_sd_configs');guest['static_configs']=rows10;equiv=yaml.safe_dump(conf,sort_keys=False).encode();oplabels=[x['labels'] for x in live['live_targets'] if x['labels'].get('job')!='guest-node'];assert len(oplabels)==5
NATIVE=r'''
import json,sys,base64,subprocess,socket,pathlib,re,hashlib
p=json.load(sys.stdin);assert socket.gethostname()=='ops-service' and not pathlib.Path('/etc/pve').exists();assert hashlib.sha256(pathlib.Path('/opt/dell/ops/config/prometheus/prometheus.yml').read_bytes()).hexdigest()==p['prom_SHA'];ids=subprocess.run(['docker','ps','--quiet','--filter','label=com.docker.compose.service=prometheus'],capture_output=True,text=True,check=True).stdout.split();assert len(ids)==1;i=ids[0]
def state():return subprocess.run(['docker','inspect','--format','{{.Id}} {{.State.Pid}} {{.State.StartedAt}} {{if .State.Health}}{{.State.Health.Status}}{{end}}',i],capture_output=True,text=True,check=True).stdout.strip()
before=state();body=base64.b64decode(p['equiv']);out={}
for k,args in [('config',['check','config','/dev/stdin']),('SD',['check','service-discovery','--timeout=1s','/dev/stdin','guest-node'])]:
 r=subprocess.run(['docker','exec','-i',i,'/bin/promtool',*args],input=body,capture_output=True,timeout=20);out[k]={'exit':r.returncode,'stderr_present':bool(r.stderr)}
 if k=='SD' and r.returncode==0:v=json.loads(r.stdout);out[k]['groups']=len(v);out[k]['addresses']=sorted(set(re.findall(r'192\.168\.19\.\d+:9100',r.stdout.decode())))
out['Prometheus_main_identity_health_unchanged']=before==state();out['live_file_write_or_service_restart']=False;print(json.dumps(out))
'''
promsha=sha(contents['/opt/dell/ops/config/prometheus/prometheus.yml']);payload={'equiv':base64.b64encode(equiv).decode(),'prom_SHA':promsha};r=control.guest(270,'sudo -n python3 -B -c '+shlex.quote(NATIVE),data=json.dumps(payload).encode(),info=T,timeout=60);assert r['exit_code']==0;native=json.loads(r['stdout']);assert native['config']['exit']==native['SD']['exit']==0 and native['SD']['groups']==10 and native['Prometheus_main_identity_health_unchanged'];assert set(native['SD']['addresses'])=={x['targets'][0] for x in rows10}
meta=next(x for x in live['files'] if x['path'].endswith('/guest-node.json'));manifest={'status':'prepared-not-applied','scope':'onlyJava231232SDremoval; noNexusstop/retirement/220changes','target_guest':270,'target_path':meta['path'],'source_state_at_capture':source_state,'current12_SHA256':sha(old12),'interim10_SHA256':sha(new10),'expected12_IDs':sorted(IDS12),'expected10_IDs':sorted(IDS10),'removed_only_IDs':[231,232],'protected221_target_unchanged':next(x for x in rows10 if x['labels']['vmid']=='221'),'candidate':'guest-node.interim.json','target_mode':meta['mode'],'target_uid':meta['uid'],'target_gid':meta['gid'],'prom_SHA256':promsha,'rules_SHA256':sha(contents['/opt/dell/ops/config/prometheus/rules/infra.yml']),'expected_Ops_own_labels':oplabels,'future_total_targets':15,'ops_own_target_count':5,'no_Promrestart':True,'live_mutation_performed':False,'Nexus_stop_authorization':'pending; automaticreview rejected priorfeasibility-only instruction'}
(HERE/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');(HERE/'live-source-inventory.json').write_text(json.dumps(live,indent=2)+'\n');(HERE/'native-check.json').write_text(json.dumps({'at':datetime.datetime.now().astimezone().isoformat(),'method':'readonly actualPromtool STDIN equivalent staticgroups; actualfileSD/15UP pendingcommit','result':native,'status':'passed-prepare-only'},indent=2)+'\n')
contract={'status':'future-full-CAS-contract-only-not-authorization','full_original_manifest_unchanged':True,'full_requires_explicit_Nexusmaintenance_authorization':True,'full_requires_Nexus221stopped/alias31healthy-on220':True,'accepted_final_source_alternatives':[{'node_IDs':sorted(IDS12),'exact_SHA256':sha(old12)},{'node_IDs':sorted(IDS10),'exact_SHA256':sha(new10)}],'final9_candidate_SHA256':next(x['new_SHA256'] for x in full['files'] if x['vmid']==270 and x['target_path']==meta['path']),'rule':'Adapt finalexpectedoldSHA only after freshactual bytes+exactIDset match one pinnedalternative; never replace SHA arbitrarily; no final9applywhilemaintenanceauthorizationpending.'};(HERE/'full-successor-CAS-contract.json').write_text(json.dumps(contract,indent=2)+'\n');print(json.dumps({'status':'prepared-only','guest_nodes':10,'future_total_targets':15,'221_kept':True,'source_state':source_state,'native':'exit0 exact10','270_writes':False,'full_manifest_modified':False}))
