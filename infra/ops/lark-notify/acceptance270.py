#!/usr/bin/python3 -I
"""Explicitly reviewed synthetic firing/resolved via Alertmanager, not direct Lark."""
import argparse,datetime,importlib.util,json,os,re,subprocess,sys,time,urllib.request,uuid
from pathlib import Path
HERE=Path(__file__).resolve().parent

def installer():
 file=HERE/'install270.py'
 if file.is_symlink() or file.stat().st_uid!=0 or file.stat().st_mode&0o022:raise RuntimeError('trusted root acceptance tool required')
 spec=importlib.util.spec_from_file_location('fixed_notify_install',file);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);m.guard();return m

def stamp(value):return datetime.datetime.fromtimestamp(value,datetime.timezone.utc).isoformat().replace('+00:00','Z')
def inject(opener,labels,started,ended):
 body=json.dumps([{'labels':labels,'annotations':{'summary':'Dell T630 通知链验收：合成故障与恢复，不代表实际业务故障'},'startsAt':stamp(started),'endsAt':stamp(ended)}]).encode()
 req=urllib.request.Request('http://10.63.30.40:9093/api/v2/alerts',data=body,method='POST',headers={'Content-Type':'application/json'})
 with opener.open(req,timeout=10) as response:
  response.read(4096)
  if response.status!=200:raise RuntimeError('synthetic AM injection failed')

def acknowledged(run,phase,since):
 raw=subprocess.run(['journalctl','--unit=dell-lark-notify.service','--since=@'+str(int(since)-1),'--output=json','--no-pager'],capture_output=True,timeout=15)
 if raw.returncode or len(raw.stdout)>2*1024*1024:raise RuntimeError('bounded notification journal unavailable')
 matches=[]
 for line in raw.stdout.splitlines():
  try:entry=json.loads(line);event=json.loads(entry['MESSAGE'])
  except (ValueError,KeyError,TypeError):continue
  if isinstance(event,dict) and event.get('event')=='lark_delivery_acknowledged' and event.get('acceptance_run')==run and event.get('phase')==phase and type(event.get('upstream_code')) is int and event['upstream_code']==0:
   digest=event.get('payload_sha256','')
   if re.fullmatch('[a-f0-9]{64}',digest):matches.append({'phase':phase,'upstream_code':0,'payload_sha256':digest,'ack_at':event.get('at')})
 return matches

def wait(run,phase,since):
 end=time.monotonic()+90
 while time.monotonic()<end:
  values=acknowledged(run,phase,since)
  if values:return values[0]
  time.sleep(1)
 raise RuntimeError('Lark successful API acknowledgment deadline exceeded')

def main():
 p=argparse.ArgumentParser();p.add_argument('--send-reviewed-acceptance-pair',action='store_true');args=p.parse_args()
 if not args.send_reviewed_acceptance_pair:raise RuntimeError('explicit manager reviewed send window required')
 m=installer();bridge,configuration=m.modules();policy=json.loads((m.ETC/'policy.json').read_text())
 if policy!=configuration.policy('acceptance') or (m.AM/'alertmanager.yml').read_text()!=configuration.dump('acceptance'):raise RuntimeError('both AM and bridge must be acceptance-only')
 before=m.guard();run=uuid.uuid4().hex;start=time.time();labels={'alertname':'DellLarkNotificationAcceptance','role':'ops-service','severity':'info','dell_acceptance':'lark-notify','acceptance_run':run}
 opener=urllib.request.build_opener(urllib.request.ProxyHandler({}));injected=False;resolved=False;result={'acceptance_run':run,'mode':'synthetic-notification-pair-via-Alertmanager','real_service_failure_injected':False,'messages_expected':2,'secrets_values_emitted':False,'status':'running','started_at':stamp(start)}
 state=m.SECRET/'acceptance-current.json';m.put(state,(json.dumps(result,indent=2)+'\n').encode())
 try:
  inject(opener,labels,start,start+600);injected=True;result['firing']=wait(run,'firing',start)
  result['firing_ack_before_resolved_injected']=True;m.put(state,(json.dumps(result,indent=2)+'\n').encode())
  inject(opener,labels,start,time.time()-1);resolved=True;result['resolved']=wait(run,'resolved',start)
  if m.guard()!=before:raise RuntimeError('unexpected Alertmanager container/process change')
  result.update(status='firing-and-resolved-acknowledged',upstream_code=0,completed_at=stamp(time.time()),alertmanager_container_unchanged=True,boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip())
  m.put(m.SECRET/'acceptance-proof.json',(json.dumps(result,indent=2)+'\n').encode());m.put(state,(json.dumps(result,indent=2)+'\n').encode());print(json.dumps(result))
 except Exception:
  if injected and not resolved:
   try:inject(opener,labels,start,time.time()-1)
   except Exception:pass
  result['status']='failed-no-real-routes-enabled';m.put(state,(json.dumps(result,indent=2)+'\n').encode());print(json.dumps(result));return 1
 return 0
if __name__=='__main__':
 try:sys.exit(main())
 except Exception:print(json.dumps({'status':'failed','message':'fixed acceptance rejected/failed; secrets and raw journal withheld'}));sys.exit(1)
