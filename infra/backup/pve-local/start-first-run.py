#!/usr/bin/python3
"""Start a bounded server-side first backup run; never tie it to a short SSH timeout."""
import os,socket,json,pathlib,subprocess,datetime
assert os.geteuid()==0 and socket.gethostname()=='pve' and pathlib.Path('/etc/pve').is_dir()
p=json.loads(pathlib.Path('/etc/dell-local-backup/policy.json').read_text());job=json.loads(subprocess.check_output(['pvesh','get','/cluster/backup/'+p['job_id'],'--output-format','json']));assert job['enabled']==0 and job['mode']=='snapshot' and job['vmid']==','.join(map(str,p['allowed_vmids'])) and job['tmpdir']==p['tmpdir']
active=json.loads(subprocess.check_output(['pvesh','get','/nodes/pve/tasks','--source','active','--typefilter','vzdump','--output-format','json']));assert not active
base=pathlib.Path('/root/dell-bootstrap/completion-20261109/pve-local-backup');log=base/'first-run-retry.log';assert not log.exists();log.touch(mode=0o600)
args=['/usr/bin/vzdump',job['vmid'],'--job-id',p['job_id'],'--storage',p['storage_id'],'--mode','snapshot','--compress','zstd','--zstd','2','--bwlimit',str(p['bwlimit_KiB_per_second']),'--ionice','7','--performance','max-workers=1','--tmpdir',p['tmpdir'],'--lockwait','0','--script','/usr/local/libexec/dell-local-backup/hook.py','--notification-mode','legacy-sendmail','--mailto','','--remove','0']
cmd=['systemd-run','--unit=dell-local-backup-first-retry','--property=Type=exec','--property=UMask=0022','--property=Nice=10','--property=RuntimeMaxSec=21600','--property=StandardOutput=append:'+str(log),'--property=StandardError=append:'+str(log),*args]
r=subprocess.run(cmd,capture_output=True,text=True,timeout=20);assert r.returncode==0,'Server-side backup unit failed to start; inspect protected log'
result={'at':datetime.datetime.now().astimezone().isoformat(),'status':'first-run-started-in-server-side-transient-unit','unit':'dell-local-backup-first-retry.service','VMs':p['allowed_vmids'],'excluded':[220],'schedule_enabled':False,'server_log':str(log),'max_runtime_seconds':21600,'mode':'snapshot','remove_old_backups':False};q=base/'server-first-run-retry.json';q.write_text(json.dumps(result,indent=2)+'\n');q.chmod(0o600);print(json.dumps(result))
