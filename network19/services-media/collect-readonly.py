#!/usr/bin/env python3
"""Only explicitly allowed active-file metadata, public keys and wired NAS model fields."""
import concurrent.futures,json,sys
sys.dont_write_bytecode=True
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts'));import control
control.BASE+=['-o','ForwardAgent=no']
rows=json.loads((ROOT/'evidence/implementation/private-guest-access.json').read_text())['roles'];targets={r['target']['vmid']:r['target'] for r in rows}
SCRIPT=r'''
import datetime,hashlib,json,os,re,socket,subprocess,urllib.parse
from pathlib import Path
import xml.etree.ElementTree as ET
ROLE=NUMBER
EXPECTED={250:'penpot-service',221:'artifact-service',260:'nas-media'}
if os.geteuid()!=0 or Path('/etc/pve').exists() or socket.gethostname().split('.')[0]!=EXPECTED[ROLE]:raise SystemExit('assigned media guest only')
ENV={'PATH':'/usr/sbin:/usr/bin:/sbin:/bin','LANG':'C','LC_ALL':'C'}
def cmd(args):
 p=subprocess.run(args,capture_output=True,text=True,env=ENV,timeout=25)
 if p.returncode:raise RuntimeError('read-only metadata command failed')
 return p.stdout
def env_public(path,keys):
 values={}
 for line in Path(path).read_text().splitlines():
  if not line or line.startswith('#') or '=' not in line:continue
  k,v=line.split('=',1)
  if k in keys:
   v=v.strip().strip("'\"")
   if '://' in v:
    u=urllib.parse.urlsplit(v)
    if u.username or u.password or u.query or u.fragment:raise RuntimeError('public endpoint unexpectedly contains private/query material')
   values[k]=v
 return values
def public_metadata(path):
 p=Path(path);s=p.stat();return {'path':path,'uid':s.st_uid,'gid':s.st_gid,'mode':oct(s.st_mode&0o777),'bytes':s.st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
out={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'role':ROLE,'hostname':socket.gethostname(),'read_only':True,'secret_or_full_config_emitted':False}
if ROLE==250:
 b=Path('/opt/dell/penpot');here=b/'runtime/health-supervision';out['public_env']=env_public('/etc/penpot/.env',{'PENPOT_PUBLIC_URI'})
 paths=[b/'assignment.json',b/'compose.fresh.yaml',b/'application/target-api.py',here/'supervisor.py',here/'node-health.mjs',here/'deployment-lock.json']
 out['public_file_metadata']=[public_metadata(str(p)) for p in paths]
 lock=json.loads((here/'deployment-lock.json').read_text());out['locked_guest']=lock['guest'];out['locked_storage']=lock['storage'];out['locked_git']=lock['Git'];out['11_image_ids']={k:v['image_id'] for k,v in lock['services'].items()}
 out['selector_counts']={'supervisor_old_ip':(here/'supervisor.py').read_text().count("'10.63.30.30'"),'admin_health_old_origin':(here/'node-health.mjs').read_text().count('http://192.168.21.22:9001'),'frontend_literal_0_bind':(b/'compose.fresh.yaml').read_text().count('    - 0.0.0.0:9001:8080\n'),'owner_loopback_origin':(b/'application/target-api.py').read_text().count("ORIGIN = 'http://127.0.0.1:9001'")}
 out['fresh_marker_keys']=sorted(json.loads(Path('/etc/penpot/fresh-instance.json').read_text()))
 out['public_hash_locks_match']=all(hashlib.sha256((prefix/rel).read_bytes()).hexdigest()==digest for group,prefix in [('package_file_sha256',b),('supervision_file_sha256',here)] for rel,digest in lock[group].items())
elif ROLE==221:
 b=Path('/opt/dell/nexus');out['public_env']=env_public('/etc/nexus.env',{'NEXUS_BIND_ADDRESS','NEXUS_DATA_DIR'})
 out['public_file_metadata']=[public_metadata(str(b/p)) for p in ['assignment.json','application-import.py','manage.py','target_guard.py']]
 marker=json.loads((b/'fresh-instance.json').read_text());out['fresh_marker']={k:marker[k] for k in ['mode','expected_guest_ip','expected_hostname','filesystem_uuid','old_h2_or_credentials_imported']}
 out['importer_loopback_origin_count']=(b/'application-import.py').read_text().count("ORIGIN = 'http://127.0.0.1:8081'")
else:
 b=Path('/srv/dev-disk-by-uuid-5b19837c-128c-498a-b79d-563db810c34a/appdata/jellyfin/config')
 out['public_env']=env_public('/opt/dell/nas/.env',{'NAS_BIND_IP','JELLYFIN_PUBLIC_URL','NAS_MOUNT','NAS_DATA_UUID','JELLYFIN_UID','JELLYFIN_GID'})
 p=b/'config/network.xml';out['network_xml_exists']=p.exists()
 if p.exists():
  tree=ET.fromstring(p.read_bytes());out['network_xml_metadata']=public_metadata(str(p));out['JF_network_structure']={x.tag:[c.tag for c in x] if list(x) else None for x in tree}
  out['JF_public_network_fields']={k:[x.text for x in tree.find(k)] if list(tree.find(k)) else tree.find(k).text for k in ['LocalNetworkSubnets','EnableRemoteAccess','EnableUPnP'] if tree.find(k) is not None}
 raw=cmd(['/usr/sbin/omv-confdbadm','read','--prettify','conf.system.network.interface']);data=json.loads(raw);data=data if isinstance(data,list) else [data]
 selected=[x for x in data if x.get('devicename')=='ens18']
 if len(selected)!=1:raise RuntimeError('NAS wired OMV object ambiguous')
 public_keys={'uuid','devicename','method','address','netmask','gateway','method6','address6','netmask6','gateway6','routemetric','routemetric6','dnsnameservers','dnssearch','mtu','wol','comment','type','macaddress','link','altmacaddress'}
 out['OMV_wired_object']={k:v for k,v in selected[0].items() if k in public_keys}
 source=Path('/usr/share/openmediavault/engined/rpc/network.inc').read_text()
 out['OMV_network_rpc_methods']=re.findall(r'public function ([A-Za-z0-9_]+)\(',source)
 pos=source.find('function setEthernetIface(');out['OMV_setEthernetIface_public_source_excerpt']=source[pos:pos+2700] if pos>=0 else None
 model=Path('/usr/share/openmediavault/datamodels/conf.system.network.interface.json');out['OMV_network_model_exists']=model.exists()
 if model.exists():out['OMV_network_model']=json.loads(model.read_text())
 ssh=cmd(['/usr/sbin/sshd','-T']);out['SSH_fields']=[x for x in ssh.splitlines() if x.split(' ',1)[0] in ['listenaddress','permitrootlogin','passwordauthentication','pubkeyauthentication']]
 out['SMB_bind_fields']={k:cmd(['/usr/bin/testparm','-s','--parameter-name='+k]).strip() for k in ['interfaces','bind interfaces only','hosts allow','hosts deny']}
print(json.dumps(out))
'''
def collect(role):
 r=control.guest(role,'sudo python3 -',data=SCRIPT.replace('NUMBER',str(role)).encode(),timeout=90,info=targets[role])
 if r['exit_code']:return {'role':role,'status':'collection-failed','details_withheld':True}
 return json.loads(r['stdout'])
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:values=list(pool.map(collect,[250,221,260]))
out=Path(__file__).with_name('active-readonly-preflight.json');out.write_text(json.dumps(values,indent=2,ensure_ascii=False)+'\n')
for v in values:
 print(json.dumps({k:val for k,val in v.items() if k not in ['OMV_network_model','OMV_setEthernetIface_public_source_excerpt','public_file_metadata','11_image_ids']},ensure_ascii=False))
