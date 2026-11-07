from pathlib import Path
import json,sys,shlex
R=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True;sys.path.insert(0,str(R/'scripts'));import control
P=r'''import json,datetime,urllib.request
op=urllib.request.build_opener(urllib.request.ProxyHandler({}));now=datetime.datetime.now(datetime.timezone.utc)
with op.open('http://192.168.19.70:9090/api/v1/targets',timeout=10) as r:v=json.load(r)
targets=v['data']['activeTargets'];assert len(targets)==17 and all(x['health']=='up' for x in targets)
p={'matchers':[{'name':'site','value':'dell-t630','isRegex':False,'isEqual':True}],'startsAt':now.isoformat(),'endsAt':(now+datetime.timedelta(hours=4)).isoformat(),'createdBy':'dell-cleanup-coordinator','comment':'Authorized node/template cleanup and Nexus consolidation;remove after actual new topology healthy'}
req=urllib.request.Request('http://192.168.19.70:9093/api/v2/silences',data=json.dumps(p).encode(),headers={'Content-Type':'application/json'},method='POST')
with op.open(req,timeout=10) as r:x=json.load(r)
print(json.dumps({'silence_id':x['silenceID'],'started_at':now.isoformat(),'ends_at':p['endsAt'],'site':'dell-t630','before_targets_up':17,'notification_mode_or_secrets_changed':False,'test_messages_sent':False}))'''
info=json.loads((R/'evidence/implementation/private-guest-access.json').read_text())['roles'];info=next(x['target'] for x in info if x['target']['vmid']==270)
r=control.guest(270,'sudo python3 -c '+shlex.quote(P),info=info,timeout=30);assert r['exit_code']==0;r=json.loads(r['stdout']);(R/'cleanup/maintenance.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
