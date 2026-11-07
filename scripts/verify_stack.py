#!/usr/bin/env python3
"""Collect read-only container/systemd/HTTP health without emitting configuration secrets."""
import argparse
import re
import sys
from urllib.parse import urlsplit
from verify_guest import base_parser, emit, remote_json, unit_name


def service_name(value):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,120}", value):
        raise argparse.ArgumentTypeError("invalid Compose service or project")
    return value


def endpoint(value):
    if "=" not in value:
        raise argparse.ArgumentTypeError("use NAME=URL")
    name, url = value.split("=", 1)
    service_name(name)
    p = urlsplit(url)
    if p.scheme not in {"http", "https"} or not p.hostname or p.username or p.password or p.query or p.fragment:
        raise argparse.ArgumentTypeError("HTTP endpoint needs http(s), no credentials/query/fragment")
    if p.path not in {"", "/", "/health", "/healthz", "/readyz", "/actuator/health", "/system/info/public"}:
        raise argparse.ArgumentTypeError("only public read-only root/health paths are supported")
    return {"name": name, "url": url, "hostname": p.hostname}


STACK_SOURCE = r'''
import platform, re, subprocess, time, urllib.error, urllib.request

def run(argv, timeout=25):
    try:
        p = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                           timeout=timeout, check=False)
        return p.returncode, p.stdout[:8388608]
    except (OSError, subprocess.TimeoutExpired): return 127, ""

def structured(argv):
    rc, raw = run(argv)
    try: return rc, json.loads(raw) if rc == 0 else None
    except ValueError: return 65, None

def pinned(image):
    return bool(re.search(r"@sha256:[0-9a-f]{64}$", image))

def safe_image(image):
    # Registry userinfo, query parameters and arguments must never appear in evidence.
    return image if re.fullmatch(r"[A-Za-z0-9._/:@+-]+", image) else "[withheld]"

checks = {"hostname_matches": platform.node() == CONFIG["expected_hostname"]}
docker = ["docker"]
probe = ["ps", "-aq"]
if CONFIG["project"]: probe += ["--filter", "label=com.docker.compose.project=" + CONFIG["project"]]
rc, ids = run(docker + probe)
if rc:
    docker = ["sudo", "-n", "docker"]
    rc, ids = run(docker + probe)
containers = []
image_arch = {}
if rc == 0:
    container_ids = [x for x in ids.splitlines() if re.fullmatch(r"[0-9a-f]{12,64}", x)]
    if container_ids:
        inspect_rc, records = structured(docker + ["inspect"] + container_ids)
        for item in records or []:
            config = item.get("Config", {})
            labels = config.get("Labels") or {}
            state = item.get("State") or {}
            service = labels.get("com.docker.compose.service") or item.get("Name", "").lstrip("/")
            image = config.get("Image", "")
            iid = item.get("Image", "")
            if iid not in image_arch:
                irc, im = structured(docker + ["image", "inspect", iid])
                image_arch[iid] = (im or [{}])[0].get("Architecture") if irc == 0 else None
            mounts = [{"type": m.get("Type"), "destination": m.get("Destination"), "read_write": m.get("RW")}
                      for m in item.get("Mounts", [])]
            health = (state.get("Health") or {}).get("Status")
            host = item.get("HostConfig") or {}
            ports = (item.get("NetworkSettings") or {}).get("Ports") or {}
            containers.append({"name": item.get("Name", "").lstrip("/"), "service": service,
                "image": safe_image(image), "image_id": iid, "architecture": image_arch[iid],
                "immutable_image_reference": pinned(image), "status": state.get("Status"),
                "running": bool(state.get("Running")), "health": health,
                "oom_killed": bool(state.get("OOMKilled")), "restart_count": item.get("RestartCount"),
                "memory_limit_bytes": host.get("Memory"), "nano_cpus": host.get("NanoCpus"),
                "restart_policy": (host.get("RestartPolicy") or {}).get("Name"),
                "log_driver": (host.get("LogConfig") or {}).get("Type"), "mounts": mounts,
                "published_ports": ports})
    else: inspect_rc = 0
else: inspect_rc = rc
for expected in CONFIG["services"]:
    found = [c for c in containers if c["service"] == expected]
    checks["service:" + expected] = bool(found) and all(c["running"] and not c["oom_killed"] and
        c["health"] not in {"unhealthy", "starting"} for c in found)
    if CONFIG["require_healthcheck"]:
        checks["healthcheck:" + expected] = bool(found) and all(c["health"] == "healthy" for c in found)
if CONFIG["require_pinned_images"]:
    checks["immutable_images"] = bool(containers) and all(c["immutable_image_reference"] for c in containers)
for expected in CONFIG["mounts"]:
    service, destination = expected.split(":", 1)
    found = [c for c in containers if c["service"] == service]
    checks["mount:" + expected] = bool(found) and all(any(m["destination"] == destination for m in c["mounts"]) for c in found)
units = {}
for unit in CONFIG["units"]:
    urc, output = run(["systemctl", "show", unit, "--no-pager", "-p", "LoadState", "-p", "ActiveState", "-p", "SubState"])
    properties = dict(line.split("=", 1) for line in output.splitlines() if "=" in line)
    units[unit] = {"exit_code": urc, "properties": properties}
    checks["unit:" + unit] = properties.get("ActiveState") == "active"
http = []
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl): return None
opener = urllib.request.build_opener(NoRedirect)
for target in CONFIG["http"]:
    begin = time.monotonic()
    result = {"name": target["name"], "url": target["url"]}
    try:
        with opener.open(urllib.request.Request(target["url"], method="GET"), timeout=10) as response:
            result.update(status_code=response.status)
    except urllib.error.HTTPError as exc: result.update(status_code=exc.code)
    except Exception as exc: result.update(error_category=type(exc).__name__)
    result["elapsed_ms"] = round((time.monotonic()-begin)*1000, 2)
    checks["http:" + target["name"]] = 200 <= result.get("status_code", 0) < 300
    http.append(result)
print(json.dumps({"status": "passed" if all(checks.values()) else "failed", "checks": checks,
    "observation": {"hostname": platform.node(), "docker_access_exit_code": rc,
                    "docker_inspect_exit_code": inspect_rc, "containers": containers,
                    "units": units, "http": http},
    "limitations": ["Read-only snapshot only; no restart, recreation, database write, restore or load test.",
      "No container Env, commands, labels, healthcheck log, application body or secrets are emitted.",
      "HTTP checks use unauthenticated local root/health paths only; redirects are not followed.",
      "Container running or health response does not prove business correctness or persistence."]}))
'''


def main():
    p = base_parser(__doc__)
    p.add_argument("--project", type=service_name)
    p.add_argument("--expect-service", action="append", default=[], type=service_name)
    p.add_argument("--require-unit", action="append", default=[], type=unit_name)
    p.add_argument("--expect-mount", action="append", default=[], help="SERVICE:/absolute/container/path")
    p.add_argument("--require-pinned-images", action="store_true", help="Require digest references, stricter than version tags")
    p.add_argument("--require-healthcheck", action="store_true")
    p.add_argument("--http", action="append", default=[], type=endpoint, help="NAME=local root/health URL")
    args = p.parse_args()
    for mount in args.expect_mount:
        if ":" not in mount:
            p.error("--expect-mount uses SERVICE:/absolute/path")
        service, path = mount.split(":", 1)
        service_name(service)
        if not path.startswith("/") or "\x00" in path:
            p.error("mount path must be absolute")
    for e in args.http:
        if e["hostname"] not in {"localhost", "127.0.0.1", "::1", args.host}:
            p.error("HTTP checks may target only loopback or this guest host")
    if not (args.expect_service or args.require_unit or args.http):
        p.error("specify at least one expected service, unit or HTTP endpoint")
    result, code = remote_json(args, STACK_SOURCE,
        {"expected_hostname": args.expected_hostname, "project": args.project,
         "services": args.expect_service, "units": args.require_unit, "mounts": args.expect_mount,
         "require_pinned_images": args.require_pinned_images, "require_healthcheck": args.require_healthcheck,
         "http": args.http})
    emit(args, result)
    return code


if __name__ == "__main__":
    sys.exit(main())
