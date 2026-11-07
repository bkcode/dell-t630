#!/bin/bash
set -euo pipefail
set +x
export MYSQL_SERVICE_PASSWORD="$(cat /run/secrets/nacos-db-password)"
export NACOS_AUTH_TOKEN="$(cat /run/secrets/nacos-auth-token)"
export NACOS_AUTH_IDENTITY_VALUE="$(cat /run/secrets/nacos-identity-value)"
exec bash /home/nacos/bin/docker-startup.sh
