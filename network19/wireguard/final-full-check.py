from pathlib import Path
import sys,json,shlex,datetime,subprocess
from zoneinfo import ZoneInfo
R=Path(__file__).resolve().parents[2];sys.dont_write_bytecode=True;sys.path.insert(0,str(R/'scripts'));import control
info=json.loads((R/'network19/evidence/gateway-initial-access.json').read_text())['target']
G=r'''import subprocess,json
from pathlib import Path
rows=json.loads(subprocess.check_output(['nft','-j','list','table','inet','dell_gateway19']))['nftables'];wanted=[]
for x in rows:
 if 'rule'in x and x['rule'].get('comment','').startswith('WG-TrustedVPN-'):
  r=x['rule'];wanted.append({'chain':r['chain'],'comment':r['comment'],'expr':r['expr']})
print(json.dumps({'WG_rules':wanted,'tables':subprocess.check_output(['nft','list','tables'],text=True).splitlines(),'pending':Path('/var/lib/dell-gateway19/pending.json').exists(),'forward':Path('/proc/sys/net/ipv4/ip_forward').read_text().strip()}))'''
r=control.guest(190,'sudo python3 -c '+shlex.quote(G),info=info,timeout=20);assert r['exit_code']==0;gw=json.loads(r['stdout']);assert len(gw['WG_rules'])==2 and not gw['pending'] and gw['forward']=='1' and gw['tables']==['table inet dell_gateway19']
H=r'''from pathlib import Path
import subprocess,json
rows=json.loads(subprocess.check_output(['nft','-j','list','chain','bridge','dell19_acl','from_gateway']))['nftables'];rules=[x['rule'] for x in rows if 'rule'in x and x['rule'].get('comment')=='trusted-WireGuard-to-server19'];assert len(rules)==1
resources=json.loads(subprocess.check_output(['pvesh','get','/cluster/resources','--type','vm','--output-format','json']));print(json.dumps({'VPN_rule':rules[0],'host_forward':Path('/proc/sys/net/ipv4/ip_forward').read_text().strip(),'all_interface_forward_zero':all(p.read_text().strip()=='0' for fam in ['ipv4','ipv6'] for p in Path('/proc/sys/net',fam,'conf').glob('*/forwarding')),'tables':subprocess.check_output(['nft','list','tables'],text=True).splitlines(),'running_VM':sum(x['status']=='running' and x['type']=='qemu' for x in resources),'running_LXC':sum(x['status']=='running' and x['type']=='lxc' for x in resources),'templates':sum(bool(x.get('template')) for x in resources),'stopped_non_templates':sum(x['status']!='running' and not x.get('template') for x in resources)}))'''
host=json.loads(control.pve('python3 -',data=H.encode(),timeout=30));assert host['host_forward']=='0' and host['all_interface_forward_zero'] and host['tables']==['table bridge dell19_acl']
urls=['http://192.168.19.50:9001/','http://192.168.19.31:8081/','http://192.168.19.60/','http://192.168.19.60:8096/health','http://192.168.19.70:3000/login','http://192.168.19.70:9090/-/ready','http://192.168.19.70:9093/-/ready','http://192.168.19.20:8848/nacos/v1/console/health/readiness','http://192.168.19.11:8848/nacos/v1/console/health/readiness']
local=[]
for u in urls:
 p=subprocess.run(['curl','--noproxy','*','--connect-timeout','3','--max-time','5','-sS','-o','/dev/null','-w','%{http_code}',u],capture_output=True,text=True,timeout=7);local.append({'URL':u,'HTTP':p.stdout,'exit':p.returncode})
assert all(x['exit']==0 and x['HTTP']=='200' for x in local)
media=json.loads((R/'network19/wireguard/media/apply-result.json').read_text());assert media['status']=='VPN-source-recognition-committed-verified'
x={'at':datetime.datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),'status':'trusted-VPN-server-network-access-configured-user-batch-confirmed','source':'10.66.66.0/24','destination':'192.168.19.0/24','protocols':'all valid IPv4','gateway_local_IPs':['192.168.21.23','192.168.19.1'],'GW':gw,'PVE':host,'local_LAN_regression':local,'remote_MacAir10.66.66.3':{'user_confirmation':'全部正常访问','HTTP_batch_targets':urls,'exact_remote_HTTP_codes':'not supplied; do not fabricate specific codes','SMB_auth_and_SSH_login_from_remote':'not individually supplied; transport policy open, original auth preserved','gateway_DNS_optional_test_result':'not separately provided'},'NAS_network_filters':'wireguard/media/apply-result.json','no_SNAT':True,'OpenWrt_peer_per_client32_unchanged':True,'service_credentials_changed':False,'Java_business_programs_started':False}
(R/'network19/wireguard/full-access-verification.json').write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n');print(json.dumps({'status':x['status'],'GW_VPN_rules':len(gw['WG_rules']),'PVE_host_forward':host['host_forward'],'local_HTTP_passed':len(local),'remote_user_confirmed':True,'runningVM':host['running_VM'],'runningLXC':host['running_LXC'],'templates':host['templates'],'stopped':host['stopped_non_templates']}))
