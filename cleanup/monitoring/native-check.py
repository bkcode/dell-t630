#!/usr/bin/env python3
"""Read-only native Prometheus candidate check over stdin; no guest staging files."""
import json,sys,shlex,hashlib,copy,datetime,re
from pathlib import Path
import yaml
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];sys.path.insert(0,str(ROOT/'scripts'));import control
manifest=json.loads((HERE/'manifest.json').read_text());p=HERE/'baselines/vm270/opt/dell/ops/config/prometheus/prometheus.yml';base=p.read_bytes();assert hashlib.sha256(base).hexdigest()==manifest['prometheus_config_SHA256'];config=yaml.safe_load(base);targets=json.loads((HERE/'candidates/ops/guest-node.json').read_text());job=next(x for x in config['scrape_configs'] if x['job_name']=='guest-node');assert set(job['file_sd_configs'][0])=={'files'};assert job['file_sd_configs'][0]['files']==['/etc/prometheus/targets/guest-node.json'];job.pop('file_sd_configs');job['static_configs']=targets;equivalent=yaml.safe_dump(config,sort_keys=False).encode();T=next(x['target'] for x in json.loads((ROOT/'evidence/implementation/private-guest-access.json').read_text())['roles'] if x['target']['vmid']==270)
CODE=r'''
import json,sys,socket,subprocess,pathlib,hashlib,base64,urllib.request,re
p=json.load(sys.stdin);assert socket.gethostname()=='ops-service' and not pathlib.Path('/etc/pve').exists();assert hashlib.sha256(pathlib.Path('/opt/dell/ops/config/prometheus/prometheus.yml').read_bytes()).hexdigest()==p['prom_SHA'];assert hashlib.sha256(pathlib.Path('/opt/dell/ops/config/prometheus/rules/infra.yml').read_bytes()).hexdigest()==p['rules_SHA']
ids=subprocess.run(['docker','ps','--quiet','--filter','label=com.docker.compose.service=prometheus'],capture_output=True,text=True,check=True).stdout.split();assert len(ids)==1;id=ids[0]
def state():return subprocess.run(['docker','inspect','--format','{{.Id}} {{.State.Pid}} {{.State.StartedAt}} {{if .State.Health}}{{.State.Health.Status}}{{end}}',id],capture_output=True,text=True,check=True).stdout.strip()
before=state();body=base64.b64decode(p['equivalent']);out={}
for name,args in [('config',['check','config','/dev/stdin']),('service_discovery',['check','service-discovery','--timeout=1s','/dev/stdin','guest-node'])]:
 r=subprocess.run(['docker','exec','-i',id,'/bin/promtool',*args],input=body,capture_output=True,timeout=20);row={'exit_code':r.returncode,'stderr_present':bool(r.stderr),'stdout_bytes':len(r.stdout)}
 if name=='service_discovery' and r.returncode==0:
  v=json.loads(r.stdout);row['discovered_objects']=len(v);row['unique_guest_addresses']=sorted(set(re.findall(r'192\.168\.19\.\d+:9100',r.stdout.decode())));row['exact_expected_addresses']=set(row['unique_guest_addresses'])==set(p['expected'])
 out[name]=row
out['Prometheus_mainPID_StartedAt_health_unchanged']=before==state();out['method']='actualpromtool in current container; stdin equivalent config replaces only guest-node file_sd with candidate static groups';out['does_not_prove']='actual candidate file_sd commit/watcher/14target UP; those remain deployment validation';out['live_config_or_targets_written']=False;out['containers_created_or_restarted']=False;print(json.dumps(out))
'''
payload={'prom_SHA':manifest['prometheus_config_SHA256'],'rules_SHA':manifest['rules_SHA256'],'equivalent':__import__('base64').b64encode(equivalent).decode(),'expected':[x['targets'][0] for x in targets]};r=control.guest(270,'sudo -n python3 -B -c '+shlex.quote(CODE),data=json.dumps(payload).encode(),timeout=65,info=T);assert r['exit_code']==0,('native readonly check transport failed',r['exit_code']);result=json.loads(r['stdout']);result['captured_at']=datetime.datetime.now().astimezone().isoformat();result['status']='passed-prepare-only' if result['config']['exit_code']==result['service_discovery']['exit_code']==0 and result['service_discovery']['exact_expected_addresses'] and result['Prometheus_mainPID_StartedAt_health_unchanged'] else 'needs-review';(HERE/'native-check.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
