#!/usr/bin/env python3
"""Arm an explicitly new Nexus for application-level artifact import; never claim H2 restore."""
import argparse,json,os,datetime
from pathlib import Path
from target_guard import verify_target,canonical
BASE=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--env-file',required=True,type=Path);p.add_argument('--confirm-new-export-import-instance',action='store_true');a=p.parse_args()
assert a.confirm_new_export_import_instance,'Explicit new-instance selection required'
c,d=verify_target();env=dict(x.split('=',1) for x in a.env_file.read_text().splitlines() if '=' in x and not x.startswith('#'))
data=canonical(env['NEXUS_DATA_DIR']);assert data==Path(c['storage']['data_path'])
assert not (BASE/'restore-complete.json').exists() and not (BASE/'fresh-instance.json').exists()
assert data.is_dir() and not any(data.iterdir()),'New initialization requires the assigned empty data directory'
assert data.stat().st_uid==200 and data.stat().st_gid==200
m={'schema_version':1,'mode':'new-instance-application-export-import','expected_guest_ip':c['expected_guest_ip'],'expected_hostname':c['expected_hostname'],'data_path':str(data),'filesystem_uuid':c['storage']['filesystem_uuid'],'empty_data_verified_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'old_h2_or_credentials_imported':False}
p=BASE/'fresh-instance.json';fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
with os.fdopen(fd,'w') as f:json.dump(m,f,indent=2);f.write('\n')
print(json.dumps({'status':'fresh-initialization-armed','migration_mode':m['mode'],'source_data_imported':False}))
