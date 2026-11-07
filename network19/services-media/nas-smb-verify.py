#!/usr/bin/env python3
"""NAS260 synthetic per-operation SMB denials and Jellyfin mount boundary checks."""
import hashlib,json,os,socket,subprocess,sys,uuid
from pathlib import Path
if os.geteuid()!=0 or socket.gethostname().split('.')[0]!='nas-media' or Path('/etc/pve').exists():raise SystemExit('NAS260 root only')
os.umask(0o077)
nonce=uuid.uuid4().hex
folder=Path('/root/private/dell-nas/acceptance')/('network19-permissions-'+nonce);folder.mkdir(mode=0o700)
# Reuse this NAS's existing root600 authentication files; credentials never leave the guest.
choices=[]
for candidate in Path('/root/private/dell-nas/acceptance').glob('permissions-*'):
 if candidate.is_dir() and candidate.stat().st_uid==0 and candidate.stat().st_mode&0o777==0o700 and all((candidate/(who+'.auth')).is_file() and (candidate/(who+'.auth')).resolve()==candidate/(who+'.auth') and (candidate/(who+'.auth')).stat().st_uid==0 and (candidate/(who+'.auth')).stat().st_mode&0o777==0o600 for who in ('writer','reader')):choices.append(candidate)
if not choices:raise SystemExit('Existing owned NAS authentication files unavailable; no fallback credentials')
auth=max(choices,key=lambda x:x.stat().st_mtime)
for who in ('writer','reader'):
 raw=(auth/(who+'.auth')).read_bytes()
 if b'username = nas'+who.encode() not in raw:raise SystemExit('Existing NAS authentication username differs')
 p=folder/(who+'.auth');p.write_bytes(raw);p.chmod(0o600)
source=folder/'original.bin';source.write_bytes(b'dell-nas-permission-original:'+nonce.encode()+bytes(range(256))*256)
modified=folder/'modified.bin';modified.write_bytes(b'dell-nas-reader-must-not-overwrite:'+nonce.encode())
expected=hashlib.sha256(source.read_bytes()).hexdigest();checks=[]
for share in ('media','games','incoming'):
 name='dell-permission-'+nonce+'.bin';attempt='dell-reader-denied-'+nonce+'.bin';renamed='dell-reader-rename-'+nonce+'.bin';lifecycle='dell-writer-lifecycle-'+nonce+'.bin';moved='dell-writer-renamed-'+nonce+'.bin'
 def smb(who,command):
  return subprocess.run(['smbclient','//192.168.19.60/'+share,'-A',str(folder/(who+'.auth')),'-m','SMB3','-c',command],capture_output=True,text=True,timeout=30)
 def matches():
  out=folder/(share+'-readback.bin');out.unlink(missing_ok=True);p=smb('reader','get '+name+' '+str(out));return p.returncode==0 and out.is_file() and hashlib.sha256(out.read_bytes()).hexdigest()==expected
 if smb('writer','put '+str(source)+' '+name).returncode:raise SystemExit('synthetic fixture creation failed; private output suppressed')
 result={'share':share,'fixture_name':name,'fixture_sha256':expected,'fixture_bytes':source.stat().st_size,'reader_read_hash_matches':matches(),'reader_denials':{}}
 for operation,command in [('create','put '+str(modified)+' '+attempt),('modify','put '+str(modified)+' '+name),('rename','rename '+name+' '+renamed),('delete','del '+name)]:
  p=smb('reader',command);denied='NT_STATUS_ACCESS_DENIED' in (p.stdout+p.stderr)
  result['reader_denials'][operation]={'access_denied':denied,'client_returncode':p.returncode,'original_still_matches':matches()}
 life_put=smb('writer','put '+str(source)+' '+lifecycle);life_rename=smb('writer','rename '+lifecycle+' '+moved)
 target_read=folder/(share+'-renamed.bin');read=smb('reader','get '+moved+' '+str(target_read))
 renamed_hash=read.returncode==0 and target_read.exists() and hashlib.sha256(target_read.read_bytes()).hexdigest()==expected
 life_delete=smb('writer','del '+moved);missing=smb('reader','get '+moved+' '+str(folder/(share+'-must-be-missing.bin')))
 result['writer_rename_success']=life_put.returncode==0 and life_rename.returncode==0 and renamed_hash
 result['writer_delete_success']=life_delete.returncode==0 and missing.returncode!=0 and 'NT_STATUS_OBJECT_NAME_NOT_FOUND' in (missing.stdout+missing.stderr)
 anonymous=subprocess.run(['smbclient','//192.168.19.60/'+share,'-U','%','-N','-m','SMB3','-c','ls'],capture_output=True,text=True,timeout=25)
 result['anonymous_denied']=anonymous.returncode!=0 and any(x in anonymous.stdout+anonymous.stderr for x in ['NT_STATUS_ACCESS_DENIED','NT_STATUS_LOGON_FAILURE','NT_STATUS_ACCOUNT_DISABLED'])
 original=Path('/srv/dev-disk-by-uuid-5b19837c-128c-498a-b79d-563db810c34a')/share/('dell-acceptance-'+share+'.bin')
 result['original_fixture_SHA_preserved']=original.is_file() and hashlib.sha256(original.read_bytes()).hexdigest()=='fbbab289f7f94b25736c58be46a994c441fd02552cc6022352e3d86d2fab7c83'
 result['retained_fixture_hash_matches']=matches();checks.append(result)
inspect=subprocess.run(['docker','--host','unix:///var/run/docker.sock','inspect','--format','[{"Mounts":{{json .Mounts}},"Config":{"User":{{json .Config.User}}}}]','dell-nas-jellyfin-1'],capture_output=True,text=True,timeout=30)
if inspect.returncode:raise SystemExit('Jellyfin inspect failed; private output suppressed')
c=json.loads(inspect.stdout)[0];mounts=c['Mounts'];base='/srv/dev-disk-by-uuid-5b19837c-128c-498a-b79d-563db810c34a'
expected_mounts={'/media':(base+'/media',False),'/config':(base+'/appdata/jellyfin/config',True),'/cache':(base+'/appdata/jellyfin/cache',True)}
actual={m['Destination']:(m['Source'],m['RW']) for m in mounts}
boundary={'mount_set_exact':actual==expected_mounts,'media_read_only':actual.get('/media')==(base+'/media',False),'no_games_incoming_mounts':all(not m['Source'].startswith(base+'/'+p) for m in mounts for p in ('games','incoming')),'runtime_user':c['Config']['User']}
probe=subprocess.run(['docker','exec','dell-nas-jellyfin-1','/bin/sh','-c','test -r /media && test ! -w /media && test ! -e /games && test ! -e /incoming && test ! -e /media/games && test ! -e /media/incoming'],capture_output=True,timeout=30)
boundary['container_media_readable_unwritable_games_incoming_absent']=probe.returncode==0
passed=all(x['anonymous_denied'] and x['original_fixture_SHA_preserved'] and x['reader_read_hash_matches'] and x['writer_rename_success'] and x['writer_delete_success'] and x['retained_fixture_hash_matches'] and all(v['access_denied'] and v['original_still_matches'] for v in x['reader_denials'].values()) for x in checks) and all(v for k,v in boundary.items() if k!='runtime_user')
result={'status':'passed' if passed else 'failed','nonce':nonce,'checks':checks,'jellyfin_boundary':boundary,'only_new_nonce_objects_touched':True,'fixtures_retained':True,'secrets_or_content_emitted':False,'original_authentication_reused_guest_local_only':True,'target':'192.168.19.60','source_or_real_media_modified':False}
(folder/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result));sys.exit(0 if passed else 1)
