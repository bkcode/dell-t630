#!/usr/bin/env python3
"""Validate local documentation, budget and pending acceptance; no network or deployment."""
from __future__ import annotations

import argparse
import os
import hashlib
import importlib.util
import json
import re
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = [
    'README.md', 'AGENTS.md', '19-manual-operations.md', '20-git-and-handoff.md',
    '11-live-handoff.md', '12-service-access-and-operations.md', '01-current-state.md', '02-architecture.md',
    '03-templates-and-access.md', '04-services-and-migration.md', '05-home-nas.md',
    '06-acceptance.md', '07-implementation-and-tasks.md', 'plan.json',
    'acceptance.json', 'tasks.json', 'machines/README.md', 'machines/index.json',
    'scripts/validate_machines.py', 'evidence/pve-audit-2026-11-05.json',
    'evidence/document-verification.md', 'evidence/local-services-2026-11-05.json',
]


def validate() -> dict:
    errors: list[str] = []
    warnings: list[str] = []
    stats: dict = {}
    for name in REQUIRED:
        if not (ROOT / name).is_file():
            errors.append(f'Missing required file: {name}')

    def read_json(name: str) -> dict:
        try:
            value = json.loads((ROOT / name).read_text())
            if not isinstance(value, dict):
                raise ValueError('top-level JSON must be an object')
            return value
        except (OSError, ValueError) as exc:
            errors.append(f'{name}: {exc}')
            return {}

    plan = read_json('plan.json')
    acceptance = read_json('acceptance.json')
    tasks = read_json('tasks.json')
    audit = read_json('evidence/pve-audit-2026-11-05.json')
    operation = plan.get('operational_state', {})
    stats['operational_state'] = operation.get('status', 'unspecified')
    stats['live_verification_in_this_check'] = False
    if operation.get('status') == 'user-paused-awaiting-memory-hardware-repair':
        if operation.get('runtime_counts_are_last_verified_not_live') is not True:
            errors.append('Hardware pause must distinguish last verified counts from current runtime')
        nexus = plan.get('Nexus_consolidation', {})
        if nexus.get('migration_started') is not False:
            errors.append('Paused Nexus handoff must remain explicitly not started')
        for key in ['hardware_gate', 'authorization_evidence']:
            if not (ROOT / nexus.get(key, '__missing__')).is_file():
                errors.append('Paused Nexus handoff lacks ' + key)
        stats['operational_state'] = 'user-paused-awaiting-memory-hardware-repair'
        stats['live_verification_in_this_check'] = False
    roles = plan.get('roles', [])
    names = [r.get('name') for r in roles]
    if len(names) != len(set(names)) or not all(names):
        errors.append('Role names must be non-empty and unique')
    if len(roles) != plan.get('expected_role_count', 13):
        errors.append('Role count differs from explicit plan expected_role_count; update agreed scope contract')
    try:
        for role in roles:
            if role['memory_gib'] <= 0 or role['vcpu'] <= 0:
                errors.append(f"Non-positive resource allocation: {role.get('name')}")
        memory = sum(r['memory_gib'] for r in roles)
        vcpu = sum(r['vcpu'] for r in roles)
        reserve = plan['pve']['memory_budget_gib'] - memory
        if reserve < plan['pve']['minimum_host_reserve_gib']:
            errors.append(f'Insufficient host memory reserve: {reserve} GiB')
        stats.update(roles=len(roles), guest_memory_gib=memory, vcpu=vcpu,
                     host_reserve_gib=reserve)
        if vcpu > plan['pve']['physical_cores']:
            warnings.append('vCPU exceeds physical cores; concurrent workload capacity is unverified')
    except (KeyError, TypeError) as exc:
        errors.append(f'Invalid resource plan: {exc}')
    if {x.get('name') for x in plan.get('templates', [])} != {
        'tpl-linux-base', 'tpl-docker-base'
    }:
        errors.append('Expected two core templates only')
    java_scope = plan.get('java_delivery')
    if java_scope is not None:
        templates = plan.get('acceptance_templates', [])
        if (java_scope.get('business_programs_allowed') is not False
                or java_scope.get('active_business_services') != 0
                or java_scope.get('publisher_baseline_enabled') is not False):
            errors.append('Current user scope requires Java business services stopped and publisher fenced')
        if (java_scope.get('acceptance_template_count') != 1 or len(templates) != 1
                or templates[0].get('vmid') != java_scope.get('acceptance_template_vmid')
                or templates[0].get('business_apps_configs_credentials') is not False):
            errors.append('Expected exactly one clean Java acceptance template in the current scope')
    if plan.get('nas', {}).get('dedicated_template_required') is not False:
        errors.append('NAS must not require another PVE template')
    if plan.get('guest_ssh', {}).get('user') != 'ub':
        errors.append('Guest SSH user must match user-provided ub')
    if plan.get('pve', {}).get('host') != '192.168.21.22':
        errors.append('PVE host must be 192.168.21.22')

    cases = acceptance.get('cases', [])
    ids = [c.get('id') for c in cases]
    if not cases or len(ids) != len(set(ids)) or not all(ids):
        errors.append('Acceptance IDs must be non-empty, unique, and present')
    required_fields = {
        'id', 'title', 'phase', 'execution_type', 'preconditions', 'steps',
        'pass_criteria', 'fail_criteria', 'evidence', 'status'
    }
    allowed_types = {'read-only', 'disruptive-test', 'manual-review'}
    for case in cases:
        missing = required_fields - case.keys()
        if missing:
            errors.append(f"{case.get('id')}: missing fields {sorted(missing)}")
        for key in required_fields:
            if key in case and not case[key]:
                errors.append(f"{case.get('id')}: empty {key}")
        if case.get('execution_type') not in allowed_types:
            errors.append(f"{case.get('id')}: invalid execution_type")
        if plan.get('scope') == 'documentation-and-read-only-verification':
            status = case.get('status')
            if case.get('phase') == 'documentation' and status == 'passed':
                proof_path = ROOT / case.get('evidence', '')
                try:
                    proof = json.loads(proof_path.read_text())
                    snapshot = proof.get('plan_snapshot', 'plan.json')
                    plan_hash = hashlib.sha256((ROOT / snapshot).read_bytes()).hexdigest()
                    if (proof.get('id') != case.get('id') or proof.get('status') != 'passed'
                            or not proof.get('executed_at') or not proof.get('reviewed_by')
                            or proof.get('preconditions_checked') is not True
                            or proof.get('plan_sha256') != plan_hash):
                        errors.append(f"{case.get('id')}: invalid documentation acceptance evidence")
                except (OSError, ValueError):
                    errors.append(f"{case.get('id')}: missing/invalid documentation acceptance evidence")
            elif status != 'pending':
                errors.append(f"{case.get('id')}: future implementation acceptance must stay pending")
    current_manifest = plan.get('delivery_scope_manifest')
    if current_manifest in {'network19/audit/network19-acceptance.json', 'cleanup/acceptance.json', 'completion/20261109/acceptance.json', 'completion/20261109-prod-db-scope/acceptance.json', 'completion/20261109-prod-db-restore/acceptance.json', 'completion/20261109-test-env/acceptance.json', 'completion/20261109-nacos-config-import/acceptance.json'}:
        current = read_json(current_manifest)
        current_cases = current.get('cases', [])
        current_ids = [c.get('id') for c in current_cases]
        if not current_cases or len(set(current_ids)) != len(current_ids):
            errors.append('Current network acceptance IDs must be present and unique')
        mandatory = {'id', 'title', 'status', 'required_for_phase', 'preconditions',
                     'steps', 'observable_pass_conditions', 'evidence'}
        for case in current_cases:
            if mandatory - case.keys():
                errors.append(f"{case.get('id')}: incomplete current network acceptance contract")
            for evidence in case.get('evidence', []):
                path = evidence.get('path') if isinstance(evidence, dict) else evidence
                if not path or not (ROOT / path).is_file():
                    errors.append(f"{case.get('id')}: missing current evidence {path}")
        required = [c for c in current_cases if c.get('required_for_phase') is True]
        passed = sum(c.get('status') == 'passed' for c in required)
        summary = current.get('summary', {})
        if (summary.get('total') != len(current_cases)
                or summary.get('current_phase_case_count') != len(required)
                or summary.get('current_phase_passed') != passed):
            errors.append('Current network acceptance summary differs from actual cases')
        stats.update(current_acceptance_manifest=current_manifest, current_network_cases=len(current_cases),
                     current_network_required_passed=passed,
                     current_network_required_count=len(required),
                     current_network_optional_pending=sum(c.get('status') == 'pending'
                         and c.get('required_for_phase') is not True for c in current_cases),
                     Java_acceptance_templates=len(plan.get('acceptance_templates', [])))
    stats['acceptance_cases'] = len(cases)
    stats['documentation_passed'] = sum(c.get('phase') == 'documentation' and c.get('status') == 'passed' for c in cases)
    stats['implementation_pending'] = sum(c.get('phase') == 'implementation' and c.get('status') == 'pending' for c in cases)
    acceptance_md = ROOT / '06-acceptance.md'
    if acceptance_md.exists():
        md = acceptance_md.read_text()
        headings = re.findall(r'^### (ACC-[A-Z]+-\d{3}) ·', md, flags=re.M)
        if set(headings) != set(ids) or len(headings) != len(ids):
            errors.append('Markdown acceptance headings do not match JSON cases')
        for case in cases:
            marker = f"### {case.get('id')} ·"
            if marker in md:
                section = md.split(marker, 1)[1].split('\n<a id=', 1)[0]
                state = case.get('status')
                if f'实际状态：**{state}' not in section:
                    errors.append(f"{case.get('id')}: Markdown/JSON status mismatch")

    expected_ids = {f'DOC-{i:02d}' for i in range(1, 6)}
    doc_tasks = tasks.get('documentation', [])
    if {t.get('id') for t in doc_tasks} != expected_ids:
        errors.append('Documentation task registry is incomplete')
    for task in doc_tasks:
        for name in task.get('outputs', []):
            if not (ROOT / name).is_file():
                errors.append(f"{task.get('id')}: missing output {name}")
        if task.get('status') == 'completed' and task.get('manager_verified') is not True:
            errors.append(f"{task.get('id')}: completed without manager verification")
    if plan.get('scope') == 'documentation-and-read-only-verification':
        for task in tasks.get('implementation', []):
            if task.get('status') != 'not_started':
                errors.append(f"{task.get('id')}: implementation scope not activated")
        for role in roles:
            if role.get('deployment_status') != 'not-accepted':
                errors.append(f"{role.get('name')}: must not claim deployment accepted")

    checks = audit.get('checks', [])
    check_ids = [c.get('id') for c in checks]
    if not checks or len(check_ids) != len(set(check_ids)):
        errors.append('PVE evidence checks missing or duplicated')
    if audit.get('host') != '192.168.21.22' or audit.get('mode') != 'read-only':
        errors.append('PVE evidence host/mode mismatch')
    if not audit.get('collected_at') or audit.get('timezone') != 'Asia/Shanghai':
        errors.append('PVE evidence requires collection time and client timezone')
    for check in checks:
        if check.get('exit_code') != 0:
            warnings.append(f"PVE check {check.get('id')} exit={check.get('exit_code')}; see scope/limitations")
    stats['pve_checks'] = len(checks)

    public_files = []
    for folder, directories, files in os.walk(ROOT):
        directories[:] = [d for d in directories if d not in {'private', '__pycache__', 'node_modules', '.git', '.gradle'}]
        public_files.extend(Path(folder) / name for name in files)
    local_links = 0
    external_links = set()
    for file in sorted(p for p in public_files if p.suffix == '.md'):
        content = file.read_text()
        if content.count('```') % 2:
            errors.append(f'Unclosed code fence: {file.relative_to(ROOT)}')
        prose = re.sub(r'```.*?```', '', content, flags=re.S)
        for match in re.finditer(r'!?\[[^\]\n]*\]\(([^\n]+?)\)', prose):
            target = match.group(1).strip()
            if target.startswith('<'):
                end = target.find('>')
                target = target[1:end] if end >= 0 else target
            else:
                target = target.split(' "', 1)[0]
            parsed = urlsplit(target)
            if parsed.scheme in {'http', 'https'}:
                external_links.add(target)
                continue
            if parsed.scheme or target.startswith('#'):
                continue
            path = unquote(target.split('#', 1)[0])
            line = None
            line_match = re.search(r':(\d+)$', path)
            if line_match:
                line = int(line_match.group(1))
                path = path[:line_match.start()]
            dest = Path(path) if Path(path).is_absolute() else file.parent / path
            if not dest.exists():
                errors.append(f'Broken local link in {file.relative_to(ROOT)}: {target}')
            elif line is not None and (line < 1 or line > len(dest.read_text().splitlines())):
                errors.append(f'Invalid source line in {file.relative_to(ROOT)}: {target}')
            local_links += 1
        for number, line in enumerate(content.splitlines(), 1):
            if line.rstrip() != line:
                errors.append(f'Trailing whitespace: {file.relative_to(ROOT)}:{number}')
    for file in public_files:
        if file.suffix not in {'.md', '.json'}:
            continue
        content = file.read_text()
        if re.search(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----', content):
            errors.append(f'Private key material in {file.relative_to(ROOT)}')
        if re.search(r'(?:ssh-rsa|ssh-ed25519)\s+AAAA[A-Za-z0-9+/=]{30,}', content):
            errors.append(f'Unexpected public key material in {file.relative_to(ROOT)}')
    if (ROOT / 'machines/index.json').is_file():
        try:
            spec = importlib.util.spec_from_file_location('dell_machine_validator', ROOT / 'scripts/validate_machines.py')
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            machine_result = module.validate()
            errors.extend('Machine directory: ' + message for message in machine_result['errors'])
            stats['machine_directory_validation'] = machine_result['status']
            stats['machine_directories'] = machine_result['stats']['machine_directories']
        except (OSError, ValueError, KeyError, TypeError) as exc:
            errors.append('Cannot validate machine directories: ' + str(exc))
    stats.update(local_links_checked=local_links, external_links_listed=len(external_links))
    warnings.append('External URL availability is not tested by this offline validator')
    return {'status': 'passed' if not errors else 'failed', 'scope': 'local-document-validation-only',
            'stats': stats, 'errors': errors, 'warnings': warnings}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--json', action='store_true', help='Print machine-readable result')
    args = parser.parse_args()
    result = validate()
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"Document validation: {result['status']}")
        print(json.dumps(result['stats'], ensure_ascii=False))
        for message in result['errors']:
            print(f'ERROR: {message}')
        for message in result['warnings']:
            print(f'NOTE: {message}')
    return 0 if result['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
