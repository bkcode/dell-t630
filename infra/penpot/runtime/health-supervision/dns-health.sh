#!/bin/sh
set -eu
reply=$(/bin/busybox timeout 4 /bin/busybox nslookup -type=A dell-penpot-health.invalid 127.0.0.1 2>/dev/null) || exit 1
case "$reply" in
    *192.0.2.53*) exit 0 ;;
    *) exit 1 ;;
esac
