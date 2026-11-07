#!/usr/bin/env python3
from pathlib import Path
import sys,json,shlex,datetime
BASE=Path(__file__).resolve().parents[1];sys.path.insert(0,str(BASE/'scripts'));import control
c=json.loads((BASE/'network19/contracts/230.json').read_text());rows=json.loads((BASE/'evidence/implementation/private-guest-access.json').read_text())['roles'];old=next(x['target'] for x in rows if x['target']['vmid']==230);new=dict(old,ip=c['new_ip'])
r=control.guest(230,'sudo install -m 750 /dev/stdin /usr/local/libexec/dell-network19-guest-net',data=(BASE/'network19/guest-network.py').read_bytes(),info=old);assert r['exit_code']==0
before=control.pve('qm config 230').decode();assert ('net0: '+c['old_PVE_net0']) in before
# Original full config remains PVE-only, never emit keys/passwords.
control.pve('install -m 600 /etc/pve/qemu-server/230.conf /root/dell-bootstrap/network19/before/vm230.conf')
def qga(action):
 args=['qm','guest','exec','230','--timeout','120','--','/usr/bin/python3','/usr/local/libexec/dell-network19-guest-net',action]
 return json.loads(control.pve(shlex.join(args),timeout=150))
record={'at':datetime.datetime.now().isoformat(),'vmid':230,'old_ip':c['old_ip'],'new_ip':c['new_ip'],'status':'starting'}
try:
 control.pve(shlex.join(['qm','set','230','--net0',c['new_PVE_net0']]))
 commit=qga('apply');record['OS_commit']=commit;assert commit.get('exitcode')==0
 control.pve(shlex.join(['qm','set','230','--ipconfig0','ip='+c['new_ip']+'/24,gw=192.168.19.1','--nameserver','192.168.19.1']))
 r=control.guest(230,"id -un; hostname; ip -4 -br addr; ip -4 route; resolvectl dns eth0; systemctl is-active systemd-networkd systemd-resolved",info=new);assert r['exit_code']==0;record['strict_new_SSH']=r
 record['status']='canary230-OS-network19-committed-apps-none-monitoring-pending';record['new_target']=new
except BaseException:
 control.pve(shlex.join(['qm','set','230','--net0',c['old_PVE_net0']]))
 record['rollback_OS']=qga('rollback');record['status']='failed-rollback-attempted';(BASE/'network19/evidence/canary230-migration.json').write_text(json.dumps(record,indent=2)+'\n');raise
(BASE/'network19/evidence/canary230-migration.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps({'status':record['status'],'IP':c['new_ip'],'strict_SSH':True,'new_target':new}))
