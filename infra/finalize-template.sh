#!/bin/bash
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
role=$1
case "$role" in tpl-linux-base|tpl-docker-base) ;; *) exit 2;; esac
[ ! -d /etc/pve ]
[ "$(id -u)" = 0 ]
. /etc/os-release
[ "$ID" = debian ] && [ "$VERSION_ID" = 13 ]
cloud-init status --wait >/dev/null
hostnamectl set-hostname "$role"
install -d -m 755 /usr/local/share/dell /etc/cloud/cloud.cfg.d
printf 'template=%s\nos=debian13\narchitecture=amd64\n' "$role" > /usr/local/share/dell/template-release
printf 'LANG=C.UTF-8\n' > /etc/default/locale
if [ "$role" = tpl-docker-base ]; then
 docker info >/dev/null
 [ -z "$(docker ps -aq)" ]
 docker version --format '{{.Server.Version}}' >> /usr/local/share/dell/template-release
 docker compose version >> /usr/local/share/dell/template-release
 systemctl stop docker docker.socket containerd
fi
apt-get clean
# These builders contain no application data. Keep only intended ub authorized key.
rm -f /root/.bash_history /home/ub/.bash_history
cloud-init clean --logs --machine-id
rm -f /etc/ssh/ssh_host_*
sync
systemctl poweroff
