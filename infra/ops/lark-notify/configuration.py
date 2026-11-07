"""No dependencies, no credential values. JSON is valid Alertmanager YAML."""
import json
from bridge import ALERTS,BIND,SOURCE
AUTH='/run/secrets/lark-bridge-token'
def policy(mode):
 if mode not in ('acceptance','active'):raise ValueError('invalid mode')
 return {'mode':mode,'bind_host':BIND[0],'bind_port':BIND[1],'allowed_source':SOURCE}
def render(mode):
 policy(mode)
 test={'receiver':'lark-acceptance','matchers':['alertname="DellLarkNotificationAcceptance"','dell_acceptance="lark-notify"'],'group_by':['alertname','acceptance_run'],'group_wait':'1s','group_interval':'15s','repeat_interval':'24h'}
 routes=[test]
 if mode=='active':routes.append({'receiver':'lark-live','matchers':['alertname=~"'+('|'.join(sorted(set(ALERTS)-{'DellLarkNotificationAcceptance'})))+'"','severity=~"warning|critical"'],'group_by':['alertname','role'],'group_wait':'30s','group_interval':'5m','repeat_interval':'4h'})
 webhook={'url':'http://172.18.0.1:19093/v1/alertmanager','send_resolved':True,'max_alerts':16,'timeout':'12s','http_config':{'authorization':{'type':'Bearer','credentials_file':AUTH},'follow_redirects':False}}
 receivers=[{'name':'local-only'},{'name':'lark-acceptance','webhook_configs':[webhook]}]
 if mode=='active':receivers.append({'name':'lark-live','webhook_configs':[webhook]})
 return {'global':{'resolve_timeout':'5m'},'route':{'receiver':'local-only','group_by':['alertname','role'],'group_wait':'30s','group_interval':'5m','repeat_interval':'4h','routes':routes},'receivers':receivers}
def dump(mode):return json.dumps(render(mode),indent=2)+'\n'
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('mode',choices=['acceptance','active']);a=p.parse_args();print(dump(a.mode),end='')
