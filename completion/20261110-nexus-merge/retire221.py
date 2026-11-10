#!/usr/bin/env python3
"""Remove only the verified stopped former Nexus VM, never the reassigned data disk."""
import hashlib,json,os,subprocess
from pathlib import Path
assert os.geteuid()==0 and Path('/etc/pve').exists()
def run(args):return subprocess.check_output(args,stderr=subprocess.PIPE,timeout=120).decode().strip()
assert run(['qm','status','221'])=='status: stopped'
source=run(['qm','config','221']);dest=run(['qm','config','220']);assert 'scsi1:'not in source and 'store:220/'not in source and 'store:220/vm-220-disk-2.qcow2'in dest
assert 'name: artifact-service'in source and 'scsi0: store:221/vm-221-disk-0.qcow2'in source
state=json.loads(Path('/root/dell-bootstrap/nexus-merge-20261110/backup-current.json').read_text());assert state['status']=='verified' and state['zstd_test']and state['VMA_full_verify'];p=Path(state['archive']);assert p.stat().st_size==state['bytes']and p.stat().st_mode&0o777==0o600
with p.open('rb')as stream:assert hashlib.file_digest(stream,'sha256').hexdigest()==state['sha256']
folder=Path('/root/dell-bootstrap/nexus-merge-20261110');q=folder/'vm221-before-final-retirement.conf';assert not q.exists();q.write_text(source);q.chmod(0o600)
help_result=subprocess.run(['qm','help','destroy'],capture_output=True,text=True);assert '--destroy-unreferenced-disks'in(help_result.stdout+help_result.stderr)
run(['qm','destroy','221','--purge','1','--destroy-unreferenced-disks','0'])
resources=json.loads(run(['pvesh','get','/cluster/resources','--type','vm','--output-format','json']));assert all(x['vmid']!=221 for x in resources)
assert 'store:220/vm-220-disk-2.qcow2'in run(['qm','config','220']) and run(['qm','status','220'])=='status: running' and p.exists()
result={'status':'former-artifact-service-VM221-removed','vmid':221,'PVE_VM221_record_absent':True,'Nexus_live_data_disk_on220_preserved':True,'publisher220_running':True,'source_OS_disk_removed_after_full_data_auth_reboot_monitoring_verification':True,'cold_backup_PVE_only_retained':True,'cold_backup_bytes':state['bytes'],'cold_backup_mode':'0600','automatic_backup_scope_changed':False,'other_VMs_removed':False}
(folder/'retirement-result.json').write_text(json.dumps(result));(folder/'retirement-result.json').chmod(0o600);print(json.dumps(result))
