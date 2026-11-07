#!/usr/bin/env python3
"""NAS-only synthetic SMB round trip; secrets enter stdin and credential files are 600."""
import hashlib,json,os,socket,subprocess,sys
from pathlib import Path
assert os.geteuid()==0 and socket.gethostname()=='nas-media'
values=json.loads(sys.stdin.read());folder=Path('/root/private/dell-nas/acceptance');folder.mkdir(parents=True,exist_ok=True,mode=0o700)
for who in ['writer','reader']:
 p=folder/(who+'.auth');content='username = nas'+who+'\npassword = '+values[who]+'\ndomain = WORKGROUP\n'
 p.write_text(content);p.chmod(0o600)
source=folder/'synthetic-game-file.bin';source.write_bytes(bytes(range(256))*4096);source.chmod(0o600);expected=hashlib.sha256(source.read_bytes()).hexdigest()
checks=[]
for share in ['media','games','incoming']:
 name='dell-acceptance-'+share+'.bin';output=folder/(share+'-roundtrip.bin')
 def smb(auth,command):
  return subprocess.run(['smbclient','//127.0.0.1/'+share,'-A',str(folder/(auth+'.auth')),'-m','SMB3','-c',command],capture_output=True,text=True,timeout=20)
 put=smb('writer','put '+str(source)+' '+name)
 get=smb('reader','get '+name+' '+str(output))
 same=output.exists() and hashlib.sha256(output.read_bytes()).hexdigest()==expected
 denied=smb('reader','put '+str(source)+' reader-write-must-fail.bin')
 anonymous=subprocess.run(['smbclient','//127.0.0.1/'+share,'-N','-U','','-m','SMB3','-c','ls'],capture_output=True,text=True,timeout=20)
 row={'share':share,'writer_put_exit':put.returncode,'reader_get_exit':get.returncode,'sha256_matches':same,'reader_write_denied':denied.returncode!=0,'anonymous_denied':anonymous.returncode!=0,'fixture_sha256':expected,'fixture_bytes':source.stat().st_size,'fixture_name':name,'protocol_requested':'SMB3'}
 checks.append(row)
passed=all(c['writer_put_exit']==0 and c['reader_get_exit']==0 and c['sha256_matches'] and c['reader_write_denied'] and c['anonymous_denied'] for c in checks)
result={'status':'passed' if passed else 'failed','checks':checks,'source_movies_or_games_used':False,'private_values_emitted':False}
p=folder/'smb-result.json';p.write_text(json.dumps(result,indent=2)+'\n');p.chmod(0o600)
print(json.dumps(result));sys.exit(0 if passed else 1)
