#!/usr/bin/env python3
"""Readonly public source image save -> target220 load, exact same config IDs, no tags/pull/data."""
import importlib.util,json,shlex,subprocess,sys
from pathlib import Path
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
s=importlib.util.spec_from_file_location('r',HERE/'relocate.py');r=importlib.util.module_from_spec(s);s.loader.exec_module(r)
sys.path.insert(0,str(ROOT/'scripts'));import control
control.BASE+=['-o','ForwardAgent=no'];targets=json.loads((ROOT/'network19/evidence/migrated-access.json').read_text())['targets'];ids=list(r.IMAGES.values())
SOURCE=r'''
import json,os,socket,subprocess,sys
from pathlib import Path
assert os.geteuid()==0 and socket.gethostname().split('.')[0]=='artifact-service' and not Path('/etc/pve').exists()
IDS=IMAGE_IDS;D=['/usr/bin/docker','--host','unix:///var/run/docker.sock']
for identity in IDS:
 value=json.loads(subprocess.check_output(D+['image','inspect','--format','{"id":{{json .Id}},"OS":{{json .Os}},"arch":{{json .Architecture}}}',identity],text=True));assert value=={'id':identity,'OS':'linux','arch':'amd64'}
raise SystemExit(subprocess.run(D+['image','save',*IDS],stdout=sys.stdout.buffer).returncode)
'''.replace('IMAGE_IDS',repr(ids))
TARGET=r'''
import json,os,socket,subprocess,sys
from pathlib import Path
assert os.geteuid()==0 and socket.gethostname().split('.')[0]=='publish-service' and not Path('/etc/pve').exists()
IDS=IMAGE_IDS;D=['/usr/bin/docker','--host','unix:///var/run/docker.sock']
info=json.loads(subprocess.check_output(D+['info','--format','{"name":{{json .Name}},"driver":{{json .Driver}},"containers":{{json .Containers}}}'],text=True));assert info=={'name':'publish-service','driver':'overlay2','containers':0}
p=subprocess.run(D+['image','load'],stdin=sys.stdin.buffer,capture_output=True);assert p.returncode==0
loaded=[]
for identity in IDS:
 value=json.loads(subprocess.check_output(D+['image','inspect','--format','{"id":{{json .Id}},"OS":{{json .Os}},"arch":{{json .Architecture}}}',identity],text=True));assert value=={'id':identity,'OS':'linux','arch':'amd64'};loaded.append(value)
assert subprocess.check_output(D+['ps','-aq'],text=True).strip()==''
print(json.dumps({'role':220,'status':'two-exact-public-AMD64-image-IDs-imported-no-stack','images':loaded,'registry_pull_or_tag_change':False,'runtime_data_or_secrets_in_image_stream':False,'Nexus_started':False}))
'''.replace('IMAGE_IDS',repr(ids))

def argv(info,code):
 proxy=shlex.join(control.BASE+['-W','%h:%p','root@192.168.21.22'])
 return control.BASE+['-o','HostKeyAlias='+info['host_key_alias'],'-o','ProxyCommand='+proxy,'ub@'+info['ip'],'sudo /usr/bin/python3 -I -B -c '+shlex.quote(code)]
a=subprocess.Popen(argv(targets['221'],SOURCE),stdout=subprocess.PIPE,stderr=subprocess.PIPE)
b=subprocess.Popen(argv(targets['220'],TARGET),stdin=a.stdout,stdout=subprocess.PIPE,stderr=subprocess.PIPE);a.stdout.close();output,error=b.communicate(timeout=600);a.wait(timeout=40)
if a.returncode or b.returncode:raise SystemExit('Exact public image stream/import unconfirmed; raw output withheld')
value=json.loads(output);(HERE/'image-import-result.json').write_text(json.dumps(value,indent=2)+'\n');print(json.dumps({'role':220,'status':value['status']}))
