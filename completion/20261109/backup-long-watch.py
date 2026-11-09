import datetime as dt
import json
import sys
import time
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import control

OUT = ROOT / 'completion/20261109/backup-long-watch.json'
OUT.parent.mkdir(parents=True, exist_ok=True)
VMIDS = [100, 190, 200, 201, 210, 221, 230, 240, 250, 260, 270]
UNIT = "dell-local-backup-first-retry.service"


def now():
    utc = dt.datetime.now(dt.timezone.utc)
    sh = utc.astimezone(ZoneInfo("Asia/Shanghai"))
    return utc.isoformat(), sh.isoformat()


def poll():
    script = r'''import json, subprocess
unit = "dell-local-backup-first-retry.service"
props = {}
for line in subprocess.run(["systemctl", "show", unit, "-p", "ActiveState", "-p", "SubState", "-p", "Result", "-p", "ExecMainStatus"], capture_output=True, text=True).stdout.splitlines():
    if "=" in line:
        k,v=line.split("=",1); props[k]=v
with open("/var/lib/dell-local-backup/current.json") as f: ledger=json.load(f)
print(json.dumps({"unit":props,"ledger":ledger}))
'''
    raw = control.pve("python3 -", data=script.encode(), timeout=50)
    return json.loads(raw.decode())


def clean(snapshot):
    unit = snapshot["unit"]
    ledger = snapshot["ledger"]
    results = ledger.get("results", {})
    vms = {}
    for vmid in VMIDS:
        row = results.get(str(vmid), {})
        vms[str(vmid)] = {
            "status": row.get("status", "absent"),
            "bytes": row.get("bytes"),
            "proof": {
                "zstd_verified": row.get("zstd_verified") is True,
                "native_archive_verified": row.get("native_archive_verified") is True,
                "status_verified": row.get("status") == "verified",
            },
        }
    utc, sh = now()
    return {
        "observed_at_utc": utc,
        "observed_at_asia_shanghai": sh,
        "run_id": ledger.get("run_id"),
        "ledger_status": ledger.get("status"),
        "unit": {k: unit.get(k) for k in ("ActiveState", "SubState", "Result", "ExecMainStatus")},
        "vms": vms,
    }


def terminal(s):
    return (s["ledger_status"] in ("verified", "failed") or
            (s["unit"].get("ActiveState") == "inactive" and s["unit"].get("SubState") == "dead"))


doc = {"watch": {"unit": UNIT, "allowed_vmids": VMIDS, "read_only": True}, "snapshots": []}
last = None
deadline = time.monotonic() + 75 * 60
while time.monotonic() < deadline:
    try:
        s = clean(poll())
        doc["snapshots"].append(s)
        OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n")
        changed = s["vms"] != (last or {}).get("vms") or s["unit"] != (last or {}).get("unit")
        print(json.dumps({"at": s["observed_at_asia_shanghai"], "ledger_status": s["ledger_status"], "unit": s["unit"], "changed": changed, "vm_statuses": {k:v["status"] for k,v in s["vms"].items()}}, ensure_ascii=False), flush=True)
        last = s
        if terminal(s):
            break
    except Exception as e:
        utc, sh = now()
        doc["snapshots"].append({"observed_at_utc": utc, "observed_at_asia_shanghai": sh, "poll_error": type(e).__name__})
        OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n")
        print(json.dumps({"at": sh, "poll_error": type(e).__name__}), flush=True)
    time.sleep(50)
print(json.dumps({"finished": True, "snapshots": len(doc["snapshots"]), "artifact": str(OUT)}), flush=True)
