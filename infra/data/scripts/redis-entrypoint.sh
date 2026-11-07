#!/bin/sh
set -eu
umask 077
runtime=/run/dell-redis
conf=$runtime/redis.conf
[ ! -L "$runtime" ] && [ ! -L "$conf" ] || exit 1
mkdir -p "$runtime"
chown root:root "$runtime"
chmod 0711 "$runtime"
printf 'bind 0.0.0.0\nprotected-mode yes\nport 6379\ndir /data\nappendonly yes\nappendfsync everysec\nsave 900 1\nmaxmemory %s\nmaxmemory-policy noeviction\nrequirepass %s\n' "$REDIS_MAXMEMORY" "$(cat /run/secrets/redis-password)" > "$conf"
chown redis:redis "$conf"
chmod 0600 "$conf"
exec /usr/local/bin/docker-entrypoint.sh redis-server "$conf"
