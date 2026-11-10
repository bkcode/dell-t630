"""Pure profile delta for a fresh VM220 health.json snapshot; no installation."""
import copy

NEXUS_CHECK = {'name': 'nexus-status', 'url': 'http://192.168.19.31:8081/service/rest/v1/status'}


def merge_publisher_health(before):
    if before.get('role') != 'publish-service' or before.get('private_ip') != '192.168.19.30':
        raise ValueError('Only the existing primary30 publish-service profile is accepted')
    result = copy.deepcopy(before)
    for field in ['services', 'candidate_service_units']:
        values = result.setdefault(field, [])
        if len(values) != len(set(values)):
            raise ValueError('Existing duplicate service entries require review')
        for unit in ['docker.service', 'dell-nexus.service']:
            if unit not in values:
                values.append(unit)
    for field in ['http_checks', 'candidate_http_checks']:
        values = result.setdefault(field, [])
        matches = [value for value in values if value.get('name') == NEXUS_CHECK['name']]
        if len(matches) > 1 or matches and matches != [NEXUS_CHECK]:
            raise ValueError('Existing Nexus check differs; no silent endpoint replacement')
        if not matches:
            values.append(copy.deepcopy(NEXUS_CHECK))
    return result
