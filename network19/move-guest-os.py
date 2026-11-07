#!/usr/bin/env python3
"""Coordinator only: exact approved role NIC/networkd transaction, no app changes."""
from pathlib import Path
import sys,json,shlex,datetime,argparse
BASE=Path(__file__).resolve().parents[1];sys.path.insert(0,str(BASE/'scripts'));import control
p=argparse.ArgumentParser();p.add_argument('vmid',type=int);p.add_argument('action',choices=['stage','apply','rollback']);a=p.parse_args()
c=json.loads((BASE/f'network19/contracts/{a.vmid}.json').read_text());assert a.vmid not in (190,260)
rows=json.loads((BASE/'evidence/implementation/private-guest-access.json').read_text())['roles'];old=next(x['target'] for x in rows if x['target']['vmid']==a.vmid);new=dict(old,ip=c['new_ip'])
helper='/usr/local/libexec/dell-network19-guest-net'
def qga(action):
 r=json.loads(control.pve(shlex.join(['qm','guest','exec',str(a.vmid),'--timeout','120','--','/usr/bin/python3',helper,action]),timeout=150));assert r.get('exitcode')==0,r;return r
record={'at':datetime.datetime.now().isoformat(),'vmid':a.vmid,'old_ip':c['old_ip'],'new_ip':c['new_ip'],'action':a.action}
if a.action=='stage':
 current=control.pve(f'qm config {a.vmid}').decode();assert ('net0: '+c['old_PVE_net0']) in current
 r=control.guest(a.vmid,'sudo install -m 750 /dev/stdin '+helper,data=(BASE/'network19/guest-network.py').read_bytes(),info=old);assert r['exit_code']==0,r
 r=control.guest(a.vmid,'sudo python3 '+helper+' stage',data=json.dumps(c).encode(),info=old);assert r['exit_code']==0,r
 record['stage']=json.loads(r['stdout']);record['status']='OS-staged-old-network-active'
elif a.action=='apply':
 current=control.pve(f'qm config {a.vmid}').decode();assert ('net0: '+c['old_PVE_net0']) in current
 previous_meta={k: next((line.split(': ',1)[1] for line in current.splitlines() if line.startswith(k+': ')),None) for k in ['ipconfig0','nameserver']}
 control.pve(f'install -d -m 700 /root/dell-bootstrap/network19/before')
 control.pve(f'install -m 600 /etc/pve/qemu-server/{a.vmid}.conf /root/dell-bootstrap/network19/before/vm{a.vmid}.conf')
 try:
  control.pve(shlex.join(['qm','set',str(a.vmid),'--net0',c['new_PVE_net0']]))
  record['OS_commit']=qga('apply')
  control.pve(shlex.join(['qm','set',str(a.vmid),'--ipconfig0','ip='+c['new_ip']+'/24,gw=192.168.19.1','--nameserver','192.168.19.1']))
  r=control.guest(a.vmid,'id -un; hostname; ip -4 -br addr; ip -4 route; resolvectl dns eth0; systemctl is-active systemd-networkd systemd-resolved',info=new);assert r['exit_code']==0,r
  record['strict_new_SSH']=r;record['new_target']=new;record['status']='OS-network19-committed-app-state-managed-separately'
  ledger=BASE/'network19/evidence/migrated-access.json';values=json.loads(ledger.read_text());values.setdefault('targets',{})[str(a.vmid)]=new;ledger.write_text(json.dumps(values,indent=2)+'\n')
 except BaseException:
  errors=[]
  for name,fn in [('NIC',lambda:control.pve(shlex.join(['qm','set',str(a.vmid),'--net0',c['old_PVE_net0']]))),('OS',lambda:qga('rollback')),('CI-metadata',lambda:control.pve(shlex.join(['qm','set',str(a.vmid)]+[part for key,value in previous_meta.items() if value is not None for part in ['--'+key,value]]+(['--delete',','.join(key for key,value in previous_meta.items() if value is None)] if any(value is None for value in previous_meta.values()) else []))))]:
   try:fn();record['rollback_'+name]='completed'
   except Exception as ex:errors.append(name+':'+type(ex).__name__)
  if not errors:
   ledger=BASE/'network19/evidence/migrated-access.json';v=json.loads(ledger.read_text());v.get('targets',{}).pop(str(a.vmid),None);ledger.write_text(json.dumps(v,indent=2)+'\n')
  record['rollback_errors']=errors;record['status']='failed-old-OS-restored-apps-separate' if not errors else 'failed-rollback-incomplete-rescue-required'
  (BASE/f'network19/evidence/OS-{a.vmid}-apply.json').write_text(json.dumps(record,indent=2)+'\n');raise
else:
 previous=control.pve(f'cat /root/dell-bootstrap/network19/before/vm{a.vmid}.conf').decode()
 assert ('net0: '+c['old_PVE_net0']) in previous
 previous_meta={k:next((line.split(': ',1)[1] for line in previous.splitlines() if line.startswith(k+': ')),None) for k in ['ipconfig0','nameserver']}
 errors=[]
 for name,fn in [('NIC',lambda:control.pve(shlex.join(['qm','set',str(a.vmid),'--net0',c['old_PVE_net0']]))),('OS',lambda:qga('rollback')),('CI-metadata',lambda:control.pve(shlex.join(['qm','set',str(a.vmid)]+[part for key,value in previous_meta.items() if value is not None for part in ['--'+key,value]]+(['--delete',','.join(key for key,value in previous_meta.items() if value is None)] if any(value is None for value in previous_meta.values()) else []))))]:
  try:fn();record['rollback_'+name]='completed'
  except Exception as ex:errors.append(name+':'+type(ex).__name__)
 if not errors:
  check=control.guest(a.vmid,'id -un; hostname',info=old);record['old_strict_SSH']=check
  if check['exit_code']!=0:errors.append('old-strict-SSH')
 if not errors:
  ledger=BASE/'network19/evidence/migrated-access.json';v=json.loads(ledger.read_text());v.get('targets',{}).pop(str(a.vmid),None);ledger.write_text(json.dumps(v,indent=2)+'\n')
 record['rollback_errors']=errors;record['status']='old-OS-restored-app-state-managed-separately' if not errors else 'rollback-incomplete-recovery-required'

(BASE/f'network19/evidence/OS-{a.vmid}-{a.action}.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps({'vmid':a.vmid,'status':record['status'],'new_ip':c['new_ip']}))
