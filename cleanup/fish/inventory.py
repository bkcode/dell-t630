#!/usr/bin/env python3
"""Read-only fish inventory for explicit retained guests + stopped template metadata."""
import concurrent.futures,datetime,hashlib,json,re,shlex,sys
from pathlib import Path
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];sys.path.insert(0,str(ROOT/'scripts'));import control
IDS=[190,200,201,210,220,230,240,260];TEMPLATES=[9001,9010,9011]
P=r'''import sys
sys.dont_write_bytecode=True
import os,json,pwd,platform,subprocess,time,hashlib
from pathlib import Path
v=json.loads(sys.stdin.read())
if os.geteuid()!=0 or Path('/etc/pve').exists() or __import__('socket').gethostname().split('.')[0]!=v['hostname']:raise SystemExit('fixed retained guest only')
def call(args):return subprocess.run(args,capture_output=True,text=True,timeout=20)
release={}
for line in Path('/etc/os-release').read_text().splitlines():
 if '=' in line:
  k,val=line.split('=',1)
  if k in ['ID','VERSION_ID','VERSION_CODENAME','PRETTY_NAME']:release[k]=val.strip('"')
users={}
for name in ['ub','root']:
 try:u=pwd.getpwnam(name);users[name]={'uid':u.pw_uid,'shell':u.pw_shell}
 except KeyError:users[name]={'absent':True}
packages={}
for name in ['fish','fish-common']:
 p=call(['dpkg-query','--show','--showformat=${db:Status-Status}\t${Version}\t${Architecture}',name]);parts=p.stdout.strip().split('\t')
 packages[name]={'installed':p.returncode==0 and len(parts)==3 and parts[0]=='installed','version':parts[1] if len(parts)>1 else None,'architecture':parts[2] if len(parts)>2 else None}
 p=call(['apt-cache','-o','Dir::Cache::pkgcache=','-o','Dir::Cache::srcpkgcache=','policy',name]);fields={}
 for line in p.stdout.splitlines():
  line=line.strip()
  if line.startswith(('Installed:','Candidate:')):key,val=line.split(':',1);fields[key.lower()]=val.strip()
 packages[name]['apt_cached_policy']=fields;packages[name]['apt_policy_exit']=p.returncode
 candidate=fields.get('candidate')
 if candidate and candidate!='(none)':
  p=call(['apt-cache','-o','Dir::Cache::pkgcache=','-o','Dir::Cache::srcpkgcache=','show',name+'='+candidate]);meta={}
  for line in p.stdout.splitlines():
   if ':' in line:
    key,val=line.split(':',1)
    if key in ['Package','Version','Architecture','Installed-Size','Size','Depends','Recommends']:meta[key]=val.strip()
  packages[name]['candidate_metadata']=meta
fish_version=None
for binary in ['/usr/bin/fish','/bin/fish']:
 if Path(binary).is_file():
  p=call([binary,'--version']);fish_version=p.stdout.strip() if p.returncode==0 else 'version-check-failed';break
cache=Path('/var/cache/apt/archives');debs=[{'name':p.name,'bytes':p.stat().st_size} for p in cache.glob('fish*.deb')]
lists=[p for p in Path('/var/lib/apt/lists').iterdir() if p.is_file()];mtime=max([p.stat().st_mtime for p in lists],default=None);root=os.statvfs('/');mem=Path('/proc/meminfo').read_text();available=int(next(l.split()[1] for l in mem.splitlines() if l.startswith('MemAvailable:')))*1024
p=call(['systemctl','is-system-running']);osstate=p.stdout.strip()
print(json.dumps({'vmid':v['vmid'],'hostname':v['hostname'],'collected_at':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'OS':release,'architecture':platform.machine(),'login_shells':users,'fish_packages':packages,'fish_binary_version':fish_version,'apt_cache':{'list_regular_files':len(lists),'latest_list_mtime_epoch':mtime,'fish_deb_files':debs,'network_update_run':False,'persistent_pkgcache_generation_disabled':True},'root_disk':{'total_bytes':root.f_blocks*root.f_frsize,'available_bytes':root.f_bavail*root.f_frsize},'memory_available_bytes':available,'systemd_state':osstate,'changes':{'installation':False,'apt_update':False,'chsh':False,'default_shell':False,'services':False}}))
'''
HOST=r'''import json,subprocess,re,hashlib
from pathlib import Path
rows=[]
for vmid in [9001,9010,9011]:
 p=Path('/etc/pve/qemu-server')/(str(vmid)+'.conf');raw=p.read_bytes();config={}
 for line in raw.decode().splitlines():
  if ': ' in line:
   key,value=line.split(': ',1)
   if key in ['name','template','memory','cores','ciuser','ostype','cicustom','ipconfig0','scsi0','ide2','net0']:config[key]=value
 state=subprocess.run(['qm','status',str(vmid)],capture_output=True,text=True,timeout=10)
 row={'vmid':vmid,'status':state.stdout.strip(),'config_SHA256':hashlib.sha256(raw).hexdigest(),'safe_metadata':config,'disk_not_opened_or_mounted':True,'OS_fish_package_shell_live_state':'unknown-stopped-template-no-start'}
 custom=config.get('cicustom','')
 match=re.search(r'(?:^|,)user=([^,]+)',custom)
 if match:
  volume=match[1];path=subprocess.run(['pvesm','path',volume],capture_output=True,text=True,timeout=10)
  if path.returncode==0:
   snippet=Path(path.stdout.strip());data=snippet.read_text();flags={}
   for key in ['ssh_deletekeys','preserve_hostname','hostname','fqdn']:
    found=re.search(r'^'+key+r':\s*([^\n#]+)',data,re.M)
    if found:flags[key]=found[1].strip()
   row['cloud_init_public_identity_flags']=flags;row['user_snippet_SHA256']=hashlib.sha256(snippet.read_bytes()).hexdigest()
 rows.append(row)
print(json.dumps({'templates':rows,'PVE_host_shell_or_packages_read_or_changed':False,'PVE_writes_template_start_or_disk_mount':False}))'''
def main():
 old={x['target']['vmid']:x for x in json.loads((ROOT/'evidence/implementation/private-guest-access.json').read_text())['roles']};new=json.loads((ROOT/'network19/evidence/migrated-access.json').read_text())['targets'];plan=json.loads((ROOT/'plan.json').read_text());roles={x['vmid']:x for x in plan['roles'] if x.get('vmid')};gateway=json.loads((ROOT/'network19/evidence/gateway-initial-access.json').read_text())['target']
 def one(vmid):
  if vmid==190:info=gateway;hostname='network-gateway'
  else:info=new.get(str(vmid),old[vmid]['target']);hostname=roles[vmid]['name']
  result=control.guest(vmid,'sudo -n python3 -I -B -c '+shlex.quote(P),data=json.dumps({'vmid':vmid,'hostname':hostname}).encode(),timeout=100,info=info)
  if result['exit_code']:return {'vmid':vmid,'status':'readonly-inventory-failed','error_category':'SSH-or-readonly-command','details':'withheld; no trust change or retry install'}
  return json.loads(result['stdout'])
 with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:guests=list(pool.map(one,IDS))
 templates=json.loads(control.pve('python3 -I -B -',data=HOST.encode(),timeout=80));out={'schema_version':1,'collected_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'mode':'read-only-preparation','included_running_guests':IDS,'included_stopped_templates':TEMPLATES,'excluded_vmid':[100,250,270,231,232,221],'old_QA_excluded':True,'PVE_host_shell_excluded':True,'default_policy_until_user_reply':'install-only; no shell change or chsh','guests':guests,'templates':templates['templates']}
 (HERE/'inventory.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
 for x in guests:print(json.dumps({'vmid':x['vmid'],'OS':x.get('OS'),'shells':x.get('login_shells'),'fish_installed':x.get('fish_packages',{}).get('fish',{}).get('installed'),'candidate':x.get('fish_packages',{}).get('fish',{}).get('apt_cached_policy',{}).get('candidate'),'root_available_bytes':x.get('root_disk',{}).get('available_bytes'),'memory_available_bytes':x.get('memory_available_bytes'),'status':x.get('status','collected')}))
 print(json.dumps({'template_states':[{'vmid':x['vmid'],'status':x['status'],'identity_flags':x.get('cloud_init_public_identity_flags')} for x in out['templates']],'template_live_packages_unknown':True,'mutations':0}))
if __name__=='__main__':main()
