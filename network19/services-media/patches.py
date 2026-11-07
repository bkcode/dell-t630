"""Pure, exact media-role address transforms. No I/O or networking."""
import hashlib
import json
import re
import xml.etree.ElementTree as ET


class Rejected(RuntimeError):
    pass


def sha(value):return hashlib.sha256(value).hexdigest()


def replace_exact(raw, old, new, count):
    if raw.count(old)!=count:raise Rejected('exact reviewed old selector count differs')
    return raw.replace(old,new)


def env_patch(raw, changes):
    """changes[key]=(reviewed old values, public new value). Preserve all other bytes."""
    out=[];seen=set();protected=[]
    for line in raw.splitlines(keepends=True):
        match=re.fullmatch(rb'([A-Za-z_][A-Za-z0-9_]*)=(.*?)(\r?\n|$)',line)
        if not match:
            out.append(line);protected.append(line);continue
        key=match[1].decode();value=match[2]
        if key in seen:raise Rejected('duplicate env key')
        seen.add(key)
        if key not in changes:
            out.append(line);protected.append(line);continue
        plain=value.decode();quote=plain[:1] if plain[:1] in ("'",'"') else ''
        if quote:
            if len(plain)<2 or not plain.endswith(quote):raise Rejected('unterminated reviewed public env value')
            plain=plain[1:-1]
        olds,new=changes[key]
        if plain not in olds or any(c in new for c in "\n\r'\"\\"):raise Rejected('unexpected old value or unsafe public replacement')
        out.append(match[1]+b'='+(quote+new+quote).encode()+match[3])
    if not set(changes)<=seen:raise Rejected('required public env key absent')
    result=b''.join(out)
    return result,sha(b''.join(protected))


def json_ip(raw, old, new):
    value=json.loads(raw)
    if value.get('expected_guest_ip')!=old:raise Rejected('assignment/marker old IP mismatch')
    value['expected_guest_ip']=new
    return (json.dumps(value,indent=2,ensure_ascii=False)+'\n').encode()


def penpot(files):
    base='/opt/dell/penpot/';here=base+'runtime/health-supervision/'
    result={}
    result[base+'application/target-api.py']=replace_exact(files[base+'application/target-api.py'],b"ORIGIN = 'http://127.0.0.1:9001'",b"ORIGIN = 'http://192.168.19.50:9001'",1)
    result[base+'assignment.json']=json_ip(files[base+'assignment.json'],'10.63.30.30','192.168.19.50')
    result['/etc/penpot/.env'],proof=env_patch(files['/etc/penpot/.env'],{'PENPOT_PUBLIC_URI':({'http://192.168.21.22:9001'},'http://192.168.19.50:9001')})
    result[base+'compose.fresh.yaml']=replace_exact(files[base+'compose.fresh.yaml'],b'    - 0.0.0.0:9001:8080\n',b'    - 192.168.19.50:9001:8080\n',1)
    result[base+'compose.fresh.yaml']=replace_exact(result[base+'compose.fresh.yaml'],b'    - --upstream=https://1.1.1.1/dns-query\n    - --upstream=https://1.0.0.1/dns-query\n',b'    - --upstream=192.168.19.1:53\n',1)
    result[here+'supervisor.py']=replace_exact(files[here+'supervisor.py'],b"'10.63.30.30'",b"'192.168.19.50'",2)
    result[here+'node-health.mjs']=replace_exact(files[here+'node-health.mjs'],b'http://192.168.21.22:9001',b'http://192.168.19.50:9001',2)
    lock=json.loads(files[here+'deployment-lock.json'])
    if lock['guest']!={'vmid':250,'hostname':'penpot-service','ip':'10.63.30.30','arch':'amd64'}:raise Rejected('old lock guest identity differs')
    for group,prefix in [('package_file_sha256',base),('supervision_file_sha256',here)]:
        for relative,digest in lock[group].items():
            path=prefix+relative
            if relative.startswith('/') or '..' in relative.split('/') or path not in files or sha(files[path])!=digest:
                raise Rejected('existing public package SHA differs; stage before any mutation')
            if path in result:lock[group][relative]=sha(result[path])
    lock['guest']['ip']='192.168.19.50'
    result[here+'deployment-lock.json']=(json.dumps(lock,indent=2,ensure_ascii=False)+'\n').encode()
    return result,{'protected_env_bytes_sha256':proof}


def nexus(files):
    b='/opt/dell/nexus/'
    result={b+x:json_ip(files[b+x],'10.63.30.20','192.168.19.31') for x in ('assignment.json','fresh-instance.json')}
    result[b+'application-import.py']=replace_exact(files[b+'application-import.py'],b"ORIGIN = 'http://127.0.0.1:8081'",b"ORIGIN = 'http://192.168.19.31:8081'",1)
    result['/etc/nexus.env'],proof=env_patch(files['/etc/nexus.env'],{'NEXUS_BIND_ADDRESS':({'0.0.0.0','10.63.30.20'},'192.168.19.31')})
    return result,{'protected_env_bytes_sha256':proof}


NAS_NETWORK='/srv/dev-disk-by-uuid-5b19837c-128c-498a-b79d-563db810c34a/appdata/jellyfin/config/config/network.xml'

def nas(files):
    result={}
    result['/opt/dell/nas/.env'],proof=env_patch(files['/opt/dell/nas/.env'],{
        'NAS_BIND_IP':({'10.63.40.10'},'192.168.19.60'),
        'JELLYFIN_PUBLIC_URL':({'http://192.168.21.22:8096','http://10.63.40.10:8096'},'http://192.168.19.60:8096')})
    raw=files[NAS_NETWORK];tree=ET.fromstring(raw)
    values=tree.findall('LocalNetworkSubnets');remote=tree.findall('EnableRemoteAccess')
    if len(values)!=1 or len(remote)!=1 or remote[0].text!='false':raise Rejected('review live Jellyfin network schema/remote-access policy')
    subnets=[x.text for x in values[0]]
    if subnets.count('10.63.40.0/24')!=1 or '192.168.19.0/24' in subnets or not {'192.168.21.0/24','127.0.0.0/8'}<=set(subnets):raise Rejected('unexpected Jellyfin LAN subset')
    # Preserve the full XML bytes except this one exact network member.
    result[NAS_NETWORK]=replace_exact(raw,b'<string>10.63.40.0/24</string>',b'<string>192.168.19.0/24</string>',1)
    return result,{'protected_env_bytes_sha256':proof}


TRANSFORMS={250:penpot,221:nexus,260:nas}
