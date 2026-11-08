#!/bin/sh
# PVE management/L2 only. Do not restart networking or change routing/ACL.
set -eu
[ "$(hostname -s)" = pve ] && [ -d /etc/pve ]
for family in ipv4 ipv6; do
    for path in /proc/sys/net/$family/conf/*/forwarding; do
        [ -f "$path" ] || continue
        printf '0\n' > "$path"
    done
done
printf '0\n' > /proc/sys/net/ipv4/ip_forward
