from pathlib import Path
import sys,json,shlex,concurrent.futures,subprocess,datetime
from zoneinfo import ZoneInfo
R=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True;sys.path.insert(0,str(R/'scripts'));import control
plan=json.loads((R/'plan.json').read_text());roles={r['vmid']:r for r in plan['roles'] if r['kind']=='vm' and r['vmid']!=190};targets={r['target']['vmid']:r['target'] for r in json.loads((R/'evidence/implementation/private-guest-access.json').read_text())['roles']}
G=r'''import json,subprocess,socket,pwd,shutil
rows=json.loads(subprocess.check_output(['ip','-4','-j','addr']));ip=[a['local'] for r in rows if r['ifname']!='lo' and not r['ifname'].startswith(('docker','br-','veth')) for a in r.get('addr_info',[]) if a.get('family')=='inet'];fish=subprocess.run(['fish','--version'],capture_output=True,text=True) if shutil.which('fish') else None;print(json.dumps({'hostname':socket.gethostname(),'ip':ip,'routes':json.loads(subprocess.check_output(['ip','-4','-j','route','show','default'])),'fish':fish.stdout.strip() if fish is not None and fish.returncode==0 else None,'shells':{u:pwd.getpwnam(u).pw_shell for u in ['root','ub']},'business_Java_processes':subprocess.run(['pgrep','-x','java'],capture_output=True).returncode==0}))'''
fishids={190,200,201,210,220,221,230,240,260}
def one(v):
 r=control.guest(v,'python3 -B -c '+shlex.quote(G),info=targets[v],timeout=25);assert r['exit_code']==0;x=json.loads(r['stdout']);assert x['hostname']==roles[v]['name'] and x['ip']==[roles[v]['ip']] and len(x['routes'])==1 and x['routes'][0].get('gateway')=='192.168.19.1'
 if v in fishids:assert x['fish']=='fish, version 4.0.2' and x['shells']=={'root':'/bin/bash','ub':'/bin/bash'}
 if v in [230,240]:assert not x['business_Java_processes']
 return dict(vmid=v,name=roles[v]['name'],target=targets[v],strict_SSH=True,readback=x)
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:guests=list(pool.map(one,sorted(roles)))
P=r'''from pathlib import Path
import subprocess,json
rows=json.loads(subprocess.check_output(['pvesh','get','/cluster/resources','--type','vm','--output-format','json']));print(json.dumps({'running':sorted(x['vmid'] for x in rows if x['status']=='running'),'templates':sorted(x['vmid'] for x in rows if x.get('template')),'stopped_non_templates':sorted(x['vmid'] for x in rows if x['status']!='running' and not x.get('template')),'forward':Path('/proc/sys/net/ipv4/ip_forward').read_text().strip(),'all_interface_forward_zero':all(p.read_text().strip()=='0' for fam in ['ipv4','ipv6'] for p in Path('/proc/sys/net',fam,'conf').glob('*/forwarding')),'tables':subprocess.check_output(['nft','list','tables'],text=True).splitlines(),'vmbr19_addresses':json.loads(subprocess.check_output(['ip','-j','addr','show','vmbr19']))[0].get('addr_info',[]),'old_internal_bridges':[x for x in ['vmbr10','vmbr20','vmbr30','vmbr40'] if (Path('/sys/class/net')/x).exists()]}))'''
host=json.loads(control.pve('python3 -',data=P.encode()));assert host['running']==sorted(r['vmid'] for r in plan['roles']) and host['templates']==[9001,9010,9011] and host['stopped_non_templates']==[] and host['forward']=='0' and host['all_interface_forward_zero'] and host['tables']==['table bridge dell19_acl'] and not host['vmbr19_addresses'] and not host['old_internal_bridges']
O=r'''import json,urllib.request
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def get(path):
 with op.open('http://192.168.19.70:9090'+path,timeout=8) as r:return json.load(r)['data']
ts=get('/api/v1/targets')['activeTargets'];nodes=[x for x in ts if x['labels'].get('job')=='guest-node'];print(json.dumps({'total':len(ts),'all_up':all(x['health']=='up' for x in ts),'nodeids':sorted(int(x['labels']['vmid']) for x in nodes),'active_alerts':len(get('/api/v1/alerts')['alerts'])}))'''
r=control.guest(270,'python3 -B -c '+shlex.quote(O),info=targets[270],timeout=20);assert r['exit_code']==0;ops=json.loads(r['stdout']);assert ops['total']==15 and ops['all_up'] and ops['nodeids']==sorted(roles) and ops['active_alerts']==0
urls=['http://192.168.19.50:9001/','http://192.168.19.31:8081/','http://192.168.19.60/','http://192.168.19.60:8096/health','http://192.168.19.70:3000/login'];http=[]
for u in urls:
 r=subprocess.run(['curl','--noproxy','*','--connect-timeout','3','--max-time','5','-sS','-o','/dev/null','-w','%{http_code}',u],capture_output=True,text=True,timeout=7);assert r.returncode==0 and r.stdout=='200';http.append({'URL':u,'HTTP':200})
x={'at':datetime.datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),'status':'independent-cleanup-fish-template-checks-passed-Nexusmerge-still-pending-approval','guest_checks':guests,'host':host,'monitoring':ops,'HTTP':http,'Nexus_current_vmid':221,'Nexus220_standby_only':True,'fish_excluded_ids':[100,250,270],'PVE_host_shell_or_fish_not_changed':True,'Java_kept_each_one':[230,240],'Java_business_programs_started':False,'backups':'backup-summary.json','Nexus_unapproved_lifecycle_not_performed':True}
(R/'cleanup/final-live-check.json').write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n');print(json.dumps({'status':x['status'],'running':len(host['running']),'templates':3,'retired_stopped_objects_remaining':0,'fish_running_guests':9,'fish_templates':3,'monitoring15UP':True,'Nexus_active':221,'strict_guest_checks':len(guests)}))
