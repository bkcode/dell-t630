#!/usr/bin/env python3
"""QA9012 read-only identity and existing nonroot temporary smoke, no configuration writes."""
import datetime,hashlib,importlib.util,json,shlex,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
s=importlib.util.spec_from_file_location('ctl',ROOT/'scripts/control.py');ctl=importlib.util.module_from_spec(s);s.loader.exec_module(ctl)
CODE=r'''import hashlib,json,os,socket,subprocess
from pathlib import Path
if os.geteuid()!=0 or Path('/etc/pve').exists() or socket.gethostname().split('.')[0]!='java-acceptance-clone-check':raise SystemExit('QA9012 only')
links=json.loads(subprocess.run(['ip','-j','addr'],capture_output=True,check=True).stdout)
if not any(a.get('local')=='192.168.19.198' for x in links for a in x.get('addr_info',[])):raise SystemExit('expected QA address')
status=subprocess.run(['cloud-init','status','--format=json'],capture_output=True,text=True)
if status.returncode:raise SystemExit('cloud-init failed; raw output withheld')
cloud=json.loads(status.stdout)
if cloud.get('status')!='done' or cloud.get('errors'):raise SystemExit('cloud-init incomplete')
key=subprocess.run(['ssh-keygen','-lf','/etc/ssh/ssh_host_ed25519_key.pub'],capture_output=True,text=True,check=True).stdout.split()[1]
file=Path('/usr/local/libexec/dell-java-acceptance/verify.py');smoke=subprocess.run(['runuser','--user','java','--','/usr/bin/python3',str(file),'--smoke'],capture_output=True,text=True,timeout=90)
if smoke.returncode:raise SystemExit('nonroot smoke failed; raw output withheld')
units=subprocess.run(['systemctl','list-unit-files','--type=service','--no-legend','--plain'],capture_output=True,text=True,check=True).stdout.splitlines();bad=[x.split()[0] for x in units if any(word in x.split()[0] for word in ['dell-finger-','nacos','docker','jenkins','dell-publish'])]
result={'hostname':socket.gethostname(),'expected_IP':'192.168.19.198','cloud_init_status':cloud['status'],'cloud_init_errors':cloud.get('errors',[]),'machine_id_sha256':hashlib.sha256(Path('/etc/machine-id').read_bytes()).hexdigest(),'host_ED25519_fingerprint':key,'verify_code_sha256':hashlib.sha256(file.read_bytes()).hexdigest(),'nonroot_acceptance':json.loads(smoke.stdout),'business_units':bad,'no_PVE_or_network_or_service_config_writes':True,'temporary_smoke_files_removed_by_tool':True}
print(json.dumps(result))
if bad:raise SystemExit(1)'''
def main():
 target=json.loads((HERE/'QA-target.json').read_text())['target']
 if target['vmid']!=9012 or target['ip']!='192.168.19.198':raise RuntimeError('root-created QA9012 target required')
 r=ctl.guest(9012,'sudo -n python3 -c '+shlex.quote(CODE),timeout=130,info=target)
 if not r['stdout'].strip():raise RuntimeError('clone verification failed; raw output withheld')
 value=json.loads(r['stdout']);builder=json.loads((HERE/'build-evidence.json').read_text())['result'];build_target=json.loads((ROOT/'network19/evidence/java-build-target.json').read_text())['target'];checks={'exit0':r['exit_code']==0,'hostname_from_explicit_instance_profile':value['hostname']=='java-acceptance-clone-check','unique_machine_id_vs_builder':value['machine_id_sha256']!=builder['machine_id_sha256'],'unique_hostkey_vs_builder':value['host_ED25519_fingerprint']!=build_target['host_key_fingerprint'],'hostkey_matches_root_QGA_trust':value['host_ED25519_fingerprint']==target['host_key_fingerprint'],'generic_verify_sha_preserved':value['verify_code_sha256']==hashlib.sha256((HERE/'verify.py').read_bytes()).hexdigest(),'java21_nonroot_smoke':value['nonroot_acceptance']['status']=='java21-clean-nonroot-acceptance-passed' and value['nonroot_acceptance']['uid']!=0,'no_business_units':not value['business_units'],'no_business_or_exporter_listeners':not value['nonroot_acceptance']['business_or_exporter_listeners'],'exporter_parked':value['nonroot_acceptance']['exporter_parked']}
 report={'at':datetime.datetime.now().astimezone().isoformat(),'scope':'only9012-readonly-plus-temporary-nonroot-smoke','status':'QA9012-identity-and-JDK-cleanliness-passed' if all(checks.values()) else 'failed','target':target,'checks':checks,'result':value,'released_after_this_action':True};(HERE/'clone-evidence.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report));return 0 if all(checks.values()) else 1
if __name__=='__main__':raise SystemExit(main())
