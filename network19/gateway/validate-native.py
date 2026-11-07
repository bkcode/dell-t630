#!/usr/bin/env python3
"""Only guest190 standby native parsers, no rule load or unit activation."""
import base64,datetime,hashlib,importlib.util,json,shlex,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('ctl',ROOT/'scripts/control.py');c=importlib.util.module_from_spec(s);s.loader.exec_module(c)
CODE=r'''import base64,datetime,importlib.util,json,os,socket,subprocess,sys
from pathlib import Path
if os.geteuid()!=0 or Path('/etc/pve').exists() or socket.gethostname().split('.')[0]!='network-gateway':raise SystemExit('190 only')
before={key:subprocess.run(['sysctl','-n',key],capture_output=True,check=True).stdout.decode().strip() for key in ['net.ipv4.ip_forward','net.ipv4.conf.all.forwarding','net.ipv4.conf.eth0.forwarding','net.ipv4.conf.eth1.forwarding']}
if set(before.values())!={'0'}:raise SystemExit('all+interfaces forwarding0 standby required')
folder=Path('/tmp/dell-gateway19-nativecheck')
if folder.resolve(strict=False)!=folder:raise SystemExit('no symlink')
folder.mkdir(mode=0o700,exist_ok=True);raw=sys.stdin.buffer.read(262145)
if len(raw)>262144:raise SystemExit('public native tool cap')
values=json.loads(raw)
for name,data in values.items():
 if name not in ['policy.py','manage.py','config.json']:raise SystemExit('fixed tools only')
 file=folder/name
 if file.is_symlink():raise SystemExit('no symlink')
 file.write_bytes(base64.b64decode(data,validate=True));file.chmod(0o600)
s=importlib.util.spec_from_file_location('policy_checked',folder/'policy.py');p=importlib.util.module_from_spec(s);s.loader.exec_module(p);config=json.loads((folder/'config.json').read_text());p.validate_config(config);links=json.loads(subprocess.run(['ip','-j','link'],capture_output=True,check=True).stdout);interfaces={}
for role in ['WAN','LAN']:
 matches=[r for r in links if r.get('address','').lower()==config[role+'_MAC']]
 if len(matches)!=1:raise SystemExit('MAC mismatch')
 interfaces[role]=matches[0]['ifname']
(folder/'candidate.nft').write_text(p.nft(config,interfaces));(folder/'candidate-dnsmasq.conf').write_text(p.dnsmasq(config,interfaces))
s=importlib.util.spec_from_file_location('manage_checked',folder/'manage.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);unitdir=folder/'units';unitdir.mkdir(mode=0o700,exist_ok=True)
for name,text in m.units((datetime.datetime.now(datetime.timezone.utc)+datetime.timedelta(seconds=180)).strftime('%Y-%m-%d %H:%M:%S UTC')).items():
 # For parser-only verification substitute the fixed Python executable for not-yet-installed script path.
 (unitdir/name).write_text(text)
checks=[]
commands=[('nft-check',['nft','--check','--file',str(folder/'candidate.nft')]),('dnsmasq-test',['dnsmasq','--test','--conf-file='+str(folder/'candidate-dnsmasq.conf')]),('systemd-unit-check',['systemd-analyze','verify',*[str(x) for x in unitdir.iterdir()]])]
for label,args in commands:
 r=subprocess.run(args,capture_output=True,text=True,timeout=30);checks.append({'name':label,'exit_code':r.returncode,'output':(r.stdout+r.stderr)[-4000:]})
after={key:subprocess.run(['sysctl','-n',key],capture_output=True,check=True).stdout.decode().strip() for key in before};tables=json.loads(subprocess.run(['nft','-j','list','ruleset'],capture_output=True,check=True).stdout)
print(json.dumps({'status':'standby-native-checks-passed' if all(x['exit_code']==0 for x in checks) and before==after else 'failed','checks':checks,'forward_before':before,'forward_after':after,'interfaces_by_MAC':interfaces,'kernel_tables':[x['table']['name'] for x in tables['nftables'] if 'table'in x],'services_started':False,'firewall_loaded':False}))'''
def main():
 target=json.loads((HERE.parent/'evidence/gateway-initial-access.json').read_text())['target'];raw=json.dumps({name:base64.b64encode((HERE/name if name.endswith('.py') else HERE/'bundle'/name).read_bytes()).decode() for name in ['policy.py','manage.py','config.json']}).encode();result=c.guest(190,'sudo -n python3 -c '+shlex.quote(CODE),data=raw,timeout=120,info=target)
 if result['exit_code']:raise RuntimeError('native standalone parser driver failed; raw withheld')
 value={'at':datetime.datetime.now().astimezone().isoformat(),'scope':'190-native-check-only','code_sha256':{x:hashlib.sha256((HERE/x).read_bytes()).hexdigest() for x in ['policy.py','manage.py']},'result':json.loads(result['stdout'])};(HERE/'native-parse-evidence.json').write_text(json.dumps(value,indent=2)+'\n');print(json.dumps(value));return 0 if value['result']['status']=='standby-native-checks-passed' else 1
if __name__=='__main__':raise SystemExit(main())
