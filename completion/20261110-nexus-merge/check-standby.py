#!/usr/bin/env python3
"""Source hashes stream directly to target for private CAS, never emitted locally."""
import importlib.util,json,shlex,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts'));import control
spec=importlib.util.spec_from_file_location('relocation',ROOT/'cleanup/nexus/relocate.py');r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)
info=json.loads((ROOT/'network19/evidence/migrated-access.json').read_text())['targets'];nonce=json.loads((ROOT/'cleanup/nexus/standby-window.json').read_text())['nonce']
source='''import hashlib,json,os,socket\nfrom pathlib import Path\nassert os.geteuid()==0 and socket.gethostname()=='artifact-service'\nfiles=FILES\nprint(json.dumps({k:{'sha256':hashlib.sha256(Path(p).read_bytes()).hexdigest(),'size':Path(p).stat().st_size}for k,p in files.items()}))\n'''.replace('FILES',repr(r.FILES))
target='''import hashlib,json,os,socket,sys\nfrom pathlib import Path\nassert os.geteuid()==0 and socket.gethostname()=='publish-service'\nbase=Path('/root/dell-nexus-merge')/NONCE\ncurrent=json.load(sys.stdin);old=json.loads((base/'incoming/private-manifest.json').read_text())['files']\nassert current==old,'source13-file-drift'\nj=json.loads((base/'relocation.json').read_text());assert j['phase']=='prepared-no-active-install'\nassert all(hashlib.sha256((base/'prepared'/k.replace('/','__')).read_bytes()).hexdigest()==v['sha256']for k,v in j['entries'].items())\nassert all(not Path(p).exists()for p in ['/opt/dell/nexus','/etc/nexus.env','/root/dell-nexus-secrets','/etc/systemd/system/dell-nexus.service'])\nprint(json.dumps({'source_13_files_equal_prepared_baseline':True,'private_hashes_or_credentials_output':False,'phase':j['phase'],'prepared_checksums_valid':True,'active_Nexus_paths_absent':True}))\n'''.replace('NONCE',repr(nonce))
def argv(v,code):
 x=info[str(v)];proxy=shlex.join(control.BASE+['-W','%h:%p','root@192.168.21.22'])
 return control.BASE+['-o','HostKeyAlias='+x['host_key_alias'],'-o','ProxyCommand='+proxy,'ub@'+x['ip'],'sudo -n '+shlex.join(['python3','-I','-B','-c',code])]
a=subprocess.Popen(argv(221,source),stdout=subprocess.PIPE,stderr=subprocess.PIPE);b=subprocess.Popen(argv(220,target),stdin=a.stdout,stdout=subprocess.PIPE,stderr=subprocess.PIPE);a.stdout.close();output,error=b.communicate(timeout=80);a.wait(timeout=20)
assert a.returncode==0 and b.returncode==0,'standby-private-CAS-failed'
d=json.loads(output);(Path(__file__).parent/'standby-current-CAS.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d))
