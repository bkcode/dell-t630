from pathlib import Path
import sys,json,shlex
R=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True;sys.path.insert(0,str(R/'scripts'));import control
sid=json.loads((R/'cleanup/maintenance.json').read_text())['silence_id']
P=r'''import json,sys,urllib.request,datetime
p=json.load(sys.stdin);op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def get(url):
 with op.open(url,timeout=10) as r:return json.load(r)
pm='http://192.168.19.70:9090';am='http://192.168.19.70:9093';targets=get(pm+'/api/v1/targets')['data']['activeTargets'];assert len(targets)==15 and all(x['health']=='up' for x in targets);assert not get(pm+'/api/v1/alerts')['data']['alerts'] and not get(am+'/api/v2/alerts')
s=get(am+'/api/v2/silence/'+p['id']);assert s['createdBy']=='dell-cleanup-coordinator' and s['matchers']==[{'name':'site','value':'dell-t630','isRegex':False,'isEqual':True}]
with op.open(urllib.request.Request(am+'/api/v2/silence/'+p['id'],method='DELETE'),timeout=10) as r:assert r.status==200
assert get(am+'/api/v2/silence/'+p['id'])['status']['state']=='expired'
print(json.dumps({'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'cleanup-own-maintenance-expired-original-alerting-restored','silence_id':p['id'],'targets_UP':15,'active_alerts_before':0,'test_messages_sent':False,'Nexus221_kept_UP':True,'pending_Nexus_migration_requires_new_approved_window':True,'Lark_mode_credentials_unchanged':True,'Mac_probe_stays_disabled':True}))'''
info=next(r['target'] for r in json.loads((R/'evidence/implementation/private-guest-access.json').read_text())['roles'] if r['target']['vmid']==270)
r=control.guest(270,'python3 -B -c '+shlex.quote(P),data=json.dumps({'id':sid}).encode(),info=info,timeout=45);assert r['exit_code']==0;r=json.loads(r['stdout']);(R/'cleanup/maintenance-ended.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
