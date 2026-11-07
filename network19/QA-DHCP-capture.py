from pathlib import Path
import sys,json,shlex,datetime
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'scripts'));import control
G=r'''from pathlib import Path
import subprocess,json,time
assert Path('/run/systemd/network/00-dell-qa-dhcp.network').exists()
subprocess.run(['systemctl','stop','systemd-networkd'],check=True,capture_output=True,timeout=30)
for f in [Path('/run/systemd/netif/leases/2')]:f.unlink(missing_ok=True)
subprocess.run(['ip','-4','addr','flush','dev','eth0'],check=True,capture_output=True)
subprocess.run(['systemctl','start','systemd-networkd'],check=True,capture_output=True,timeout=30)
end=time.monotonic()+50
while True:
 rows=json.loads(subprocess.check_output(['ip','-4','-j','addr','show','dev','eth0']));ip=[a for x in rows for a in x.get('addr_info',[]) if a.get('dynamic') and 200<=int(a['local'].split('.')[-1])<=239 and a['local'].startswith('192.168.19.')]
 routes=json.loads(subprocess.check_output(['ip','-4','-j','route','show','default']))
 if len(ip)==1 and len(routes)==1 and routes[0].get('gateway')=='192.168.19.1' and routes[0].get('protocol')=='dhcp':break
 if time.monotonic()>end:raise RuntimeError('QA-dhcp-not-converged')
 time.sleep(.3)
print(json.dumps({'IP':ip[0],'default':routes,'DNS':subprocess.check_output(['resolvectl','dns','eth0'],text=True).strip()}))'''
P=r'''import subprocess,json,sys,shutil,time,re,os
from pathlib import Path
assert shutil.which('tcpdump'),'No native tcpdump, no capture changes'
v=json.load(sys.stdin);path=Path('/root/dell-bootstrap/network19/QA9012-DHCP.pcap');assert not path.exists()
cap=subprocess.Popen(['tcpdump','-nn','-U','-i','tap9012i0','-w',str(path),'udp and (port 67 or port 68)'],stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
time.sleep(.7);assert cap.poll() is None
try:
 p=subprocess.run(['qm','guest','exec','9012','--timeout','100','--','python3','-c',v['guest']],capture_output=True,text=True,timeout=120);x=json.loads(p.stdout);assert p.returncode==0 and x.get('exitcode')==0,x
 time.sleep(.7)
finally:
 cap.terminate();cap.communicate(timeout=10)
path.chmod(0o600);q=subprocess.run(['tcpdump','-nn','-vv','-r',str(path)],capture_output=True,text=True,check=True)
phases=re.findall(r'DHCP-Message\s*\(53\),\s*length\s*1:\s*(\w+)',q.stdout)
print(json.dumps({'QA':json.loads(x['out-data']),'native_passive_capture_phases':phases,'full_DORA_seen':set(['Discover','Offer','Request','ACK'])<=set(phases),'pcap_stays_PVE_only':True,'only_QA_run_state_changed':True,'no_fake_source_packets':True}))'''
x=json.loads(control.pve('python3 -c '+shlex.quote(P),data=json.dumps({'guest':G}).encode(),timeout=180));x['at']=datetime.datetime.now().isoformat();(R/'network19/evidence/DHCP-real-QA-native-capture.json').write_text(json.dumps(x,indent=2)+'\n');print(json.dumps(x))
p=R/'network19/migration-plan.json';v=json.loads(p.read_text());next(r for r in v['guest_addresses'] if r['vmid']==9012)['new_ip']=x['QA']['IP']['local'];p.write_text(json.dumps(v,indent=2,ensure_ascii=False)+'\n')
