import concurrent.futures,json,sys
from pathlib import Path
root=Path(__file__).resolve().parents[2];sys.path.insert(0,str(root/'scripts'));import control
folder=root/'completion/20261110-filebrowser-remove';known=json.loads((root/'evidence/implementation/private-guest-access.json').read_text())['roles'];info={x['target']['vmid']:x['target']for x in known if x.get('target',{}).get('vmid')in [230,240]}
def one(v):
 code="import json,subprocess; print(json.dumps({'vmid':"+str(v)+",'guard':json.loads(subprocess.check_output(['python3','-I','-B','/opt/dell/resources/guard.py','--role','client-"+str(v)+"'])),'mount':json.loads(subprocess.check_output(['findmnt','-J','--mountpoint','/mnt/resources','-t','nfs4','-o','TARGET,SOURCE,FSTYPE,OPTIONS']))['filesystems']}))"
 r=control.guest(v,'sudo -n python3 -',data=code.encode(),info=info[v],timeout=50);assert r['exit_code']==0;d=json.loads(r['stdout']);assert d['guard']['mount_guard']and len(d['mount'])==1 and d['mount'][0]['source']=='192.168.19.80:/';return d
with concurrent.futures.ThreadPoolExecutor(max_workers=2)as pool:rows=list(pool.map(one,[230,240]))
(folder/'clients-postcheck.json').write_text(json.dumps({'status':'both-existing-NFS-mounts-verified','clients':rows,'client_writes_or_restarts':False,'Nexus_operations':False},indent=2)+'\n');print(json.dumps(rows))
