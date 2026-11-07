from pathlib import Path
import sys,json,datetime
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'scripts'));import control
clean=json.loads((R/'network19/java-template/clean-evidence.json').read_text());assert clean['exit_code']==0 and clean['result']['host_SSH_keys_absent'] and clean['result']['machine_id_nextboot_reset']
script=r'''from pathlib import Path
import subprocess,json
assert not Path('/etc/pve/qemu-server/9012.conf').exists()
def run(a,timeout=180):
 p=subprocess.run(a,capture_output=True,text=True,timeout=timeout)
 if p.returncode:raise RuntimeError('Java template seal/clone failed '+a[0])
 return p.stdout
run(['qm','shutdown','9011','--timeout','60']);assert 'stopped' in run(['qm','status','9011'])
run(['qm','set','9011','--name','tpl-java-acceptance','--cicustom','user=store:snippets/dell-linux-default-user.yaml','--ipconfig0','ip=dhcp','--nameserver','192.168.19.1','--onboot','0','--description','Single clean Java acceptance template: JDK21, nonroot java, generic verification; exporter parked; no business apps/configuration/credentials. Clone requires assigned19 IP+L2 registry.'])
run(['qm','template','9011'])
run(['qm','clone','9011','9012','--full','1','--storage','store','--format','qcow2','--name','java-acceptance-clone-check'],240)
run(['qm','set','9012','--memory','2048','--cores','2','--balloon','0','--net0','virtio,bridge=vmbr19,firewall=0','--ipconfig0','ip=192.168.19.198/24,gw=192.168.19.1','--nameserver','192.168.19.1','--onboot','0','--description','Disposable dedicated QA clone of single Java acceptance template9011; no business state.'])
net=next(l.partition(': ')[2] for l in Path('/etc/pve/qemu-server/9012.conf').read_text().splitlines() if l.startswith('net0: '))
print(json.dumps({'template_vmid':9011,'template_name':'tpl-java-acceptance','state':'sealed-stopped','CI':'generic Linux user,19 DHCP when assigned','QA_vmid':9012,'QA_state':'stopped-await-L2-registry','QA_net0':net,'QA_IP':'192.168.19.198','business_apps':False}))'''
x=json.loads(control.pve('python3 -',data=script.encode(),timeout=360));(R/'network19/java-template/seal-and-clone.json').write_text(json.dumps(x,indent=2)+'\n');print(json.dumps(x))
p=R/'network19/migration-plan.json';v=json.loads(p.read_text());v['guest_addresses'].append({'vmid':9012,'name':'java-acceptance-clone-check','old_ip':'new-clean-QA','new_ip':'192.168.19.198','prefix':24,'gateway':'192.168.19.1','bridge':'vmbr19','kind':'vm','temporary_QA_only':True});v['template_VMIDs'].append(9011);p.write_text(json.dumps(v,indent=2,ensure_ascii=False)+'\n')
