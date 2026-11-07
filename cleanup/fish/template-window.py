#!/usr/bin/env python3
"""Authorized installation only; root owns all VM lifecycle and later seal window."""
import argparse,datetime,hashlib,json,re,shlex,sys
from pathlib import Path
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];sys.path.insert(0,str(ROOT/'scripts'));import control
ROLES={9040:(9010,'fish-build-linux','192.168.19.197','bc:24:11:8f:30:c7'),9041:(9001,'fish-build-docker','192.168.19.198','bc:24:11:a6:72:55'),9042:(9011,'fish-build-java','192.168.19.199','bc:24:11:db:14:ec')}
STAGE=r'''import json,os,socket,stat,subprocess,sys
from pathlib import Path
v=json.load(sys.stdin);c=v['contract'];stage=Path('/root/dell-fish-template-stage-'+str(c['vmid']))
assert os.geteuid()==0 and not Path('/etc/pve').exists() and socket.gethostname().split('.')[0]==c['hostname']
links=json.loads(subprocess.run(['ip','-j','addr'],capture_output=True,check=True).stdout);rows=[x for x in links if x.get('address','').lower()==c['mac']];assert len(rows)==1 and [x['local'] for x in rows[0].get('addr_info',[]) if x.get('family')=='inet']==[c['ip']]
assert not stage.exists();stage.mkdir(mode=0o700)
for name,content in v['files'].items():
 assert name in ['template-builder.py','install-guest.py','contract.json','install-window.json']
 fd=os.open(stage/name,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
 with os.fdopen(fd,'w') as file:file.write(content)
result={'stage':str(stage),'vmid':c['vmid'],'phases':{}}
for phase in ['check','install']:
 command=['python3','-I','-B',str(stage/'template-builder.py'),'--contract',str(stage/'contract.json'),'--phase',phase]
 if phase=='install':command+=['--window',str(stage/'install-window.json')]
 p=subprocess.run(command,capture_output=True,text=True)
 try:x=json.loads(p.stdout)
 except Exception:x={'status':'unparseable-sanitized-receipt','raw_output_withheld':True}
 result['phases'][phase]={'exit_code':p.returncode,'receipt':x}
 if p.returncode:print(json.dumps(result));raise SystemExit(1)
print(json.dumps(result))'''
SMOKE=r'''import json,os,pwd,subprocess,tempfile
from pathlib import Path
assert pwd.getpwuid(os.geteuid()).pw_name=='ub'
with tempfile.TemporaryDirectory(prefix='dell-fish-newSSH-') as tmp:
 for n in ['config','cache','data']:(Path(tmp)/n).mkdir(mode=0o700)
 env=dict(os.environ,XDG_CONFIG_HOME=tmp+'/config',XDG_CACHE_HOME=tmp+'/cache',XDG_DATA_HOME=tmp+'/data')
 p=subprocess.run(['/usr/bin/fish','--no-config','--private','-c','printf fish-smoke-ok'],capture_output=True,text=True,env=env,timeout=20)
 ok=p.returncode==0 and p.stdout=='fish-smoke-ok';print(json.dumps({'user':'ub','shell':pwd.getpwuid(os.geteuid()).pw_shell,'fish_newSSH_noconfig_private':ok,'temporary_smoke_cleaned':True}));raise SystemExit(0 if ok else 1)'''
def main():
 p=argparse.ArgumentParser();p.add_argument('--vmid',type=int,choices=ROLES,required=True);a=p.parse_args();source,name,ip,mac=ROLES[a.vmid]
 rows=json.loads((HERE/'builder-targets.json').read_text());matches=[x for x in rows if x['vmid']==a.vmid and x.get('strict_SSH') is True and x.get('cloud_init_done') is True];assert len(matches)==1,'root strict ready target required';row=matches[0];assert row['source_template']==source and row['name']==name and row['IP']==ip and re.search(r'virtio='+re.escape(mac)+r'(?:,|$)',row['net0'].lower());info=row['target'];assert info['vmid']==a.vmid and info['ip']==ip
 contract={'schema_version':1,'vmid':a.vmid,'source_template':source,'hostname':name,'ip':ip,'mac':mac,'fish_version':'4.0.2-1','no_chsh':True};window={'vmid':a.vmid,'allowed_phase':'install','expires_at':(datetime.datetime.now(datetime.timezone.utc)+datetime.timedelta(hours=1)).isoformat(),'contract_sha256':hashlib.sha256(json.dumps(contract,sort_keys=True,separators=(',',':')).encode()).hexdigest()}
 files={n:(HERE/n).read_text() for n in ['template-builder.py','install-guest.py']};files.update({'contract.json':json.dumps(contract),'install-window.json':json.dumps(window)})
 r=control.guest(a.vmid,'sudo -n python3 -I -B -c '+shlex.quote(STAGE),data=json.dumps({'contract':contract,'files':files}).encode(),timeout=900,info=info)
 try:value=json.loads(r['stdout'])
 except Exception:value={'status':'unparseable-remote-receipt','raw_output_withheld':True}
 result={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'vmid':a.vmid,'phase':'install-only','exit_code':r['exit_code'],'target':info,'contract':contract,'result':value,'no_seal_no_PVE':True}
 if r['exit_code']==0:
  q=control.guest(a.vmid,'python3 -I -B -c '+shlex.quote(SMOKE),timeout=35,info=info)
  try:result['new_strict_SSH']=json.loads(q['stdout'])
  except Exception:result['new_strict_SSH']={'fish_newSSH_noconfig_private':False}
  result['new_strict_SSH_exit']=q['exit_code']
 path=HERE/'evidence'/('builder'+str(a.vmid)+'-install.json');assert not path.exists(),'never overwrite earlier attempt evidence';path.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result));return r['exit_code'] or (0 if result.get('new_strict_SSH_exit')==0 else 1)
if __name__=='__main__':raise SystemExit(main())
