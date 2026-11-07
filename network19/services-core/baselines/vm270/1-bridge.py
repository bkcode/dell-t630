#!/usr/bin/python3 -I
"""Private Alertmanager -> Lark text adapter. No URL/body/token is ever logged."""
import argparse, collections, datetime, hashlib, hmac, http.server, json, os, re, socket, socketserver, ssl, subprocess, sys, threading, time, urllib.error, urllib.parse, urllib.request
from pathlib import Path
BIND=('172.18.0.1',19093);SOURCE='172.18.0.3';PATH='/v1/alertmanager';MAX_BODY=65536;MAX_ALERTS=16;MAX_LARK=18000
POLICY=Path('/etc/dell-lark-notify/policy.json')
ALERTS={
 'DellLarkNotificationAcceptance':'通知链验收（受控测试）',
 'GuestExporterUnavailable':'来宾监控采集不可达', 'HttpHealthUnavailable':'HTTP健康探测失败',
 'GuestMemoryAvailableLow':'来宾可用内存低于10%', 'GuestFilesystemSpaceLow':'来宾文件系统可用空间低于20%',
 'PveCollectorStale':'PVE指标采集已停止更新','PveRaidDegraded':'PVE RAID虚拟磁盘未处于Optimal',
 'PveRaidMemberOffline':'PVE RAID物理磁盘离线','PveStorageSpaceLow':'PVE存储可用空间低于20%',
 'PveMemoryAvailableLow':'PVE可用内存低于10%','CloudflareProcessUnavailable':'现有Cloudflare进程未运行',
 'GuestManagedUnitUnavailable':'来宾配置的服务未运行','GuestLocalHealthUnavailable':'来宾本地应用健康检查失败'}
ROLES={'cf-tunnel','data-prod-db','data-prod-infra','data-test','publish-service','artifact-service','java-prod-01','java-prod-02','java-prod-03','java-test-01','penpot-service','nas-media','ops-service','pve'}
LABELS=('alertname','role','severity','check','unit','service','dell_acceptance','acceptance_run')
class Rejected(Exception):pass
class DeliveryFailed(Exception):
 def __init__(self,message='delivery not acknowledged',code=None,http_status=None):
  super().__init__('delivery not acknowledged');self.code=code if type(code) is int and -1000000<=code<=1000000 else None;self.http_status=http_status if type(http_status) is int and 100<=http_status<=599 else None

def log(event,**fields):
 # Callers pass bounded numeric/boolean/status/correlation fields only, never exceptions.
 print(json.dumps({'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'event':event,**fields},ensure_ascii=False),flush=True)

def pairs(values):
 result={}
 for key,value in values:
  if key in result:raise Rejected('duplicate JSON key')
  result[key]=value
 return result

def decode(raw):
 try:return json.loads(raw,object_pairs_hook=pairs)
 except (ValueError,UnicodeError,RecursionError):raise Rejected('invalid JSON') from None

def validate_url(value):
 if not isinstance(value,str) or len(value)>256 or value!=value.strip() or not value.isascii():raise Rejected('invalid credential')
 try:u=urllib.parse.urlsplit(value)
 except ValueError:raise Rejected('invalid credential') from None
 if u.scheme!='https' or u.netloc!='open.larksuite.com' or u.query or u.fragment or not re.fullmatch(r'/open-apis/bot/v2/hook/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',u.path):raise Rejected('credential endpoint outside allowlist')
 return value

def credential(name,root):
 p=root/name
 if p.is_symlink() or not p.is_file() or p.stat().st_size>1024:raise Rejected('credential file invalid')
 data=p.read_bytes().rstrip(b'\n')
 try:return data.decode('ascii')
 except UnicodeError:raise Rejected('credential encoding invalid') from None

def event_identity(alert):
 fingerprint=alert.get('fingerprint');started=alert.get('startsAt')
 if not isinstance(fingerprint,str) or not re.fullmatch('[a-f0-9]{16}',fingerprint):raise Rejected('invalid event fingerprint')
 if not isinstance(started,str) or len(started)>40:raise Rejected('invalid event start')
 match=re.fullmatch(r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(?:\.(\d{1,9}))?(Z|[+-]\d{2}:\d{2})',started)
 if not match:raise Rejected('invalid event timestamp')
 try:
  # Preserve nanoseconds separately: datetime alone would merge sub-microsecond cycles.
  moment=datetime.datetime.fromisoformat(match[1]+('+00:00' if match[3]=='Z' else match[3])).astimezone(datetime.timezone.utc)
  if not 1970<=moment.year<=2199:raise ValueError()
  canonical_start=str(int(moment.timestamp()))+'.'+(match[2] or '').ljust(9,'0')
 except (ValueError,OverflowError):raise Rejected('invalid event timestamp') from None
 return [fingerprint,canonical_start,alert['status']]

def render(raw,mode):
 data=decode(raw)
 if not isinstance(data,dict) or data.get('version')!='4' or data.get('status') not in ('firing','resolved'):raise Rejected('unknown webhook version/status')
 alerts=data.get('alerts');phase=data['status']
 if not isinstance(alerts,list) or not 1<=len(alerts)<=MAX_ALERTS:raise Rejected('alert batch limit')
 output=[];runs=set();states=[];events=[]
 for alert in alerts:
  if not isinstance(alert,dict) or alert.get('status') not in ('firing','resolved') or not isinstance(alert.get('labels'),dict):raise Rejected('invalid alert')
  events.append(event_identity(alert));states.append(alert['status']);labels=alert['labels'];name=labels.get('alertname')
  if name not in ALERTS:raise Rejected('alert outside whitelist')
  acceptance=name=='DellLarkNotificationAcceptance'
  if mode=='acceptance' and not acceptance:raise Rejected('real notifications are not enabled')
  if acceptance:
   if labels.get('dell_acceptance')!='lark-notify' or labels.get('role')!='ops-service' or labels.get('severity')!='info' or not re.fullmatch('[a-f0-9]{32}',str(labels.get('acceptance_run',''))):raise Rejected('acceptance labels required')
   runs.add(labels['acceptance_run'])
  elif labels.get('dell_acceptance') or labels.get('acceptance_run'):raise Rejected('test labels cannot mark real alerts')
  safe={}
  for key in LABELS:
   if key not in labels:continue
   value=labels[key]
   if not isinstance(value,str) or not 1<=len(value)<=96 or not re.fullmatch('[A-Za-z0-9_.-]+',value):raise Rejected('unsafe allowed label')
   if key=='role' and value not in ROLES:raise Rejected('unknown role')
   if key=='severity' and value not in ('info','warning','critical'):raise Rejected('unknown severity')
   safe[key]=value
  if not safe.get('severity'):raise Rejected('severity required')
  output.append((name,alert['status'],safe))
 if phase!=('firing' if 'firing' in states else 'resolved'):raise Rejected('inconsistent group phase')
 if len(runs)>1:raise Rejected('mixed acceptance runs')
 header='【Dell T630 告警】' if phase=='firing' else '【Dell T630 恢复】'
 if runs:header='【验收】'+header
 lines=[header]
 for name,state,labels in sorted(output,key=lambda x:(x[0],x[1],json.dumps(x[2],sort_keys=True))):
  lines.append(('故障：' if state=='firing' else '恢复：')+ALERTS[name])
  lines.extend(k+'='+labels[k] for k in LABELS if k in labels)
 payload=json.dumps({'msg_type':'text','content':{'text':'\n'.join(lines)}},ensure_ascii=False,separators=(',',':')).encode()
 if len(payload)>MAX_LARK:raise Rejected('outbound body limit')
 payload_sha256=hashlib.sha256(payload).hexdigest()
 # The same message text can belong to a new incident. Identity is separate and never forwarded.
 event_key=hashlib.sha256(json.dumps({'phase':phase,'events':sorted(events),'payload_sha256':payload_sha256},sort_keys=True,separators=(',',':')).encode()).hexdigest()
 return payload,{'phase':phase,'alerts':len(alerts),'acceptance_run':next(iter(runs),None),'payload_sha256':payload_sha256,'event_key_sha256':event_key}

class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,*args,**kwargs):return None

class LarkSender:
 def __init__(self,url):
  self.url=validate_url(url)
  self.opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect(),urllib.request.HTTPSHandler(context=ssl.create_default_context()))
 def __call__(self,payload):
  req=urllib.request.Request(self.url,data=payload,method='POST',headers={'Content-Type':'application/json; charset=utf-8','User-Agent':'Dell-Ops-Lark-Bridge/1'})
  try:
   with self.opener.open(req,timeout=10) as result:
    if result.status!=200:raise DeliveryFailed(http_status=result.status)
    raw=result.read(4097)
    if len(raw)>4096:raise DeliveryFailed()
    data=decode(raw)
    if not isinstance(data,dict) or type(data.get('code')) is not int or data['code']!=0:raise DeliveryFailed(code=data.get('code') if isinstance(data,dict) else None,http_status=result.status)
  except DeliveryFailed:raise
  except urllib.error.HTTPError as error:raise DeliveryFailed(http_status=error.code) from None
  except Exception:raise DeliveryFailed() from None
  return 0

class BoundedSender:
 def __init__(self,credentials):self.credentials=credentials
 def __call__(self,payload):
  # A fixed native worker gives an absolute deadline even if DNS or TLS stalls.
  try:
   result=subprocess.run(['/usr/bin/python3','-I',str(Path(__file__).resolve()),'send-one'],input=payload,capture_output=True,timeout=15,env={'PATH':'/usr/bin:/bin','CREDENTIALS_DIRECTORY':str(self.credentials)})
   response=decode(result.stdout)
   if result.returncode or response!={'ok':True,'upstream_code':0}:raise DeliveryFailed(code=response.get('upstream_code') if isinstance(response,dict) else None,http_status=response.get('upstream_http_status') if isinstance(response,dict) else None)
  except DeliveryFailed:raise
  except Exception:raise DeliveryFailed() from None
  return 0

class Context:
 def __init__(self,token,mode,sender):
  if mode not in ('acceptance','active') or not re.fullmatch('[A-Za-z0-9_-]{64}',token):raise Rejected('invalid bridge policy/auth')
  self.token=token;self.mode=mode;self.sender=sender;self.lock=threading.Lock();self.attempts=collections.deque();self.delivered={};self.inflight=set()
 def deliver(self,raw):
  payload,receipt=render(raw,self.mode);key=receipt['event_key_sha256'];now=time.monotonic()
  with self.lock:
   self.delivered={k:v for k,v in self.delivered.items() if now-v<600}
   if key in self.delivered:return {**receipt,'cached':True}
   if key in self.inflight:raise DeliveryFailed('delivery in progress')
   while self.attempts and now-self.attempts[0]>=60:self.attempts.popleft()
   if len(self.attempts)>=30:raise DeliveryFailed('local rate limit')
   self.attempts.append(now);self.inflight.add(key)
  try:self.sender(payload)
  except Exception as error:
   with self.lock:self.inflight.discard(key)
   code=error.code if isinstance(error,DeliveryFailed) else None;status=error.http_status if isinstance(error,DeliveryFailed) else None
   log('lark_delivery_failed',phase=receipt['phase'],alerts=receipt['alerts'],acceptance_run=receipt['acceptance_run'],payload_sha256=receipt['payload_sha256'],event_key_sha256=key,upstream_code=code,upstream_http_status=status);raise DeliveryFailed() from None
  with self.lock:
   self.inflight.discard(key)
   if len(self.delivered)>=256:self.delivered.pop(next(iter(self.delivered)))
   self.delivered[key]=time.monotonic()
  log('lark_delivery_acknowledged',phase=receipt['phase'],alerts=receipt['alerts'],acceptance_run=receipt['acceptance_run'],payload_sha256=receipt['payload_sha256'],event_key_sha256=key,upstream_code=0)
  return {**receipt,'cached':False}

class Handler(http.server.BaseHTTPRequestHandler):
 protocol_version='HTTP/1.1';server_version='DellNotify';sys_version=''
 def log_message(self,*args):pass
 def log_error(self,*args):pass
 def setup(self):super().setup();self.connection.settimeout(8)
 def handle(self):
  # Bound the whole connection, including slow-dripped headers/body, not only each read.
  def expire():
   try:self.connection.shutdown(socket.SHUT_RDWR)
   except OSError:pass
  deadline=threading.Timer(25,expire);deadline.daemon=True;deadline.start()
  try:super().handle()
  finally:deadline.cancel()
 def reply(self,code,value):
  self.close_connection=True;body=json.dumps(value,separators=(',',':')).encode();self.send_response(code);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(body)));self.send_header('Connection','close')
  if code==503:self.send_header('Retry-After','10')
  self.end_headers();self.wfile.write(body)
 def send_error(self,code,message=None,explain=None):
  try:self.reply(code,{'ok':False,'message':'request rejected'})
  except OSError:pass
 def do_POST(self):
  try:
   if self.client_address[0]!=self.server.allowed_source or self.path!=PATH:self.reply(403,{'ok':False});return
   auth=self.headers.get_all('Authorization',[])
   if len(auth)!=1 or not auth[0].isascii() or not hmac.compare_digest(auth[0],'Bearer '+self.server.context.token):self.reply(401,{'ok':False});return
   if self.headers.get_all('Transfer-Encoding',[]) or len(self.headers.get_all('Content-Length',[]))!=1:self.reply(400,{'ok':False});return
   value=self.headers['Content-Length']
   if not re.fullmatch('[1-9][0-9]{0,5}',value) or int(value)>MAX_BODY:self.reply(413,{'ok':False});return
   if self.headers.get_content_type()!='application/json':self.reply(415,{'ok':False});return
   raw=self.rfile.read(int(value))
   if len(raw)!=int(value):self.reply(400,{'ok':False});return
   receipt=self.server.context.deliver(raw);self.reply(200,{'ok':True,'upstream_code':0,**receipt})
  except Rejected:
   self.reply(400,{'ok':False,'message':'payload rejected'})
  except DeliveryFailed:
   self.reply(503,{'ok':False,'message':'delivery not acknowledged'})
  except (OSError,TimeoutError):pass
  except Exception:
   log('request_internal_error')
   try:self.reply(503,{'ok':False,'message':'internal request failure'})
   except OSError:pass
 def do_GET(self):self.reply(405,{'ok':False})
 do_PUT=do_DELETE=do_PATCH=do_OPTIONS=do_GET

class Server(http.server.ThreadingHTTPServer):
 daemon_threads=True;request_queue_size=4
 def server_bind(self):
  socketserver.TCPServer.server_bind(self);self.server_name='dell-lark-bridge';self.server_port=self.server_address[1]
 def __init__(self,address,context,allowed_source=SOURCE):
  self.context=context;self.allowed_source=allowed_source;self.slots=threading.BoundedSemaphore(2);super().__init__(address,Handler)
 def process_request(self,request,address):
  if not self.slots.acquire(blocking=False):
   try:request.sendall(b'HTTP/1.1 503 Service Unavailable\r\nContent-Length: 12\r\nConnection: close\r\nRetry-After: 10\r\n\r\n{"ok":false}')
   except OSError:pass
   self.shutdown_request(request);return
  try:super().process_request(request,address)
  except BaseException:self.slots.release();raise
 def process_request_thread(self,request,address):
  try:super().process_request_thread(request,address)
  finally:self.slots.release()
 def handle_error(self,*args):log('request_handler_error')

def main():
 p=argparse.ArgumentParser();p.add_argument('action',choices=['check','serve','send-one']);args=p.parse_args()
 root=Path(os.environ.get('CREDENTIALS_DIRECTORY','/invalid'))
 if args.action=='send-one':
  raw=sys.stdin.buffer.read(MAX_LARK+1)
  if not 0<len(raw)<=MAX_LARK:raise Rejected('worker body limit')
  LarkSender(credential('lark-webhook',root))(raw);print(json.dumps({'ok':True,'upstream_code':0}));return
 config=decode(POLICY.read_bytes())
 if config not in ({'mode':'acceptance','bind_host':BIND[0],'bind_port':BIND[1],'allowed_source':SOURCE},{'mode':'active','bind_host':BIND[0],'bind_port':BIND[1],'allowed_source':SOURCE}):raise Rejected('fixed policy required')
 token=credential('bridge-auth',root);validate_url(credential('lark-webhook',root));context=Context(token,config['mode'],BoundedSender(root))
 if args.action=='check':print(json.dumps({'ok':True,'mode':config['mode'],'secret_values_emitted':False}));return
 server=Server(BIND,context);log('bridge_ready',mode=config['mode'],port=BIND[1]);server.serve_forever(poll_interval=0.5)

if __name__=='__main__':
 try:main()
 except DeliveryFailed as error:print(json.dumps({'ok':False,'upstream_code':error.code,'upstream_http_status':error.http_status}));sys.exit(1)
 except Exception:log('bridge_start_failed');sys.exit(1)
