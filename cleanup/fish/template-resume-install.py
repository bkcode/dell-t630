#!/usr/bin/env python3
"""Only9041 profile-refusal correction, actual Docker configuration stays unchanged."""
import datetime,importlib.util,json,shlex,sys
from pathlib import Path
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;s=importlib.util.spec_from_file_location('window',HERE/'template-window.py');w=importlib.util.module_from_spec(s);s.loader.exec_module(w)
CODE=r'''import json,subprocess,sys
from pathlib import Path
v=json.load(sys.stdin);stage=Path('/root/dell-fish-template-stage-9041');assert json.loads((stage/'contract.json').read_text())==v['contract'];result={'stage':str(stage),'vmid':9041,'phases':{}}
for phase in ['check','install']:
 cmd=['python3','-I','-B',str(stage/'template-builder.py'),'--contract',str(stage/'contract.json'),'--phase',phase]
 if phase=='install':cmd+=['--window',str(stage/'install-window.json')]
 p=subprocess.run(cmd,capture_output=True,text=True)
 try:receipt=json.loads(p.stdout)
 except Exception:receipt={'status':'unparseable-output-withheld'}
 result['phases'][phase]={'exit_code':p.returncode,'receipt':receipt}
 if p.returncode:print(json.dumps(result));raise SystemExit(1)
print(json.dumps(result))'''
def main():
 path=HERE/'evidence/builder9041-install-retry-profile.json';assert not path.exists();old=json.loads((HERE/'evidence/builder9041-install.json').read_text());refresh=json.loads((HERE/'evidence/builder9041-tool-refresh.json').read_text());assert old['exit_code']!=0 and refresh['exit_code']==0;info=old['target'];c=refresh['contract'];r=w.control.guest(9041,'sudo -n python3 -I -B -c '+shlex.quote(CODE),data=json.dumps({'contract':c}).encode(),info=info,timeout=900)
 try:value=json.loads(r['stdout'])
 except Exception:value={'status':'unparseable-output-withheld'}
 result={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'vmid':9041,'phase':'install-only-reviewed-original-profile-correction','target':info,'contract':c,'exit_code':r['exit_code'],'result':value,'no_seal_no_PVE':True,'original_failed_attempt_preserved':True}
 if r['exit_code']==0:
  q=w.control.guest(9041,'python3 -I -B -c '+shlex.quote(w.SMOKE),info=info,timeout=35)
  try:result['new_strict_SSH']=json.loads(q['stdout'])
  except Exception:result['new_strict_SSH']={'fish_newSSH_noconfig_private':False}
  result['new_strict_SSH_exit']=q['exit_code']
 path.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result));return r['exit_code'] or result.get('new_strict_SSH_exit',1)
if __name__=='__main__':raise SystemExit(main())
