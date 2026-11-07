from pathlib import Path
import sys,json,shlex,datetime,re
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'scripts'));import control
sid=json.loads((R/'network19/evidence/maintenance-silence.json').read_text())['result']['silence_id'];assert re.fullmatch(r'[0-9a-f-]{36}',sid)
P=r'''import json,sys,urllib.request,urllib.error,datetime
v=json.load(sys.stdin);sid=v['silence_id'];op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def get(url):
 with op.open(url,timeout=10) as r:return json.load(r)
prom='http://192.168.19.70:9090';am='http://192.168.19.70:9093'
t=get(prom+'/api/v1/targets')['data']['activeTargets'];assert len(t)==17 and all(x['health']=='up' for x in t)
a=get(prom+'/api/v1/alerts')['data']['alerts'];active=[x for x in a if x['state'] in ['firing','pending']]
alerts=get(am+'/api/v2/alerts');assert not active and not alerts,'Real active alerts must be investigated before unmute'
s=get(am+'/api/v2/silence/'+sid);assert s['matchers']==[{'isEqual':True,'isRegex':False,'name':'site','value':'dell-t630'}]
with op.open(urllib.request.Request(am+'/api/v2/silence/'+sid,method='DELETE'),timeout=10) as r:status=r.status
assert status==200
s=get(am+'/api/v2/silence/'+sid);assert s['status']['state']=='expired'
print(json.dumps({'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'own-network19-maintenance-silence-expired-monitoring-restored','silence_id':sid,'only_own_silence_changed':True,'targets_up':17,'Prometheus_firing_or_pending_before':0,'Alertmanager_active_before':0,'mode_or_secrets_changed':False,'test_notifications_sent':False,'external_Mac_probe_unchanged_disabled':True}))'''
info=json.loads((R/'network19/evidence/migrated-access.json').read_text())['targets']['270'];r=control.guest(270,'sudo python3 -c '+shlex.quote(P),data=json.dumps({'silence_id':sid}).encode(),info=info,timeout=60);assert r['exit_code']==0,r['stderr'];x=json.loads(r['stdout']);(R/'network19/evidence/maintenance-ended.json').write_text(json.dumps(x,indent=2)+'\n');print(json.dumps(x))
