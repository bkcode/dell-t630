#!/usr/bin/env python3
from pathlib import Path
import sys,json,shlex,datetime
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'scripts'));import control
nonce=json.loads((R/'network19/services-media/stage-nonces.json').read_text())['260'];helper='/opt/dell/network19/services-media/nas-os-network.py';before=control.pve('qm config 260').decode();old=next(l.partition(': ')[2] for l in before.splitlines() if l.startswith('net0: '));assert 'bridge=vmbr40' in old and 'BC:24:11:A7:3B:73' in old
new='virtio=BC:24:11:A7:3B:73,bridge=vmbr19,firewall=0'
control.pve('install -m 600 /etc/pve/qemu-server/260.conf /root/dell-bootstrap/network19/before/vm260.conf')
record={'at':datetime.datetime.now().isoformat(),'vmid':260,'old_net0':old,'new_net0':new,'status':'starting'}
def action(op):
 v=json.loads(control.pve(shlex.join(['qm','guest','exec','260','--timeout','300','--','python3','-I','-B',helper,op,'--window',nonce,'--qga-console-standby','--smb-clients-drained']),timeout=340));assert v.get('exitcode')==0,v;return v
try:
 control.pve(shlex.join(['qm','set','260','--net0',new]));record['QGA_OMV_commit']=action('apply')
 info=control.trust_guest(260,expected_ip='192.168.19.60');record['strict_SSH']=control.guest(260,'id -un; hostname; ip -4 -br addr; ip -4 route; resolvectl dns ens18; systemctl is-active ssh qemu-guest-agent',info=info);assert record['strict_SSH']['exit_code']==0
 rows=json.loads(control.qga(260,['ip','-4','-j','addr','show','dev','ens18']));ips=[a['local'] for x in rows for a in x.get('addr_info',[]) if a.get('family')=='inet'];assert ips==['192.168.19.60']
 routes=json.loads(control.qga(260,['ip','-4','-j','route','show','default']));assert len(routes)==1 and routes[0].get('gateway')=='192.168.19.1'
 control.pve('qm set 260 --ipconfig0 ip=192.168.19.60/24,gw=192.168.19.1 --nameserver 192.168.19.1')
 p=R/'network19/evidence/migrated-access.json';v=json.loads(p.read_text());v['targets']['260']=info;p.write_text(json.dumps(v,indent=2)+'\n');record['status']='NAS-official-OMV-network19-committed-app-still-quiesced'
except BaseException:
 errors=[]
 for name,fn in [('NIC',lambda:control.pve(shlex.join(['qm','set','260','--net0',old]))),('OMV',lambda:action('rollback'))]:
  try:record['rollback_'+name]=fn()
  except Exception as e:errors.append(name+':'+type(e).__name__)
 record['status']='failed-rollback-attempted';record['rollback_errors']=errors
 (R/'network19/evidence/NAS-OS-apply.json').write_text(json.dumps(record,indent=2)+'\n');raise
(R/'network19/evidence/NAS-OS-apply.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps({'vmid':260,'status':record['status'],'new_IP':'192.168.19.60'}))
