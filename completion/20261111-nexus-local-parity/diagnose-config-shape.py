#!/usr/bin/env python3
"""Read only JSON field-shape differences; never emit authentication values."""
import importlib.util,json,socket,sys
from pathlib import Path
assert socket.gethostname()=='publish-service'
x=json.load(sys.stdin);base=Path('/opt/dell/nexus');sys.path.insert(0,str(base));s=importlib.util.spec_from_file_location('shape_api',base/'application-import.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);api=m.API();repos={r['name']:r for r in api.json('GET','/repositories')};rows=[]
for d in x['local_configurations']:
 if d['name']not in repos:continue
 fmt={'maven2':'maven'}.get(d['format'],d['format']);c=api.json('GET','/repositories/'+fmt+'/'+d['type']+'/'+d['name']);diff=[k for k,v in d.items()if k not in ['format','type']and c.get(k)!=v]
 if diff:rows.append({'repository':d['name'],'different_fields':diff,'local_httpClient_keys':sorted(d.get('httpClient',{})),'server_httpClient_keys':sorted(c.get('httpClient',{})),'server_authentication_configured':bool(c.get('httpClient',{}).get('authentication'))})
print(json.dumps({'differences':rows,'server_write_performed':False,'transaction_directory_exists':Path('/root/dell-nexus-local-config-keep-extra-20261111').exists(),'credential_values_output':False}))
