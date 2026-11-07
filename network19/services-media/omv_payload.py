"""Pure NAS network payload builder from the actually installed OMV8.6 public schema."""
import json
from pathlib import Path

FIELDS={'uuid','devicename','method','address','netmask','gateway','routemetric','method6','address6','netmask6','gateway6','routemetric6','dnsnameservers','dnssearch','mtu','wol','comment','altmacaddress'}


def build(before,schema):
    if schema.get('id')!='rpc.network.setethernetiface' or set(schema['params']['properties'])!=FIELDS:
        raise ValueError('OMV RPC model changed; review instead of guessing')
    if not FIELDS<=set(before):raise ValueError('Actual wired object missing required RPC fields')
    if (before['uuid'],before['devicename'],before['address'],before['gateway'],before['method'])!=('f5ea6395-ec2e-47ca-9e5e-4d541eeb9f5f','ens18','10.63.40.10','10.63.40.1','static'):
        raise ValueError('Assigned existing wired object differs')
    old={key:before[key] for key in schema['params']['properties']}
    new=dict(old,address='192.168.19.60',netmask='255.255.255.0',gateway='192.168.19.1',dnsnameservers='192.168.19.1')
    for values in (old,new):
        for key,rule in schema['params']['properties'].items():
            value=values[key];typ={'string':str,'integer':int,'boolean':bool}[rule['type']]
            if type(value) is not typ:raise ValueError('OMV field type differs')
            if 'enum' in rule and value not in rule['enum']:raise ValueError('OMV field enum differs')
            if 'minimum' in rule and value<rule['minimum'] or 'maximum' in rule and value>rule['maximum']:raise ValueError('OMV field range differs')
    return {'status':'prepared-not-applied','owner':'root network/QGA window only','MAC_must_match':'bc:24:11:a7:3b:73','old_RPC':{'service':'Network','method':'setEthernetIface','params':old},'new_RPC':{'service':'Network','method':'setEthernetIface','params':new},'apply_then_deploy':'root separately invokes installed official network setter then reviewed omv-salt systemd-networkd deployment; never populate/reinitialize','preserved_fields':sorted(FIELDS-{'address','netmask','gateway','dnsnameservers'})}


if __name__=='__main__':
    base=Path(__file__).resolve().parent
    nas=next(x for x in json.loads((base/'active-readonly-preflight.json').read_text()) if x['role']==260)
    schemas=json.loads((base/'omv-ethernet-rpc-schema.json').read_text())['matching_schemas']
    if len(schemas)!=1:raise SystemExit('Exact installed network RPC schema unavailable')
    result=build(nas['OMV_wired_object'],schemas[0]['schema'])
    (base/'omv-network-payload.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps({'status':result['status'],'MAC_must_match':result['MAC_must_match'],'secrets_or_identity_changes':False}))
