import json,sys,tempfile,subprocess,uuid
from pathlib import Path
v=json.loads(sys.stdin.read());project=v['project'];mount=v['mount']
with tempfile.TemporaryDirectory(prefix='NAS-sys001-merge-'+v['nonce']+'-') as tmp:
 root=Path(tmp);env=root/'qa.env';env.write_text('NAS_MOUNT='+mount+'\nNAS_DATA_UUID='+str(uuid.uuid4())+'\nNAS_BIND_IP=127.0.0.1\nJELLYFIN_IMAGE='+v['image']+'\nJELLYFIN_UID=2000\nJELLYFIN_GID=2000\nJELLYFIN_PUBLIC_URL=http://127.0.0.1:8096\n');override=root/'override.yaml';override.write_text(v['override'])
 p=subprocess.run(['docker','--host','unix:///var/run/docker.sock','compose','--project-name',project,'--env-file',str(env),'-f','/opt/dell/nas/compose.yaml','-f',str(override),'config','--format','json'],capture_output=True,text=True,timeout=30)
 if p.returncode:print(json.dumps({'status':'failed','safe_reason':'native-compose-config-failed'}));raise SystemExit(1)
 c=json.loads(p.stdout);s=c['services']['jellyfin'];expected={(mount+'/appdata/jellyfin/config','/config',False),(mount+'/appdata/jellyfin/cache','/cache',False),(mount+'/media','/media',True)};actual={(x['source'],x['target'],x.get('read_only',False)) for x in s['volumes']}
 raw={k:s[k] for k in ['mem_limit','memswap_limit','cpus','pids_limit']};types={k:type(v).__name__ for k,v in raw.items()}
 checks={'exact_QA_project':c['name']==project,'exact_one_service':set(c['services'])=={'jellyfin'},'exact_zero_publish_mappings':not s.get('ports'),'only_exact_QA_bind_sources':actual==expected and all(x['type']=='bind' and x['bind']['create_host_path'] is False for x in s['volumes']),'internal_network':c['networks']['default']['internal'],'CPU025':float(s['cpus'])==.25,'memory512':int(s['mem_limit'])==536870912 and int(s['memswap_limit'])==536870912,'pids128':int(s['pids_limit'])==128}
 print(json.dumps({'status':'passed' if all(checks.values()) else 'failed','checks':checks,'numeric_raw_values':raw,'numeric_JSON_types':types,'nonce':v['nonce'],'new_target_objects_or_services_changed':False}));raise SystemExit(0 if all(checks.values()) else 1)
