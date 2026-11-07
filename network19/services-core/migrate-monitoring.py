#!/usr/bin/env python3
"""Reusable single-role LOCAL stage only. Reads approved public snapshots, never SSH/writes guest."""
import argparse,ast,hashlib,ipaddress,json,re,copy
from pathlib import Path
from urllib.parse import urlsplit,urlunsplit
H=Path(__file__).resolve().parent;R=H.parents[1]
class Refused(RuntimeError):pass

def local_url(url,old,new):
 u=urlsplit(url)
 if u.username or u.password or u.query or u.fragment:raise Refused('credential-or-query-health-URL')
 if u.hostname!=old:return url
 return urlunsplit((u.scheme,new+(':'+str(u.port) if u.port else ''),u.path,u.query,u.fragment))

def stage(vmid):
 inventory=json.loads((H/'monitoring-inventory.json').read_text());row=next(x for x in inventory['roles'] if x['vmid']==vmid)
 row=copy.deepcopy(row)
 if vmid==240 and (H/'monitoring-scope240-override.json').exists():
  override=json.loads((H/'monitoring-scope240-override.json').read_text());item=row['files'][override['path']];item['captured_file']=override['source_file'];item['sha256']=override['source_sha256']
 plan=json.loads((R/'network19/migration-plan.json').read_text());mapping={r['vmid']:r for r in plan['guest_addresses']};assigned=mapping[vmid];old,new=assigned['old_ip'],assigned['new_ip']
 if ipaddress.ip_address(new) not in ipaddress.ip_network('192.168.19.0/24'):raise Refused('new-private-subnet-contract')
 out=H/'prepared/monitoring'/('vm'+str(vmid));records=[]
 for path,meta in row['files'].items():
  if not meta.get('exists'):raise Refused('required-baseline-file-missing:'+path)
  source=H/meta['captured_file'];raw=source.read_bytes()
  if hashlib.sha256(raw).hexdigest()!=meta['sha256']:raise Refused('captured-source-SHA-differs')
  text=raw.decode();changes=[]
  if path.endswith('/health.json'):
   x=json.loads(text)
   if x.get('role')!=assigned['name'] or x.get('private_ip')!=old:raise Refused('health-role-or-old-IP-differs')
   x['private_ip']=new;changes.append('private_ip')
   for field in ['http_checks','candidate_http_checks']:
    for i,check in enumerate(x.get(field,[])):
     value=local_url(check['url'],old,new)
     if value!=check['url']:check['url']=value;changes.append(field+'.'+str(i)+'.url')
   text=json.dumps(x,indent=2)+'\n'
  elif path.endswith('/guest-targets.json'):
   x=json.loads(text)
   if len(x['roles'])!=12:raise Refused('exact12-role-catalog-required')
   for target in x['roles']:
    assignment=mapping[target['vmid']]
    if target['private_ip']!=assignment['old_ip'] or target['hostname']!=assignment['name']:raise Refused('catalog-old-map-differs')
    target['private_ip']=assignment['new_ip'];changes.append('roles.'+str(target['vmid'])+'.private_ip')
   x['network_revision']='network19';text=json.dumps(x,indent=2)+'\n'
  elif path.endswith('/install-guest-baseline.py'):
   needle="ipaddress.ip_network('10.63.0.0/16')"
   if text.count(needle)!=1:raise Refused('installer-subnet-guard-source-differs')
   text=text.replace(needle,"ipaddress.ip_network('192.168.19.0/24')");text=text.replace("'assigned 10.63 private IP is not configured on an UP guest interface'","'assigned network19 private IP is not configured on an UP guest interface'")
   ast.parse(text);changes.append('exact-subnet-guard-literal')
  elif path.endswith('/10-private-only.conf') or path=='/etc/default/prometheus-node-exporter':
   # Exact known public listen flag only, preserving ARGS/ExecStart, regexes and comments.
   flag='--web.listen-address='+old+':9100';count=text.count(flag)
   if path.endswith('/10-private-only.conf') and count!=1:raise Refused('exact-old-listen-flag-required')
   if count>1:raise Refused('ambiguous-listen-flags')
   if count:text=text.replace(flag,'--web.listen-address='+new+':9100');changes.append('exact-web.listen-address-flag')
   elif path=='/etc/default/prometheus-node-exporter':
    # Actual defaults currently ARGS=""; do not invent a second source of flags.
    if not re.search(r'^ARGS=(?:""|\'\')\s*$',text,re.M):raise Refused('unknown-default-ARGS-requires-review')
  elif path.endswith('/collect-guest-health.py'):
   ast.parse(text)  # Generic validates assigned config address; unchanged.
  else:raise Refused('path-not-in-monitoring-whitelist')
  dest=out/path.lstrip('/');dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(text)
  records.append({'target_path':path,'expected_old_SHA256':meta['sha256'],'new_SHA256':hashlib.sha256(text.encode()).hexdigest(),'staged_path':str(dest.relative_to(H)),'changes':changes,'target_mode':meta['mode'],'target_owner_uid':meta['uid']})
 contract={'vmid':vmid,'role':assigned['name'],'old_ip':old,'new_ip':new,'gateway_and_DNS':'192.168.19.1','status':'local-staged-not-applied','files':records,'apply_gate':'OScommit: exact new address UP /24; root600 per-role window receipt; all old source SHAs still match','apply_order':['pause only guest-health timer preserving prior enabled/active state; no app service changes','install new catalog+installer guard+health JSON+listen files as root with original modes, each atomic','daemon-reload; native --check-private-ip with new row; restart only node exporter','prove listen only own newIP9100 and local real active HTTP health; collector --check is access-only, not HTTP pass','restore original collector timer activation; check textfile freshness and Ops targetUP'],'candidate_activation_changed':False,'business_services_started_or_restarted':False,'source_host_key_alias_unchanged':True,'guest_writes_performed':False,'rollback':'Restore same per-role old files only together with root OS old-address rollback; new-only file rollback on new-only OS is invalid'}
 (out/'role-contract.json').write_text(json.dumps(contract,indent=2)+'\n');return contract

def main():
 p=argparse.ArgumentParser();p.add_argument('--vmid',type=int,action='append');a=p.parse_args();ids=a.vmid or [200,201,210,220,221,230,231,232,240,250,260,270]
 result=[stage(v) for v in ids];(H/'monitoring-stage-contract.json').write_text(json.dumps({'status':'local-staged','roles':result,'targets_kept':12,'router190_and_legacy104_not_auto_enrolled':True,'apply_available':'root coordinator only after OScommit; no guest write command in this tool'},indent=2)+'\n')
 print(json.dumps({'roles_staged':len(result),'guest_writes':0,'formal_apps_started':False,'source_candidates_activated':False}))
if __name__=='__main__':main()
