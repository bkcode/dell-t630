#!/usr/bin/env python3
"""Native curl LAN verification: public static content only, no response body stdout."""
import datetime,hashlib,json,subprocess,tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;original=json.loads((HERE.parents[1]/'application/lan-frontend.json').read_text())
paths={'frontend':'/','git_login_helper':'/js/selfhost-login-defaults.js','git_sidebar':'/css/selfhost-sidebar.css','browser_defaults':'/js/selfhost-login.json','backend_ready':'/readyz'};rows={}
with tempfile.TemporaryDirectory(prefix='dell-penpot-LAN-') as folder:
 for name,path in paths.items():
  p=Path(folder)/name;r=subprocess.run(['/usr/bin/curl','-q','--noproxy','*','--fail','--silent','--connect-timeout','4','--max-time','15','--output',str(p),'--write-out','%{http_code}','http://192.168.21.22:9001'+path],capture_output=True,timeout=20)
  body=p.read_bytes() if p.exists() else b'';item={'HTTP_status':r.stdout.decode(),'curl_exit_code':r.returncode,'bytes':len(body),'sha256':hashlib.sha256(body).hexdigest(),'HTTP_body_emitted':False}
  if name in original:item['same_SHA_as_Git_deployment_acceptance']=item['sha256']==original[name]['sha256']
  if name=='browser_defaults':
   try:item['password_empty']=json.loads(body).get('password')==''
   except Exception:item['password_empty']=False
  if name=='backend_ready':item['body_exact_OK']=body.strip()==b'OK'
  rows[name]=item
checks=[x['curl_exit_code']==0 and x['HTTP_status']=='200' and x.get('same_SHA_as_Git_deployment_acceptance',True) and x.get('password_empty',True) and x.get('body_exact_OK',True) for x in rows.values()]
report={'status':'passed' if all(checks) else 'failed','at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'transport':'native curl -q --noproxy *','checks':rows,'source_Mac_runtime_read_or_changed':False,'credentials_used':False}
(HERE/'evidence/post-reboot-LAN.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report));raise SystemExit(0 if report['status']=='passed' else 1)
