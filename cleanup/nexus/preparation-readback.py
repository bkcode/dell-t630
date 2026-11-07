#!/usr/bin/env python3
"""Readonly preparation facts, public file SHAs and private-mode booleans only."""
import concurrent.futures,json,sys
from pathlib import Path
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];sys.path.insert(0,str(ROOT/'scripts'));import control
control.BASE+=['-o','ForwardAgent=no'];targets=json.loads((ROOT/'network19/evidence/migrated-access.json').read_text())['targets'];nonce=json.loads((HERE/'standby-window.json').read_text())['nonce']
SCRIPT=r'''
import hashlib,json,os,socket,stat,subprocess
from pathlib import Path
ROLE=ROLE_ID;NONCE=NONCE_VALUE
assert os.geteuid()==0 and socket.gethostname().split('.')[0]=={220:'publish-service',221:'artifact-service'}[ROLE] and not Path('/etc/pve').exists()
D=['/usr/bin/docker','--host','unix:///var/run/docker.sock']
def run(args):return subprocess.check_output(args,text=True,timeout=30)
out={'role':ROLE,'status':'readonly-prepare-final-metadata','OS_hostname':socket.gethostname(),'physical_ipv4':[{ 'name':x['ifname'],'IPs':[a['local'] for a in x.get('addr_info',[]) if a['family']=='inet']} for x in json.loads(run(['/usr/sbin/ip','-j','addr'])) if x['ifname']=='eth0']}
if ROLE==220:
 out['changed_public_files_SHA']={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in map(Path,['/etc/apt/sources.list.d/docker.sources','/etc/apt/keyrings/docker.asc','/etc/docker/daemon.json','/opt/dell/cleanup/nexus/target.py','/opt/dell/cleanup/nexus/relocate.py'])}
 base=Path('/root/dell-nexus-merge')/NONCE
 out['private_standby_dirs_root700']=all(p.is_dir() and p.stat().st_uid==0 and stat.S_IMODE(p.stat().st_mode)==0o700 for p in [base,base/'incoming',base/'prepared'])
 out['all_standby_files_root600']=all(p.stat().st_uid==0 and stat.S_IMODE(p.stat().st_mode)==0o600 for folder in [base/'incoming',base/'prepared'] for p in folder.iterdir())
 j=json.loads((base/'relocation.json').read_text());out['phase']=j['phase'];out['env_and_three_secrets_byte_preserved']=all(v['source_unchanged'] for k,v in j['entries'].items() if k.startswith(('env/','secret/')))
 out['Nexus_active_paths_absent']=all(not Path(p).exists() for p in ['/opt/dell/nexus','/etc/nexus.env','/root/dell-nexus-secrets','/etc/systemd/system/dell-nexus.service'])
 key=Path('/var/lib/dell-publisher/.ssh/test240_ed25519').stat();out['publisher_key_metadata_only']={'uid':key.st_uid,'gid':key.st_gid,'mode':stat.S_IMODE(key.st_mode),'size':key.st_size,'inode':key.st_ino,'mtime_ns':key.st_mtime_ns,'ctime_ns':key.st_ctime_ns}
 out['publisher_groups']=run(['/usr/bin/id','publisher']).strip()
 out['container_count']=int(run(D+['info','--format','{{.Containers}}']).strip())
else:
 out['containers']=[json.loads(run(D+['inspect','--format','{"name":{{json .Name}},"id":{{json .Id}},"image":{{json .Image}},"running":{{json .State.Running}},"health":{{if .State.Health}}{{json .State.Health.Status}}{{else}}null{{end}}}',name])) for name in ['nexus-nexus-1','nexus-gateway-1']]
 out['source_mutations_performed']=False
print(json.dumps(out))
'''
def one(role):
 code=SCRIPT.replace('ROLE_ID',str(role)).replace('NONCE_VALUE',repr(nonce));res=control.guest(role,'sudo /usr/bin/python3 -I -B -',data=code.encode(),timeout=90,info=targets[str(role)])
 if res['exit_code']:return {'role':role,'status':'readonly-readback-unconfirmed'}
 return json.loads(res['stdout'])
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:values=list(pool.map(one,[220,221]))
(HERE/'preparation-readback.json').write_text(json.dumps(values,indent=2)+'\n')
for value in values:print(json.dumps({'role':value['role'],'status':value['status']}))
