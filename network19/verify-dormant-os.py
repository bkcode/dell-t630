from pathlib import Path
import sys,json,shlex,datetime
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'scripts'));import control
script=r'''import subprocess,json,time,datetime
from pathlib import Path
out=[];query="import json,subprocess,socket; x=json.loads(subprocess.check_output(['ip','-4','-j','addr'])); print(json.dumps({'hostname':socket.gethostname(),'addresses':[a['local'] for r in x if r['ifname']!='lo' and not r['ifname'].startswith(('docker','br-','veth')) for a in r.get('addr_info',[]) if a.get('family')=='inet'],'defaults':json.loads(subprocess.check_output(['ip','-4','-j','route','show','default']))}))"
def run(a,timeout=30):return subprocess.run(a,capture_output=True,text=True,timeout=timeout)
for vmid,expected in [(9000,'192.168.19.190'),(9002,'192.168.19.191'),(9003,'192.168.19.192'),(9004,'192.168.19.193'),(9005,'192.168.19.194'),(9006,'192.168.19.195'),(9020,'192.168.19.196')]:
 assert 'stopped' in run(['qm','status',str(vmid)]).stdout
 row={'vmid':vmid,'expected_IP':expected,'started_at':datetime.datetime.now().isoformat()}
 try:
  p=run(['qm','start',str(vmid)],60);assert p.returncode==0
  end=time.monotonic()+90
  while True:
   p=run(['qm','guest','exec',str(vmid),'--timeout','10','--','python3','-c',query],20)
   if p.returncode==0:
    try:
     v=json.loads(p.stdout);value=json.loads(v.get('out-data','{}'))
     if value.get('addresses')==[expected] and len(value.get('defaults',[]))==1 and value['defaults'][0].get('gateway')=='192.168.19.1':row['OS_network']=value;row['passed']=True;break
    except Exception:pass
   if time.monotonic()>end:row.update(passed=False,reason='OS-new-IP-and-unique-default-not-confirmed');break
   time.sleep(2)
 except Exception as e:row.update(passed=False,reason=type(e).__name__)
 finally:
  p=run(['qm','shutdown',str(vmid),'--timeout','60'],80);row['normal_shutdown_exit']=p.returncode;row['final_stopped']='stopped' in run(['qm','status',str(vmid)]).stdout
 out.append(row)
 # Partial progress remains private PVE, result contains public identities only.
 f=Path('/root/dell-bootstrap/network19/dormant-OS-verification.json');f.write_text(json.dumps(out,indent=2));f.chmod(0o600)
print(json.dumps({'at':datetime.datetime.now().isoformat(),'scope':'7 originally stopped QA clones actual boot/readback/normal-stop','rows':out,'all_passed':all(x.get('passed') and x.get('final_stopped') for x in out)}))'''
x=json.loads(control.pve('python3 -',data=script.encode(),timeout=1100));(R/'network19/evidence/dormant-QA-real-OS.json').write_text(json.dumps(x,indent=2)+'\n');print(json.dumps({'all_passed':x['all_passed'],'rows':[{'vmid':x['vmid'],'passed':x.get('passed'),'stopped':x['final_stopped']} for x in x['rows']]}))
