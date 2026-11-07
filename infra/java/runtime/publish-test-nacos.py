#!/usr/bin/env python3
"""Publish only prepared test namespace/group files; apply is target-guest-only."""
import argparse,hashlib,json,os,socket,sys,time,urllib.error,urllib.parse,urllib.request
from pathlib import Path
NAMES=['finger-common.yaml','finger-auth.yaml','finger-service-system.yaml','finger-service-coms.yaml','finger-bff-system.yaml','finger-gateway-mobile-lan-v2.yaml']
class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,*args,**kwargs):return None

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--package',required=True,type=Path);p.add_argument('--data-bundle',required=True,type=Path);p.add_argument('--apply',action='store_true');p.add_argument('--output',type=Path);a=p.parse_args()
 meta=json.loads((a.package/'metadata.json').read_text());assert meta['target']['data_ip']=='10.63.20.10' and meta['nacos_group']=='DELL_TEST'
 config={}
 for line in (a.data_bundle/'.env').read_text().splitlines():
  if '=' in line and not line.startswith('#'):k,v=line.split('=',1);config[k]=v
 assert config['ENVIRONMENT']=='test' and config['SERVICE_IP']=='10.63.20.10' and config['NACOS_NAMESPACE_ID']==meta['nacos_namespace']
 files={name:a.package/'nacos-configs/DELL_TEST'/name for name in NAMES}
 assert all(p.is_file() and not p.is_symlink() and not p.stat().st_mode&0o077 for p in files.values())
 if not a.apply:print(json.dumps({'status':'prepared-files-validated-no-api-write','configs':len(files)}));return
 assert os.geteuid()==0 and not Path('/etc/pve').exists() and socket.gethostname().split('.')[0] in ['data-test','test-data']
 addresses=json.loads(__import__('subprocess').check_output(['ip','-j','addr'],text=True));assert any(v.get('local')=='10.63.20.10' for n in addresses for v in n.get('addr_info',[]))
 secret=a.data_bundle/'secrets/nacos-admin-password';assert not secret.stat().st_mode&0o077
 password=secret.read_text().strip();base='http://10.63.20.10:8848/nacos';opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect)
 def request(method,path,values=None,token=None,missing_ok=False):
  headers={};body=None
  if token:headers['Authorization']='Bearer '+token
  if values is not None:
   encoded=urllib.parse.urlencode(values)
   if method=='GET':path+='?'+encoded
   else:body=encoded.encode();headers['Content-Type']='application/x-www-form-urlencoded'
  try:
   with opener.open(urllib.request.Request(base+path,data=body,method=method,headers=headers),timeout=15) as r:return r.read(1024*1024)
  except urllib.error.HTTPError as e:
   if missing_ok and e.code==404:return None
   raise RuntimeError('Nacos '+method+' '+path.split('?')[0]+' HTTP status '+str(e.code)) from None
 token=json.loads(request('POST','/v1/auth/users/login',{'username':'nacos','password':password}))['accessToken']
 records=[]
 for name,path in files.items():
  content=path.read_text();payload={'dataId':name,'group':'DELL_TEST','tenant':meta['nacos_namespace'],'type':'yaml','content':content}
  existing=request('GET','/v1/cs/configs',{k:payload[k] for k in ['dataId','group','tenant']},token,missing_ok=True)
  if existing is not None:
   assert hashlib.sha256(existing).hexdigest()==hashlib.sha256(content.encode()).hexdigest(),'Existing same-ID config differs; use a separately reviewed version/group, never overwrite rollback inputs'
  else:
   assert request('POST','/v1/cs/configs',payload,token).decode().strip()=='true','Config publication rejected'
  restored=None
  for attempt in range(30):
   restored=request('GET','/v1/cs/configs',{k:payload[k] for k in ['dataId','group','tenant']},token,missing_ok=True)
   if restored is not None:break
   time.sleep(1)
  assert restored is not None,'Published config did not become readable within 30 seconds'
  assert hashlib.sha256(restored).hexdigest()==hashlib.sha256(content.encode()).hexdigest(),'Published content hash mismatch'
  records.append({'data_id':name,'sha256':hashlib.sha256(restored).hexdigest()})
 result={'status':'target-test-nacos-configs-published-and-hash-verified','target_ip':'10.63.20.10','nacos_configs_ready':True,'group':'DELL_TEST','config_count':len(records),'configs':records,'runtime_started':False,'credential_values_emitted':False}
 if a.output:
  a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');a.output.chmod(0o600)
 print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':
 try:main()
 except Exception as e:print(json.dumps({'status':'failed','error_category':type(e).__name__,'message':str(e)}));sys.exit(1)
