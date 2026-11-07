#!/bin/sh
set -eu
case "${1:-}" in
    backend) url=http://127.0.0.1:6060/readyz ;;
    exporter) url=http://127.0.0.1:6061/readyz ;;
    *) exit 1 ;;
esac
body=$(/usr/bin/curl -q --noproxy '*' --fail --silent --max-time 3 "$url" 2>/dev/null) || exit 1
[ "$body" = OK ]
