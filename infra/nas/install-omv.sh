#!/usr/bin/env bash
# Run only on the assigned, clean Debian 13 nas-media VM after manager review.
set -euo pipefail
umask 077
APPLY=0
NETWORK=0
CONSOLE=0
EXPECTED_HOST=nas-media
IFACE=''
ADDRESS=''
GATEWAY=''
DNS=''
ADMIN_FILE=''
OMV_VERSION=''
ARCHIVE_KEY_FILE=''
REPOSITORY_ROOT=''
die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
usage() {
  cat <<'EOF'
Usage: sudo bash install-omv.sh --check|--apply --expected-hostname nas-media
       --interface ens18 --address 10.63.40.10/24 --gateway 10.63.40.1
       --dns 1.1.1.1 --admin-password-file /root/private/omv-admin-password
       [--apply-network --console-available] [--omv-version VERSION]
Default is check-only. Apply does not format disks, install Docker or start Jellyfin.
Apply-network imports the exact existing address into OMV and can interrupt SSH.
EOF
}
while (($#)); do
  case "$1" in
    --check) APPLY=0; shift;;
    --apply) APPLY=1; shift;;
    --apply-network) NETWORK=1; shift;;
    --console-available) CONSOLE=1; shift;;
    --expected-hostname|--interface|--address|--gateway|--dns|--admin-password-file|--omv-version|--archive-key-file|--repository-root)
      (($# >= 2)) || die "Missing option value"
      case "$1" in
        --expected-hostname) EXPECTED_HOST=$2;; --interface) IFACE=$2;;
        --address) ADDRESS=$2;; --gateway) GATEWAY=$2;; --dns) DNS=$2;;
        --admin-password-file) ADMIN_FILE=$2;; --omv-version) OMV_VERSION=$2;;
        --archive-key-file) ARCHIVE_KEY_FILE=$2;; --repository-root) REPOSITORY_ROOT=$2;;
      esac
      shift 2;;
    -h|--help) usage; exit 0;;
    *) die "Unknown option";;
  esac
done
[[ $(id -u) == 0 ]] || die 'Must run as root on the assigned guest'
[[ ! -d /etc/pve ]] || die 'Refusing to run on a PVE host'
[[ $(hostname -s) == "$EXPECTED_HOST" && "$EXPECTED_HOST" == nas-media ]] || die 'Wrong guest hostname'
# shellcheck disable=SC1091
. /etc/os-release
[[ ${ID:-} == debian && ${VERSION_ID:-} == 13 && $(dpkg --print-architecture) == amd64 ]] || die 'Only Debian 13 amd64 is supported by this recipe'
[[ -d /run/systemd/system ]] || die 'systemd is required'
[[ "$IFACE" =~ ^[A-Za-z0-9][A-Za-z0-9_.:-]{0,30}$ && -d /sys/class/net/$IFACE ]] || die 'Explicit valid network interface is required'
python3 - "$IFACE" "$ADDRESS" "$GATEWAY" "$DNS" <<'PY'
import ipaddress,json,subprocess,sys
iface,address,gateway,dns=sys.argv[1:]
network=ipaddress.ip_interface(address)
assert network.version==4
assert ipaddress.ip_address(gateway) in network.network
assert ipaddress.ip_address(dns).version==4
current=json.loads(subprocess.check_output(['ip','-j','addr','show','dev',iface],text=True))
assert any(a.get('local')==str(network.ip) and a.get('prefixlen')==network.network.prefixlen for x in current for a in x.get('addr_info',[])), 'Requested IP must already be assigned to this interface'
routes=json.loads(subprocess.check_output(['ip','-j','route','show','default'],text=True))
assert any(r.get('dev')==iface and r.get('gateway')==gateway for r in routes), 'Requested gateway must match existing route'
PY
id ub >/dev/null || die 'Existing ub user required'
KEYFILE=$(getent passwd ub | cut -d: -f6)/.ssh/authorized_keys
[[ -s "$KEYFILE" ]] || die 'Existing ub authorized_keys required; install public key through trusted provisioning first'
KEY_HASH=$(sha256sum "$KEYFILE" | cut -d' ' -f1)
for pkg in task-desktop gdm3 lightdm apache2 nginx; do
  if dpkg-query -W -f='${Status}' "$pkg" 2>/dev/null | grep -qx 'install ok installed'; then
    die 'Desktop or existing web server detected; require a clean minimal guest'
  fi
done
if dpkg-query -W -f='${Status}' openmediavault 2>/dev/null | grep -qx 'install ok installed'; then
  die 'OMV is already installed; inspect existing state instead of rerunning installation'
fi
if (( NETWORK )); then (( CONSOLE )) || die 'Explicit console availability confirmation required'; fi
[[ -f "$ADMIN_FILE" && ! -L "$ADMIN_FILE" ]] || die 'Root-owned admin password file required'
python3 - "$ADMIN_FILE" <<'PY'
from pathlib import Path
import os,stat,sys
p=Path(sys.argv[1]); s=p.stat(); value=p.read_text().rstrip('\n')
assert s.st_uid==0 and stat.S_IMODE(s.st_mode)==0o600, 'Secret file must be owned by root with mode 600'
assert len(value)>=20 and '\n' not in value and ':' not in value and '\r' not in value, 'Use a long single-line password without colon'
PY
if (( ! APPLY )); then
  printf '{"status":"preflight-passed","role":"nas-media","os":"debian-13-amd64","writes_performed":false}\n'
  exit 0
fi
BACKUP=/root/dell-omv-preinstall-$(date -u +%Y%m%dT%H%M%SZ)
install -d -m 700 "$BACKUP"
for path in /etc/network/interfaces /etc/network/interfaces.d /etc/systemd/network /etc/netplan /etc/resolv.conf /etc/ssh/sshd_config /etc/cloud/cloud.cfg.d; do
  [[ ! -e "$path" && ! -L "$path" ]] || cp -a --parents "$path" "$BACKUP/"
done
cp -a "$KEYFILE" "$BACKUP/ub-authorized_keys"
export LANG=C.UTF-8 DEBIAN_FRONTEND=noninteractive APT_LISTCHANGES_FRONTEND=none
apt-get update
apt-get install --yes --no-install-recommends ca-certificates curl gnupg systemd-resolved psmisc
systemctl enable --now systemd-resolved.service
resolvectl dns "$IFACE" "$DNS"
resolvectl domain "$IFACE" '~.'
getent ahostsv4 packages.openmediavault.org >/dev/null || die 'DNS resolution failed before OMV installation'
getent group _ssh >/dev/null || groupadd --system _ssh
usermod -a -G _ssh,sudo ub
TMPDIR_OMV=$(mktemp -d)
trap 'rm -rf -- "$TMPDIR_OMV"' EXIT
if [[ -n "$ARCHIVE_KEY_FILE" ]]; then
  [[ -f "$ARCHIVE_KEY_FILE" && ! -L "$ARCHIVE_KEY_FILE" ]] || die 'Explicit public archive key file missing'
  grep -q 'BEGIN PGP PUBLIC KEY BLOCK' "$ARCHIVE_KEY_FILE" || die 'Not an armored public archive key'
  cp "$ARCHIVE_KEY_FILE" "$TMPDIR_OMV/archive.key"
else
  curl --fail --silent --show-error --location --retry 2 --proto '=https' --tlsv1.2 https://packages.openmediavault.io/archive.key -o "$TMPDIR_OMV/archive.key"
fi
gpg --batch --yes --dearmor --output "$TMPDIR_OMV/archive.gpg" "$TMPDIR_OMV/archive.key"
install -m 644 "$TMPDIR_OMV/archive.gpg" /usr/share/keyrings/openmediavault-archive-keyring.gpg
if [[ -n "$REPOSITORY_ROOT" ]]; then
  case "$REPOSITORY_ROOT" in
    https://openmediavault.github.io/packages/|https://packages.openmediavault.org/public/|https://packages.openmediavault.io/) ;;
    *) die 'Only verified official OMV repository roots accepted';;
  esac
  printf 'deb [signed-by=/usr/share/keyrings/openmediavault-archive-keyring.gpg] %s synchrony main\n' "$REPOSITORY_ROOT" > /etc/apt/sources.list.d/openmediavault.list
else
  cat > /etc/apt/sources.list.d/openmediavault.list <<'EOF'
deb [signed-by=/usr/share/keyrings/openmediavault-archive-keyring.gpg] http://packages.openmediavault.org/public/ synchrony main
deb [signed-by=/usr/share/keyrings/openmediavault-archive-keyring.gpg] http://packages.openmediavault.io/ synchrony main
EOF
fi
apt-get update
if [[ -z "$OMV_VERSION" ]]; then OMV_VERSION=$(apt-cache policy openmediavault | awk '/Candidate:/ {print $2}'); fi
[[ "$OMV_VERSION" =~ ^8[.][A-Za-z0-9.+:~_-]+$ ]] || die 'OMV candidate must be an explicit 8.x version'
apt-get --yes --no-install-recommends --option DPkg::Options::=--force-confdef --option DPkg::Options::=--force-confold install "openmediavault=$OMV_VERSION"
getent group _ssh >/dev/null || die 'OMV _ssh group missing'
usermod -a -G _ssh,sudo ub
[[ $(sha256sum "$KEYFILE" | cut -d' ' -f1) == "$KEY_HASH" ]] || die 'ub authorized_keys changed unexpectedly'
chown ub:ub "$(dirname "$KEYFILE")" "$KEYFILE"
chmod 700 "$(dirname "$KEYFILE")"
chmod 600 "$KEYFILE"
# Admin is a system-authenticated Web UI account. Pass the new password via stdin only.
python3 - "$ADMIN_FILE" <<'PY'
from pathlib import Path
import subprocess,sys
password=Path(sys.argv[1]).read_text().rstrip('\n')
subprocess.run(['chpasswd'],input='admin:'+password+'\n',text=True,check=True,
               stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
PY
if (( NETWORK )); then
  cat > /etc/network/interfaces <<EOF
auto lo
iface lo inet loopback

auto $IFACE
iface $IFACE inet static
    address $ADDRESS
    gateway $GATEWAY
    dns-nameservers $DNS
EOF
  omv-confdbadm populate
  # Cloud-init must not reintroduce a competing network definition on reboot.
  install -d -m 755 /etc/cloud/cloud.cfg.d
  printf 'network: {config: disabled}\n' > /etc/cloud/cloud.cfg.d/99-dell-omv-network.cfg
  # OMV owns the subsequent network definition; preserve earlier definitions in root-only backup.
  for path in /etc/netplan/50-cloud-init.yaml /etc/systemd/network/10-cloud-init.network; do
    if [[ -f "$path" ]]; then mv "$path" "$BACKUP/$(basename "$path").disabled"; fi
  done
  omv-salt deploy run systemd-networkd
else
  omv-confdbadm populate
fi
/usr/sbin/sshd -t
VERSION_INSTALLED=$(dpkg-query -W -f='${Version}' openmediavault)
printf '{"status":"installed-needs-live-verification","role":"nas-media","omv_version":"%s","network_adopted":%s,"ub_key_unchanged":true,"disk_formatting_performed":false}\n' "$VERSION_INSTALLED" "$([[ $NETWORK == 1 ]] && printf true || printf false)"
