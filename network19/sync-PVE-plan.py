from pathlib import Path
import sys,json,shlex
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'scripts'));import control
P=r'''from pathlib import Path
import sys,json,os,hashlib,ast
v=json.load(sys.stdin);root=Path('/root/dell-bootstrap');assert Path('/root/dell-bootstrap/network19/management-only-active').exists();p=root/'plan.json'
backup=root/'network19/old-host-retirement/plan-before-final-active.json';assert not backup.exists();backup.write_bytes(p.read_bytes());backup.chmod(0o600)
new=v['plan'].encode();x=json.loads(new);assert x['network']['PVE_NAT'] is False and x['java_delivery']['business_programs_allowed'] is False and x['java_delivery']['acceptance_template_vmid']==9011
q=p.with_name('plan.network19-final-new');q.write_bytes(new);q.chmod(0o600);os.replace(q,p)
legacy=[]
for name in ['provision_network.py','provision-network.py']:
 old=root/name
 if old.is_file():
  body=old.read_text();guard="\nfrom pathlib import Path as _DellNetwork19Path\nif _DellNetwork19Path('/root/dell-bootstrap/network19/management-only-active').exists():\n raise SystemExit('Legacy host NAT retired; use network19 gateway workflow')\n"
  if 'Legacy host NAT retired' not in body:
   candidate=guard+body;ast.parse(candidate);b=root/'network19/old-host-retirement'/('retired-source-'+name);b.write_text(body);b.chmod(0o600);old.write_text(candidate)
  legacy.append(name)
print(json.dumps({'status':'PVE-active-plan-synced-and-old-network-bootstrap-gated','plan_SHA':hashlib.sha256(new).hexdigest(),'legacy_sources_gated':legacy,'secret_or_service_configuration_changed':False}))'''
x=json.loads(control.pve('python3 -c '+shlex.quote(P),data=json.dumps({'plan':(R/'plan.json').read_text()}).encode()));(R/'network19/evidence/PVE-active-plan-synced.json').write_text(json.dumps(x,indent=2)+'\n');print(json.dumps(x))
