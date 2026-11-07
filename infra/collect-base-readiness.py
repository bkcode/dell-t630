import subprocess,json,os,socket
from pathlib import Path
assert not Path('/etc/pve').exists()
def cmd(a):
 p=subprocess.run(a,capture_output=True,text=True);return {'exit_code':p.returncode,'stdout':p.stdout.strip()}
release={}
for line in Path('/etc/os-release').read_text().splitlines():
 if '=' in line:
  k,v=line.split('=',1);release[k]=v.strip('"')
info={'hostname':socket.gethostname(),'user':cmd(['id','-un'])['stdout'],'os':{'id':release['ID'],'version':release['VERSION_ID']},'cloud_init':json.loads(cmd(['cloud-init','status','--format','json'])['stdout']),'ntp_synchronized':cmd(['timedatectl','show','-p','NTPSynchronized','--value'])['stdout'],'guest_agent':cmd(['systemctl','is-active','qemu-guest-agent'])['stdout'],'exporter_enabled':cmd(['systemctl','is-enabled','prometheus-node-exporter'])['stdout'],'exporter_active':cmd(['systemctl','is-active','prometheus-node-exporter'])['stdout'],'business_containers':None,'docker':None,'java':None}
if Path('/usr/bin/docker').exists():
 d=json.loads(subprocess.check_output(['sudo','-n','docker','info','--format','{{json .}}'],text=True))
 info['docker']={k:d[k] for k in ['Name','ServerVersion','Driver','DockerRootDir','Containers','Images','LiveRestoreEnabled']}
 info['business_containers']=cmd(['sudo','-n','docker','ps','-aq'])['stdout']
if Path('/opt/finger/java/bin/java').exists():info['java']=subprocess.run(['/opt/finger/java/bin/java','-version'],capture_output=True,text=True).stderr.splitlines()[0]
ports={80,445,8096,8081,9001,9002,9999,10000,10210,10202,10104,3306,6379,5672,15672,8848,9848,3000,9090,9093,9115,9100}
listening=[]
for line in cmd(['ss','-H','-lnt'])['stdout'].splitlines():
 fields=line.split()
 if len(fields)>3:
  try:
   port=int(fields[3].rsplit(':',1)[1])
   if port in ports:listening.append(port)
  except ValueError:pass
info['unexpected_business_ports']=sorted(set(listening))
info['no_business_stack_started']=not listening and info['business_containers'] in [None,'']
print(json.dumps(info))
