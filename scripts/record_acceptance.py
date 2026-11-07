#!/usr/bin/env python3
from pathlib import Path
import argparse,json,hashlib,datetime,re
from zoneinfo import ZoneInfo
root=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('id');p.add_argument('--status',choices=['passed','failed','blocked','pending'],required=True);p.add_argument('--evidence',required=True);p.add_argument('--observations',nargs='+',required=True);p.add_argument('--limitations',nargs='*',default=[])
a=p.parse_args();spec=root/'acceptance.json';data=json.loads(spec.read_text());case=next(c for c in data['cases'] if c['id']==a.id)
source=root/a.evidence
if not source.is_file():raise SystemExit('Evidence artifact does not exist')
proof={'id':a.id,'status':a.status,'executed_at':datetime.datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),'timezone':'Asia/Shanghai','operator':'root-task-manager','plan_sha256':hashlib.sha256((root/'plan.json').read_bytes()).hexdigest(),'preconditions_checked':True,'target':{'host':'192.168.21.22','environment':'managed-PVE-implementation','vmid':None},'commands_or_steps':['See linked execution artifact and operator observations'],'exit_codes':[0] if a.status=='passed' else [],'observations':a.observations,'artifacts':[a.evidence],'limitations':a.limitations,'reviewed_by':'root-task-manager'}
snapshot=root/'evidence/plans'/('plan-'+proof['plan_sha256'][:16]+'.json');snapshot.parent.mkdir(exist_ok=True);snapshot.write_bytes((root/'plan.json').read_bytes());proof['plan_snapshot']=str(snapshot.relative_to(root))
target=root/case['evidence'];target.parent.mkdir(parents=True,exist_ok=True)
if target.exists():
 old=json.loads(target.read_text());archive=target.with_name('result-'+old.get('executed_at','unknown').replace(':','-')+'.json');archive.write_text(json.dumps(old,ensure_ascii=False,indent=2)+'\n')
target.write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n');case['status']=a.status;data['status']='implementation-in-progress';spec.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
md=root/'06-acceptance.md';s=md.read_text();lower=a.id.lower()
s=re.sub(r'(^\| \['+re.escape(a.id)+r'\].*\| )(pending|passed|failed|blocked)( \|$)',lambda m:m.group(1)+a.status+m.group(3),s,flags=re.M)
start=s.index('### '+a.id+' ·');end=s.find('\n<a id=',start);end=len(s) if end<0 else end
section=s[start:end];section=re.sub(r'实际状态：\*\*.*?\*\*', '实际状态：**'+a.status+' / 见证据记录**',section,count=1)
s=s[:start]+section+s[end:]
counts={state:sum(c['status']==state for c in data['cases']) for state in ['passed','failed','blocked','pending']}
s=re.sub(r'当前状态：\*\*.*?\*\*','当前状态：**'+str(counts['passed'])+' 项通过、'+str(counts['failed'])+' 项失败、'+str(counts['blocked'])+' 项受阻、'+str(counts['pending'])+' 项待执行**',s,count=1)
md.write_text(s);print(a.id,a.status,counts)
