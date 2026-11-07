"""NAS260-only SSH helper; existing manager trust info, no known_hosts mutation."""
from pathlib import Path
import datetime as dt,json,os,sys
from zoneinfo import ZoneInfo
sys.dont_write_bytecode=True
BASE=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(BASE/'scripts'))
import control

def info():
 rows=json.loads((BASE/'evidence/implementation/private-guest-access.json').read_text())['roles']
 value=next(r['target'] for r in rows if r['name']=='nas-media')
 assert value['vmid']==260 and value['ip']=='10.63.40.10'
 return value

def guest(command,data=None,timeout=120,phase=None):
 result=control.guest(260,command,data=data,timeout=timeout,info=info())
 if phase:
  assert phase.replace('-','').isalnum()
  folder=BASE/'private/nas/logs';folder.mkdir(parents=True,exist_ok=True,mode=0o700)
  record={'collected_at':dt.datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),'target':result['target'],'exit_code':result['exit_code'],'stdout':result['stdout'],'stderr':result['stderr']}
  path=folder/(phase+'.json');path.write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n');path.chmod(0o600)
 return result
