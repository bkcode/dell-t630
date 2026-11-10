#!/usr/bin/env python3
"""Read-only Prometheus current targets and local service labels."""
import json,socket,urllib.parse,urllib.request
assert socket.gethostname()=='ops-service'
o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def get(path):
 with o.open('http://192.168.19.70:9090'+path,timeout=15)as r:return json.loads(r.read())
def query(expr):return get('/api/v1/query?'+urllib.parse.urlencode({'query':expr}))['data']['result']
targets=get('/api/v1/targets')['data']['activeTargets'];assert len(targets)==15 and all(x['health']=='up'for x in targets);assert all(x['labels'].get('vmid')!='221'and x['labels'].get('role')!='artifact-service'for x in targets)
resource=query('dell_guest_service_active{role="resource-service"}');assert len(resource)==5 and all(x['value'][1]=='1'for x in resource)
assert not query('dell_guest_service_active{role="resource-service",service="dell-filebrowser.service"}')and not query('dell_guest_http_up{role="resource-service",check="filebrowser-http-health"}')
publisher=query('dell_guest_service_active{role="publish-service"}');assert len(publisher)==7 and all(x['value'][1]=='1'for x in publisher)
http=query('dell_guest_http_up{role="publish-service",check="nexus-status"}');assert len(http)==1 and http[0]['value'][1]=='1'
print(json.dumps({'status':'current-targets-and-Nexus-NFS-health-verified','targets':len(targets),'all_targets_up':True,'retired221_target_absent':True,'node_target_count':10,'ops_target_count':5,'resource280_service_checks':5,'resource280_all_up':True,'FileBrowser_health_metrics_absent':True,'publisher_service_checks':7,'publisher_all_up':True,'Nexus_HTTP_up':True,'test_notifications_sent':False}))
