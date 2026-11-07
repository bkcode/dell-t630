#!/usr/bin/env python3
"""Optional one-shot LAN probe. No scheduler, credentials, notifications or writes to services."""
import argparse, concurrent.futures, datetime, ipaddress, json, os, re, socket, sys, urllib.error, urllib.request
from pathlib import Path
from urllib.parse import urlsplit
ALLOWED_HTTP_PATHS={'/','/health','/-/ready','/api/health','/service/rest/v1/status','/nacos/v1/console/health/readiness'}

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None

def endpoint(value):
    if not isinstance(value,dict) or not re.fullmatch(r'[A-Za-z0-9_.-]+',value.get('name','')):raise ValueError('endpoint name must be a plain label')
    u=urlsplit(value.get('url',''))
    if u.scheme not in ('tcp','http','https') or not u.hostname or u.username or u.password or u.query or u.fragment:
        raise ValueError('only credential-free, query-free TCP/HTTP(S) endpoints are allowed')
    if u.hostname!='localhost':
        address=ipaddress.ip_address(u.hostname)
        if not (address.is_private or address.is_loopback):raise ValueError('LAN or loopback IP required')
    port=u.port or (443 if u.scheme=='https' else 80 if u.scheme=='http' else None)
    if not port or port<1 or port>65535:raise ValueError('valid explicit TCP port required')
    if u.scheme=='tcp' and u.path not in ('','/'):raise ValueError('TCP probe has no path')
    if u.scheme!='tcp' and (u.path or '/') not in ALLOWED_HTTP_PATHS:raise ValueError('HTTP probe path must be a read-only health/root endpoint')
    return {'name':value['name'],'url':value['url'],'host':u.hostname,'port':port,'scheme':u.scheme,'scope':value.get('scope','endpoint-only'),'enabled':value.get('enabled',False)}

def probe(item,timeout):
    result={'name':item['name'],'host':item['host'],'port':item['port'],'scope':item['scope'],'status':'failed'}
    try:
        if item['scheme']=='tcp':
            with socket.create_connection((item['host'],item['port']),timeout=timeout):pass
            result.update(status='passed',evidence='TCP connection only; no protocol authentication or application acceptance')
        else:
            request=urllib.request.Request(item['url'],method='GET',headers={'User-Agent':'dell-lan-readonly-probe/1'})
            with urllib.request.build_opener(NoRedirect).open(request,timeout=timeout) as response:
                response.read(4096)
                if response.status!=200:raise ValueError('non-200 health response')
                result.update(status='passed',http_status=200,evidence='GET status only; response body not retained')
    except urllib.error.HTTPError as error:result.update(error='HTTP status '+str(error.code))
    except (OSError,ValueError):result.update(error='connection, TLS or readiness failure; sensitive response suppressed')
    return result

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',required=True,type=Path)
    parser.add_argument('--include-candidates',action='store_true')
    parser.add_argument('--timeout',type=float,default=5)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    if not 0<args.timeout<=10:parser.error('timeout must be between 0 and 10 seconds')
    doc=json.loads(args.config.read_text());items=[endpoint(x) for x in doc.get('endpoints',[])]
    if len(items)>64:raise ValueError('at most 64 endpoints per one-shot run')
    selected=[x for x in items if x['enabled'] or args.include_candidates]
    if not selected:raise ValueError('no enabled probe endpoints')
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        results=list(pool.map(lambda item:probe(item,args.timeout),selected))
    report={'timestamp':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),'scope':'one-shot-read-only-LAN-probe','scheduler_installed':False,'notifications_sent':False,'results':results}
    text=json.dumps(report,ensure_ascii=False,indent=2)+'\n'
    if args.output:
        fd=os.open(args.output,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
        with os.fdopen(fd,'w') as out:out.write(text)
        args.output.chmod(0o600)
    print(text,end='')
    return 0 if all(x['status']=='passed' for x in results) else 1

if __name__=='__main__':
    try:sys.exit(main())
    except ValueError as error:print('PROBE CONFIG ERROR: '+str(error),file=sys.stderr);sys.exit(2)
