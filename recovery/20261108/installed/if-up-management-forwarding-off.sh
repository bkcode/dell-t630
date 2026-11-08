#!/bin/sh
# ifupdown2 sets forwarding on bridges with IP; restore original management-only contract.
set -eu
[ "${IFACE:-}" = vmbr0 ] || exit 0
exec /usr/local/sbin/dell-management-forwarding-off
