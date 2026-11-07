#!/usr/bin/env python3
"""NAS260 only, read-only effective share/Jellyfin VPN recognition preflight."""
import json,sys
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'scripts'));import control
control.BASE+=['-o','ForwardAgent=no']
info=json.loads((ROOT/'network19/evidence/migrated-access.json').read_text())['targets']['260']
assert info['ip']=='192.168.19.60'
script=r'''
import datetime,json,os,socket,subprocess
from pathlib import Path
import xml.etree.ElementTree as ET
assert os.geteuid()==0 and socket.gethostname().split('.')[0]=='nas-media' and not Path('/etc/pve').exists()
ENV={'PATH':'/usr/sbin:/usr/bin:/sbin:/bin','LANG':'C','LC_ALL':'C'}
def run(args):
 p=subprocess.run(args,capture_output=True,text=True,env=ENV,timeout=25)
 if p.returncode:raise RuntimeError('fixed metadata read failed')
 return p.stdout
fields=['hosts allow','hosts deny','valid users','read list','write list','read only','guest ok']
shares={name:{key:run(['/usr/bin/testparm','-s','--section-name='+name,'--parameter-name='+key]).strip() for key in fields} for name in ['media','games','incoming']}
objects=json.loads(run(['/usr/sbin/omv-confdbadm','read','--prettify','conf.service.smb.share']));objects=objects if isinstance(objects,list) else [objects]
ids={'media':'32e8c383-753a-48b4-b397-9adf490bb0e1','games':'86815a17-f9cd-4c0e-b548-4266949b75d4','incoming':'c9c8d068-e056-4ed3-be78-775118367582'}
model=json.loads(Path('/usr/share/openmediavault/datamodels/rpc.smb.json').read_text());model=model if isinstance(model,list) else [model];schema=[x for x in model if x.get('id')=='rpc.smb.setshare'];assert len(schema)==1
safe={name:{k:next(x for x in objects if x['uuid']==ident)[k] for k in ['uuid','sharedfolderref','hostsallow','hostsdeny','readonly','guest']} for name,ident in ids.items()}
mount='/srv/dev-disk-by-uuid-5b19837c-128c-498a-b79d-563db810c34a';p=Path(mount+'/appdata/jellyfin/config/config/network.xml');tree=ET.fromstring(p.read_bytes())
keys=['LocalNetworkSubnets','EnableRemoteAccess','EnableUPnP','LocalNetworkAddresses','KnownProxies','RemoteIPFilter','IsRemoteIPFilterBlacklist']
network={k:([x.text for x in tree.find(k)] if list(tree.find(k)) else tree.find(k).text) for k in keys if tree.find(k) is not None}
fmt='{"id":{{json .Id}},"image":{{json .Image}},"pid":{{json .State.Pid}},"started_at":{{json .State.StartedAt}},"running":{{json .State.Running}},"health":{{if .State.Health}}{{json .State.Health.Status}}{{else}}null{{end}}}'
container=json.loads(run(['/usr/bin/docker','--host','unix:///var/run/docker.sock','inspect','--type','container','--format',fmt,'dell-nas-jellyfin-1']))
units={name:dict(x.split('=',1) for x in run(['/usr/bin/systemctl','show',name,'--property=ActiveState,SubState,MainPID']).splitlines() if '='in x) for name in ['dell-nas-jellyfin.service','smbd.service','openmediavault-engined.service']}
result={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'role':260,'ip':'192.168.19.60','read_only':True,'effective_shares':shares,'OMV_share_network_fields':safe,'official_SMB_setShare_parameter_fields':sorted(schema[0]['params']['properties']),'Jellyfin_network_fields':network,'Jellyfin_XML_metadata':{'path':str(p),'uid':p.stat().st_uid,'gid':p.stat().st_gid,'mode':oct(p.stat().st_mode&0o777)},'units':units,'container':container,'data_mount':json.loads(run(['/usr/bin/findmnt','--json','--mountpoint',mount,'--output','TARGET,SOURCE,FSTYPE,UUID'])),'Env_Cmd_health_logs_private_credentials_read':False,'mutations':False}
print(json.dumps(result))
'''
r=control.guest(260,'sudo python3 -',data=script.encode(),timeout=130,info=info)
if r['exit_code']:raise SystemExit('NAS VPN readonly preflight unconfirmed; raw output withheld')
v=json.loads(r['stdout']);Path(__file__).with_name('preflight.json').write_text(json.dumps(v,indent=2)+'\n')
print(json.dumps({'role':260,'status':'readonly-VPN-recognition-preflight-complete','SMB_hosts_allow':{k:x['hosts allow'] for k,x in v['effective_shares'].items()},'JF_local_subnets':v['Jellyfin_network_fields'].get('LocalNetworkSubnets'),'JF_remote_access':v['Jellyfin_network_fields'].get('EnableRemoteAccess'),'JF_UPnP':v['Jellyfin_network_fields'].get('EnableUPnP')}))
