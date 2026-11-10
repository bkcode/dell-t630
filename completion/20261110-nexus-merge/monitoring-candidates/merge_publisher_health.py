"""Pure merge against the captured VM220 profile, never a baseline reinstall."""
import copy
NEXUS_CHECK = {'name': 'nexus-status', 'url': 'http://192.168.19.31:8081/service/rest/v1/status'}
ADDED_UNITS = ['docker.service', 'dell-nexus.service', 'puyu-deploy-mcp.service']


def merge_publisher_health(before):
    if before.get('role') != 'publish-service' or before.get('private_ip') != '192.168.19.30':
        raise ValueError('Existing VM220 primary30 profile required')
    if 'dell-service-directory.service' not in before.get('services', []):
        raise ValueError('Existing navigation check must be present and preserved')
    result = copy.deepcopy(before)
    for field in ['services', 'candidate_service_units']:
        values = result.setdefault(field, [])
        if len(values) != len(set(values)):
            raise ValueError('Existing duplicate units require review')
        for unit in ADDED_UNITS:
            if unit not in values:
                values.append(unit)
    for field in ['http_checks', 'candidate_http_checks']:
        values = result.setdefault(field, [])
        matches = [value for value in values if value.get('name') == NEXUS_CHECK['name']]
        if len(matches) > 1 or matches and matches != [NEXUS_CHECK]:
            raise ValueError('Nexus endpoint conflict requires review')
        if not matches:
            values.append(copy.deepcopy(NEXUS_CHECK))
    return result
