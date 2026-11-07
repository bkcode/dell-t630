#!/usr/bin/env python3
"""Export only manager-created new-environment snapshots to approved private Mac fallback."""
from pathlib import Path
import sys,json,shlex,subprocess,os,hashlib,tarfile,datetime
BASE=Path(__file__).resolve().parents[2];sys.path.insert(0,str(BASE/'scripts'));import control
proof=json.loads((BASE/'evidence/implementation/prod-local-application-backups.json').read_text());assert proof['status']=='new-prod-local-application-backups-created'
folder=BASE/'private/backups/app-initial-environment';folder.mkdir(parents=True,exist_ok=True);folder.chmod(0o700);results=[]
for row in proof['results']:
 component=row['component'];assert component in ['nacos','redis','rabbit-topology'];r=row['result'];assert r['exit_code']==0;meta=json.loads(r['stdout']);target=r['target']
 required=200 if component=='nacos' else 201;assert target['vmid']==required
 item={'component':component,'directory':meta['private_directory']}
 code='''import sys,json,re,os,socket,tarfile,hashlib
from pathlib import Path
m=json.load(sys.stdin);expected='data-prod-db' if m['component']=='nacos' else 'data-prod-infra';assert os.geteuid()==0 and socket.gethostname()==expected and not Path('/etc/pve').exists()
assert re.fullmatch('/srv/dell-data/_app_backups/[a-f0-9]{32}',m['directory'])
p=Path(m['directory']);assert p.resolve()==p and not p.is_symlink();s=json.loads((p/'manifest.json').read_text());assert s['component']==m['component'] and s['cf_included'] is False
names={'nacos':'mysql.sql.gz','redis':'redis.rdb','rabbit-topology':'rabbit-definitions.json'};name=names[m['component']];assert set(s['files'])=={name}
for n in ['manifest.json',name]:
 f=p/n;assert f.is_file() and not f.is_symlink() and f.stat().st_uid==0 and not f.stat().st_mode&0o077
assert hashlib.sha256((p/name).read_bytes()).hexdigest()==s['files'][name]
out=p.parent/('export-'+m['component']+'-'+p.name+'.tar.gz');assert not out.exists()
fd=os.open(out,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
with os.fdopen(fd,'wb') as stream,tarfile.open(fileobj=stream,mode='w:gz') as t:
 for n in ['manifest.json',name]:t.add(p/n,arcname=n,recursive=False)
print(json.dumps({'path':str(out),'sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'bytes':out.stat().st_size,'files':s['files']}))
'''
 output=control.guest(required,'sudo python3 -c '+shlex.quote(code),data=json.dumps(item).encode(),info=target);assert output['exit_code']==0,'Snapshot archive preparation failed'
 archive=json.loads(output['stdout']);local=folder/Path(archive['path']).name;assert not local.exists()
 proxy=shlex.join(control.BASE+['-W','%h:%p','root@192.168.21.22']);args=control.BASE+['-o','HostKeyAlias='+target['host_key_alias'],'-o','ProxyCommand='+proxy,'ub@'+target['ip'],'sudo cat '+shlex.quote(archive['path'])]
 fd=os.open(local,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
 with os.fdopen(fd,'wb') as f:result=subprocess.run(args,stdout=f,stderr=subprocess.PIPE,timeout=120)
 assert result.returncode==0 and hashlib.sha256(local.read_bytes()).hexdigest()==archive['sha256'] and local.stat().st_size==archive['bytes']
 with tarfile.open(local,'r:gz') as t:
  members=t.getmembers();assert {x.name for x in members}=={'manifest.json',*archive['files']} and all(x.isfile() for x in members)
  for n,expected in archive['files'].items():assert hashlib.sha256(t.extractfile(n).read()).hexdigest()==expected
 results.append({'component':component,'vmid':required,'local_archive':str(local.relative_to(BASE)),'archive_sha256':archive['sha256'],'bytes':archive['bytes'],'mode':oct(local.stat().st_mode&0o777),'payload_sha256_verified':True})
 receipt={'at':datetime.datetime.now().isoformat(),'status':'initial-new-environment-snapshots-private-Mac-copy-verified','components':results,'scope':'current fresh Nacos metadata/new-target identity hashes, empty Redis RDB, Rabbit definitions only; no credential files/old Mac source identities/CF','restoration_evidence':'infra/backup/full-snapshot-restore/runtime-status.json','limitations':['Rabbit definitions have no messages','Current Redis snapshot is empty','Nacos active config_info empty, 12 tables/10 rows','No full independent-host disaster/RPO/RTO or continuous schedule claim']}
(BASE/'evidence/implementation/prod-initial-private-Mac-backups.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({'status':receipt['status'],'components':len(results),'total_bytes':sum(x['bytes'] for x in results),'CF_included':False}))
