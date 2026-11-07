#!/usr/bin/env python3
from pathlib import Path
import argparse,subprocess,json,hashlib,socket,os,re
p=argparse.ArgumentParser();p.add_argument('--role',required=True);p.add_argument('--archive',required=True);p.add_argument('--sha256',required=True);p.add_argument('--expected-id',action='append',default=[]);p.add_argument('--reference',action='append',default=[]);a=p.parse_args()
assert os.geteuid()==0 and not Path('/etc/pve').exists() and socket.gethostname()==a.role
assert a.role in ['data-prod-db','data-prod-infra','data-test','artifact-service','penpot-service','ops-service','nas-media']
allowed=['target-amd64-data-images.tar','target-amd64-penpot-images.tar','target-amd64-nexus-images.tar','target-amd64-extras-images.tar','custom-penpot-amd64-images.tar']
assert a.archive in allowed and re.fullmatch('[0-9a-f]{64}',a.sha256)
docker=['docker','--host','unix:///var/run/docker.sock']
info=json.loads(subprocess.check_output(docker+['info','--format','{{json .}}'],text=True));assert info['Name']==a.role and info['OSType']=='linux' and info['Architecture'] in ['x86_64','amd64'] and info['Containers']==0
source=Path('/dev/disk/by-label/DELL_ARTIFACTS');assert source.exists()
mount=Path('/mnt/dell-artifacts');mount.mkdir(exist_ok=True);assert mount.resolve()==mount
if subprocess.run(['mountpoint','-q',str(mount)]).returncode:subprocess.run(['mount','-t','udf','-o','ro,nodev,nosuid,noexec',str(source),str(mount)],check=True,capture_output=True)
fs=json.loads(subprocess.check_output(['findmnt','-J','-M',str(mount),'-o','TARGET,OPTIONS'],text=True))['filesystems'][0];assert 'ro' in fs['options'].split(',')
archive=mount/'amd64'/a.archive;h=hashlib.sha256()
with archive.open('rb') as f:
 for part in iter(lambda:f.read(1024*1024),b''):h.update(part)
assert h.hexdigest()==a.sha256,'Public archive checksum mismatch'
result=subprocess.run(docker+['load','--platform','linux/amd64','--input',str(archive)],capture_output=True,text=True)
if result.returncode:raise RuntimeError('Image load failed; no application started')
verified=[]
for expected in a.expected_id:
 assert re.fullmatch('sha256:[0-9a-f]{64}',expected)
 image=json.loads(subprocess.check_output(docker+['image','inspect',expected],text=True))[0]
 assert image['Id']==expected and image['Architecture']=='amd64' and image['Os']=='linux';verified.append(expected)
aliases={}
for reference in a.reference:
 assert '@sha256:' in reference
 r=subprocess.run(docker+['image','inspect',reference],capture_output=True,text=True)
 aliases[reference]=r.returncode==0
assert not subprocess.check_output(docker+['ps','-aq'],text=True).strip()
print(json.dumps({'status':'images-preloaded-no-containers','role':a.role,'archive':a.archive,'sha256':a.sha256,'verified_image_ids':verified,'registry_reference_available':aliases,'applications_started':False,'image_load_stdout':result.stdout[-1500:]}))
