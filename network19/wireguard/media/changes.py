"""Pure exact append of the explicitly trusted VPN subnet; never changes auth or other XML bytes."""
import copy
import re
import xml.etree.ElementTree as ET

VPN='10.66.66.0/24'
SMB_OLD='192.168.21.0/24 192.168.19.0/24 127.0.0.1'
SMB_NEW=SMB_OLD+' '+VPN
JF_OLD=['192.168.19.0/24','192.168.21.0/24','127.0.0.0/8','172.18.0.1/32']
JF_NEW=JF_OLD+[VPN]


def smb_parameters(value):
    if value.get('hostsallow')!=SMB_OLD:raise ValueError('SMB source allowlist drift or VPN already present; review instead of duplicate append')
    result=copy.deepcopy(value);result['hostsallow']=SMB_NEW
    return result


def xml_append(raw):
    if len(raw)>1024*1024:raise ValueError('Unexpected network XML size')
    root=ET.fromstring(raw);subnets=root.findall('LocalNetworkSubnets')
    if len(subnets)!=1 or [x.text for x in subnets[0]]!=JF_OLD:raise ValueError('Jellyfin original subnets differ')
    for key in ['EnableRemoteAccess','EnableUPnP']:
        elements=root.findall(key)
        if len(elements)!=1 or (elements[0].text or '').strip()!='false':raise ValueError('Remote access/UPnP must remain disabled')
    matches=list(re.finditer(rb'(<LocalNetworkSubnets>)(.*?)(</LocalNetworkSubnets>)',raw,re.S))
    if len(matches)!=1:raise ValueError('Unexpected XML serialization; no broad rewrite')
    match=matches[0];body=match[2];node=b'<string>'+VPN.encode()+b'</string>'
    if b'\n' in body:
        newline=b'\r\n' if b'\r\n' in body else b'\n'
        indent=re.search(rb'(?m)^([ \t]*)<string>',body)
        if indent is None:raise ValueError('Unknown subnet indentation')
        tail=body.rsplit(b'\n',1)[1]
        if tail.strip():
            # Jellyfin may put its closing container tag immediately after the last item.
            # Append one node at that boundary; every existing byte remains untouched.
            changed=body+node
        else:
            prefix=body[:-len(tail)] if tail else body
            changed=prefix+indent[1]+node+newline+tail
    else:changed=body+node
    result=raw[:match.start(2)]+changed+raw[match.end(2):]
    check=ET.fromstring(result)
    if [x.text for x in check.find('LocalNetworkSubnets')]!=JF_NEW:raise ValueError('New subnet structure verification failed')
    return result
