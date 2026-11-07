#!/usr/bin/env python3
"""Actual restricted key negatives from220; no application transition requested."""
import importlib.util,json,shlex,sys
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('ctl',ROOT/'scripts/control.py');ctl=importlib.util.module_from_spec(s);s.loader.exec_module(ctl)
s=importlib.util.spec_from_file_location('limited',HERE/'manager-install-limited.py');limited=importlib.util.module_from_spec(s);s.loader.exec_module(limited)
DRIVER=limited.NEG.split("checks=[",1)[0]+r'''
import io,tarfile,hashlib
checks=[('shell',base+['deployer@10.63.20.20','id'],b''),('sftp',base+['-s','deployer@10.63.20.20','sftp'],b''),('forward',base+['-W','127.0.0.1:22','deployer@10.63.20.20'],b''),('shell-injection',base+['deployer@10.63.20.20','dell-publish-v1 activate 20261106T121030; id'],b''),('unknown-target-option',base+['deployer@10.63.20.20','dell-publish-v1 status --target prod'],b''),('root-helper-extra-argument',base+['deployer@10.63.20.20','sudo /usr/local/libexec/dell-publish-test240 --shell'],b'')]
for i,(label,name,kind) in enumerate([('pax-metadata','manifest.json',tarfile.XHDTYPE),('path-traversal','../../tmp/publisher-escape',tarfile.REGTYPE),('uploaded-script','deploy.py',tarfile.REGTYPE),('symlink','manifest.json',tarfile.SYMTYPE)]):
 out=io.BytesIO()
 with tarfile.open(fileobj=out,mode='w',format=tarfile.USTAR_FORMAT) as t:
  info=tarfile.TarInfo(name);info.type=kind;info.mode=0o600;info.size=1 if kind!=tarfile.SYMTYPE else 0;info.linkname='../../tmp/escape' if kind==tarfile.SYMTYPE else '';t.addfile(info,io.BytesIO(b'x') if info.size else None)
 raw=out.getvalue();rid='20261106T2359'+str(10+i);command='dell-publish-v1 stage '+rid+' '+hashlib.sha256(raw).hexdigest()+' '+str(len(raw));checks.append((label,base+['deployer@10.63.20.20',command],raw))
raw=bytes(10240);checks.append(('wrong-digest',base+['deployer@10.63.20.20','dell-publish-v1 stage 20261106T235920 '+'0'*64+' '+str(len(raw))],raw));checks.append(('immutable-existing-A',base+['deployer@10.63.20.20','dell-publish-v1 stage 20261106T121030 '+hashlib.sha256(raw).hexdigest()+' '+str(len(raw))],raw))
results=[]
for name,args,raw in checks:
 try:
  r=subprocess.run(args,input=raw,capture_output=True,timeout=40);obj=None
  for line in r.stdout.decode(errors='replace').splitlines():
   try:
    frame=json.loads(line)
    if isinstance(frame,dict):obj=frame
   except ValueError:pass
  passed=r.returncode!=0 and (('administratively prohibited' in r.stderr.decode(errors='replace').lower()) if name=='forward' else isinstance(obj,dict) and obj.get('ok') is False)
  results.append({'name':name,'exit_code':r.returncode,'expected_rejection':passed,'response':obj,'raw_output_withheld':True})
 except subprocess.TimeoutExpired:results.append({'name':name,'exit_code':124,'expected_rejection':False})
print(json.dumps({'source':'VM220 10.63.30.10','tests':results,'private_key_exported':False,'real_application_transition_requested':False}))
'''
def main():
 if sys.argv[1:]!=['--apply-approved-negative-tests']:raise SystemExit('explicit approved test window required')
 rows=json.loads((ROOT/'evidence/implementation/private-guest-access.json').read_text())['roles'];targets={r['target']['vmid']:r['target'] for r in rows}
 before=ctl.guest(240,'sudo -n python3 -',data=limited.SNAP.encode(),timeout=120,info=targets[240]);assert before['exit_code']==0
 r=ctl.guest(220,'sudo -n python3 -',data=DRIVER.encode(),timeout=600,info=targets[220]);assert r['exit_code']==0
 v=json.loads(r['stdout']);after=ctl.guest(240,'sudo -n python3 -',data=limited.SNAP.encode(),timeout=120,info=targets[240]);assert after['exit_code']==0
 v['before']=json.loads(before['stdout']);v['after']=json.loads(after['stdout']);v['core_units_pointer_pids_unchanged']=v['before']==v['after'];v['passed']=v['core_units_pointer_pids_unchanged'] and all(t['expected_rejection'] for t in v['tests'])
 (ROOT/'evidence/implementation/publisher-actual-negative-tests.json').write_text(json.dumps(v,indent=2)+'\n');print(json.dumps({'passed':v['passed'],'tests':len(v['tests']),'core_units_pointer_pids_unchanged':v['core_units_pointer_pids_unchanged']}));return 0 if v['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
