#!/usr/bin/python3
"""Add exactly resource-service DNS record; restart only dnsmasq, never network/firewall."""
import datetime,importlib.util,json,os,pathlib,socket,subprocess,sys
E=pathlib.Path('/etc/dell-gateway19');C=E/'config.json';F=E/'dnsmasq.conf';P=pathlib.Path('/var/lib/dell-gateway19/resource-dns-20261109-r2')
def run(a):
 p=subprocess.run(a,capture_output=True,timeout=20)
 if p.returncode:raise RuntimeError('fixed-resource-DNS-operation-failed')
 return p.stdout

def put(p,b,mode):
 t=p.with_name(p.name+'.resource-tmp');assert not t.exists();fd=os.open(t,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,mode)
 os.fchmod(fd,mode)
 with os.fdopen(fd,'wb')as f:f.write(b);f.flush();os.fsync(f.fileno())
 os.replace(t,p)

def main():
 assert os.geteuid()==0 and socket.gethostname()=='network-gateway' and not pathlib.Path('/etc/pve').exists();assert not pathlib.Path('/var/lib/dell-gateway19/pending.json').exists()
 x=json.load(sys.stdin);oldraw=C.read_bytes();old=json.loads(oldraw);old_dns=F.read_bytes();new=x['config']
 assert [h for h in new['hosts']if h not in old['hosts']]==[{'role':'resource-service','address':'192.168.19.80'}] and new['hosts']==old['hosts']+[{'role':'resource-service','address':'192.168.19.80'}]
 assert {k:v for k,v in new.items()if k not in ['hosts','migration_plan_sha256']}=={k:v for k,v in old.items()if k not in ['hosts','migration_plan_sha256']}
 s=importlib.util.spec_from_file_location('gw_policy','/usr/local/libexec/dell-gateway19/policy.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);i={'WAN':'eth0','LAN':'eth1'};m.validate_config(new);assert m.nft(old,i)==m.nft(new,i) and old_dns==m.dnsmasq(old,i).encode();dns=m.dnsmasq(new,i).encode()
 assert not P.exists();P.mkdir(mode=0o700);os.umask(0o077);(P/'config.before.json').write_bytes(oldraw);(P/'dnsmasq.before.conf').write_bytes(old_dns);(P/'candidate.conf').write_bytes(dns)
 run(['dnsmasq','--test','--conf-file='+str(P/'candidate.conf')])
 try:
  put(C,(json.dumps(new,indent=2)+'\n').encode(),0o600);put(F,dns,0o644);run(['runuser','-u','dnsmasq','--','test','-r',str(F)]);run(['systemctl','restart','dell-gateway19-dnsmasq.service']);run(['systemctl','is-active','--quiet','dell-gateway19-dnsmasq.service'])
 except Exception:
  put(C,oldraw,0o600);put(F,old_dns,0o644);run(['systemctl','restart','dell-gateway19-dnsmasq.service']);raise
 out={'at':datetime.datetime.now().astimezone().isoformat(),'status':'single-resource-DNS-record-added','new_host':'resource-service.dell.home.arpa','IP':'192.168.19.80','only_dnsmasq_restarted':True,'config_firewall_render_unchanged':True,'route_address_networkd_nft_or_NAT_changed':False};(P/'result.json').write_text(json.dumps(out));print(json.dumps(out))
if __name__=='__main__':main()
