#!/usr/bin/env python3
"""Read-only final evidence, no credentials content or private key read."""
import importlib.util,json,sys
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('ctl',ROOT/'scripts/control.py');ctl=importlib.util.module_from_spec(s);s.loader.exec_module(ctl)
s=importlib.util.spec_from_file_location('limited',HERE/'manager-install-limited.py');limited=importlib.util.module_from_spec(s);s.loader.exec_module(limited)
AUDIT=r'''import hashlib,json,os,subprocess,pwd,urllib.request
from pathlib import Path
current=Path('/opt/finger/current-test');release=current.resolve();m=json.loads((release/'manifest.json').read_text());policy=json.loads(Path('/etc/dell-publisher/test240-policy.json').read_text());out={'release':release.name,'policy_baseline_migrated':policy.get('baseline_migrated'),'root_fixed_code_matches_policy':hashlib.sha256(Path('/usr/local/libexec/dell/deploy-test-chain.py').read_bytes()).hexdigest()==policy.get('fixed_deployer_sha256'),'core_hashes':{},'services':[]}
for row in m['services']:
 name=row['name'];folder=release/name;cfg=folder/'application.yaml';unit=folder/'unit.service';st=cfg.stat();unit_text=unit.read_text();entry={'name':name,'persistent_yaml_root600':st.st_uid==0 and st.st_gid==0 and st.st_mode&0o777==0o600,'fixed_LoadCredential':('LoadCredential=application.yaml:/opt/finger/current-test/'+name+'/application.yaml') in unit_text,'credential_argv':'--spring.config.location=file:%d/application.yaml' in unit_text}
 state=subprocess.run(['systemctl','show','dell-finger-'+name+'.service','-p','User','-p','Group','-p','ActiveState','-p','SubState'],capture_output=True,text=True,check=True);entry['systemd']=dict(x.split('=',1) for x in state.stdout.splitlines() if '=' in x);out['services'].append(entry)
 for file in ['app.jar','application.yaml']:out['core_hashes'][name+'/'+file]=hashlib.sha256((folder/file).read_bytes()).hexdigest()
out['core_hashes']['manifest.json']=hashlib.sha256((release/'manifest.json').read_bytes()).hexdigest()
auth=Path('/etc/ssh/authorized_keys/deployer')
if not auth.exists():auth=Path('/var/lib/dell-deployer/.ssh/authorized_keys')
# The actual key file is found from trusted installed Match configuration, never output.
sshd=subprocess.run(['sshd','-T','-C','user=deployer,host=java-test-01,addr=10.63.30.10'],capture_output=True,text=True,check=True)
fields=dict(x.split(' ',1) for x in sshd.stdout.splitlines() if ' ' in x);out['sshd_effective']={k:fields.get(k) for k in ['disableforwarding','allowtcpforwarding','allowagentforwarding','permittty','permituserrc','passwordauthentication','kbdinteractiveauthentication','authenticationmethods','authorizedkeysfile']}
keyfile=Path(fields['authorizedkeysfile'].replace('%u','deployer'));text=keyfile.read_text();st=keyfile.stat();out['authorized_key_controls']={'root_owned':st.st_uid==0,'from220':'from="10.63.30.10"' in text,'restrict':'restrict' in text,'forced_dispatch':'command="/usr/local/libexec/dell-publisher-dispatch"' in text,'raw_key_emitted':False}
out['native_sudo_negatives']=[]
for label,command in [('arbitrary-root-command',['/usr/bin/id']),('root-helper-extra-argv',['/usr/local/libexec/dell-publish-test240','--shell'])]:
 r=subprocess.run(['runuser','--user','deployer','--','sudo','-n','--',*command],capture_output=True,timeout=10);out['native_sudo_negatives'].append({'name':label,'exit_code':r.returncode,'denied':r.returncode!=0,'raw_output_withheld':True})
out['deployer_groups']=[x for x in subprocess.run(['id','-Gn','deployer'],capture_output=True,text=True,check=True).stdout.split()];out['sudoers_native_valid']=subprocess.run(['visudo','-cf','/etc/sudoers.d/dell-publisher-test240'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0;out['sshd_native_valid']=subprocess.run(['sshd','-t'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0
print(json.dumps(out))'''
KEY_AUDIT=r'''import json,subprocess,pwd
from pathlib import Path
key=Path('/var/lib/dell-publisher/.ssh/test240_ed25519');st=key.stat();who=pwd.getpwnam('publisher');r=subprocess.run(['ssh-keygen','-lf',str(key)+'.pub'],capture_output=True,text=True,check=True)
print(json.dumps({'private_key_owner_mode':st.st_uid==who.pw_uid and st.st_mode&0o777==0o600,'fingerprint':r.stdout.split()[1],'private_key_read_or_exported':False,'publisher_groups':subprocess.run(['id','-Gn','publisher'],capture_output=True,text=True,check=True).stdout.split()}))'''
def main():
 targets={r['target']['vmid']:r['target'] for r in json.loads((ROOT/'evidence/implementation/private-guest-access.json').read_text())['roles']};import datetime;v={'at':datetime.datetime.now().astimezone().isoformat(),'mode':'read-only-final-audit','scope':'VM220 and VM240 only','source_key_contents_read':False}
 for vmid,code in [(240,AUDIT),(220,KEY_AUDIT)]:
  r=ctl.guest(vmid,'sudo -n python3 -',data=code.encode(),timeout=120,info=targets[vmid]);assert r['exit_code']==0,'audit failed; output withheld';v['vm'+str(vmid)]=json.loads(r['stdout'])
 v['ub_strict_reconnect']=limited.guest_strict(targets[240],'id -un; hostname');original=ROOT/'private/java/releases/20261106T121030';actual=v['vm240']['core_hashes'];import hashlib
 v['A_all_core_bytes_match_original']=all(hashlib.sha256((original/name).read_bytes()).hexdigest()==sha for name,sha in actual.items());v['A_manifest_expected_sha']=actual['manifest.json']=='208bc8ecd57465726af7a0d5671fb38ebdc9c000e8f4dcab27eb7196b7e83c0e';v['ub_maintained']=v['ub_strict_reconnect']['exit_code']==0 and v['ub_strict_reconnect']['stdout'].splitlines()[:2]==['ub','java-test-01']
 target=v['vm240'];key=v['vm220'];effective=target['sshd_effective'];controls=target['authorized_key_controls']
 v['all_security_checks_pass']=all([target['release']=='20261106T121030',target['policy_baseline_migrated'],target['root_fixed_code_matches_policy'],target['deployer_groups']==['deployer'],target['sudoers_native_valid'],all(x['denied'] for x in target['native_sudo_negatives']),target['sshd_native_valid'],key['private_key_owner_mode'],key['publisher_groups']==['publisher'],v['A_all_core_bytes_match_original'],v['A_manifest_expected_sha'],v['ub_maintained'],all(controls[k] for k in ['root_owned','from220','restrict','forced_dispatch']),all(effective.get(k)==expected for k,expected in {'disableforwarding':'yes','allowtcpforwarding':'no','allowagentforwarding':'no','permittty':'no','permituserrc':'no','passwordauthentication':'no','kbdinteractiveauthentication':'no','authenticationmethods':'publickey'}.items()),len(target['services'])==5 and all(x['persistent_yaml_root600'] and x['fixed_LoadCredential'] and x['credential_argv'] and x['systemd'].get('User')=='finger' and x['systemd'].get('Group')=='finger' and x['systemd'].get('ActiveState')=='active' for x in target['services'])])
 (ROOT/'evidence/implementation/publisher-final-security-audit.json').write_text(json.dumps(v,indent=2)+'\n');print(json.dumps({'all_security_checks_pass':v['all_security_checks_pass'],'A_bytes_match':v['A_all_core_bytes_match_original'],'A_manifest_sha_match':v['A_manifest_expected_sha'],'ub_maintained':v['ub_maintained'],'private_key_exported':False}));return 0 if v['all_security_checks_pass'] else 1
if __name__=='__main__':raise SystemExit(main())
