#!/usr/bin/env python3
"""Manager-approved bounded packet acceptance; never alters persistent state."""
import json,sys,shlex,datetime,subprocess,time,socket,struct,ipaddress
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts'));import control
E=ROOT/'network19/audit/packet-acceptance.json'
def now():return datetime.datetime.now().astimezone().isoformat()
D=json.loads(E.read_text()) if E.exists() else {'started_at':now(),'scope':'230/231 bounded diagnostic; 3 UDP plus1 SYN only after readiness','persistent_network_ACL_sysctl_mutations':False,'secret_access':False,'stages':[]}
def save():E.write_text(json.dumps(D,ensure_ascii=False,indent=2)+'\n')
def qga(v,code,timeout=40):
 cmd=shlex.join(['qm','guest','exec',str(v),'--timeout','30','--','/usr/bin/python3','-c',code]);r=json.loads(control.pve(cmd,timeout=timeout));assert r.get('exitcode')==0,('bounded diagnostic failed',v,r.get('exitcode'));return json.loads(r['out-data'])
def host(code):return json.loads(control.pve('python3 -',data=code.encode(),timeout=45))
def counters():return host("import json,subprocess; p=subprocess.run(['nft','-j','list','table','bridge','dell19_acl'],capture_output=True,text=True,check=True); print(p.stdout)")
def add(name,result):D['stages'].append({'name':name,'at':now(),'result':result});save()
NORMAL=r'''
import socket,json,subprocess,time,pathlib
assert socket.gethostname()==HOSTNAME and not pathlib.Path('/etc/pve').exists()
ips=json.loads(subprocess.run(['ip','-j','-4','addr'],capture_output=True,text=True,check=True).stdout);assert any(a.get('local')==SOURCE for x in ips for a in x.get('addr_info',[]))
listen=[l.split()[3] for l in subprocess.run(['ss','-lntH'],capture_output=True,text=True,check=True).stdout.splitlines()];results=[];begin=time.monotonic()
for dst,port,label in CASES:
 start=time.monotonic();s=socket.socket();s.settimeout(2)
 try:s.connect((dst,port));ok=True;err=None
 except OSError as e:ok=False;err=type(e).__name__
 finally:s.close()
 results.append({'destination':dst,'port':port,'purpose':label,'TCP_connected':ok,'elapsed_seconds':round(time.monotonic()-start,3),'error_category':err,'payload_sent':False})
print(json.dumps({'hostname':socket.gethostname(),'source_ip':SOURCE,'listeners':listen,'tests':results,'diagnostic_seconds':round(time.monotonic()-begin,2),'no_interface_or_persistent_change':True}))
'''
def normal():
 assert not any(x['name']=='normal-matrix-complete' for x in D['stages']),'refuse repeat completed diagnostic'
 D['normal_counters_before']=counters();save()
 for vm,name,ip,peer in [(230,'java-prod-01','192.168.19.40','192.168.19.41'),(231,'java-prod-02','192.168.19.41','192.168.19.40')]:
  cases=[(peer,22,'peer-SSH-deny'),(peer,9100,'peer-exporter-deny'),('192.168.21.22',22,'host-via-gateway-SSH-deny'),('192.168.21.22',8006,'host-via-gateway-PVE-deny')];r=qga(vm,NORMAL.replace('HOSTNAME',repr(name)).replace('SOURCE',repr(ip)).replace('CASES',repr(cases)));add('guest'+str(vm)+'-ordinary-TCP',r)
 D['normal_counters_after']=counters();save();add('normal-matrix-complete',{'negative_cases':8,'passed_observed_denied':all(not c['TCP_connected'] for s in D['stages'] if s['name'].endswith('-ordinary-TCP') for c in s['result']['tests'])})
# Extra host-originated positives wait for the gateway's planned reboot to finish.
def positive():
 code="""import json,socket,time
out=[]
for ip in ['192.168.19.40','192.168.19.41']:
 for port in [22,9100]:
  s=socket.socket();s.settimeout(3)
  try:s.connect((ip,port));ok=True;err=None
  except OSError as e:ok=False;err=type(e).__name__
  finally:s.close()
  out.append({'source':'192.168.21.22','destination':ip,'port':port,'TCP_connected':ok,'error_category':err,'payload_sent':False})
print(json.dumps({'cases':out,'all_passed':all(x['TCP_connected'] for x in out)}))"""
 r=host(code);add('PVE-management-positive',r);assert r['all_passed']
 vals=json.loads((ROOT/'network19/evidence/migrated-access.json').read_text())['targets'];r=control.guest(230,'id -un; hostname',info=vals['230'],timeout=25);assert r['exit_code']==0 and r['stdout'].strip().splitlines()==['ub','java-prod-01'];add('current-strict-SSH230',{'passed':True,'current_fingerprint':vals['230']['host_key_fingerprint'],'no_trust_bypass':True})

RAW=r"""
import socket,struct,json,subprocess,time,pathlib
P=PARAMETERS
assert socket.gethostname()=='java-prod-01' and not pathlib.Path('/etc/pve').exists()
links=json.loads(subprocess.run(['ip','-j','addr'],capture_output=True,text=True,check=True,timeout=5).stdout);link=next(x for x in links if x.get('address','').lower()==P['source_mac']);assert link['ifname']=='eth0' and any(a.get('local')==P['source_ip'] for a in link.get('addr_info',[]))
def mac(s):return bytes.fromhex(s.replace(':',''))
def checksum(b):
 if len(b)%2:b+=b'\0'
 n=sum(struct.unpack('!%dH'%(len(b)//2),b));n=(n&65535)+(n>>16);n=(n&65535)+(n>>16);return (~n)&65535
def ip(s,d,proto,payload,identifier):
 h=struct.pack('!BBHHHBBH4s4s',69,0,20+len(payload),identifier,0,64,proto,0,socket.inet_aton(s),socket.inet_aton(d));h=h[:10]+struct.pack('!H',checksum(h))+h[12:];return h+payload
def udp(s,d,sport,dport,payload):
 h=struct.pack('!HHHH',sport,dport,8+len(payload),0);pseudo=socket.inet_aton(s)+socket.inet_aton(d)+struct.pack('!BBH',0,17,len(h)+len(payload));c=checksum(pseudo+h+payload) or 65535;return h[:6]+struct.pack('!H',c)+payload
def dns(identifier):
 labels=b''.join(bytes([len(x)])+x for x in [b'dell-network19-packet-test',b'invalid'])+b'\0';return struct.pack('!HHHHHH',identifier,0x0100,1,0,0,0)+labels+struct.pack('!HH',1,1)
def frame(sm,dm,payload):return mac(dm)+mac(sm)+struct.pack('!H',0x0800)+payload
begin=time.monotonic();out={'source':'230','frames':[],'persistent_changes':False,'ARP_frames_sent':0};client=None;raw=None
try:
 client=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);client.bind((P['source_ip'],49553));client.settimeout(5)
 raw=socket.socket(socket.AF_PACKET,socket.SOCK_RAW,socket.htons(0x0800));raw.bind(('eth0',0))
 for case,sm,src,sport,identifier in [('DNS-positive',P['source_mac'],P['source_ip'],49553,0x1901),('wrong-unregistered-MAC',P['bad_mac'],P['source_ip'],49554,0x1902),('wrong-src-IP-own231',P['source_mac'],'192.168.19.41',49555,0x1903)]:
  payload=udp(src,'192.168.19.1',sport,53,dns(identifier));packet=frame(sm,P['gateway_mac'],ip(src,'192.168.19.1',17,payload,identifier));sent=raw.send(packet);assert sent==len(packet);out['frames'].append({'case':case,'protocol':'UDP','source_mac':sm,'source_ip':src,'destination_ip':'192.168.19.1','source_port':sport,'destination_port':53,'sent_packets':1,'bytes':sent,'DNS_query_id':identifier})
  if case=='DNS-positive':
   body,peer=client.recvfrom(512);rid,flags=struct.unpack('!HH',body[:4]);assert peer==('192.168.19.1',53) and rid==identifier and flags&0x8000;out['positive_DNS']={'source':peer[0],'source_port':peer[1],'matching_id':True,'QR_response':True,'RCODE':flags&15,'response_body_saved':False}
  time.sleep(.02)
 tcp=struct.pack('!HHIIBBHHH',49556,22,0x19001900,0,5<<4,2,1024,0,0);pseudo=socket.inet_aton(P['source_ip'])+socket.inet_aton('192.168.21.22')+struct.pack('!BBH',0,6,len(tcp));tcp=tcp[:16]+struct.pack('!H',checksum(pseudo+tcp))+tcp[18:];packet=frame(P['source_mac'],P['host_bridge_mac'],ip(P['source_ip'],'192.168.21.22',6,tcp,0x1904));sent=raw.send(packet);assert sent==len(packet);out['frames'].append({'case':'host-weak-model-direct-L2','protocol':'TCP-SYN','source_ip':P['source_ip'],'source_mac':P['source_mac'],'destination_ip':'192.168.21.22','destination_ethernet_mac':P['host_bridge_mac'],'source_port':49556,'destination_port':22,'sent_packets':1,'bytes':sent,'application_payload_bytes':0});out['status']='bounded-frames-sent'
except Exception as e:out['status']='failed-no-repeat';out['error_class']=type(e).__name__
finally:
 if raw:raw.close()
 if client:client.close()
out['UDP_sent']=sum(x['protocol']=='UDP' for x in out['frames']);out['TCP_SYN_sent']=sum(x['protocol']=='TCP-SYN' for x in out['frames']);out['diagnostic_seconds']=round(time.monotonic()-begin,3);print(json.dumps(out))
"""
def raw():
 assert not D.get('raw_attempt_started'),'refuse repeat of bounded raw packet budget'
 ready=qga(190,"import subprocess,json; p=subprocess.run(['ss','-lnutH'],capture_output=True,text=True,timeout=5); print(json.dumps({'DNS_UDP_ready':any('udp' in l and '192.168.19.1:53' in l for l in p.stdout.splitlines()),'DNS_TCP_ready':any('tcp' in l and '192.168.19.1:53' in l for l in p.stdout.splitlines())}))")
 add('gateway-post-reboot-DNS-listeners',ready)
 if not all(ready.values()):raise SystemExit('gateway planned reboot DNS not ready; no raw frames sent')
 params=host("import pathlib,json; b=pathlib.Path('/sys/class/net/vmbr19/address').read_text().strip(); print(json.dumps({'host_bridge_mac':b}))")
 params.update(source_mac='bc:24:11:1c:20:00',source_ip='192.168.19.40',gateway_mac='02:63:19:01:90:01',bad_mac='02:63:19:fe:00:01');assert params['host_bridge_mac'] not in [params['source_mac'],params['gateway_mac']]
 D['raw_counters_before']=counters();D['raw_attempt_started']=now();D['raw_budget']={'UDP_max':3,'TCP_SYN_max':1,'ARP_max':0,'new_listener':False};save()
 result=qga(230,RAW.replace('PARAMETERS',repr(params)));add('bounded-raw-result',result);D['raw_counters_after']=counters();save()
 assert result['status']=='bounded-frames-sent' and result['UDP_sent']==3 and result['TCP_SYN_sent']==1 and result['ARP_frames_sent']==0

if __name__=='__main__':
 action=sys.argv[1]
 if action=='normal':normal()
 elif action=='positive':positive()
 elif action=='raw':raw()
 else:raise SystemExit('unsupported phase')
 print(json.dumps({'phase':action,'stages':len(D['stages']),'persistent_changes':False}))
