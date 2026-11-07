#!/bin/bash
# Existing NGINX status endpoint; no external utility, credential or request query.
set -eu
exec 3<>/dev/tcp/127.0.0.1/8082
printf 'GET /stub_status HTTP/1.0\r\nHost: localhost\r\nConnection: close\r\n\r\n' >&3
IFS= read -r status <&3
[[ "$status" =~ ^HTTP/1\.[01]\ 200\  ]] || exit 1
while IFS= read -r line <&3; do
    [[ "$line" == 'Active connections:'* ]] && exit 0
done
exit 1
