#!/usr/bin/env python3
import json,subprocess,time
from pathlib import Path
D=['docker','--host','unix:///var/run/docker.sock']
p=subprocess.run(['systemctl','show','dell-penpot.service','--property=Type,ActiveState,SubState,Result,NRestarts,MainPID,InvocationID,Restart,RemainAfterExit'],capture_output=True,text=True,timeout=15);unit=dict(l.split('=',1) for l in p.stdout.splitlines() if '=' in l)
ids=subprocess.run(D+['ps','-aq','--no-trunc'],capture_output=True,text=True,timeout=20).stdout.split();rows=[]
fmt='{"id":{{json .Id}},"name":{{json .Name}},"image":{{json .Image}},"running":{{json .State.Running}},"status":{{json .State.Status}},"started_at":{{json .State.StartedAt}},"health":{{if (index .State "Health")}}{{json .State.Health.Status}}{{else}}null{{end}},"pids_limit":{{json .HostConfig.PidsLimit}}}'
for cid in ids:
 p=subprocess.run(D+['inspect','--format',fmt,cid],capture_output=True,text=True,timeout=20)
 if p.returncode==0:rows.append(json.loads(p.stdout))
p=Path('/run/dell-penpot-supervision-state.json');state=json.loads(p.read_text()) if p.exists() else None
result={'status':'read-only-runtime-status','unit':unit,'container_count':len(rows),'healthy_count':sum(c['health']=='healthy' for c in rows),'running_count':sum(c['running'] for c in rows),'all_11_healthy':len(rows)==11 and all(c['health']=='healthy' and c['running'] for c in rows),'supervisor_state':state,'containers':rows,'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'observed_at':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())}
print(json.dumps(result))
