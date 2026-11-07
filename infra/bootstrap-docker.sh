set -eu
sudo install -d -m 0755 /etc/apt/keyrings
sudo apt-get update -qq
sudo apt-get install -y --no-install-recommends ca-certificates curl python3 qemu-guest-agent sudo chrony
curl -fsSL https://download.docker.com/linux/debian/gpg -o /tmp/dell-docker.asc
sudo install -m 0644 /tmp/dell-docker.asc /etc/apt/keyrings/docker.asc
printf '%s\n' 'Types: deb' 'URIs: https://download.docker.com/linux/debian' 'Suites: trixie' 'Components: stable' 'Architectures: amd64' 'Signed-By: /etc/apt/keyrings/docker.asc' | sudo tee /etc/apt/sources.list.d/docker.sources >/dev/null
sudo apt-get update -qq
sudo apt-get install -y --no-install-recommends docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo install -d -m 0755 /etc/docker
printf '%s\n' '{"log-driver":"local","log-opts":{"max-size":"10m","max-file":"3"},"live-restore":true}' | sudo tee /etc/docker/daemon.json >/dev/null
sudo systemctl enable --now docker qemu-guest-agent chrony
sudo systemctl restart docker
sudo docker version --format '{{.Server.Version}}'
sudo docker compose version
