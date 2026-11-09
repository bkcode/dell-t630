#!/usr/bin/python3
"""One new stopped VM280 from accepted Linux9010; never reuses a VMID or data disk."""
import datetime,json,os,pathlib,socket,subprocess
VM=280;MAC='02:63:19:02:80:00'
def run(args):
 p=subprocess.run(args,capture_output=True,text=True,timeout=240)
 if p.returncode:raise RuntimeError('fixed-new-VM-operation-failed')
 return p.stdout

def main():
 assert os.geteuid()==0 and socket.gethostname()=='pve' and pathlib.Path('/etc/pve').is_dir()
 assert not pathlib.Path('/etc/pve/qemu-server/280.conf').exists() and not pathlib.Path('/etc/pve/lxc/280.conf').exists()
 assert 'template: 1' in run(['qm','config','9010']) and 'name: tpl-linux-base' in run(['qm','config','9010'])
 rows=json.loads(run(['pvesh','get','/cluster/resources','--type','vm','--output-format','json']));assert all(x['vmid']!=VM for x in rows)
 for r in rows:
  if r['type']=='qemu':assert MAC not in run(['qm','config',str(r['vmid'])]).upper()
 s=pathlib.Path('/mnt/pve/store/snippets');p=s/'dell-resource-service-user.yaml';assert not p.exists()
 original=(s/'dell-linux-default-user.yaml').read_text();assert original.count('preserve_hostname: false')==1 and '\nhostname:'not in original
 p.write_text(original.replace('preserve_hostname: false','preserve_hostname: false\nhostname: resource-service',1));p.chmod(0o600)
 run(['qm','clone','9010','280','--name','resource-service','--full','1','--storage','store','--format','qcow2'])
 run(['qm','set','280','--memory','2048','--cores','2','--balloon','0','--net0','virtio='+MAC+',bridge=vmbr19,firewall=0','--ipconfig0','ip=192.168.19.80/24,gw=192.168.19.1','--nameserver','192.168.19.1','--cicustom','user=store:snippets/'+p.name,'--onboot','0','--startup','order=35,up=20,down=120','--description','Unified empty resource storage for prod/test running; NFS only; no source data/Java/automatic backup'])
 run(['qm','set','280','--scsi1','store:100,format=qcow2,iothread=1,discard=on'])
 assert run(['qm','status','280']).strip()=='status: stopped'
 print(json.dumps({'at':datetime.datetime.now().astimezone().isoformat(),'status':'new-resource-VM-created-stopped','vmid':280,'name':'resource-service','ip':'192.168.19.80','MAC':MAC,'cpu':2,'memory_MiB':2048,'system_disk_GiB':32,'new_data_disk_GiB':100,'template':9010,'existing_guests_or_disks_changed':False,'started':False}))
if __name__=='__main__':main()
