#!/usr/bin/env python3
"""Manager invocation with existing strict guest identity; output safe metadata only."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts'));import control
info=json.loads((ROOT/'completion/20261109-resources/guest-access.json').read_text())['target']
result=control.guest(280,'sudo -n python3 -',data=Path(__file__).with_name('retire-filebrowser.py').read_bytes(),timeout=150,info=info)
try:value=json.loads(result['stdout'])
except ValueError:raise SystemExit('retirement-output-unconfirmed-no-raw-log-output')
Path(__file__).with_name('retirement-result.json').write_text(json.dumps(value,indent=2)+'\n')
print(json.dumps(value))
raise SystemExit(result['exit_code'])
