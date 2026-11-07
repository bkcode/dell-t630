#!/usr/bin/env bash
set -euo pipefail
umask 077
[[ $(id -u) == 0 && $(hostname -s) == nas-media && ! -d /etc/pve ]] || { echo 'Assigned NAS guest root only' >&2;exit 1; }
. /etc/os-release
[[ ${ID:-} == debian && ${VERSION_ID:-} == 13 && $(dpkg --print-architecture) == amd64 ]] || exit 1
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install --yes --no-install-recommends ca-certificates curl smbclient
install -m 755 -d /etc/apt/keyrings
curl --fail --silent --show-error --location --retry 2 --proto '=https' https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc
chmod 644 /etc/apt/keyrings/docker.asc
cat >/etc/apt/sources.list.d/docker.sources <<'EOF'
Types: deb
URIs: https://download.docker.com/linux/debian
Suites: trixie
Components: stable
Architectures: amd64
Signed-By: /etc/apt/keyrings/docker.asc
EOF
apt-get update
DELL_DOCKER_VERSION=$(apt-cache policy docker-ce | awk '/Candidate:/ {print $2}')
[[ "$DELL_DOCKER_VERSION" =~ ^[0-9]+:[0-9]+[.][A-Za-z0-9.+:~_-]+$ ]] || { echo 'No valid Docker candidate' >&2;exit 1; }
apt-get install --yes --no-install-recommends "docker-ce=$DELL_DOCKER_VERSION" "docker-ce-cli=$DELL_DOCKER_VERSION" containerd.io docker-compose-plugin
systemctl enable --now docker.service
python3 - <<'PY'
import subprocess,json
print(json.dumps({'status':'docker-engine-installed','engine':subprocess.check_output(['docker','version','--format','{{.Server.Version}}'],text=True).strip(),'compose':subprocess.check_output(['docker','compose','version','--short'],text=True).strip(),'other_stacks_started':False}))
PY
