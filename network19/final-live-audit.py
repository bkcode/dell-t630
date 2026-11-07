from pathlib import Path
import sys,json,shlex,datetime,concurrent.futures
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'scripts'));import control
plan=json.loads((R/'plan.json').read_text());roles={r['vmid']:r for r in plan['roles'] if r['kind']=='vm' and r['vmid']!=190};targets=json.loads((R/'network19/evidence/migrated-access.json').read_text())['targets']
G=r'''import subprocess,json,socket,os
rows=json.loads(subprocess.check_output(['ip','-4','-j','addr']));nics=[r for r in rows if r['ifname']!='lo' and not r['ifname'].startswith(('docker','br-','veth'))];v={'user':os.getlogin() if False else subprocess.check_output(['id','-un'],text=True).strip(),'hostname':socket.gethostname(),'NICs':[{k:r.get(k) for k in ['ifname','address','addr_info']} for r in nics],'default':json.loads(subprocess.check_output(['ip','-4','-j','route','show','default'])),'sudo_noninteractive':subprocess.run(['sudo','-n','true'],capture_output=True).returncode==0,'DNS':[subprocess.check_output(['resolvectl','dns',r['ifname']],text=True).strip() for r in nics]};print(json.dumps(v))'''
def one(vmid):
 role=roles[vmid];target=targets[str(vmid)];r=control.guest(vmid,'python3 -c '+shlex.quote(G),info=target,timeout=30);v=json.loads(r['stdout']) if r['exit_code']==0 else {};ips=[a['local'] for n in v.get('NICs',[]) for a in n.get('addr_info',[]) if a.get('family')=='inet'];passed=r['exit_code']==0 and v['user']=='ub' and v['hostname']==role['name'] and ips==[target['ip']] and len(v['default'])==1 and v['default'][0].get('gateway')=='192.168.19.1' and v['sudo_noninteractive'] and all(d.partition(':')[2].split()==['192.168.19.1'] for d in v['DNS']);return {'vmid':vmid,'name':role['name'],'target':target,'exit':r['exit_code'],'passed':passed,'network_identity':v}
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:out=list(pool.map(one,sorted(roles)))
P=r'''from pathlib import Path
import subprocess,json
out={'host_forward':Path('/proc/sys/net/ipv4/ip_forward').read_text().strip(),'all_forwarding_zero':all(p.read_text().strip()=='0' for fam in ['ipv4','ipv6'] for p in Path('/proc/sys/net',fam,'conf').glob('*/forwarding')),'tables':subprocess.check_output(['nft','list','tables'],text=True).splitlines(),'vmbr19_host_addresses':json.loads(subprocess.check_output(['ip','-j','addr','show','vmbr19']))[0].get('addr_info',[]),'host_route19':subprocess.check_output(['ip','route','get','192.168.19.10'],text=True).strip(),'old_bridges_present':[x for x in ['vmbr10','vmbr20','vmbr30','vmbr40'] if (Path('/sys/class/net')/x).exists()]}
rows=json.loads(subprocess.check_output(['pvesh','get','/cluster/resources','--type','vm','--output-format','json']));out['permanent_running']=sorted(r['vmid'] for r in rows if r['status']=='running');out['template_ids']=sorted(r['vmid'] for r in rows if r.get('template')==1);out['QA9012_absent']=all(r['vmid']!=9012 for r in rows)
def ct(a):return subprocess.run(['pct','exec','100','--',*a],capture_output=True,text=True,timeout=15)
out['CF_active']=ct(['systemctl','is-active','cloudflared']).stdout.strip()=='active';out['CF_IP']=json.loads(ct(['ip','-4','-j','addr','show','dev','eth0']).stdout)
sockets=ct(['ss','-H','-ltn']).stdout;out['CF_local_ready']=None
if ':20241 ' in sockets or ':20241\t' in sockets:
 p=ct(['curl','--noproxy','*','--max-time','3','-sS','-w','\n%{http_code}','http://127.0.0.1:20241/ready'])
 if p.returncode==0:
  body,_,status=p.stdout.rpartition('\n');out['CF_local_ready']={'HTTP':status}
  try:
   j=json.loads(body);out['CF_local_ready']['readyConnections']=j.get('readyConnections')
  except ValueError:pass
print(json.dumps(out))'''
host=json.loads(control.pve('python3 -',data=P.encode(),timeout=80));expected=sorted([100,190,*roles]);passed=all(r['passed'] for r in out) and host['host_forward']=='0' and host['all_forwarding_zero'] and not host['old_bridges_present'] and not host['vmbr19_host_addresses'] and host['tables']==['table bridge dell19_acl'] and host['permanent_running']==expected and host['CF_active'] and host['QA9012_absent']
x={'at':datetime.datetime.now().astimezone().isoformat(),'scope':'current final network/strict SSH and management-only host, not whole-host reboot','roles':out,'host':host,'all_passed':passed};(R/'network19/evidence/final-live-network-identity.json').write_text(json.dumps(x,indent=2)+'\n');print(json.dumps({'all_passed':passed,'strict_roles':len(out),'roles_passed':sum(r['passed'] for r in out),'host':host}));assert passed
# Refresh operator access page with current live identity stdout, not stale staging receipts.
p=R/'evidence/implementation/private-guest-access.json';v=json.loads(p.read_text())
for row in v['roles']:
 a=next(i for i in out if i['vmid']==row['target']['vmid']);row.update(status='strict-network19-identity-verified',target=a['target'],stdout=json.dumps(a['network_identity']))
v.update(at=x['at'],scope='current-active-operator-targets-network19',evidence='network19/evidence/final-live-network-identity.json');p.write_text(json.dumps(v,indent=2,ensure_ascii=False)+'\n')
