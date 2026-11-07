#!/opt/homebrew/opt/python@3.14/bin/python3.14 -I
"""Two fixed, clearly labelled test messages. No scheduler or production probe writes."""
import argparse
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import secrets
import stat
import time

spec = importlib.util.spec_from_file_location('probe', Path(__file__).with_name('probe.py'))
probe = importlib.util.module_from_spec(spec); spec.loader.exec_module(probe)


def body(phase, run):
    if phase not in ('firing', 'resolved') or not __import__('re').fullmatch('[a-f0-9]{16}', run):
        raise probe.Rejected('fixed acceptance fields rejected')
    text = ('【验收】【Dell T630 Mac外部探测】\ncheck=DellMacExternalProbeAcceptance\nphase=' + phase +
            '\nrun=' + run + '\n仅验证外部通知链，不代表PVE或业务发生真实故障。')
    return json.dumps({'msg_type':'text','content':{'text':text}},ensure_ascii=False,separators=(',',':')).encode()


def save(path, value):
    probe.atomic_json(path, value)


def execute(phase, send):
    if not send:
        raw=body(phase,'0000000000000000')
        return {'mode':'plan-only','phase':phase,'would_send_fixed_acceptance_only':True,'hook_read':False,
                'payload_sha256_placeholder':hashlib.sha256(raw).hexdigest()}
    probe.private_dir()
    fd=os.open(probe.PRIVATE/'run.lock',os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW,0o600)
    try:
        s=os.fstat(fd)
        if not stat.S_ISREG(s.st_mode) or s.st_uid!=os.getuid() or s.st_mode&0o777!=0o600 or s.st_nlink!=1:raise probe.Rejected('lock rejected')
        fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        path=probe.PRIVATE/'acceptance.json'
        record=json.loads(probe.read_private(path)) if path.exists() else {'run':secrets.token_hex(8),'phases':{}}
        if phase=='resolved' and not record['phases'].get('firing',{}).get('acknowledged'):
            raise probe.Rejected('firing acknowledgement required before resolved')
        item=record['phases'].setdefault(phase,{'attempts':0,'acknowledged':False,'last_attempt':0})
        if item['acknowledged']:
            return {'mode':'already-acknowledged','phase':phase,'run':record['run'],'duplicate_sent':False}
        if item['attempts']>=3 or time.time()-item['last_attempt']<60:raise probe.Rejected('acceptance attempt limit or spacing')
        raw=body(phase,record['run'])
        item.update(attempts=item['attempts']+1,last_attempt=time.time(),payload_sha256=hashlib.sha256(raw).hexdigest())
        save(path,record)
        ok=probe.send_lark(raw)
        item.update(acknowledged=ok,checked_at=probe.now())
        save(path,record)
        result={'mode':'actual-send','phase':phase,'run':record['run'],'upstream_code':0 if ok else None,
                'acknowledged':ok,'attempt':item['attempts'],'payload_sha256':item['payload_sha256']}
        probe.log({'event':'acceptance_delivery_acknowledged' if ok else 'acceptance_delivery_failed',
                   'phase':phase,'run':record['run'],'attempt':item['attempts']})
        return result
    finally:
        os.close(fd)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['firing','resolved']);parser.add_argument('--send',action='store_true')
    args=parser.parse_args()
    try:
        result=execute(args.phase,args.send);print(json.dumps(result))
        if result.get('mode')=='actual-send' and not result['acknowledged']:raise SystemExit(1)
    except Exception:
        print(json.dumps({'event':'acceptance_not_sent_or_unconfirmed','details_logged':False}));raise SystemExit(1)
