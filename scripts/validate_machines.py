#!/usr/bin/env python3
"""Validate offline per-machine records against plan.json; never contact a server."""
from __future__ import annotations
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def validate() -> dict:
    errors = []
    stats = {'machine_directories': 0, 'guest_records': 0, 'template_records': 0, 'source_references': 0, 'snapshot_copies': 0}
    def safe_file(path: Path, boundary: Path = ROOT) -> bool:
        try:
            relative = path.relative_to(ROOT)
            if any(part in {'private', '.git'} for part in relative.parts):
                return False
            if any(ROOT.joinpath(*relative.parts[:i]).is_symlink() for i in range(1, len(relative.parts) + 1)):
                return False
            return path.resolve(strict=True).is_relative_to(boundary.resolve()) and path.is_file()
        except (OSError, ValueError):
            return False

    def read(path: Path):
        try:
            if not safe_file(path):
                raise ValueError('unsafe file')
            value = json.loads(path.read_text())
            if not isinstance(value, dict):
                raise ValueError('object required')
            return value
        except (OSError, ValueError):
            errors.append('Missing or invalid JSON: ' + str(path.relative_to(ROOT)))
            return {}
    plan = read(ROOT/'plan.json')
    registry = read(ROOT/'machines/index.json')
    entries = registry.get('machines', [])
    if not isinstance(entries, list):
        return {'status': 'failed', 'errors': ['machines/index.json must contain a machines list'], 'stats': stats}
    roles = {r['vmid']: r for r in plan.get('roles', [])}
    templates = {r['vmid']: r for r in plan.get('templates', []) + plan.get('acceptance_templates', [])}
    expected = {('pve', None), *((r['kind'], v) for v, r in roles.items()), *(('template', v) for v in templates)}
    observed = []
    known_paths = set()
    for entry in entries:
        rel = entry.get('path', '')
        pure = Path(rel)
        if pure.is_absolute() or '..' in pure.parts or len(pure.parts) != 2 or pure.parts[0] != 'machines':
            errors.append('Unsafe or non-machine registry path: ' + rel)
            continue
        if rel in known_paths:
            errors.append('Duplicate machine directory: ' + rel)
        known_paths.add(rel)
        folder = ROOT/rel
        if not safe_file(folder/'README.md', folder):
            errors.append('Machine README missing or symlink: ' + rel)
        cfg = read(folder/'config.json')
        sources = read(folder/'config-sources.json')
        machine = cfg.get('machine', {})
        identity = (machine.get('kind'), machine.get('vmid'))
        observed.append(identity)
        for key in ('kind', 'vmid', 'name', 'ip'):
            if entry.get(key) != machine.get(key):
                errors.append(f'{rel}: registry {key} differs from machine record')
        stats['machine_directories'] += 1
        if cfg.get('schema_version') != 1 or sources.get('schema_version') != 1:
            errors.append('Invalid per-machine schema_version: ' + rel)
        if cfg.get('source_of_truth') != 'plan.json' or not cfg.get('last_verified_at'):
            errors.append('Missing source/time contract: ' + rel)
        live = cfg.get('current_runtime_verified')
        if live is True:
            proof = cfg.get('current_verification_evidence', '')
            if (not plan.get('operational_state', {}).get('current_runtime_verified')
                    or not proof or not safe_file(ROOT/proof)):
                errors.append('Current runtime claim requires recovered plan and verification evidence: ' + rel)
        elif live is not False:
            errors.append('Explicit current runtime verification boolean required: ' + rel)
        if identity[0] in ('vm', 'lxc'):
            stats['guest_records'] += 1
            role = roles.get(identity[1], {})
            for key in ('name', 'kind', 'vmid', 'ip', 'vcpu', 'memory_gib'):
                if machine.get(key) != role.get(key):
                    errors.append(f'{rel}: machine.{key} differs from current plan role')
            if cfg.get('startup_order') != role.get('startup_order'):
                errors.append('Startup order differs from plan role: ' + rel)
            network = cfg.get('network', {})
            if identity[1] != 190:
                dns = network.get('dns', network.get('DNS'))
                dns = dns if isinstance(dns, list) else [dns]
                if network.get('gateway') != role.get('gateway') or dns != [role.get('DNS')]:
                    errors.append('Guest gateway/DNS differs from plan: ' + rel)
                if network.get('bridge') != role.get('planned_bridge'):
                    errors.append('Guest bridge differs from plan: ' + rel)
                if network.get('additional_ips', []) != role.get('additional_ips', []):
                    errors.append('Guest aliases differ from applied plan: ' + rel)
            else:
                wan, lan = network.get('WAN', {}), network.get('LAN', {})
                if (wan.get('address', '').split('/')[0] != role.get('WAN_ip')
                        or lan.get('address', '').split('/')[0] != role.get('LAN_ip')
                        or wan.get('bridge') != role.get('WAN_bridge')
                        or lan.get('bridge') != role.get('planned_bridge')
                        or wan.get('MAC') != role.get('WAN_MAC') or lan.get('MAC') != role.get('LAN_MAC')
                        or wan.get('gateway') != role.get('gateway')):
                    errors.append('Gateway WAN/LAN identity differs from plan: ' + rel)
            storage = cfg.get('storage', {})
            if role.get('system_storage') and storage.get('system_storage') != role['system_storage']:
                errors.append('System storage differs from plan: ' + rel)
            if role.get('data_filesystem_uuid'):
                volumes = storage.get('data_volumes', [])
                volume = volumes[0] if len(volumes) == 1 else {}
                actual = (storage.get('data_filesystem_uuid', volume.get('filesystem_uuid')),
                          storage.get('guest_mountpoint', volume.get('mountpoint')),
                          storage.get('data_disk_gib', volume.get('size_gib')),
                          storage.get('data_storage', volume.get('pve_storage')))
                wanted = tuple(role.get(key) for key in ('data_filesystem_uuid', 'guest_mountpoint', 'data_disk_gib', 'data_storage'))
                if actual != wanted:
                    errors.append('Data disk UUID/mount/size/storage differs from plan: ' + rel)
            expected_status = plan.get('operational_state', {}).get('machine_status_contract', 'paused-awaiting-hardware-repair')
            if cfg.get('status') != expected_status:
                errors.append('Guest record status differs from current operational scope: ' + rel)
        elif identity[0] == 'template':
            stats['template_records'] += 1
            template = templates.get(identity[1], {})
            if machine.get('name') != template.get('name') or machine.get('ip') is not None:
                errors.append('Template identity or unassigned IP differs from contract: ' + rel)
        elif identity[0] == 'pve':
            if machine.get('ip') != plan.get('pve', {}).get('host'):
                errors.append('PVE management address differs from plan')
        items = sources.get('entries', [])
        if not items:
            errors.append('Empty configuration source list: ' + rel)
        for item in items:
            path = item.get('path', '')
            pp = Path(path)
            if (not path or pp.is_absolute() or '..' in pp.parts or 'private' in pp.parts
                    or pp.name == '.env' or (pp.name.startswith('.env.') and pp.name != '.env.example')):
                errors.append('Private/unsafe source reference in ' + rel)
                continue
            source = ROOT/pp
            if not safe_file(source):
                errors.append(f'{rel}: missing or symlink source {path}')
                continue
            if item.get('type') not in {'current-contract', 'historical-evidence', 'pending-candidate'} or not item.get('purpose'):
                errors.append(f'{rel}: source classification/purpose missing for {path}')
            if not isinstance(item.get('sha256'), str) or not re.fullmatch(r'[0-9a-f]{64}', item['sha256']):
                errors.append(f'{rel}: missing or invalid source SHA for {path}')
            elif hashlib.sha256(source.read_bytes()).hexdigest() != item['sha256']:
                errors.append(f'{rel}: indexed local source SHA changed for {path}')
            stats['source_references'] += 1
            if item.get('snapshot_path'):
                sp = Path(item['snapshot_path'])
                if sp.is_absolute() or '..' in sp.parts:
                    errors.append('Unsafe local snapshot path in ' + rel)
                    continue
                snapshot = folder/sp
                if not safe_file(snapshot, folder):
                    errors.append('Missing snapshot in ' + rel)
                elif hashlib.sha256(snapshot.read_bytes()).hexdigest() != item.get('source_sha256'):
                    errors.append('Snapshot bytes differ from recorded source SHA in ' + rel)
                elif hashlib.sha256(source.read_bytes()).hexdigest() != item.get('source_sha256'):
                    errors.append('Snapshot source has changed; refresh/review required in ' + rel)
                stats['snapshot_copies'] += 1
    counts = registry.get('counts', {})
    expected_counts = {'PVE_hosts': 1, 'retained_guest_instances': len(roles),
                       'retained_templates': len(templates), 'total_directories': len(expected)}
    if counts != expected_counts:
        errors.append('Registry counts differ from PVE/plan roles/templates')
    if set(observed) != expected or len(observed) != len(expected):
        errors.append('Machine registry must cover exactly PVE + current plan roles + retained templates')
    actual = {str(p.relative_to(ROOT)) for p in (ROOT/'machines').iterdir() if p.is_dir()} if (ROOT/'machines').is_dir() else set()
    if actual != known_paths:
        errors.append('Machine directories and registry differ')
    return {'status': 'failed' if errors else 'passed', 'scope': 'offline-per-machine-contracts-only', 'stats': stats, 'errors': errors,
            'limitations': ['No live SSH or configuration export', 'Source files may be historical or pending; respect classification', 'Private deployment credentials and archives are intentionally absent']}


if __name__ == '__main__':
    result = validate()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(result['status'] != 'passed')
