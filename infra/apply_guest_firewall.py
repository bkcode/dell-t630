#!/usr/bin/env python3
"""PVE only; atomic updates of dedicated tables, then enable IPv4 forwarding."""
from pathlib import Path
import subprocess


def nft(text, check=False):
    command = ['nft'] + (['-c'] if check else []) + ['-f', '-']
    result = subprocess.run(command, input=text, text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError(result.stderr.strip())


def table(family, name):
    result = subprocess.run(['nft', 'list', 'table', family, name], capture_output=True, text=True)
    return result.stdout if result.returncode == 0 else ''


before = {(family, name): table(family, name) for family, name in
          [('inet', 'dell_filter'), ('ip', 'dell_nat')]}
old_forward = Path('/proc/sys/net/ipv4/ip_forward').read_text().strip()
deletes = ''.join(f'delete table {family} {name}\n' for (family, name), text in before.items() if text)
transaction = deletes + Path('/etc/nftables.d/dell.nft').read_text()
nft(transaction, check=True)
applied = False
try:
    nft(transaction)
    applied = True
    subprocess.run(['sysctl', '-w', 'net.ipv4.ip_forward=1'], check=True, capture_output=True)
except Exception:
    try:
        if old_forward == '0':
            subprocess.run(['sysctl', '-w', 'net.ipv4.ip_forward=0'], check=True, capture_output=True)
        if applied:
            restore = 'delete table inet dell_filter\ndelete table ip dell_nat\n' + ''.join(before.values())
            nft(restore)
    finally:
        subprocess.run(['sysctl', '-w', 'net.ipv4.ip_forward=' + old_forward], check=True, capture_output=True)
    raise
print('Dedicated firewall applied atomically; IPv4 forwarding enabled after filter commit')
