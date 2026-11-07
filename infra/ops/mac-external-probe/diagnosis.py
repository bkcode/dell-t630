#!/opt/homebrew/opt/python@3.14/bin/python3.14 -I
"""One-shot observation only. No sender/secret imports and no production state access."""
import concurrent.futures
import datetime
import json
import os
from pathlib import Path
import subprocess
import sys
import time

BASE=Path(__file__).resolve().parent
HOST='192.168.21.22'
CHECKS=(('pve-ssh','tcp',22,''),('pve-ui','tcp',8006,''),('penpot','http',9001,'/'),
        ('nexus','http',8081,'/service/rest/v1/status'),('nas-web','http',9080,'/'),
        ('jellyfin','http',8096,'/health'),('java-test-oidc','http',19999,'/.well-known/openid-configuration'))
ENV={'PATH':'/usr/bin:/bin','LANG':'C','LC_ALL':'C'}


def at():return datetime.datetime.now(datetime.timezone.utc).isoformat()


def one(item):
    name,kind,port,path=item
    if item not in CHECKS:raise RuntimeError('fixed scope only')
    if kind=='tcp':cmd=['/usr/bin/nc','-z','-G','3','-w','3',HOST,str(port)]
    else:cmd=['/usr/bin/curl','-q','--noproxy','*','--proto','=http','--max-redirs','0','--connect-timeout','3',
              '--max-time','5','--silent','--show-error','--output','/dev/null','--write-out','%{http_code}',
              'http://'+HOST+':'+str(port)+path]
    try:
        p=subprocess.run(cmd,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=7,env=ENV)
        status=int(p.stdout) if kind=='http' and p.stdout.isdigit() and len(p.stdout)==3 else None
        return {'name':name,'at':at(),'native_argv':cmd,'exit_code':p.returncode,'http_status':status,
                'ok':p.returncode==0 and (kind=='tcp' or status==200),'stderr':p.stderr.decode('utf8','replace')[:2048]}
    except (OSError,subprocess.TimeoutExpired) as exc:
        return {'name':name,'at':at(),'exit_code':None,'ok':False,'stderr_class':type(exc).__name__}


def measure():
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:return list(pool.map(one,CHECKS))


if __name__=='__main__':
    if sys.argv[1:]==['direct']:
        result={'at':at(),'mode':'direct-observation','pid':os.getpid(),'uid':os.getuid(),'results':measure()}
        (BASE/'background-diagnosis-direct.json').write_text(json.dumps(result,indent=2)+'\n')
    elif sys.argv[1:]==['background']:
        start=time.monotonic()
        result={'at':at(),'mode':'one-shot-launchd-observation','pid':os.getpid(),'ppid':os.getppid(),
                'uid':os.getuid(),'gid':os.getgid(),'executable':sys.executable,'cwd':os.getcwd(),
                'nice':os.getpriority(os.PRIO_PROCESS,0),'subprocess_env':ENV,'secret_access':False,
                'production_state_access':False,'notification_requests':0,'rounds':[]}
        for due in (0,60):
            while time.monotonic()-start<due:time.sleep(min(1,due-(time.monotonic()-start)))
            result['rounds'].append({'at':at(),'results':measure()})
            (BASE/'background-diagnosis.json').write_text(json.dumps(result,indent=2)+'\n')
        while time.monotonic()-start<120:time.sleep(min(1,120-(time.monotonic()-start)))
        result.update(finished_at=at(),runtime_seconds=round(time.monotonic()-start,2))
        (BASE/'background-diagnosis.json').write_text(json.dumps(result,indent=2)+'\n')
    else:raise SystemExit('Only fixed direct/background observation modes are accepted')
