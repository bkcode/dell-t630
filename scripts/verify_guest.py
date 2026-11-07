#!/usr/bin/env python3
"""Collect an allowlisted, read-only guest snapshot over verified ub SSH."""
import argparse
import datetime as dt
import ipaddress
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys


def utc_now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def safe_host(value):
    try:
        ipaddress.ip_address(value)
    except ValueError:
        if not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9.-]{0,251}[A-Za-z0-9])?", value):
            raise argparse.ArgumentTypeError("host must be an IP or plain DNS name")
    return value


def unit_name(value):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.@:-]{0,160}(?:\.service)?", value):
        raise argparse.ArgumentTypeError("invalid systemd unit name")
    return value if value.endswith(".service") else value + ".service"


def base_parser(description):
    p = argparse.ArgumentParser(description=description)
    p.add_argument("--host", required=True, type=safe_host)
    p.add_argument("--role", required=True)
    p.add_argument("--expected-hostname", required=True)
    p.add_argument("--port", type=int, default=22)
    p.add_argument("--identity", default="~/.ssh/yang_local_rsa")
    p.add_argument("--known-hosts", help="Existing trusted known_hosts; no automatic trust")
    p.add_argument("--jump-host", type=safe_host, help="Verified PVE SSH jump host, root account")
    p.add_argument("--jump-port", type=int, default=22)
    p.add_argument("--output", type=Path)
    p.add_argument("--timeout", type=int, default=120)
    return p


def ssh_command(args):
    if not 1 <= args.port <= 65535 or not 10 <= args.timeout <= 300:
        raise ValueError("invalid SSH port or timeout")
    identity = Path(args.identity).expanduser()
    if not identity.is_file():
        raise ValueError("identity file is unavailable")
    if identity.stat().st_mode & 0o077:
        raise ValueError("identity file must not be group/world accessible")
    cmd = ["ssh", "-T", "-i", str(identity), "-p", str(args.port),
           "-o", "IdentitiesOnly=yes", "-o", "BatchMode=yes",
           "-o", "PreferredAuthentications=publickey", "-o", "PasswordAuthentication=no",
           "-o", "KbdInteractiveAuthentication=no", "-o", "NumberOfPasswordPrompts=0",
           "-o", "StrictHostKeyChecking=yes", "-o", "ForwardAgent=no",
           "-o", "ClearAllForwardings=yes", "-o", "PermitLocalCommand=no",
           "-o", "ConnectTimeout=10", "-o", "ServerAliveInterval=15",
           "-o", "ServerAliveCountMax=2"]
    if args.known_hosts:
        known = Path(args.known_hosts).expanduser()
        if not known.is_file():
            raise ValueError("trusted known_hosts file is unavailable")
        cmd += ["-o", "UserKnownHostsFile=" + str(known)]
    if args.jump_host:
        if not 1 <= args.jump_port <= 65535:
            raise ValueError("invalid jump port")
        jump = cmd.copy()
        jump[jump.index("-p") + 1] = str(args.jump_port)
        jump += ["-W", "%h:%p", "root@" + args.jump_host]
        cmd += ["-o", "ProxyCommand=" + shlex.join(jump)]
    return cmd + ["ub@" + args.host, "python3", "-"]


def remote_json(args, source, config):
    payload = "import json\nCONFIG = json.loads(" + repr(json.dumps(config)) + ")\n" + source
    started = utc_now()
    try:
        result = subprocess.run(ssh_command(args), input=payload, text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                timeout=args.timeout, check=False)
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        return {"status": "failed", "started_at": started,
                "finished_at": utc_now(), "error_category": type(exc).__name__,
                "limitations": ["No raw SSH output is emitted."]}, 2
    if result.returncode:
        low = result.stderr.lower()
        category = "ssh_or_remote_failure"
        for pattern, label in [("host key verification", "host_key_not_trusted"),
                               ("host identification has changed", "host_key_changed"),
                               ("permission denied", "public_key_or_privilege_denied"),
                               ("timed out", "connection_timeout"),
                               ("connection refused", "connection_refused")]:
            if pattern in low:
                category = label
                break
        return {"status": "failed", "started_at": started,
                "finished_at": utc_now(), "exit_code": result.returncode,
                "error_category": category,
                "limitations": ["Raw SSH/remote output withheld; verify target via trusted console."]}, 2
    try:
        data = json.loads(result.stdout)
    except (json.JSONDecodeError, ValueError):
        return {"status": "failed", "started_at": started, "finished_at": utc_now(),
                "error_category": "non_json_remote_result",
                "limitations": ["No raw remote output is emitted."]}, 2
    data.update(started_at=started, finished_at=utc_now())
    return data, 0 if data.get("status") == "passed" else 1


def emit(args, data):
    envelope = {"schema_version": 1, "collected_at": utc_now(), "timezone": "UTC",
                "target": {"host": args.host, "port": args.port, "user": "ub", "role": args.role,
                           "expected_hostname": args.expected_hostname},
                "execution_type": "read-only", "result": data}
    encoded = json.dumps(envelope, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        # Evidence is metadata only, but retain private file permissions.
        descriptor = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w") as out:
            out.write(encoded)
    sys.stdout.write(encoded)


GUEST_SOURCE = r'''
import hashlib, os, pathlib, platform, pwd, re, shutil, subprocess

def run(argv, timeout=15):
    try:
        p = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           text=True, timeout=timeout, check=False)
        return p.returncode, p.stdout[:1048576]
    except (OSError, subprocess.TimeoutExpired):
        return 127, ""

def read(path):
    try: return pathlib.Path(path).read_text()
    except (OSError, UnicodeError): return ""

def digest(value):
    return hashlib.sha256(value.encode()).hexdigest() if value else None

def service(unit):
    rc, output = run(["systemctl", "show", unit, "--no-pager",
                      "-p", "LoadState", "-p", "ActiveState", "-p", "SubState", "-p", "UnitFileState"])
    return {"exit_code": rc, "properties": dict(l.split("=",1) for l in output.splitlines() if "=" in l)}

os_release = {}
for line in read("/etc/os-release").splitlines():
    if "=" in line:
        k, v = line.split("=", 1)
        if k in {"ID", "VERSION_ID", "VERSION_CODENAME", "PRETTY_NAME"}: os_release[k] = v.strip('"')
username = pwd.getpwuid(os.getuid()).pw_name
hostname = platform.node()
rc, groups = run(["id", "-Gn"])
keys = read("/home/ub/.ssh/authorized_keys")
key_count = sum(1 for line in keys.splitlines() if line.strip() and not line.lstrip().startswith("#"))
cloud = {"installed": bool(shutil.which("cloud-init"))}
if cloud["installed"]:
    rc, value = run(["cloud-init", "status", "--format", "json"])
    try:
        parsed = json.loads(value)
        cloud.update(exit_code=rc, status=parsed.get("status"), extended_status=parsed.get("extended_status"))
    except ValueError:
        cloud.update(exit_code=rc, status="unparsed")
rc, state = run(["systemctl", "is-system-running"])
rc_t, ntp = run(["timedatectl", "show", "-p", "NTPSynchronized", "-p", "Timezone"])
rc_s, sudo_output = run(["sudo", "-n", "true"])
rc_b, block = run(["lsblk", "--json", "--bytes", "-o", "NAME,TYPE,SIZE,FSTYPE,MOUNTPOINTS,ROTA"])
try: block_data = json.loads(block) if rc_b == 0 else None
except ValueError: block_data = None
memory = {}
for line in read("/proc/meminfo").splitlines():
    if line.split(":",1)[0] in {"MemTotal", "MemAvailable", "SwapTotal", "SwapFree"}:
        key, value = line.split(":",1); memory[key + "_kib"] = int(value.split()[0])
filesystems = []
for point in ["/", "/var/lib/docker", "/srv"]:
    if pathlib.Path(point).exists():
        info = os.statvfs(point)
        filesystems.append({"path": point, "total_bytes": info.f_blocks*info.f_frsize,
                            "available_bytes": info.f_bavail*info.f_frsize})
units = sorted(set(["ssh.service", "cloud-init.service", "qemu-guest-agent.service", "docker.service",
                    "systemd-resolved.service", "openmediavault-engined.service", "nginx.service", "smbd.service"] + CONFIG["units"]))
services = {unit: service(unit) for unit in units}
checks = {"login_is_ub": username == "ub", "hostname_matches": hostname == CONFIG["expected_hostname"]}
for unit in CONFIG["units"]:
    checks["active:" + unit] = services[unit]["properties"].get("ActiveState") == "active"
if CONFIG.get("expected_os"):
    checks["os_matches"] = os_release.get("ID") == CONFIG["expected_os"]
if CONFIG.get("expected_version"):
    checks["os_version_matches"] = os_release.get("VERSION_ID") == CONFIG["expected_version"]
print(json.dumps({"status": "passed" if all(checks.values()) else "failed", "checks": checks,
 "observation": {"hostname": hostname, "user": username, "uid": os.getuid(), "groups": groups.split(),
  "sudo_noninteractive_available": rc_s == 0, "os": os_release, "architecture": platform.machine(),
  "kernel": platform.release(), "logical_cpus": os.cpu_count(), "memory": memory,
  "machine_id_sha256": digest(read("/etc/machine-id").strip()),
  "ub_authorized_keys_present": key_count > 0, "ub_authorized_key_count": key_count,
  "cloud_init": cloud, "systemd_state": state.strip(),
  "time": dict(l.split("=",1) for l in ntp.splitlines() if "=" in l),
  "services": services, "block_devices": block_data, "filesystem_capacity": filesystems},
 "limitations": ["Read-only snapshot; no reboot, recreation, recovery, load or application write test.",
  "sudo availability is distinct from permission to publish a specific application.",
  "No Env, private/public key contents, service ExecStart, logs or credentials are emitted."]}))
'''


def main():
    p = base_parser(__doc__)
    p.add_argument("--require-unit", action="append", default=[], type=unit_name)
    p.add_argument("--expected-os")
    p.add_argument("--expected-version")
    args = p.parse_args()
    data, code = remote_json(args, GUEST_SOURCE,
                            {"expected_hostname": args.expected_hostname, "units": args.require_unit,
                             "expected_os": args.expected_os, "expected_version": args.expected_version})
    emit(args, data)
    return code


if __name__ == "__main__":
    sys.exit(main())
