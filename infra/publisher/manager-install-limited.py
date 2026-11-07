#!/usr/bin/env python3
"""Local prepared orchestration. Requires informed user approval before remote security changes."""
import hashlib,importlib.util,io,json,os,shlex,subprocess,sys,tarfile,datetime
from pathlib import Path
from zoneinfo import ZoneInfo
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent;E=ROOT/'evidence/implementation'
s=importlib.util.spec_from_file_location('publisher_control',ROOT/'scripts/control.py');ctl=importlib.util.module_from_spec(s);s.loader.exec_module(ctl)
SNAP=r'''import json,hashlib,subprocess,socket
from pathlib import Path
if socket.gethostname().split('.')[0]!='java-test-01' or Path('/etc/pve').exists():raise SystemExit('240 required')
pointer=Path('/opt/finger/current-test')
if not pointer.is_symlink():raise SystemExit('managed A pointer required')
p=pointer.resolve();m=json.loads((p/'manifest.json').read_text());files={};services=[]
for relative in ['manifest.json']+[r['name']+'/'+f for r in m['services'] for f in ['app.jar','application.yaml','unit.service']]:
 f=p/relative;st=f.stat()
 with f.open('rb') as data:sha=hashlib.file_digest(data,'sha256').hexdigest()
 files[relative]={'sha256':sha,'uid':st.st_uid,'gid':st.st_gid,'mode':oct(st.st_mode&0o777)}
for r in m['services']:
 out=subprocess.run(['systemctl','show','dell-finger-'+r['name']+'.service','--property=MainPID','--property=ExecMainStartTimestampMonotonic','--property=ActiveState','--property=SubState'],capture_output=True,text=True,check=True)
 services.append({'name':r['name'],'state':dict(x.split('=',1) for x in out.stdout.splitlines() if '=' in x)})
policy=Path('/etc/dell-publisher/test240-policy.json')
print(json.dumps({'release':p.name,'pointer':str(p),'core_owner_units':files,'services':services,'baseline_migrated':json.loads(policy.read_text()).get('baseline_migrated') if policy.exists() else None}))'''
COPY=r'''import json,os,socket,subprocess,sys,tarfile,io
from pathlib import Path
vmid=VMID;names=NAMES;installer=INSTALLER;flag=FLAG
if os.geteuid()!=0 or Path('/etc/pve').exists() or socket.gethostname().split('.')[0]!=('java-test-01' if vmid==240 else 'publish-service'):raise SystemExit('scope mismatch')
p=Path('/tmp/dell-publisher-transport')
if p.resolve(strict=False)!=p:raise SystemExit('symlink rejected')
p.mkdir(mode=0o700,exist_ok=True);p.chmod(0o700)
blob=sys.stdin.buffer.read(262145)
if len(blob)>262144:raise SystemExit('trusted code bundle too large')
with tarfile.open(fileobj=io.BytesIO(blob),mode='r:') as t:
 seen=set()
 for m in t:
  if m.name not in names or m.name in seen or not m.isfile() or m.size>65536:raise SystemExit('trusted bundle member rejected')
  seen.add(m.name);f=p/m.name
  if f.is_symlink():raise SystemExit('tool symlink rejected')
  fd=os.open(f,os.O_WRONLY|os.O_CREAT|os.O_TRUNC|os.O_NOFOLLOW,0o600)
  with os.fdopen(fd,'wb') as out:out.write(t.extractfile(m).read())
 if seen!=set(names):raise SystemExit('trusted bundle incomplete')
try:
 with (p/'input.json').open('rb') as public_input:r=subprocess.run(['/usr/bin/python3','-I',str(p/installer),flag],stdin=public_input,capture_output=True,timeout=180)
finally:(p/'input.json').unlink(missing_ok=True)
if r.returncode:raise SystemExit('native transport install failed; public key withheld')
sys.stdout.buffer.write(r.stdout)'''
NEG=r'''import json,subprocess,socket
if socket.gethostname().split('.')[0]!='publish-service':raise SystemExit('220 required')
base=['runuser','--user','publisher','--','ssh','-F','/dev/null','-i','/var/lib/dell-publisher/.ssh/test240_ed25519','-o','IdentitiesOnly=yes','-o','IdentityAgent=none','-o','ForwardAgent=no','-o','RequestTTY=no','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','UserKnownHostsFile=/etc/dell-publisher/known_hosts','-o','HostKeyAlias=dell-test240-publisher','-o','ControlMaster=no','-o','ControlPath=none','-o','ConnectTimeout=8']
checks=[('shell',base+['deployer@10.63.20.20','id']),('sftp',base+['-s','deployer@10.63.20.20','sftp']),('forward',base+['-W','127.0.0.1:22','deployer@10.63.20.20']),('baseline-false-status',['runuser','--user','publisher','--','/usr/local/bin/dell-publish','status'])]
results=[]
for name,args in checks:
 try:
  r=subprocess.run(args,input=b'',capture_output=True,timeout=20);obj=None
  for line in r.stdout.decode(errors='replace').splitlines():
   try:obj=json.loads(line)
   except ValueError:pass
  if name in ('shell','sftp'):passed=r.returncode!=0 and isinstance(obj,dict) and obj.get('ok') is False and 'shell/subsystem' in obj.get('message','')
  elif name=='forward':passed=r.returncode!=0 and 'administratively prohibited' in r.stderr.decode(errors='replace').lower()
  else:passed=r.returncode!=0 and isinstance(obj,dict) and obj.get('ok') is False and obj.get('error_category')=='RuntimeError'
  results.append({'name':name,'exit_code':r.returncode,'expected_rejection':passed,'response':obj,'raw_output_withheld':True})
 except subprocess.TimeoutExpired:results.append({'name':name,'exit_code':124,'expected_rejection':False})
print(json.dumps({'source':'VM220 10.63.30.10','tests':results,'private_key_exported':False}))'''

def save(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
def bundle(files,public_input):
 out=io.BytesIO();data={name:(HERE/name).read_bytes() for name in files};data['input.json']=json.dumps(public_input).encode()
 with tarfile.open(fileobj=out,mode='w',format=tarfile.USTAR_FORMAT) as t:
  for name,content in data.items():
   m=tarfile.TarInfo(name);m.mode=0o600;m.size=len(content);t.addfile(m,io.BytesIO(content))
 return out.getvalue(),list(data)
def guest_strict(target,command):
 proxy=shlex.join(ctl.BASE+['-o','ControlMaster=no','-o','ControlPath=none','-W','%h:%p','root@192.168.21.22'])
 args=ctl.BASE+['-o','ControlMaster=no','-o','ControlPath=none','-o','HostKeyAlias='+target['host_key_alias'],'-o','ProxyCommand='+proxy,'ub@'+target['ip'],command]
 r=subprocess.run(args,capture_output=True,text=True,timeout=60);return {'exit_code':r.returncode,'stdout':r.stdout,'stderr':r.stderr}

def main():
 if sys.argv[1:]!=['--apply-after-informed-user-security-approval']:raise SystemExit('remote security changes require informed user approval first; no action taken')
 rows=json.loads((E/'private-guest-access.json').read_text())['roles'];targets={r['target']['vmid']:r['target'] for r in rows}
 if targets[220]['ip']!='10.63.30.10' or targets[240]['ip']!='10.63.20.20':raise RuntimeError('approved endpoints mismatch')
 report={'at':datetime.datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),'scope':'limited-transport-only','adopt_activate_rollback_requested':False,'application_restart_requested':False,'status':'running'};path=E/'publisher-limited-transport.json'
 before=ctl.guest(240,'sudo -n python3 -',data=SNAP.encode(),timeout=120,info=targets[240])
 if before['exit_code']:raise RuntimeError('240 baseline read failed')
 report['A_before']=json.loads(before['stdout']);save(path,report)
 public=(ROOT/'private/publisher/publisher220-test240.pub').read_text().strip()
 line=next(x for x in (ROOT/'private/known_hosts').read_text().splitlines() if x.startswith(targets[240]['host_key_alias']+' '));part=line.split();trusted=part[1]+' '+part[2]
 jobs=[(220,['publisher_client220.py','publisher_protocol.py','install220-client.py'],{'trusted240_host_public_key':trusted},'install220-client.py','--apply-reviewed220-client-window'),(240,['publisher_root.py','publisher_dispatch.py','publisher_protocol.py','fixed-deploy-test-chain.py','adopt-baseline240.py','install240-transport.py'],{'publisher220_public_key':public},'install240-transport.py','--apply-reviewed240-transport-window')]
 for vmid,files,private,installer,flag in jobs:
  raw,names=bundle(files,private);code=COPY.replace('vmid=VMID','vmid='+str(vmid)).replace('names=NAMES','names='+repr(names)).replace('installer=INSTALLER','installer='+repr(installer)).replace('flag=FLAG','flag='+repr(flag))
  r=ctl.guest(vmid,'sudo -n python3 -c '+shlex.quote(code),data=raw,timeout=240,info=targets[vmid])
  if r['exit_code']:raise RuntimeError('limited transport install failed; no raw key output')
  report['install'+str(vmid)]=json.loads(r['stdout']);save(path,report)
 ub=guest_strict(targets[240],'id -un; hostname');report['ub_strict_reconnect']=ub
 if ub['exit_code'] or ub['stdout'].splitlines()[:2]!=['ub','java-test-01']:raise RuntimeError('strict UB SSH reconnect failed')
 native=ctl.guest(240,'sudo -n sshd -t && sudo -n visudo -cf /etc/sudoers.d/dell-publisher-test240 >/dev/null',timeout=60,info=targets[240]);report['native_sshd_visudo']={'exit_code':native['exit_code']}
 if native['exit_code']:raise RuntimeError('native configuration validation failed')
 negative=ctl.guest(220,'sudo -n python3 -',data=NEG.encode(),timeout=150,info=targets[220])
 if negative['exit_code']:raise RuntimeError('220 negative-test driver failed')
 report['negative_tests']=json.loads(negative['stdout'])
 after=ctl.guest(240,'sudo -n python3 -',data=SNAP.encode(),timeout=120,info=targets[240])
 if after['exit_code']:raise RuntimeError('240 baseline readback failed')
 report['A_after']=json.loads(after['stdout']);report['A_unchanged']=all(report['A_before'][k]==report['A_after'][k] for k in ['release','pointer','core_owner_units','services']);report['baseline_still_false']=report['A_after']['baseline_migrated'] is False
 report['status']='limited-transport-verified-no-app-changes' if report['A_unchanged'] and report['baseline_still_false'] and all(x['expected_rejection'] for x in report['negative_tests']['tests']) else 'limited-transport-test-failed-no-app-actions'
 save(path,report);print(json.dumps({'status':report['status'],'A_unchanged':report['A_unchanged'],'baseline_false':report['baseline_still_false'],'negative':report['negative_tests']}));return 0 if report['status'].endswith('no-app-changes') else 1

if __name__=='__main__':raise SystemExit(main())
