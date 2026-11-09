#!/usr/bin/python3
"""Fixed resource-role enum/fileSD additions on existing Ops; no test notifications."""
import base64,datetime,hashlib,json,os,pathlib,socket,stat,subprocess,sys,urllib.request
ROOT=pathlib.Path('/root/dell-resource-ops-20261109')
FILES={'lark':('/usr/local/libexec/dell-lark-notify/bridge.py','12d733376239919ba55c3739ebf8a0564de12ceaad9fba28c75d8632630a41e6','a78a84351fd0bf8e79b2d6ef7b4ef2a4464734108a01666850f4c290f8ffe458'),'prom':('/opt/dell/ops/config/prometheus/targets/guest-node.json','dc7cf106ebb42021191018c7eda121cf1deb7128308fee7a75beff9a5bf3c9f0','9e51cc2cca214e5754ed76c5472686143650f737b05bdf15ce1c312d79a67263')}
def run(a):
 p=subprocess.run(a,capture_output=True,timeout=25)
 if p.returncode:raise RuntimeError('fixed-Ops-native-operation-failed')
 return p.stdout

def sha(b):return hashlib.sha256(b).hexdigest()
def put(p,b,mode):
 t=p.with_name(p.name+'.resource-tmp');assert not t.exists();fd=os.open(t,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,mode);os.fchmod(fd,mode)
 with os.fdopen(fd,'wb')as f:f.write(b);f.flush();os.fsync(f.fileno())
 os.replace(t,p)

def main():
 assert os.geteuid()==0 and socket.gethostname()=='ops-service' and not pathlib.Path('/etc/pve').exists();os.umask(0o077)
 x=json.load(sys.stdin);kind=x['kind'];path,oldsha,newsha=FILES[kind];p=pathlib.Path(path)
 for item in [p,*p.parents]:
  s=item.lstat();assert not stat.S_ISLNK(s.st_mode)and s.st_uid==0 and not s.st_mode&0o022
 before=p.read_bytes();after=base64.b64decode(x['candidate_b64']);assert sha(before)==oldsha and sha(after)==newsha;mode=stat.S_IMODE(p.stat().st_mode)
 if ROOT.exists()or ROOT.is_symlink():
  q=ROOT.lstat();assert not stat.S_ISLNK(q.st_mode)and q.st_uid==0 and stat.S_IMODE(q.st_mode)==0o700
 else:ROOT.mkdir(mode=0o700)
 backup=ROOT/(kind+'.before');fd=os.open(backup,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
 with os.fdopen(fd,'wb')as f:f.write(before);f.flush();os.fsync(f.fileno())
 if kind=='lark':
  compile(after,'resource-role-whitelist','exec');assert after==before.replace(b"'ops-service','pve'}",b"'ops-service','pve','resource-service'}",1)
  assert not run(['ss','-H','-tn','state','established','sport','=',':19093']).strip(),'in-flight-notification-connection'
 else:
  a,b=json.loads(before),json.loads(after);assert b==a+[{'targets':['192.168.19.80:9100'],'labels':{'role':'resource-service','zone':'shared','vmid':'280'}}]and len(a)==10
  opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
  with opener.open('http://192.168.19.80:9100/metrics',timeout=8)as response:
   assert response.status==200;metrics=response.read(4194304).decode()
  for unit in ['ssh.service','qemu-guest-agent.service','prometheus-node-exporter.service','nfs-server.service','dell-resources-firewall.service']:
   assert 'dell_guest_service_active{role="resource-service",service="'+unit+'"} 1' in metrics,'resource-native-service-not-ready'
  assert 'dell_guest_health_collection_success{role="resource-service"} 1' in metrics
  ids=run(['docker','ps','--quiet','--filter','label=com.docker.compose.project=dell-ops','--filter','label=com.docker.compose.service=prometheus']).decode().split();assert len(ids)==1;cid=ids[0]
  run(['docker','exec',cid,'/bin/promtool','check','config','/etc/prometheus/prometheus.yml'])
 try:
  put(p,after,mode)
  if kind=='lark':run(['systemctl','restart','dell-lark-notify.service']);run(['systemctl','is-active','--quiet','dell-lark-notify.service'])
  else:run(['docker','exec',cid,'/bin/promtool','check','config','/etc/prometheus/prometheus.yml'])
 except Exception:
  assert sha(p.read_bytes())==newsha;put(p,before,mode)
  if kind=='lark':run(['systemctl','restart','dell-lark-notify.service'])
  raise
 out={'at':datetime.datetime.now().astimezone().isoformat(),'kind':kind,'status':'exact-resource-role-increment-installed','new_public_SHA256':newsha,'test_notifications_sent':False,'receivers_tokens_rules_or_other_targets_changed':False,'only_Lark_bridge_restarted':kind=='lark','Prometheus_restarted':False};(ROOT/(kind+'.result.json')).write_text(json.dumps(out));print(json.dumps(out))
if __name__=='__main__':main()
