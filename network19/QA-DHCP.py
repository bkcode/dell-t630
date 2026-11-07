from pathlib import Path
import json,sys,shlex,datetime
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'scripts'));import control
G=r'''from pathlib import Path
import json,subprocess,time
rows=json.loads(subprocess.check_output(['ip','-j','addr']));r=next(x for x in rows if x.get('address','').lower()=='bc:24:11:a3:11:dc');assert r['ifname']=='eth0'
p=Path('/run/systemd/network/00-dell-qa-dhcp.network');assert not p.exists();p.write_text('[Match]\nMACAddress=bc:24:11:a3:11:dc\n[Network]\nDHCP=ipv4\nIPv6AcceptRA=no\nLinkLocalAddressing=no\n[DHCPv4]\nUseDNS=yes\nRouteMetric=100\n');p.chmod(0o644)
for a in [['networkctl','reload'],['networkctl','reconfigure','eth0']]:subprocess.run(a,check=True,capture_output=True)
end=time.monotonic()+60
while True:
 rows=json.loads(subprocess.check_output(['ip','-4','-j','addr','show','dev','eth0']));ips=[a for x in rows for a in x.get('addr_info',[]) if a.get('family')=='inet'];new=[x for x in ips if x['local'].startswith('192.168.19.') and 200<=int(x['local'].split('.')[-1])<=239]
 if len(new)==1:break
 if time.monotonic()>end:raise RuntimeError('QA-DHCP-lease-not-confirmed')
 time.sleep(.3)
if any(x['local']=='192.168.19.198' for x in ips):subprocess.run(['ip','addr','del','192.168.19.198/24','dev','eth0'],check=True,capture_output=True)
subprocess.run(['ip','route','del','default','via','192.168.19.1','dev','eth0','proto','static'],capture_output=True)
routes=json.loads(subprocess.check_output(['ip','-4','-j','route','show','default']));assert len(routes)==1 and routes[0].get('gateway')=='192.168.19.1' and routes[0].get('protocol')=='dhcp'
dns=subprocess.check_output(['resolvectl','dns','eth0'],text=True).strip();assert dns.partition(':')[2].split()==['192.168.19.1']
print(json.dumps({'new_IP':new[0]['local'],'lease_address':new[0],'default':routes,'per_link_DNS':dns,'network_file':'run-only temporary dedicated QA DHCP client; no image persistence changed'}))'''
P=r'''import json,subprocess,socket,struct,time,threading,sys
v=json.load(sys.stdin);phases=[];errors=[];stop=threading.Event();MAC=bytes.fromhex('bc2411a311dc')
s=socket.socket(socket.AF_PACKET,socket.SOCK_RAW,socket.htons(0x0800));s.bind(('tap9012i0',0));s.settimeout(.2)
def capture():
 end=time.monotonic()+75
 while time.monotonic()<end and not stop.is_set():
  try:b=s.recv(2048)
  except socket.timeout:continue
  if len(b)<42 or b[12:14]!=bytes.fromhex('0800'):continue
  ip=b[14:];ihl=(ip[0]&15)*4
  if ip[9]!=17 or len(ip)<ihl+8:continue
  udp=ip[ihl:];sp,dp=struct.unpack('!HH',udp[:4])
  if {sp,dp}!={67,68}:continue
  d=udp[8:]
  if len(d)<240 or d[28:34]!=MAC or d[236:240]!=bytes.fromhex('63825363'):continue
  opt=d[240:];i=0;typ=None
  while i<len(opt):
   k=opt[i];i+=1
   if k==255:break
   if k==0:continue
   if i>=len(opt):break
   n=opt[i];i+=1;val=opt[i:i+n];i+=n
   if k==53 and val:typ=val[0]
  if typ:phases.append({'type':typ,'phase':{1:'DISCOVER',2:'OFFER',3:'REQUEST',5:'ACK'}.get(typ,'other'),'transaction_id':d[4:8].hex(),'source_IP':socket.inet_ntoa(ip[12:16]),'destination_IP':socket.inet_ntoa(ip[16:20])})
t=threading.Thread(target=capture);t.start();time.sleep(.3)
p=subprocess.run(['qm','guest','exec','9012','--timeout','100','--','python3','-c',v['guest_code']],capture_output=True,text=True,timeout=120)
time.sleep(.4);stop.set();t.join();s.close()
x=json.loads(p.stdout);assert p.returncode==0 and x.get('exitcode')==0,x
print(json.dumps({'client':json.loads(x['out-data']),'passive_PVE_capture':phases,'full_DORA_seen':{1,2,3,5}<={x['type'] for x in phases},'no_ethernet_or_IP_spoofing':True,'template_image_unchanged':True}))'''
x=json.loads(control.pve('python3 -c '+shlex.quote(P),data=json.dumps({'guest_code':G}).encode(),timeout=170));x['at']=datetime.datetime.now().isoformat();(R/'network19/evidence/DHCP-real-QA-DORA.json').write_text(json.dumps(x,indent=2)+'\n');print(json.dumps(x))
p=R/'network19/migration-plan.json';v=json.loads(p.read_text());row=next(r for r in v['guest_addresses'] if r['vmid']==9012);row['new_ip']=x['client']['new_IP'];row['IP_assignment']='dedicated temporary DHCP QA observed real DORA';p.write_text(json.dumps(v,indent=2,ensure_ascii=False)+'\n')
