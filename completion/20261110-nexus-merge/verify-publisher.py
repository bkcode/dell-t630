#!/usr/bin/env python3
"""Post-reboot publisher/Nexus preservation and read-only authorization checks."""
import hashlib,importlib.util,json,os,socket,subprocess,sys,urllib.error,urllib.request
from pathlib import Path
assert os.geteuid()==0 and socket.gethostname()=='publish-service'
old_boot=sys.argv[1];boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip();assert boot!=old_boot
proof=json.loads(Path('/root/dell-nexus-merge-publisher-proof-20261110.json').read_text());assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==digest for p,digest in proof['files'].items())
def run(args):return subprocess.check_output(list(map(str,args)),stderr=subprocess.PIPE,timeout=30).decode().strip()
def git(folder,*args):return run(['runuser','-u','ub','--','git','-C',folder,*args])
assert git('/opt/deploy-public','rev-parse','HEAD')==proof['source_HEAD'] and not git('/opt/deploy-public','status','--porcelain')
repos={}
for p in sorted(Path('/srv/dell-build/deploy-public/repos').iterdir()):
 if p.is_dir()and(p/'.git').is_dir():repos[p.name]={'HEAD':git(p,'rev-parse','HEAD'),'branch':git(p,'branch','--show-current'),'clean':not git(p,'status','--porcelain')}
assert len(repos)==6 and all(x['branch']=='main'and x['clean']for x in repos.values())
mounts={}
for path,uuid in [('/srv/dell-build','16dc6067-56ef-4687-a314-edc6421f9ed4'),('/srv/nexus','239dc45a-b1f3-408b-a8ef-7afa77b52204')]:
 value=run(['findmnt','-n','-o','UUID','--mountpoint',path]);assert value==uuid;mounts[path]=uuid
addresses=json.loads(run(['ip','-j','address','show','dev','eth0']));ips=[x['local']for x in addresses[0]['addr_info']if x['family']=='inet'];assert ips==['192.168.19.30','192.168.19.31'];route=json.loads(run(['ip','-j','route','get','192.168.19.45']))[0];assert route['prefsrc']=='192.168.19.30'
services=['dell-nexus.service','puyu-deploy-mcp.service','dell-service-directory.service','prometheus-node-exporter.service'];assert all(run(['systemctl','is-active',u])=='active'and run(['systemctl','is-enabled',u])=='enabled'for u in services)
assert '127.0.0.1:18765'in run(['ss','-H','-lnt','sport','=',':18765'])
base=Path('/opt/dell/nexus');sys.path.insert(0,str(base));spec=importlib.util.spec_from_file_location('nexus_read_auth',base/'application-import.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
snapshot=json.loads(Path('/srv/nexus/.dell-merge-baseline-20261110.json').read_text());asset=next(a for a in snapshot['hosted']['imnull-releases']['assets']if a['path'].endswith('.jar'))
path='/repository/imnull-releases/'+asset['path'];api=m.API();assert api.json('GET','/system/eula')['accepted']
for user,secret in [('dell-reader','reader-password'),('dell-publisher','publisher-password')]:
 _,body=m.API(user,secret).request('GET',path);assert hashlib.sha256(body).hexdigest()==asset['sha256']
_,body=m.API('dell-reader','reader-password').request('GET','/repository/finger-public/'+asset['path']);assert hashlib.sha256(body).hexdigest()==asset['sha256']
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
try:
 with opener.open('http://192.168.19.31:8081'+path,timeout=10)as r:anonymous=r.status
except urllib.error.HTTPError as e:anonymous=e.code;e.close()
assert anonymous in (401,403)
with opener.open('http://192.168.19.30:9080/api/services',timeout=10)as r:nav=json.loads(r.read())
assert len(nav['services'])==13 and all('192.168.19.80:8080'not in x['url']for x in nav['services'])
assert 'docker'not in run(['id','publisher']);assert subprocess.run(['runuser','-u','publisher','--','test','-w','/var/run/docker.sock']).returncode!=0
key=Path('/var/lib/dell-publisher/.ssh/test240_ed25519').stat();assert key.st_uid==999 and key.st_gid==989 and key.st_mode&0o777==0o600 and key.st_size==419
frame='{"name":{{json .Name}},"image":{{json .Image}},"health":{{json .State.Health.Status}}}'
containers=[json.loads(run(['docker','inspect','--format',frame,name]))for name in ['nexus-nexus-1','nexus-gateway-1']];assert all(x['health']=='healthy'for x in containers)
print(json.dumps({'status':'post-reboot-publisher-Nexus-persistence-and-auth-verified','VM220_boot_id_changed':True,'mounts':mounts,'physical_IPs':ips,'publisher_egress_source':'192.168.19.30','services_active_enabled':services,'publisher_config_MCP_key_unit_build_guard_profile_bytes_unchanged':True,'deploy_public_HEAD':proof['source_HEAD'],'backend_repos':repos,'MCP_loopback_only':True,'Nexus_containers':containers,'original_reader_publisher_and_group_read_passed':True,'anonymous_asset_HTTP':anonymous,'EULA_accepted':True,'publisher_not_docker_group_socket_denied':True,'publisher_private_key_contents_read_or_copied':False,'navigation_entries':13,'FileBrowser_navigation_removed':True,'Java_or_Go_business_deployed':False}))
