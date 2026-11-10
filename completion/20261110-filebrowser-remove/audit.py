#!/usr/bin/env python3
"""Read-only installed FileBrowser paths and NFS preservation facts; no secret reads."""
import datetime,json,os,pwd,subprocess
from pathlib import Path
from zoneinfo import ZoneInfo
assert os.geteuid()==0 and __import__('socket').gethostname()=='resource-service'
paths=['/opt/dell/filebrowser','/etc/dell-filebrowser','/var/lib/dell-filebrowser','/var/lib/dell-filebrowser-manager']
def info(path):
 p=Path(path)
 if not p.exists()and not p.is_symlink():return {'exists':False}
 st=p.lstat();r={'exists':True,'symlink':p.is_symlink(),'uid':st.st_uid,'gid':st.st_gid,'mode':oct(st.st_mode&0o7777),'same_filesystem_as_root':st.st_dev==os.stat('/').st_dev}
 if p.is_symlink():r['target']=os.readlink(p)
 return r
def run(args):return subprocess.check_output(args,stderr=subprocess.PIPE,timeout=30).decode().strip()
owned=0
for base,dirs,files in os.walk('/srv/resources',followlinks=False):
 for name in dirs+files:
  if (Path(base)/name).lstat().st_uid==2000:owned+=1
try:
 user=pwd.getpwnam('filebrowser');account={'uid':user.pw_uid,'gid':user.pw_gid,'home':user.pw_dir,'shell':user.pw_shell}
except KeyError:account=None
out={'at':datetime.datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),'paths':{p:info(p)for p in paths},'units':{n:info('/etc/systemd/system/'+n)for n in ['dell-filebrowser.service','dell-filebrowser-firewall.service']},'FileBrowser_named_opt_paths':run(['find','/opt/dell','-maxdepth','3','-iname','*filebrowser*','-printf','%p\n']).splitlines(),'service_account':account,'resource_entries_owned_by_UID2000':owned,'NFS_guard':json.loads(run(['python3','-I','-B','/opt/dell/resources/guard.py','--role','server'])),'secret_or_resource_file_contents_read':False}
print(json.dumps(out))
