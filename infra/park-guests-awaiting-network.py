from pathlib import Path
import subprocess,json,datetime
root=Path('/root/dell-bootstrap');plan=json.loads((root/'plan.json').read_text());records=[]
for role in reversed(plan['roles']):
 if role['kind']!='vm':continue
 vm=str(role['planned_vmid']);name=role['name'];cfg=Path('/etc/pve/qemu-server/'+vm+'.conf').read_text()
 assert 'name: '+name+'\n' in cfg and 'Managed by harness/dell' in cfg
 state=subprocess.check_output(['qm','status',vm],text=True).strip()
 if state=='status: running':
  p=subprocess.run(['qm','shutdown',vm,'--timeout','45'],capture_output=True,text=True)
  if p.returncode:raise SystemExit('Graceful shutdown failed; no forced stop: '+vm)
 assert subprocess.check_output(['qm','status',vm],text=True).strip()=='status: stopped'
 cfg=Path('/etc/pve/qemu-server/'+vm+'.conf').read_text();net=next(l.split(': ',1)[1] for l in cfg.splitlines() if l.startswith('net0: '))
 options=[item for item in net.split(',') if not item.startswith(('bridge=','link_down='))]
 options.append('bridge='+role['planned_bridge']);ip=role['planned_ip'];gateway=ip.rsplit('.',1)[0]+'.1'
 p=subprocess.run(['qm','set',vm,'--net0',','.join(options),'--ipconfig0','ip='+ip+'/24,gw='+gateway,'--nameserver','1.1.1.1','--onboot','0'],capture_output=True,text=True)
 if p.returncode:raise SystemExit('Failed private parked configuration '+vm)
 p=subprocess.run(['qm','cloudinit','update',vm],capture_output=True,text=True)
 if p.returncode:raise SystemExit('CloudInit update failed '+vm)
 records.append({'vmid':int(vm),'name':name,'state':'stopped','configured_ip':ip,'bridge':role['planned_bridge'],'network_live':False,'onboot':False,'mac_preserved':True})
 print('PARKED_PRIVATE_STOPPED',vm,name,flush=True)
assert Path('/proc/sys/net/ipv4/ip_forward').read_text().strip()=='0','Unexpected host forwarding state'
bridges=subprocess.check_output(['ip','-j','link'],text=True);names={x['ifname'] for x in json.loads(bridges)}
assert not names.intersection({'vmbr10','vmbr20','vmbr30','vmbr40'}),'Managed host bridges unexpectedly exist'
for family,table in [('inet','dell_filter'),('ip','dell_nat')]:
 assert subprocess.run(['nft','list','table',family,table],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode!=0,'Host table unexpectedly applied'
assert subprocess.check_output(['pct','status','100'],text=True).strip()=='status: running'
receipt={'at':datetime.datetime.now().isoformat(),'status':'all-target-guests-parked-awaiting-explicit-network-approval','records':records,'host_forwarding':0,'managed_host_bridges_created':False,'dedicated_host_firewall_applied':False,'cf100_running':True,'business_stacks_started':False}
(root/'guests-parked-awaiting-network.json').write_text(json.dumps(receipt,indent=2)+'\n');print('PARKED_ALL',len(records))
