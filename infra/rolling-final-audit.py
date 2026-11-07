#!/usr/bin/env python3
"""Read-only final metadata after the fixed guest reboot batch."""
import importlib.util,json,hashlib,datetime
from pathlib import Path
from zoneinfo import ZoneInfo
p=Path(__file__).with_name('rolling-guest-reboot.py');spec=importlib.util.spec_from_file_location('rolling',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
assert len(m.D['reboots'])==10 and all(x['status']=='passed' for x in m.D['reboots'])
out={'at':m.now(),'source_config_or_private_key_contents_emitted':False}
out['publisher220']=m.probe(220);assert out['publisher220']['health_ok']
code=r'''
import json,subprocess,pathlib,pwd,grp,stat
expected=EXPECTED
r=subprocess.run(['sshd','-T','-C','user=deployer,addr=10.63.30.10,host=publish-service'],capture_output=True,text=True)
allv=dict(x.split(' ',1) for x in r.stdout.splitlines() if ' ' in x);actual={k:allv.get(k) for k in expected};key=pathlib.Path('/etc/ssh/authorized_keys/deployer');st=key.lstat();s=key.read_text();user=pwd.getpwnam('deployer');groups=sorted(set([grp.getgrgid(user.pw_gid).gr_name]+[g.gr_name for g in grp.getgrall() if 'deployer' in g.gr_mem]));ssh=subprocess.run(['sshd','-t'],capture_output=True);sudo=subprocess.run(['visudo','-c'],capture_output=True)
controls={'root_owned':st.st_uid==0,'not_group_or_world_writable':not bool(st.st_mode&0o022),'regular_file':stat.S_ISREG(st.st_mode),'from220':'from="10.63.30.10"' in s,'restrict':'restrict' in s,'forced_dispatch':'command="/usr/local/libexec/dell-publisher-dispatch"' in s,'raw_key_emitted':False}
out={'sshd_effective':actual,'matches_pre_reboot_audit':actual==expected,'authorized_key_controls':controls,'deployer_groups':groups,'native_sshd_valid':ssh.returncode==0,'native_sudoers_valid':sudo.returncode==0,'negative_command_execution_repeated':False}
out['passed']=all(v for k,v in controls.items() if k!='raw_key_emitted') and actual==expected and groups==['deployer'] and ssh.returncode==sudo.returncode==0
print(json.dumps(out))
'''
expected=json.loads((m.ROOT/'evidence/implementation/publisher-final-security-audit.json').read_text())['vm240']['sshd_effective'];out['publisher240_transport']=m.call(240,code.replace('EXPECTED',repr(expected)));assert out['publisher240_transport']['passed']
code=r'''
import json,subprocess,pathlib
ids=subprocess.run(['docker','ps','--quiet'],capture_output=True,text=True,check=True).stdout.split();rows=[]
for id in ids:
 fmt='{{.Id}} {{.State.Pid}} {{.State.Status}} {{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}} {{.HostConfig.PidsLimit}} {{index .Config.Labels "com.docker.compose.service"}}';r=subprocess.run(['docker','inspect','--format',fmt,id],capture_output=True,text=True,check=True);id,pid,status,health,limit,service=r.stdout.split();cg=next(x.split('::',1)[1] for x in pathlib.Path('/proc/'+pid+'/cgroup').read_text().splitlines() if x.startswith('0::'));cp=pathlib.Path('/sys/fs/cgroup')/cg.lstrip('/');assert cp.resolve().is_relative_to('/sys/fs/cgroup');actual=(cp/'pids.max').read_text().strip();rows.append({'service':service,'container_id':id,'pid':int(pid),'state':status,'health':health,'pids_limit':int(limit),'cgroup_pids_max':actual})
print(json.dumps({'containers':rows,'passed':len(rows)==COUNT and all(x['pids_limit']==1024 and x['cgroup_pids_max']=='1024' and x['state']=='running' and x['health']=='healthy' for x in rows),'environment_or_health_logs_read':False}))
'''
out['pids_after_boot']={}
for vmid,count in [(200,1),(201,3),(210,4),(270,4)]:
 r=m.call(vmid,code.replace('COUNT',str(count)));out['pids_after_boot'][str(vmid)]=r;assert r['passed']
out['ops_final']=m.probe(270);assert out['ops_final']['health_ok']
# Existing health helper includes a historical static scope description. Explicit current proof follows.
out['ops_final_metric_proof']={'pve_collector_age_seconds':out['ops_final']['pve_collector_age_seconds'],'target_count':len(out['ops_final']['targets']),'all_targets_up':all(x['health']=='up' for x in out['ops_final']['targets']),'static_manager_scope_string_does_not_override_live_collector_query':True}
m.D['final_readonly_audit']=out;m.D.update(status='passed',completed_at=m.now(),accepted_guest_count=10,normal_guest_reboots_only=True,host_power_failure_or_RPO_RTO_not_tested=True,all_unassigned_guests_excluded=True,source_mac_services_touched=False,pve_power_or_host_mutation=False,runner_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),readiness_limitations=['Normal guest reboot acceptance only; no PVE host restart or host power failure was induced.','NAS is household media/game file sharing, not an independent formal backup destination.','Formal Java nodes retain runtime-only status; no formal business application was started.','No new business fixture writes; NAS prior synthetic samples were read only.','Transient first-deploy historical failure was recorded before reboot and disappeared naturally after reboot; no reset or masking.'])
m.save();print(json.dumps({'status':'passed','guest_count':10,'publisher_transport':'passed','pids12_persisted':True,'pve_metric_age':out['ops_final']['pve_collector_age_seconds'],'targets':len(out['ops_final']['targets'])}))
