#!/usr/bin/env python3
"""Only root-ready candidate QA9043/44/45; no PVE/package/config/service writes."""
import argparse,datetime,hashlib,importlib.util,json,re,shlex,sys
from pathlib import Path
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;spec=importlib.util.spec_from_file_location('window',HERE/'template-window.py');w=importlib.util.module_from_spec(spec);spec.loader.exec_module(w)
MAPPING={9043:(9040,9010,'fish-qa-linux','192.168.19.197'),9044:(9041,9001,'fish-qa-docker','192.168.19.198'),9045:(9042,9011,'fish-qa-java','192.168.19.199')}
CODE=r'''import json,os,socket,subprocess,sys
from pathlib import Path
v=json.load(sys.stdin);c=v['contract'];stage=Path('/root/dell-fish-template-QA-'+str(c['vmid']));assert os.geteuid()==0 and not Path('/etc/pve').exists() and socket.gethostname().split('.')[0]==c['hostname']
links=json.loads(subprocess.run(['ip','-j','addr'],capture_output=True,check=True).stdout);rows=[x for x in links if x.get('address','').lower()==c['mac']];assert len(rows)==1 and [a['local'] for a in rows[0].get('addr_info',[]) if a.get('family')=='inet']==[c['ip']]
assert not stage.exists();stage.mkdir(mode=0o700)
for name,content in [('template-qa.py',v['source']),('contract.json',json.dumps(c))]:
 fd=os.open(stage/name,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
 with os.fdopen(fd,'w') as f:f.write(content)
p=subprocess.run(['python3','-I','-B',str(stage/'template-qa.py'),'--contract',str(stage/'contract.json')],capture_output=True,text=True)
try:receipt=json.loads(p.stdout)
except Exception:receipt={'status':'unparseable-output-withheld'}
assert sorted(x.name for x in stage.iterdir())==['contract.json','template-qa.py']
for file in stage.iterdir():assert file.is_file() and not file.is_symlink();file.unlink()
stage.rmdir();print(json.dumps({'exit_code':p.returncode,'receipt':receipt,'own_QA_stage_removed':not stage.exists()}));raise SystemExit(p.returncode)'''
def install_receipt(builder):
 name='builder9041-install-retry-profile.json' if builder==9041 else 'builder'+str(builder)+'-install.json';e=json.loads((HERE/'evidence'/name).read_text());assert e['exit_code']==0 and e['new_strict_SSH_exit']==0;return e['result']['phases']['install']['receipt']['result']
def main():
 p=argparse.ArgumentParser();p.add_argument('--vmid',type=int,choices=MAPPING,required=True);a=p.parse_args();candidate,source,name,ip=MAPPING[a.vmid];rows=json.loads((HERE/'QA-targets.json').read_text());match=[r for r in rows if r['vmid']==a.vmid and r.get('strict_SSH') is True and r.get('cloud_init_done') is True];assert len(match)==1,'root-QGA-and-strictSSH-ready-required';row=match[0];assert (row['candidate_vmid'],row['source_template'],row['name'],row['IP'])==(candidate,source,name,ip);info=row['target'];assert info['vmid']==a.vmid and info['ip']==ip;mac=re.search(r'virtio=([0-9a-f:]+),',row['net0'].lower()).group(1)
 all_builders=[install_receipt(i) for i in [9040,9041,9042]];base=install_receipt(candidate);c={'purpose':'fish-template-independent-QA','vmid':a.vmid,'source_template':source,'candidate_vmid':candidate,'hostname':name,'ip':ip,'mac':mac,'expected_shells':base['before']['shells'],'protected_files':base['before']['files'],'trusted_hostkey_fingerprint':info['host_key_fingerprint'],'forbidden_machine_id_sha256':[v['machine_id_sha256'] for v in all_builders],'forbidden_hostkey_fingerprints':[v['hostkey_fingerprint'] for v in all_builders]}
 if source==9001:c['forbidden_engine_id_sha256']=[base['before']['docker']['engine_id_sha256']]
 for previous in (HERE/'evidence').glob('QA90*.json'):
  e=json.loads(previous.read_text())
  if e.get('exit_code')==0:
   r=e['result']['receipt'];c['forbidden_machine_id_sha256'].append(r['machine_id_sha256']);c['forbidden_hostkey_fingerprints'].append(r['hostkey_fingerprint'])
   if source==9001 and r.get('extra',{}).get('engine_id_sha256'):c['forbidden_engine_id_sha256'].append(r['extra']['engine_id_sha256'])
 path=HERE/'evidence'/('QA'+str(a.vmid)+'.json');assert not path.exists(),'do-not-overwrite-prior-QA-evidence'
 r=w.control.guest(a.vmid,'sudo -n python3 -I -B -c '+shlex.quote(CODE),data=json.dumps({'source':(HERE/'template-qa.py').read_text(),'contract':c}).encode(),info=info,timeout=180)
 try:value=json.loads(r['stdout'])
 except Exception:value={'status':'unparseable-output-withheld'}
 result={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'vmid':a.vmid,'candidate_source':candidate,'logical_final_template':source,'contract':c,'target':info,'exit_code':r['exit_code'],'result':value,'no_PVE_package_configuration_or_service_actions':True}
 if r['exit_code']==0:
  q=w.control.guest(a.vmid,'python3 -I -B -c '+shlex.quote(w.SMOKE),info=info,timeout=35)
  try:result['new_strict_SSH']=json.loads(q['stdout'])
  except Exception:result['new_strict_SSH']={'fish_newSSH_noconfig_private':False}
  result['new_strict_SSH_exit']=q['exit_code']
 result['released_after_verification']=True;path.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result));return r['exit_code'] or result.get('new_strict_SSH_exit',1)
if __name__=='__main__':raise SystemExit(main())
