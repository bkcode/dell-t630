import json,subprocess,hashlib
from pathlib import Path
nonce='b5b52c6b0565410ba9c510728ba13f54';work=Path('/var/lib/dell-nas-sys001')/nonce;m=json.loads((work/'manifest.json').read_text());D=['docker','--host','unix:///var/run/docker.sock']
def run(a):return subprocess.run(a,capture_output=True,text=True,timeout=20)
fmt='{{.Id}}|{{.State.Status}}|{{.State.StartedAt}}|{{.State.FinishedAt}}|{{.State.ExitCode}}|{{.State.OOMKilled}}|{{.RestartCount}}'
p=run(D+['inspect','--format',fmt,m['container']]);v=p.stdout.strip().split('|')
if p.returncode or len(v)!=7:print(json.dumps({'status':'not-proven','safe_reason':'QA-metadata-read-failed'}));raise SystemExit(1)
c=dict(zip(['id','status','StartedAt','FinishedAt','exit_code','OOM','restart_count'],v))
p=run(['systemctl','show',m['unit'],'--property=ActiveState,SubState,Result,ExecMainStartTimestamp,ExecMainExitTimestamp,ExecMainStatus']);unit=dict(l.split('=',1) for l in p.stdout.splitlines() if '=' in l)
p=run(['/usr/local/libexec/dell-nas-check-data','--mountpoint',m['mount'],'--uuid',m['uuid'],'--minimum-gib','1']);guard_rc=p.returncode;g=json.loads(p.stdout)
p=run(['journalctl','--unit',m['unit'],'--since','2026-11-06 06:49:50 UTC','--output=json','--no-pager']);guard_records=[]
for line in p.stdout.splitlines():
 try:
  row=json.loads(line);message=json.loads(row.get('MESSAGE',''))
  if isinstance(message,dict) and message.get('status')=='passed' and message.get('filesystem_uuid')==m['uuid']:guard_records.append({'timestamp':row.get('__REALTIME_TIMESTAMP'),'guard_passed_same_QA_UUID':True})
 except (ValueError,TypeError):pass
canary=hashlib.sha256((Path(m['mount'])/'QA-volume-canary').read_bytes()).hexdigest()==m['volume_canary_sha256'];real={}
for n in ['openmediavault-engined.service','smbd.service','dell-nas-jellyfin.service']:
 p=run(['systemctl','show',n,'--property=MainPID,ActiveState,SubState']);real[n]=dict(x.split('=',1) for x in p.stdout.splitlines() if '=' in x)
checks={'same_A_container_id':c['id']==m['A']['container_id'],'old_StartedAt_before_C_request':c['StartedAt']<'2026-11-06T06:50:00','old_FinishedAt_before_C_request':c['FinishedAt']<'2026-11-06T06:50:00','OOM_false':c['OOM']=='false','no_container_restart':c['restart_count']=='0','C_unit_start_after_old_container_stop':'06:50:' in unit.get('ExecMainStartTimestamp',''),'C_execpre_guard_pass_record':bool(guard_records),'same_QA_UUID_current_guard_exit0':guard_rc==0 and g.get('status')=='passed','same_volume_canary':canary,'real_unit_PIDs_unchanged':real==m['baseline']['units']}
print(json.dumps({'status':'race-proven' if all(checks.values()) else 'not-proven','checks':checks,'QA_container':c,'QA_unit':unit,'C_guard_records':guard_records,'current_guard_exit':guard_rc,'current_guard':g,'nonce':nonce,'cleanup_not_started':work.exists(),'source_logs_or_random_keys_emitted':False}))
