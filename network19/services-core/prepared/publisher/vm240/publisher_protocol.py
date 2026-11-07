#!/usr/bin/env python3
"""Pure restricted test240 protocol/archive validation. No command execution."""
import datetime,hashlib,json,re,tarfile,uuid,zipfile
from pathlib import Path
from urllib.parse import urlsplit,parse_qs
import yaml
NAMES=['finger-service-system','finger-service-coms','finger-auth','finger-bff-system','finger-gateway-mobile']
PORTS=dict(zip(NAMES,[10210,10202,10000,10104,9999]))
CONFIG_IDS={'finger-service-system': 'finger-service-system.network19-v1.yaml', 'finger-service-coms': 'finger-service-coms.network19-v1.yaml', 'finger-auth': 'finger-auth.network19-v1.yaml', 'finger-bff-system': 'finger-bff-system.network19-v1.yaml', 'finger-gateway-mobile': 'finger-gateway-mobile-lan-v2.network19-v1.yaml'}
HEAPS={'finger-service-system':512,'finger-service-coms':768,'finger-auth':768,'finger-bff-system':768,'finger-gateway-mobile':512}
SNOWFLAKE={'finger-gateway-mobile':1,'finger-auth':2,'finger-service-system':3,'finger-service-coms':4,'finger-bff-system':5}
MAX_ARCHIVE=1024**3
MAX_JAR=256*1024**2
MAX_CONFIG=512*1024
FILES={'manifest.json',*[name+'/'+file for name in NAMES for file in ['app.jar','application.yaml']]}
class Rejected(ValueError):pass

def release_id(value):
 if not isinstance(value,str) or not re.fullmatch('[0-9]{8}T[0-9]{6}',value):raise Rejected('invalid release id')
 try:datetime.datetime.strptime(value,'%Y%m%dT%H%M%S')
 except ValueError:raise Rejected('invalid release timestamp') from None
 return value

def unique_pairs(items):
 result={}
 for key,value in items:
  if key in result:raise Rejected('duplicate JSON key')
  result[key]=value
 return result

def json_read(data):
 try:return json.loads(data,object_pairs_hook=unique_pairs)
 except (ValueError,UnicodeError):raise Rejected('invalid or duplicate JSON data') from None

def validate_header(h):
 if not isinstance(h,dict):raise Rejected('protocol header must be an object')
 action=h.get('action')
 allowed={'status':{'action'},'stage':{'action','release_id','archive_sha256','archive_bytes'},'activate':{'action','release_id'},'rollback':{'action','release_id'}}
 if action not in allowed or set(h)!=allowed[action]:raise Rejected('unknown action or fields')
 if action!='status':release_id(h['release_id'])
 if action=='stage':
  if not isinstance(h['archive_sha256'],str) or not re.fullmatch('[a-f0-9]{64}',h['archive_sha256']):raise Rejected('invalid archive digest')
  if type(h['archive_bytes']) is not int or not 0<h['archive_bytes']<=MAX_ARCHIVE:raise Rejected('invalid archive byte limit')
 return h

def parse_ssh(command):
 if not isinstance(command,str) or not command.isascii() or any(x in command for x in '\r\n\t\x00'):raise Rejected('noncanonical SSH command')
 parts=command.split(' ')
 if len(parts)<2 or parts[0]!='dell-publish-v1' or any(not x for x in parts):raise Rejected('unknown SSH command')
 action=parts[1]
 if action=='status' and len(parts)==2:return validate_header({'action':'status'})
 if action in ('activate','rollback') and len(parts)==3:return validate_header({'action':action,'release_id':parts[2]})
 if action=='stage' and len(parts)==5 and re.fullmatch('[1-9][0-9]{0,10}',parts[4]):return validate_header({'action':'stage','release_id':parts[2],'archive_sha256':parts[3],'archive_bytes':int(parts[4])})
 raise Rejected('unsupported SSH request grammar')

class UniqueYaml(yaml.SafeLoader):pass

def yaml_mapping(loader,node,deep=False):
 if any(k.value=='<<' for k,v in node.value):raise Rejected('YAML merge keys are not accepted in release config')
 result={}
 for key,value in node.value:
  name=loader.construct_object(key,deep=deep)
  if name in result:raise Rejected('duplicate YAML key')
  result[name]=loader.construct_object(value,deep=deep)
 return result
UniqueYaml.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,yaml_mapping)

def parse_yaml(data):
 if len(data)>MAX_CONFIG:raise Rejected('config exceeds byte cap')
 try:result=yaml.load(data,Loader=UniqueYaml)
 except Exception:raise Rejected('unsafe or invalid YAML data; values suppressed') from None
 if not isinstance(result,dict):raise Rejected('config must be mapping')
 return result

def check_config(cfg,name,namespace=None):
 try:
  spring=cfg['spring'];server=cfg['server'];nacos=spring['cloud']['nacos']
  if spring['application']['name']!=name or spring['profiles']['active']!='dell-test' or server['address']!='192.168.19.45' or server['port']!=PORTS[name]:raise Rejected('runtime identity/port/profile mismatch')
  if nacos['server-addr']!='192.168.19.20:8848':raise Rejected('Nacos target outside test')
  found=[]
  for section in ['discovery','config']:
   section_cfg=nacos[section]
   if section_cfg.get('server-addr') not in (None,'192.168.19.20:8848','${spring.cloud.nacos.server-addr}'):raise Rejected('nested Nacos address outside test')
   ns=str(uuid.UUID(section_cfg['namespace']))
   if namespace and ns!=namespace:raise Rejected('Nacos namespace differs from trusted policy')
   if section_cfg.get('group')!='DELL_TEST':raise Rejected('Nacos group outside trusted test chain')
   found.append(ns)
  if found[0]!=found[1]:raise Rejected('discovery/config namespace mismatch')
  imports=spring['config']['import']
  if not isinstance(imports,list) or len(imports)!=2:raise Rejected('exact common/service mandatory imports required')
  expected={'finger-common.network19-v1.yaml',CONFIG_IDS[name]};seen=set()
  for item in imports:
   u=urlsplit(item)
   if u.scheme!='nacos' or u.path not in expected or u.netloc or u.fragment:raise Rejected('remote or optional config imports rejected')
   q=parse_qs(u.query,keep_blank_values=True)
   if set(q)-{'group','refreshEnabled','refresh'} or q.get('group')!=['DELL_TEST']:raise Rejected('unexpected Nacos import options')
   if q.get('refreshEnabled',['false'])!=['false'] or q.get('refresh',['false'])!=['false']:raise Rejected('live import refresh not allowed by this release contract')
   seen.add(u.path)
  if seen!=expected:raise Rejected('mandatory import set mismatch')
  redis=spring.get('data',{}).get('redis')
  if redis and (redis.get('host')!='192.168.19.20' or redis.get('port')!=6379):raise Rejected('Redis outside test data node')
  rabbit=spring.get('rabbitmq')
  if rabbit and (rabbit.get('host')!='192.168.19.20' or rabbit.get('port')!=5672 or rabbit.get('virtual-host')!='/finger-test'):raise Rejected('Rabbit outside test data/vhost')
  if 'datasource' in spring:
   domain={'finger-auth':'auth','finger-service-system':'system','finger-service-coms':'coms'}.get(name)
   if not domain:raise Rejected('unexpected JDBC config in BFF/Gateway')
   ds=spring['datasource']
   if ds['username']!='finger_'+domain+'_test' or not ds['url'].startswith('jdbc:mysql://192.168.19.20:3306/finger_'+domain+'_test?'):raise Rejected('datasource outside approved test component')
  if cfg.get('snowflake')!={'data-center-id':1,'worker-id':SNOWFLAKE[name]}:raise Rejected('Snowflake identity differs from source metadata')
  if name=='finger-service-coms' and (cfg.get('file',{}).get('upload',{}).get('domain')!='http://192.168.19.45:9999/finger-bff-system/dell-test-files' or cfg.get('file',{}).get('upload',{}).get('path')!='/var/lib/finger/finger-service-coms/uploads'):raise Rejected('COMS upload contract differs from verified LAN V2')
  if name=='finger-auth' and cfg['finger']['auth']['bootstrap']['issuer']!='http://192.168.19.45:9999':raise Rejected('issuer differs from approved LAN candidate')
  return found[0]
 except Rejected:raise
 except Exception:raise Rejected('required runtime config structure missing; values suppressed') from None

def sha(path):
 with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def check_release(path,expected_id,namespace=None):
 release_id(expected_id)
 if path.resolve()!=path or path.is_symlink():raise Rejected('release path symlink rejected')
 m=json_read((path/'manifest.json').read_bytes())
 if m.get('schema_version')!=1 or m.get('release_id')!=expected_id or m.get('target_hostname')!='java-test-01' or m.get('target_ip')!='192.168.19.45' or m.get('data_ip')!='192.168.19.20' or m.get('profile')!='dell-test' or m.get('issuer')!='http://192.168.19.45:9999':raise Rejected('manifest target/profile identity rejected')
 rows=m.get('services',[])
 if not isinstance(rows,list) or len(rows)!=5 or {x.get('name') for x in rows}!=set(NAMES):raise Rejected('service set must be exact five-chain')
 namespaces=[]
 for row in rows:
  name=row['name']
  if set(row)!={'name','port','xms_mib','xmx_mib','metaspace_mib','memory_max_mib','jar_sha256','config_sha256'}:raise Rejected('unexpected service/unit fields')
  expected={'port':PORTS[name],'xms_mib':128,'xmx_mib':HEAPS[name],'metaspace_mib':256,'memory_max_mib':1024 if HEAPS[name]==512 else 1536}
  if any(type(row.get(k)) is not int or row[k]!=v for k,v in expected.items()):raise Rejected('service port/resource budget rejected')
  for filename,key,cap in [('app.jar','jar_sha256',MAX_JAR),('application.yaml','config_sha256',MAX_CONFIG)]:
   file=path/name/filename
   if not file.is_file() or file.is_symlink() or file.resolve()!=file or file.stat().st_size>cap or not re.fullmatch('[a-f0-9]{64}',str(row.get(key,''))) or sha(file)!=row[key]:raise Rejected('release file/hash/type mismatch')
  if not zipfile.is_zipfile(path/name/'app.jar'):raise Rejected('JAR is not ZIP/JAR format')
  namespaces.append(check_config(parse_yaml((path/name/'application.yaml').read_bytes()),name,namespace))
 if len(set(namespaces))!=1:raise Rejected('release namespaces differ')
 return m,namespaces[0]

def octal(field):
 value=field.strip(b'\0 ')
 if not value or any(x not in b'01234567' for x in value):raise Rejected('non-octal USTAR numeric field')
 return int(value,8)

def text_field(field):
 pos=field.find(b'\0')
 if pos<0 or any(field[pos:]):raise Rejected('noncanonical USTAR text field')
 try:return field[:pos].decode('ascii')
 except UnicodeError:raise Rejected('non-ASCII USTAR member name') from None

def canonical_members():
 return ['manifest.json']+[name+'/'+file for name in NAMES for file in ['app.jar','application.yaml']]

def build_canonical_archive(bundle,output,expected_id,namespace=None):
 check_release(bundle,expected_id,namespace)
 estimated=sum(512+((bundle/name).stat().st_size+511)//512*512 for name in canonical_members())+1024
 if ((estimated+10239)//10240)*10240>MAX_ARCHIVE:raise Rejected('canonical total size exceeds cap before packing')
 if output.exists() or output.is_symlink():raise Rejected('new private archive output required')
 with output.open('xb') as stream:
  output.chmod(0o600)
  with tarfile.open(fileobj=stream,mode='w',format=tarfile.USTAR_FORMAT) as t:
   for name in canonical_members():
    file=bundle/name;info=tarfile.TarInfo(name);info.type=tarfile.REGTYPE;info.size=file.stat().st_size;info.mode=0o600;info.uid=0;info.gid=0;info.mtime=0;info.uname='';info.gname=''
    with file.open('rb') as data:t.addfile(info,data)
 if output.stat().st_size>MAX_ARCHIVE:raise Rejected('canonical archive exceeds total cap')
 return output

def extract_archive(archive,destination,expected_id,namespace=None):
 # No TarFile parsing on privileged input: PAX/GNU metadata is rejected at its header.
 if destination.exists() or destination.resolve(strict=False)!=destination:raise Rejected('new root-owned pending directory required')
 size=archive.stat().st_size
 if size>MAX_ARCHIVE or size%512:raise Rejected('archive total size/block alignment rejected')
 expected=canonical_members();count=0;total=0
 destination.mkdir(mode=0o700,parents=False)
 with archive.open('rb') as stream:
  while True:
   header=stream.read(512)
   if len(header)!=512:raise Rejected('USTAR header truncated')
   if header==bytes(512):
    if stream.read(512)!=bytes(512):raise Rejected('USTAR requires two zero terminator blocks')
    if size!=((stream.tell()+10239)//10240)*10240:raise Rejected('noncanonical excess USTAR record padding')
    while True:
     block=stream.read(1024*1024)
     if not block:break
     if any(block):raise Rejected('nonzero trailing archive data')
    break
   count+=1
   if count>11:raise Rejected('USTAR member12 rejected before payload parsing')
   if header[156:157]!=b'0':raise Rejected('only regular USTAR files; PAX/GNU/link/device rejected')
   if header[257:263]!=b'ustar\0' or header[263:265]!=b'00':raise Rejected('canonical uncompressed USTAR required')
   checksum=octal(header[148:156])
   if checksum!=sum(header[:148]+b' '*8+header[156:]):raise Rejected('USTAR header checksum mismatch')
   name=text_field(header[:100])
   if name!=expected[count-1] or text_field(header[345:500]) or text_field(header[157:257]):raise Rejected('USTAR exact ordered member/path required')
   if text_field(header[265:297]) or text_field(header[297:329]):raise Rejected('USTAR owner names must be empty')
   if octal(header[100:108])!=0o600 or octal(header[108:116])!=0 or octal(header[116:124])!=0 or octal(header[136:148])!=0:raise Rejected('USTAR canonical owner/mode/time required')
   length=octal(header[124:136]);cap=128*1024 if name=='manifest.json' else MAX_JAR if name.endswith('.jar') else MAX_CONFIG
   total+=length
   if not 0<length<=cap or total>MAX_ARCHIVE:raise Rejected('USTAR file/logical total cap exceeded')
   target=destination/name;target.parent.mkdir(mode=0o700,exist_ok=True)
   with target.open('xb') as out:
    target.chmod(0o600);remaining=length
    while remaining:
     data=stream.read(min(remaining,1024*1024))
     if not data:raise Rejected('USTAR file payload truncated')
     out.write(data);remaining-=len(data)
   padding=stream.read((-length)%512)
   if len(padding)!=(-length)%512 or any(padding):raise Rejected('USTAR file padding rejected')
 if count!=11:raise Rejected('USTAR exact11 files required')
 return check_release(destination,expected_id,namespace)
