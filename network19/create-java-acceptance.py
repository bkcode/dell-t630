from pathlib import Path
import sys,json,shlex,datetime
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'scripts'));import control
script=r'''from pathlib import Path
import subprocess,json
assert not Path('/etc/pve/qemu-server/9011.conf').exists() and not Path('/etc/pve/qemu-server/9012.conf').exists()
def run(a):
 p=subprocess.run(a,capture_output=True,text=True,timeout=180)
 if p.returncode:raise RuntimeError('fixed Java template provisioning failed '+a[0])
 return p.stdout
run(['qm','shutdown','232','--timeout','60']);assert 'stopped' in run(['qm','status','232'])
p=Path('/mnt/pve/store/snippets/dell-java-acceptance-user.yaml');assert not p.exists();base=Path('/mnt/pve/store/snippets/dell-linux-default-user.yaml').read_text();assert base.count('preserve_hostname: false')==1 and 'ssh_deletekeys: true' in base
p.write_text(base.replace('preserve_hostname: false','preserve_hostname: false\nhostname: java-acceptance-build'));p.chmod(0o600)
run(['qm','clone','9010','9011','--full','1','--storage','store','--format','qcow2','--name','java-acceptance-build'])
run(['qm','set','9011','--memory','2048','--cores','2','--balloon','0','--net0','virtio,bridge=vmbr19,firewall=0','--ipconfig0','ip=192.168.19.197/24,gw=192.168.19.1','--nameserver','192.168.19.1','--cicustom','user=store:snippets/'+p.name,'--agent','enabled=1','--onboot','0','--description','Single Java acceptance template build; no business program, configuration, credentials or data.'])
config=Path('/etc/pve/qemu-server/9011.conf').read_text();net=next(l.partition(': ')[2] for l in config.splitlines() if l.startswith('net0: '))
print(json.dumps({'vmid':9011,'state':'stopped-awaiting-L2-registry','net0':net,'build_IP':'192.168.19.197','temporary_resource_budget':'232 stopped releases16GiB; build2GiB; eventualQA2GiB; at least20GiB planned reserve','source':9010,'business_apps_installed':False}))'''
x=json.loads(control.pve('python3 -',data=script.encode(),timeout=270));(R/'network19/evidence/java-template-created-stopped.json').write_text(json.dumps(x,indent=2)+'\n');print(json.dumps(x))
p=R/'network19/migration-plan.json';v=json.loads(p.read_text());v['guest_addresses'].append({'vmid':9011,'name':'java-acceptance-build','old_ip':'new-clean-clone','new_ip':'192.168.19.197','prefix':24,'gateway':'192.168.19.1','bridge':'vmbr19','kind':'vm','temporary_build_only':True});p.write_text(json.dumps(v,indent=2,ensure_ascii=False)+'\n')
