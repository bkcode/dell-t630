#!/usr/bin/env python3
"""Root-created disposable QA clone: metadata-only verification plus disposable smoke."""
import argparse,datetime,hashlib,json,os,pwd,socket,stat,subprocess,sys,tempfile
from pathlib import Path
sys.dont_write_bytecode=True
class Refused(RuntimeError):pass
def require(x,message):
 if not x:raise Refused(message)
def run(args):
 p=subprocess.run(args,capture_output=True,text=True,timeout=90);require(p.returncode==0,'fixed-check-failed');return p.stdout

def verify(c):
 require(c.get('purpose')=='fish-template-independent-QA' and c.get('source_template') in [9001,9010,9011],'explicit-independent-QA-contract')
 require(c.get('candidate_vmid')=={9010:9040,9001:9041,9011:9042}[c['source_template']],'actual-candidate-source-required')
 require(c.get('vmid') not in [100,190,200,201,210,220,221,230,231,232,240,250,260,270,9001,9010,9011,9040,9041,9042] and c.get('hostname','').startswith('fish-qa-'),'QA-only-target')
 for field in ['forbidden_machine_id_sha256','forbidden_hostkey_fingerprints']:
  require(isinstance(c.get(field),list) and len(c[field])>=1,'builder-identity-baseline-required')
 expected_files={9001:{'/etc/docker/daemon.json'},9010:set(),9011:{'/usr/local/libexec/dell-java-acceptance/verify.py'}}[c['source_template']]
 require(set(c.get('protected_files',{}))==expected_files,'exact-source-protected-file-contract')
 if c['source_template']==9001:require(isinstance(c.get('forbidden_engine_id_sha256'),list) and len(c['forbidden_engine_id_sha256'])>=1,'builder-Docker-ID-baseline-required')
 require(os.geteuid()==0 and not Path('/etc/pve').exists() and socket.gethostname().split('.')[0]==c['hostname'],'exact-root-QA-guest')
 links=json.loads(run(['ip','-j','addr']));rows=[x for x in links if x.get('address','').lower()==c['mac']];require(len(rows)==1 and [x['local'] for x in rows[0].get('addr_info',[]) if x.get('family')=='inet']==[c['ip']],'exact-QA-MAC-IP')
 ci=json.loads(run(['cloud-init','status','--format=json']));require(ci.get('status')=='done' and not ci.get('errors'),'cloudinit-not-done')
 shells={n:pwd.getpwnam(n).pw_shell for n in ['ub','root']};require(shells==c['expected_shells'],'default-shell-not-preserved')
 for package in ['fish','fish-common']:require(run(['dpkg-query','-W','-f=${Version}',package])=='4.0.2-1','exact-fish-version-required')
 ub=pwd.getpwnam('ub')
 with tempfile.TemporaryDirectory(prefix='dell-fish-QA-') as tmp:
  base=Path(tmp);os.chown(base,ub.pw_uid,ub.pw_gid)
  for n in ['config','data','cache']:(base/n).mkdir(mode=0o700);os.chown(base/n,ub.pw_uid,ub.pw_gid)
  require(run(['runuser','--user','ub','--','env','XDG_CONFIG_HOME='+tmp+'/config','XDG_DATA_HOME='+tmp+'/data','XDG_CACHE_HOME='+tmp+'/cache','fish','--no-config','--private','-c','printf fish-smoke-ok'])=='fish-smoke-ok','nonconfig-fish-smoke-failed')
 machine=hashlib.sha256(Path('/etc/machine-id').read_bytes()).hexdigest();key=run(['ssh-keygen','-lf','/etc/ssh/ssh_host_ed25519_key.pub']).split()[1]
 require(machine not in c['forbidden_machine_id_sha256'] and key not in c['forbidden_hostkey_fingerprints'],'clone-identity-not-unique')
 require(key==c['trusted_hostkey_fingerprint'],'QGA-trusted-key-mismatch')
 for path,expected in c.get('protected_files',{}).items():require(hashlib.sha256(Path(path).read_bytes()).hexdigest()==expected,'protected-file-mismatch')
 require(not any(Path('/root').glob('dell-fish-template-stage-*')) and not any(Path('/root').glob('dell-fish-builder-*.json')),'builder-tools-or-receipt-leaked')
 require(not any(Path(x).exists() for x in ['/opt/finger','/etc/nacos','/var/lib/mysql','/opt/dell/ops','/etc/penpot','/var/lib/dell-publisher']),'business-state-present')
 extra={}
 if c['source_template']==9001:
  docker=['docker','--host','unix:///var/run/docker.sock'];info=json.loads(run(docker+['info','--format','{{json .}}']));engine=hashlib.sha256(info['ID'].encode()).hexdigest();require(engine not in c['forbidden_engine_id_sha256'],'Docker-engine-identity-reused');require(info['Containers']==0 and not run(docker+['volume','ls','-q']).strip() and not run(docker+['image','ls','-q']).strip() and sorted(run(docker+['network','ls','--format','{{.Name}}']).split())==['bridge','host','none'] and info.get('Swarm',{}).get('LocalNodeState')=='inactive' and info['Driver']=='overlayfs' and info['DockerRootDir']=='/var/lib/docker' and info['LiveRestoreEnabled'] is True,'Docker-baseline-failed');extra={'engine_id_sha256':engine,'driver':info['Driver'],'live_restore':info['LiveRestoreEnabled'],'original_profile_preserved':True,'zero_containers_volumes_images_default_networks_inactive_swarm':True}
 if c['source_template']==9011:
  extra['java']=json.loads(run(['runuser','--user','java','--','python3','/usr/local/libexec/dell-java-acceptance/verify.py','--smoke']));require(extra['java']['uid']==999 and extra['java']['exporter_parked'],'Java-baseline-failed')
 return {'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'vmid':c['vmid'],'logical_final_template':c['source_template'],'actual_candidate_source_vmid':c['candidate_vmid'],'status':'QA-checks-passed','machine_id_sha256':machine,'hostkey_fingerprint':key,'shells':shells,'cloud_init':'done','fish':'4.0.2-1','extra':extra,'no_network_package_service_config_writes':True,'temporary_nonroot_smoke_removed':True,'new_strict_SSH_connection_still_required_by_caller':True}
def main():
 p=argparse.ArgumentParser();p.add_argument('--contract',required=True);a=p.parse_args();path=Path(a.contract);st=path.lstat();require(stat.S_ISREG(st.st_mode) and st.st_uid==0 and stat.S_IMODE(st.st_mode)==0o600,'root600-QA-contract-required');print(json.dumps(verify(json.loads(path.read_text()))))
if __name__=='__main__':
 try:main()
 except Exception as e:print(json.dumps({'status':'refused-or-failed','category':type(e).__name__,'reason':str(e) if isinstance(e,Refused) else 'details-withheld'}));sys.exit(1)
