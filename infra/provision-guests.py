from pathlib import Path
import subprocess,json,datetime
root=Path('/root/dell-bootstrap');plan=json.loads((root/'plan.json').read_text())
snippets=Path('/mnt/pve/store/snippets')
disks={'data-test':40,'publish-service':100,'artifact-service':100,'penpot-service':100,'nas-media':2048,'ops-service':32}
linux={'publish-service','java-prod-01','java-prod-02','java-prod-03','java-test-01','nas-media'}
created=[]
for role in plan['roles']:
 name=role['name']
 if role['kind']!='vm' or name in ['data-prod-db','data-prod-infra']:continue
 vm=str(role['planned_vmid'])
 if Path('/etc/pve/qemu-server/'+vm+'.conf').exists():raise SystemExit('VMID exists; inspect before reuse: '+vm)
 src='9010' if name in linux else '9001'
 profile=(snippets/('dell-linux-default-user.yaml' if src=='9010' else 'dell-docker-default-user.yaml')).read_text()
 profile=profile.replace('preserve_hostname: false','preserve_hostname: false\nhostname: '+name)
 f=snippets/('dell-'+name+'-user.yaml');f.write_text(profile);f.chmod(0o600)
 ip=role['planned_ip'];gateway=ip.rsplit('.',1)[0]+'.1'
 commands=[['qm','clone',src,vm,'--name',name,'--full','1','--storage','store','--format','qcow2'],['qm','set',vm,'--memory',str(int(role['memory_gib']*1024)),'--cores',str(role['vcpu']),'--balloon','0','--net0','virtio,bridge='+role['planned_bridge'],'--ipconfig0','ip='+ip+'/24,gw='+gateway,'--nameserver','1.1.1.1','--cicustom','user=store:snippets/'+f.name,'--onboot','0','--description','Managed by harness/dell; stopped until network approval and role verification']]
 if name in disks:commands.append(['qm','set',vm,'--scsi1',f'store:{disks[name]},format=qcow2,iothread=1,discard=on'])
 for args in commands:
  p=subprocess.run(args,capture_output=True,text=True)
  if p.returncode:print(p.stdout[-600:],p.stderr[-600:]);raise SystemExit(p.returncode)
 created.append({'name':name,'vmid':int(vm),'configured_ip':ip,'state':'stopped','system_storage':'store','data_disk_gib':disks.get(name)})
 print('CREATED_STOPPED',vm,name,flush=True)
(root/'guests-provisioned.json').write_text(json.dumps({'at':datetime.datetime.now().isoformat(),'roles':created},indent=2)+'\n')
print('Guest provisioning completed; host network unchanged; none started')
