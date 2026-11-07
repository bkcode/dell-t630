#!/usr/bin/env python3
"""Compare PVE-only user-data bytes without returning any profile or public key."""
import json,sys,datetime,shlex
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts'));import control
receipt=json.loads((ROOT/'network19/evidence/cloud-init-hostkey-preservation.json').read_text())
CODE=r'''
import pathlib,json,subprocess,re,stat,datetime,sys,socket
assert pathlib.Path('/etc/pve').exists();rows=json.load(sys.stdin);out=[]
for row in rows:
 v=row['vmid'];old=pathlib.Path('/root/dell-bootstrap/network19/cloud-identity')/(str(v)+'-before.yaml');oldbytes=old.read_bytes();ref=row['reference'];assert ref.startswith('store:snippets/')
 r=subprocess.run(['pvesm','path',ref],capture_output=True,text=True,timeout=15);assert r.returncode==0;p=pathlib.Path(r.stdout.strip());new=p.read_bytes()
 pattern=rb'(?m)^([ \t]*ssh_deletekeys:[ \t]*)true([ \t]*)(\r?$)';replacement,count=re.subn(pattern,rb'\1false\2\3',oldbytes,count=1);oldcount=len(re.findall(rb'(?m)^[ \t]*ssh_deletekeys:',oldbytes));newcount=len(re.findall(rb'(?m)^[ \t]*ssh_deletekeys:',new))
 config=pathlib.Path('/etc/pve/qemu-server')/(str(v)+'.conf');ciref=next((l.partition(':')[2].strip() for l in config.read_text().splitlines() if l.startswith('cicustom:')),None);userrefs=[x.split('=',1)[1] for x in (ciref or '').split(',') if x.startswith('user=')]
 st=p.stat();b=old.stat();out.append({'vmid':v,'reference':ref,'single_line_only_change':count==1 and oldcount==newcount==1 and replacement==new,'ssh_deletekeys_now_false':bool(re.search(rb'(?m)^ssh_deletekeys:[ \t]*false[ \t]*$',new)),'host_private_keys_embedded':bool(re.search(rb'(?m)^ssh_keys:',new)),'cicustom_reference_matches':userrefs==[ref],'backup_root600':b.st_uid==0 and stat.S_IMODE(b.st_mode)==0o600,'snippet_root600':st.st_uid==0 and stat.S_IMODE(st.st_mode)==0o600,'full_userdata_or_key_contents_emitted':False})
templates=[]
for v in [9001,9010]:
 r=subprocess.run(['qm','cloudinit','dump',str(v),'user'],capture_output=True,timeout=20);b=r.stdout;templates.append({'vmid':v,'dump_exit_code':r.returncode,'ssh_deletekeys_default_true':bool(re.search(rb'(?m)^ssh_deletekeys:[ \t]*true[ \t]*$',b)),'profile_contents_emitted':False})
guest="import pathlib,socket,json,subprocess; ips=json.loads(subprocess.run(['ip','-j','addr'],capture_output=True,text=True).stdout); print(json.dumps({'hostname':socket.gethostname(),'machine_id':pathlib.Path('/etc/machine-id').read_text().strip(),'interfaces':[{'ifname':x['ifname'],'MAC':x.get('address'),'IPv4':[(a['local'],a['prefixlen']) for a in x.get('addr_info',[]) if a['family']=='inet']} for x in ips if x['ifname']!='lo'],'ed25519_public_fingerprint':subprocess.run(['ssh-keygen','-lf','/etc/ssh/ssh_host_ed25519_key.pub'],capture_output=True,text=True).stdout.split()[1]}))"
r=subprocess.run(['qm','guest','exec','230','--timeout','30','--','/usr/bin/python3','-c',guest],capture_output=True,text=True,timeout=40);g={'qga_exit_code':r.returncode}
if r.returncode==0:
 q=json.loads(r.stdout);g['guest_exit_code']=q.get('exitcode')
 if q.get('exitcode')==0:g['identity']=json.loads(q['out-data'])
print(json.dumps({'captured_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'profile_rows':out,'templates':templates,'guest230':g,'host_guest_or_trust_file_mutations':False}))
'''
r=control.pve('python3 -c '+shlex.quote(CODE),data=json.dumps(receipt['rows']).encode(),timeout=240);j=json.loads(r);base=json.loads((ROOT/'evidence/implementation/rolling-guest-reboot-acceptance.json').read_text());old=next(x for x in base['preflight'] if x['vmid']==230);j['original230_evidence']={'path':'evidence/implementation/rolling-guest-reboot-acceptance.json','machine_id_lines':[207,726,784],'machine_id':old['machine_id'],'hostname':old['hostname'],'original_fingerprint':old['host_key_fingerprint']}
i=j['guest230'].get('identity');j['guest230']['original_machine_id_matches']=bool(i and i['machine_id']==old['machine_id']);j['guest230']['expected_hostname_MAC_IP_matches']=bool(i and i['hostname']=='java-prod-01' and any((x.get('MAC') or '').lower()=='bc:24:11:1c:20:00' and ['192.168.19.40',24] in x['IPv4'] for x in i['interfaces']));j['status']='passed' if all(x['single_line_only_change'] and x['ssh_deletekeys_now_false'] and not x['host_private_keys_embedded'] and x['cicustom_reference_matches'] and x['backup_root600'] and x['snippet_root600'] for x in j['profile_rows']) and all(x['ssh_deletekeys_default_true'] for x in j['templates']) and j['guest230']['original_machine_id_matches'] and j['guest230']['expected_hostname_MAC_IP_matches'] else 'needs-review';(ROOT/'network19/audit/hostkey-profile-independent-verification.json').write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'status':j['status'],'profiles':len(j['profile_rows']),'single_line_only':sum(x['single_line_only_change'] for x in j['profile_rows']),'template_true':[x['vmid'] for x in j['templates'] if x['ssh_deletekeys_default_true']],'230_original_machineID':j['guest230']['original_machine_id_matches'],'230_expected_identity':j['guest230']['expected_hostname_MAC_IP_matches']}))
