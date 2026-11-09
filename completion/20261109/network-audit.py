#!/usr/bin/env python3
"""One-time read-only network/CF liveness; no credentials or configuration writes."""
import sys,json,shlex,subprocess,datetime
from pathlib import Path
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts'));import control
CF=r'''import json,urllib.request
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with op.open('http://127.0.0.1:20241/ready',timeout=4) as r:v=json.load(r);print(json.dumps({'HTTP':r.status,'readyConnections':v.get('readyConnections')}))'''
GW=r'''import json,subprocess,socket,struct,random,pathlib
out={'forward4':pathlib.Path('/proc/sys/net/ipv4/ip_forward').read_text().strip(),'units':{}}
for unit in ['dell-gateway19-firewall.service','dell-gateway19-ready.service','dell-gateway19-dnsmasq.service']:
 out['units'][unit]=subprocess.check_output(['systemctl','show',unit,'--property=ActiveState,SubState,Result'],text=True).splitlines()
out['physical_IPs']=[a['local'] for n in json.loads(subprocess.check_output(['ip','-4','-j','addr'])) for a in n.get('addr_info',[]) if n['ifname']!='lo'];out['DNS']={}
for name in ['penpot-service.dell.home.arpa','artifact-service.dell.home.arpa','publish-service.dell.home.arpa']:
 ident=random.randrange(65536);question=struct.pack('!HHHHHH',ident,256,1,0,0,0)+b''.join(bytes([len(p)])+p.encode() for p in name.split('.'))+b'\0'+struct.pack('!HH',1,1)
 with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as s:s.settimeout(3);s.sendto(question,('192.168.19.1',53));raw=s.recv(4096)
 assert struct.unpack('!H',raw[:2])[0]==ident
 def skip(i):
  while raw[i]:
   if raw[i]&192==192:return i+2
   i+=raw[i]+1
  return i+1
 pos=skip(12)+4;answers=[]
 for _ in range(struct.unpack('!H',raw[6:8])[0]):
  pos=skip(pos);typ,cls,ttl,size=struct.unpack('!HHIH',raw[pos:pos+10]);pos+=10
  if typ==1 and size==4:answers.append(socket.inet_ntoa(raw[pos:pos+4]))
  pos+=size
 out['DNS'][name]={'rcode':raw[3]&15,'A':answers}
print(json.dumps(out))'''
cf=json.loads(control.pve(shlex.join(['pct','exec','100','--','python3','-B','-c',CF]),timeout=15))
info=json.loads((ROOT/'network19/evidence/gateway-initial-access.json').read_text())['target'];r=control.guest(190,'sudo -n python3 -B -',data=GW.encode(),info=info,timeout=30);assert r['exit_code']==0;gw=json.loads(r['stdout']);HTTP=[]
for url in ['https://192.168.21.22:8006/','http://192.168.19.31:8081/','http://192.168.19.50:9001/','http://192.168.19.60/','http://192.168.19.60:8096/health','http://192.168.19.70:3000/login']:
 args=['curl','--noproxy','*','--connect-timeout','3','--max-time','6','-sS','-o','/dev/null','-w','%{http_code}'];args+=['-k'] if url.startswith('https') else []
 p=subprocess.run(args+[url],capture_output=True,text=True,timeout=8);HTTP.append({'URL':url,'exit':p.returncode,'HTTP':p.stdout,'scope':'reachability; PVEselfsignedTLS not authenticated by curl' if url.startswith('https') else 'public landing/health only; no app authentication'})
result={'at':datetime.datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),'scope':'read-only liveness; no active externalVPN or Cloudflarepublicorigin E2E test','CF':cf,'gateway':gw,'HTTP':HTTP,'credentials_read':False,'writes_to_server':False}
(ROOT/'completion/20261109/network-audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False,indent=2))
