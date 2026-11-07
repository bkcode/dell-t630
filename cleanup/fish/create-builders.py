from pathlib import Path
import json,sys,shlex,datetime
R=Path(__file__).resolve().parents[2];sys.dont_write_bytecode=True;sys.path.insert(0,str(R/'scripts'));import control
P=r'''from pathlib import Path
import subprocess,json
jobs=[(9040,9010,'fish-build-linux','192.168.19.197','dell-linux-default-user.yaml'),(9041,9001,'fish-build-docker','192.168.19.198','dell-docker-default-user.yaml'),(9042,9011,'fish-build-java','192.168.19.199','dell-linux-default-user.yaml')]
assert all(not Path('/etc/pve/qemu-server/'+str(v)+'.conf').exists() for v,*_ in jobs)
assert all('stopped' in subprocess.check_output(['qm','status',str(i)],text=True) for i in [231,232])
out=[]
for vmid,src,name,ip,base in jobs:
 original=Path('/etc/pve/qemu-server/'+str(src)+'.conf').read_text().split('\n[',1)[0];assert 'template: 1' in original
 profile=Path('/mnt/pve/store/snippets')/('dell-'+name+'-user.yaml');assert not profile.exists();text=(profile.parent/base).read_text();assert not any(l.startswith('hostname:') for l in text.splitlines());assert 'ssh_deletekeys: true' in text
 profile.write_text(text.replace('preserve_hostname: false','preserve_hostname: false\nhostname: '+name));profile.chmod(0o600)
 for cmd in [['qm','clone',str(src),str(vmid),'--full','1','--storage','store','--format','qcow2','--name',name],['qm','set',str(vmid),'--memory','2048','--cores','2','--balloon','0','--net0','virtio,bridge=vmbr19,firewall=0','--ipconfig0','ip='+ip+'/24,gw=192.168.19.1','--nameserver','192.168.19.1','--cicustom','user=store:snippets/'+profile.name,'--onboot','0','--description','Dedicated temporary fish template builder; no business data; source template remains unchanged']]:
  p=subprocess.run(cmd,capture_output=True,text=True,timeout=240)
  if p.returncode:raise RuntimeError('fixed builder create action failed '+cmd[1])
 conf=subprocess.check_output(['qm','config',str(vmid)],text=True);net=next(l.split(': ',1)[1] for l in conf.splitlines() if l.startswith('net0: '));out.append({'vmid':vmid,'source_template':src,'name':name,'IP':ip,'net0':net,'state':'stopped-await-L2-registry'})
print(json.dumps(out))'''
x=json.loads(control.pve('python3 -',data=P.encode(),timeout=900));(R/'cleanup/fish/builders-created-stopped.json').write_text(json.dumps(x,indent=2)+'\n')
p=R/'network19/migration-plan.json';plan=json.loads(p.read_text())
for r in x:plan['guest_addresses'].append({'vmid':r['vmid'],'name':r['name'],'old_ip':'dedicated-new-fish-builder','new_ip':r['IP'],'prefix':24,'gateway':'192.168.19.1','bridge':'vmbr19','kind':'vm','temporary_build_only':True})
p.write_text(json.dumps(plan,indent=2,ensure_ascii=False)+'\n');print(json.dumps(x))
