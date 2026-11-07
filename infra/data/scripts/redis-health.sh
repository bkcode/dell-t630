#!/bin/sh
set -eu
export REDISCLI_AUTH="$(cat /run/secrets/redis-password)"
[ "$(redis-cli --no-auth-warning --raw ping)" = PONG ]
