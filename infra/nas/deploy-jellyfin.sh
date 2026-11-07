#!/usr/bin/env bash
# Guest-only, reviewed deployment. Never formats or mounts a disk.
set -euo pipefail
umask 077
APPLY=0
ENV_FILE=''
EXPECTED_HOST=nas-media
HERE=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
while (($#)); do
  case "$1" in
    --check) APPLY=0; shift;;
    --apply) APPLY=1; shift;;
    --env-file) (($#>=2)) || die 'Missing env file'; ENV_FILE=$2; shift 2;;
    --expected-hostname) (($#>=2)) || die 'Missing hostname'; EXPECTED_HOST=$2; shift 2;;
    -h|--help) printf 'Usage: sudo bash deploy-jellyfin.sh --check|--apply --env-file /root/private/nas.env --expected-hostname nas-media\n'; exit 0;;
    *) die 'Unknown argument';;
  esac
done
[[ $(id -u) == 0 && ! -d /etc/pve ]] || die 'Run only as root on the assigned guest'
[[ $(hostname -s) == "$EXPECTED_HOST" && "$EXPECTED_HOST" == nas-media ]] || die 'Wrong guest hostname'
[[ -f "$ENV_FILE" && ! -L "$ENV_FILE" ]] || die 'Explicit regular env file required'
# Parse, validate and emit only non-secret deployment fields. Never source a shell env file.
mapfile -t FIELDS < <(python3 - "$ENV_FILE" <<'PY'
from pathlib import Path
import ipaddress,re,stat,sys,urllib.parse
p=Path(sys.argv[1]); s=p.stat()
assert s.st_uid==0 and stat.S_IMODE(s.st_mode)==0o600, 'env file must be root-owned mode 600'
values={}
for line in p.read_text().splitlines():
 line=line.strip()
 if not line or line.startswith('#'): continue
 k,v=line.split('=',1)
 assert k not in values, 'duplicate environment key'
 values[k]=v
required=['NAS_MOUNT','NAS_DATA_UUID','NAS_BIND_IP','JELLYFIN_IMAGE','JELLYFIN_UID','JELLYFIN_GID','JELLYFIN_PUBLIC_URL']
assert set(values)==set(required), 'unexpected or missing environment keys'
assert re.fullmatch(r'/srv/dev-disk-by-uuid-[0-9a-fA-F-]+',values['NAS_MOUNT'])
assert re.fullmatch(r'[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}',values['NAS_DATA_UUID'])
assert values['NAS_MOUNT'].endswith(values['NAS_DATA_UUID'])
assert ipaddress.ip_address(values['NAS_BIND_IP']).version==4
assert re.fullmatch(r'(?:jellyfin/jellyfin|ghcr.io/jellyfin/jellyfin)@sha256:[0-9a-f]{64}',values['JELLYFIN_IMAGE'])
for k in ['JELLYFIN_UID','JELLYFIN_GID']: assert values[k].isdigit() and 1000<=int(values[k])<=60000
url=urllib.parse.urlsplit(values['JELLYFIN_PUBLIC_URL'])
assert url.scheme in {'http','https'} and url.hostname and not(url.username or url.password or url.query or url.fragment)
assert re.fullmatch(r'https?://[A-Za-z0-9.:-]+/?', values['JELLYFIN_PUBLIC_URL'])
for k in required: print(values[k])
PY
)
[[ ${#FIELDS[@]} == 7 ]] || die 'Invalid env file'
MOUNT=${FIELDS[0]}; UUID=${FIELDS[1]}; BIND_IP=${FIELDS[2]}; IMAGE=${FIELDS[3]}; MEDIA_UID=${FIELDS[4]}; MEDIA_GID=${FIELDS[5]}
python3 "$HERE/check-data-mount.py" --mountpoint "$MOUNT" --uuid "$UUID"
command -v docker >/dev/null || die 'Docker Engine must be installed using the approved base bootstrap'
docker compose version >/dev/null
ip -j addr | python3 -c 'import json,sys; assert any(a.get("local")==sys.argv[1] for n in json.load(sys.stdin) for a in n.get("addr_info",[]))' "$BIND_IP"
docker compose --env-file "$ENV_FILE" -f "$HERE/compose.yaml" config --quiet
if (( ! APPLY )); then printf '{"status":"preflight-passed","writes_performed":false}\n'; exit 0; fi
# No downloaders, VPN or old all-in-one units are installed by this script.
if getent group "$MEDIA_GID" >/dev/null; then
  [[ $(getent group "$MEDIA_GID" | cut -d: -f1) == media ]] || die 'Selected GID already belongs to another group'
else groupadd --gid "$MEDIA_GID" media; fi
if id jellyfin >/dev/null 2>&1; then
  [[ $(id -u jellyfin) == "$MEDIA_UID" && $(id -g jellyfin) == "$MEDIA_GID" ]] || die 'Existing jellyfin identity differs'
else
  ! getent passwd "$MEDIA_UID" >/dev/null || die 'Selected UID already belongs to another account'
  useradd --uid "$MEDIA_UID" --gid "$MEDIA_GID" --no-create-home --home-dir /nonexistent --shell /usr/sbin/nologin jellyfin
fi
for dir in media media/movies media/tv media/animation media/music games games/ps4 games/ps5 incoming; do
  install -d -o root -g media -m 2775 "$MOUNT/$dir"
done
install -d -o jellyfin -g media -m 700 "$MOUNT/appdata/jellyfin/config" "$MOUNT/appdata/jellyfin/cache"
install -d -o root -g root -m 700 "$MOUNT/family" "$MOUNT/family/photos" "$MOUNT/family/documents"
install -d -m 755 /opt/dell/nas /usr/local/libexec
install -m 644 "$HERE/compose.yaml" /opt/dell/nas/compose.yaml
install -m 600 "$ENV_FILE" /opt/dell/nas/.env
install -m 755 "$HERE/check-data-mount.py" /usr/local/libexec/dell-nas-check-data
# The digest is adopted only if the actual image architecture matches the guest.
docker pull "$IMAGE"
[[ $(docker image inspect --format '{{.Architecture}}' "$IMAGE") == amd64 ]] || die 'Jellyfin image is not amd64'
MOUNT_UNIT=$(systemd-escape --path --suffix=mount "$MOUNT")
cat > /etc/systemd/system/dell-nas-jellyfin.service <<EOF
[Unit]
Description=Dell NAS Jellyfin (requires verified data filesystem)
Requires=docker.service
After=docker.service network-online.target $MOUNT_UNIT
Wants=network-online.target
RequiresMountsFor=$MOUNT
BindsTo=docker.service $MOUNT_UNIT
StartLimitIntervalSec=120
StartLimitBurst=3

[Service]
Type=simple
WorkingDirectory=/opt/dell/nas
ExecStartPre=/usr/local/libexec/dell-nas-check-data --mountpoint $MOUNT --uuid $UUID
ExecStart=/usr/bin/docker compose --env-file /opt/dell/nas/.env -f /opt/dell/nas/compose.yaml up --no-build --abort-on-container-exit --exit-code-from jellyfin
ExecStop=/usr/bin/docker compose --env-file /opt/dell/nas/.env -f /opt/dell/nas/compose.yaml stop --timeout 30
Restart=on-failure
RestartSec=10
TimeoutStopSec=60

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable dell-nas-jellyfin.service
systemctl reset-failed dell-nas-jellyfin.service
systemctl restart dell-nas-jellyfin.service
printf '{"status":"deployed-needs-live-verification","service":"dell-nas-jellyfin","disk_formatting_performed":false}\n'
