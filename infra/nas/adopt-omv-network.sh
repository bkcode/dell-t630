#!/usr/bin/env bash
# Separate, reviewed network adoption after OMV installation; same current IP/gateway only.
set -euo pipefail
umask 077
APPLY=0;CONSOLE=0;IFACE='';ADDRESS='';GATEWAY='';DNS=''
die(){ printf 'ERROR: %s\n' "$*" >&2;exit 1; }
while (($#));do
 case "$1" in
 --check)APPLY=0;shift;; --apply)APPLY=1;shift;; --console-available)CONSOLE=1;shift;;
 --interface|--address|--gateway|--dns)
  (($#>=2))||die 'Missing value';case "$1" in --interface)IFACE=$2;;--address)ADDRESS=$2;;--gateway)GATEWAY=$2;;--dns)DNS=$2;;esac;shift 2;;
 *)die 'Unknown argument';;esac
done
[[ $(id -u) == 0 && ! -d /etc/pve && $(hostname -s) == nas-media ]]||die 'Assigned NAS guest root only'
dpkg-query -W -f='${Status}' openmediavault 2>/dev/null|grep -qx 'install ok installed'||die 'OMV not installed'
[[ "$IFACE" =~ ^[A-Za-z0-9][A-Za-z0-9_.:-]{0,30}$ ]]||die 'Invalid interface'
python3 - "$IFACE" "$ADDRESS" "$GATEWAY" "$DNS" <<'PY'
import ipaddress,json,subprocess,sys
iface,address,gateway,dns=sys.argv[1:];value=ipaddress.ip_interface(address)
assert value.version==4 and str(value.ip)=='10.63.40.10' and value.network.prefixlen==24
assert gateway=='10.63.40.1' and ipaddress.ip_address(dns).version==4
rows=json.loads(subprocess.check_output(['ip','-j','addr','show','dev',iface],text=True))
assert any(a.get('local')==str(value.ip) and a.get('prefixlen')==24 for r in rows for a in r.get('addr_info',[]))
routes=json.loads(subprocess.check_output(['ip','-j','route','show','default'],text=True))
assert any(r.get('dev')==iface and r.get('gateway')==gateway for r in routes)
PY
id ub >/dev/null;KEY=/home/ub/.ssh/authorized_keys;[[ -s "$KEY" ]]||die 'ub public key missing'
if ((!APPLY));then printf '{"status":"network-adoption-precheck-passed","ip_changes":false}\n';exit 0;fi
((CONSOLE))||die 'Manager QGA/console standby confirmation is required'
BACKUP=/root/dell-omv-network-$(date -u +%Y%m%dT%H%M%SZ);install -d -m700 "$BACKUP"
for path in /etc/network/interfaces /etc/network/interfaces.d /etc/systemd/network /etc/netplan /etc/resolv.conf /etc/cloud/cloud.cfg.d;do
 [[ ! -e "$path" && ! -L "$path" ]]||cp -a --parents "$path" "$BACKUP/"
done
KEYHASH=$(sha256sum "$KEY"|cut -d' ' -f1)
usermod -a -G _ssh,sudo ub
cat >/etc/network/interfaces <<EOF
auto lo
iface lo inet loopback

auto $IFACE
iface $IFACE inet static
    address ${ADDRESS%/*}
    netmask 255.255.255.0
    gateway $GATEWAY
    dns-nameservers $DNS
EOF
# OMV 8.6 netplan import failed on the original static cloud-init YAML.
# Preserve it first and use the official interfaces importer; active kernel addresses remain unchanged.
for path in /etc/netplan/50-cloud-init.yaml /etc/systemd/network/10-cloud-init.network;do
 [[ ! -f "$path" ]]||mv "$path" "$BACKUP/$(basename "$path").disabled"
done
omv-confdbadm populate
printf 'network: {config: disabled}\n' >/etc/cloud/cloud.cfg.d/99-dell-omv-network.cfg
omv-salt deploy run systemd-networkd
[[ $(sha256sum "$KEY"|cut -d' ' -f1) == "$KEYHASH" ]]||die 'ub key unexpectedly changed'
/usr/sbin/sshd -t
printf '{"status":"network-adopted-needs-reconnect-verification","same_ip":"10.63.40.10/24","same_gateway":"10.63.40.1","ub_key_unchanged":true}\n'
