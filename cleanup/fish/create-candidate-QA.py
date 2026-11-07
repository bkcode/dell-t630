from pathlib import Path
import sys,json,shlex
R=Path(__file__).resolve().parents[2];sys.dont_write_bytecode=True;sys.path.insert(0,str(R/'scripts'));import control
checks={9040:'builder9040-seal-retry-netplan.json',9041:'builder9041-seal.json',9042:'builder9042-seal.json'}
for v,n in checks.items():
 x=json.loads((R/'cleanup/fish/evidence'/n).read_text());assert x['exit_code']==0 and x['result']['receipt']['result']['sealed'] and x['result']['receipt']['result']['machine_id_reset']
P=r'''from pathlib import Path
import subprocess,json
jobs=[(9040,9043,9010,'linux','192.168.19.197','dell-linux-default-user.yaml'),(9041,9044,9001,'docker','192.168.19.198','dell-docker-default-user.yaml'),(9042,9045,9011,'java','192.168.19.199','dell-linux-default-user.yaml')]
assert all(not Path('/etc/pve/qemu-server/'+str(q)+'.conf').exists() for b,q,*_ in jobs)
def run(a,timeout=180):
 p=subprocess.run(a,capture_output=True,text=True,timeout=timeout)
 if p.returncode:raise RuntimeError('candidateQA action failed '+a[1])
 return p.stdout
out=[]
for builder,qa,logical,kind,ip,generic in jobs:
 run(['qm','shutdown',str(builder),'--timeout','90']);assert 'stopped' in run(['qm','status',str(builder)])
 run(['qm','set',str(builder),'--name','fish-candidate-'+kind,'--cicustom','user=store:snippets/'+generic,'--ipconfig0','ip=dhcp','--nameserver','192.168.19.1','--onboot','0','--description','Sealed fish candidate; original template'+str(logical)+'remains preserved; QA before replacement'])
 run(['qm','template',str(builder)])
 name='fish-qa-'+kind;profile=Path('/mnt/pve/store/snippets')/('dell-'+name+'-user.yaml');assert not profile.exists();text=(profile.parent/generic).read_text();assert not any(l.startswith('hostname:') for l in text.splitlines());profile.write_text(text.replace('preserve_hostname: false','preserve_hostname: false\nhostname: '+name));profile.chmod(0o600)
 run(['qm','clone',str(builder),str(qa),'--full','1','--storage','store','--format','qcow2','--name',name],240)
 run(['qm','set',str(qa),'--memory','2048','--cores','2','--balloon','0','--net0','virtio,bridge=vmbr19,firewall=0','--ipconfig0','ip='+ip+'/24,gw=192.168.19.1','--nameserver','192.168.19.1','--cicustom','user=store:snippets/'+profile.name,'--onboot','0','--description','Dedicated independent QA of sealed fish candidate'+str(builder)+'logical template'+str(logical)])
 conf=run(['qm','config',str(qa)]);net=next(x.partition(': ')[2] for x in conf.splitlines() if x.startswith('net0: '));out.append({'vmid':qa,'candidate_vmid':builder,'source_template':logical,'name':name,'IP':ip,'net0':net,'state':'stopped-await-L2-registry'})
print(json.dumps(out))'''
x=json.loads(control.pve('python3 -',data=P.encode(),timeout=900));(R/'cleanup/fish/candidates-and-QA-created.json').write_text(json.dumps(x,indent=2)+'\n')
p=R/'network19/migration-plan.json';v=json.loads(p.read_text());v['guest_addresses']=[row for row in v['guest_addresses'] if row['vmid'] not in checks]
for row in x:v['guest_addresses'].append({'vmid':row['vmid'],'name':row['name'],'old_ip':'dedicated-fish-QA','new_ip':row['IP'],'prefix':24,'gateway':'192.168.19.1','bridge':'vmbr19','kind':'vm','temporary_build_only':True})
v['temporary_bootstrap_vmids']=[9043,9044,9045];p.write_text(json.dumps(v,indent=2,ensure_ascii=False)+'\n');print(json.dumps(x))
