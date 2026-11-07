#!/usr/bin/env python3
"""Apply only onboot/startup metadata to newly assigned VMs, never power-cycle."""
from pathlib import Path
import sys,json,datetime,shlex
BASE=Path(__file__).resolve().parents[1];sys.path.insert(0,str(BASE/'scripts'));import control
plan=json.loads((BASE/'plan.json').read_text());order=json.loads((BASE/'infra/startup-order.json').read_text());results=[]
allowed={200,201,210,220,221,230,231,232,240,250,260,270};assert {r['vmid'] for r in order['roles']}==allowed
for row in order['roles']:
 vmid=row['vmid'];expected=next(r['name'] for r in plan['roles'] if r.get('vmid',r.get('planned_vmid'))==vmid)
 def read():
  lines=control.pve('qm config '+str(vmid)).decode().splitlines();m=dict(l.split(':',1) for l in lines if ':' in l);return {k:m[k].strip() for k in ['name','onboot','startup'] if k in m}
 before=read();assert before['name']==expected
 startup='order='+str(row['order'])+',up='+str(row['up_seconds'])+',down='+str(row['down_seconds'])
 control.pve(shlex.join(['qm','set',str(vmid),'--onboot','1','--startup',startup]))
 after=read();assert after.get('onboot')=='1' and all(x in after.get('startup','').split(',') for x in startup.split(','))
 results.append({'vmid':vmid,'before':before,'after':after})
value={'at':datetime.datetime.now().isoformat(),'status':'assigned-VM-start-stop-order-applied-no-reboot','scope':order['scope'],'roles':results,'limitations':['Startup delays are sequencing only; whole-host reboot and application recovery not yet tested']}
(BASE/'evidence/implementation/startup-order-applied.json').write_text(json.dumps(value,indent=2)+'\n');print(json.dumps({'status':value['status'],'vms':len(results)}))
