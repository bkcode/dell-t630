#!/usr/bin/env python3
"""Read-only current Puyu repository/security and publisher contract audit; no secrets output."""
import importlib.util,json,os,socket,subprocess,sys
from pathlib import Path
assert os.geteuid()==0 and socket.gethostname()=='publish-service'
base=Path('/opt/dell/nexus');sys.path.insert(0,str(base));spec=importlib.util.spec_from_file_location('nexus_current',base/'application-import.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);api=m.API()
repos=api.json('GET','/repositories');out=[]
for r in repos:
 row={k:r[k]for k in ['name','type','format']}
 if r['format']=='maven2':
  c=api.json('GET','/repositories/maven/'+r['type']+'/'+r['name']);row['online']=c['online']
  if r['type']=='hosted':row.update(write_policy=c['storage']['writePolicy'],maven=c['maven'])
  if r['type']=='group':row['members']=c['group']['memberNames']
 out.append(row)
roles=api.json('GET','/security/roles');users=api.json('GET','/security/users')
managed=Path('/srv/dell-build/deploy-public/repos');contracts={}
for p in managed.iterdir():
 if not(p/'.git').is_dir():continue
 settings=(p/'settings.gradle.kts').read_text()if(p/'settings.gradle.kts').exists()else''
 publish='\n'.join(f.read_text()for f in p.glob('*/build.gradle.kts'))
 if (p/'build.gradle.kts').exists():publish+=(p/'build.gradle.kts').read_text()
 contracts[p.name]={'HEAD':subprocess.check_output(['runuser','-u','ub','--','git','-C',str(p),'rev-parse','HEAD']).decode().strip(),'uses_NEXUS_URL':'NEXUS_URL'in settings,'uses_NEXUS_USERNAME':'NEXUS_USERNAME'in settings,'uses_NEXUS_PASSWORD':'NEXUS_PASSWORD'in settings,'HTTP_read_opt_in':('isAllowInsecureProtocol'in settings or'allowInsecureProtocol'in settings),'uses_NEXUS_PUBLISH_URL':'NEXUS_PUBLISH_URL'in publish,'HTTP_publish_opt_in':('isAllowInsecureProtocol'in publish or'allowInsecureProtocol'in publish)}
net=json.loads(subprocess.check_output(['docker','network','inspect','nexus_backend']))[0]
print(json.dumps({'repositories':out,'puyu_users':[{'userId':u['userId'],'status':u['status'],'roles':u['roles']}for u in users if'puyu'in u['userId']],'puyu_roles':[r for r in roles if'puyu'in r['id']],'anonymous_enabled':api.json('GET','/security/anonymous')['enabled'],'EULA_accepted':api.json('GET','/system/eula')['accepted'],'Nexus_backend_internal':net['Internal'],'publisher_source_contracts':contracts,'Nexus_unit':subprocess.check_output(['systemctl','is-active','dell-nexus.service']).decode().strip(),'mutations':False,'credential_values_output':False}))
