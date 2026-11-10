#!/usr/bin/env python3
"""Read-only final VM280 state and original NFS mount/config preservation proof."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts'));import control
info=json.loads((ROOT/'completion/20261109-resources/guest-access.json').read_text())['target']
SCRIPT=r'''
import datetime,hashlib,json,os,socket,subprocess
from pathlib import Path
from zoneinfo import ZoneInfo
assert os.geteuid()==0 and socket.gethostname()=='resource-service'and not Path('/etc/pve').exists()
def run(args,allowed=(0,)):
 p=subprocess.run(args,capture_output=True,text=True,timeout=12);assert p.returncode in allowed;return p.stdout.strip()
health=json.loads(Path('/etc/dell-guest-monitoring/health.json').read_text())
units={n:dict(x.split('=',1)for x in run(['systemctl','show',n,'--property=MainPID,ActiveState,SubState,UnitFileState']).splitlines()if'='in x)for n in ['dell-filebrowser.service','dell-filebrowser-firewall.service',*health['services']]}
assert all(units[n]['ActiveState']=='inactive'and units[n]['UnitFileState']=='masked'for n in ['dell-filebrowser.service','dell-filebrowser-firewall.service'])
assert all(units[n]['ActiveState']=='active'for n in health['services'])
assert not health['http_checks']and len(health['services'])==5
assert run(['ss','-H','-lntu','sport = :8080'])==''
assert subprocess.run(['nft','list','table','inet','dell_filebrowser_input'],capture_output=True).returncode!=0
guard=json.loads(run(['python3','-I','-B','/opt/dell/resources/guard.py','--role','server']))
metrics=Path('/var/lib/prometheus/node-exporter-textfile/dell_guest_health.prom').read_text()
assert 'filebrowser'not in metrics
assert all('dell_guest_service_active{role="resource-service",service="'+n+'"} 1'in metrics for n in health['services'])
exports=run(['exportfs','-v']);assert exports.count('/srv/resources')==2 and '192.168.19.40('in exports and '192.168.19.45('in exports and exports.count('root_squash')==2
files={p:hashlib.sha256(Path(p).read_bytes()).hexdigest()for p in ['/etc/exports.d/dell-resources.exports','/etc/nfs.conf.d/90-dell-resources.conf','/etc/dell-resources/input.nft']}
print(json.dumps({'at':datetime.datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),'status':'NFS-only-current-runtime-verified','vmid':280,'units':units,'health':health,'resource_service_metrics_active':5,'FileBrowser_metrics_absent':True,'TCP_UDP_8080_listeners_absent':True,'FileBrowser_owned_table_absent':True,'NFS_guard':guard,'NFS_public_config_SHA256':files,'exports_exact_clients':['192.168.19.40','192.168.19.45'],'root_squash':True,'NFS_versions':Path('/proc/fs/nfsd/versions').read_text().strip(),'NFS_or_resource_mutations':False,'credentials_output':False}))
'''
r=control.guest(280,'sudo -n python3 -',data=SCRIPT.encode(),info=info,timeout=70)
assert r['exit_code']==0,'final-readonly-check-unconfirmed'
d=json.loads(r['stdout']);before=next(x for x in json.loads(Path(__file__).with_name('before-resume.json').read_text())if x['vmid']==280)
assert all(before['public_files'][p]['sha256']==sha for p,sha in d['NFS_public_config_SHA256'].items())
d['NFS_public_config_matches_before']=True
Path(__file__).with_name('final-postcheck.json').write_text(json.dumps(d,indent=2)+'\n')
Path(__file__).with_name('health.nfs-only.json').write_text(json.dumps(d['health'],indent=2)+'\n')
print(json.dumps({k:d[k]for k in ['at','status','resource_service_metrics_active','TCP_UDP_8080_listeners_absent','FileBrowser_metrics_absent','NFS_public_config_matches_before']}))
