#!/usr/bin/env python3
"""Prepare private ops bundle and candidate inventory; never starts a service."""
import argparse, ipaddress, json, os, re, secrets, shutil, uuid
from pathlib import Path
from urllib.parse import urlsplit
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]

def canonical(value):
    if not value.startswith('/') or not re.fullmatch(r'/[A-Za-z0-9_./-]+',value):raise ValueError('absolute safe path required')
    if any(x in ('.','..') for x in value.split('/')) or os.path.normpath(value)!=value:raise ValueError('non-normalized or traversal path rejected')
    p=Path(value)
    if p.resolve(strict=False)!=p:raise ValueError('symlink path component rejected')
    return p

def private_file(path,data):
    if path.is_symlink():raise ValueError('private symlink rejected')
    path.write_text(data);path.chmod(0o600)

def guard_notification_reprepare(bundle,baseline):
    # Re-running preparation must never erase a configured notification receiver.
    marker=bundle/'lark-notify-state.json'
    config=bundle/'config/alertmanager/alertmanager.yml'
    if marker.exists() or marker.is_symlink():
        raise ValueError('notification state already exists; generic prepare refuses to reset it')
    if config.is_symlink() or (config.exists() and config.read_bytes()!=baseline.read_bytes()):
        raise ValueError('existing Alertmanager config differs; notification/custom configuration preserved')
    for name in ('bridge-auth','lark-bridge-token'):
        file=bundle/'config/alertmanager'/name
        if file.exists() or file.is_symlink():raise ValueError('credential in public config directory rejected')

def stable_bridge_token(private,bundle):
    primary=private/'lark-bridge-token';copy=bundle/'secrets/lark-bridge-token'
    for file in (primary,copy):
        if file.is_symlink():raise ValueError('bridge token symlink rejected')
    values=[file.read_text() for file in (primary,copy) if file.exists()]
    if any(not re.fullmatch('[A-Za-z0-9_-]{64}\n',value) for value in values):raise ValueError('existing bridge token format invalid')
    if len(set(values))>1:raise ValueError('existing bridge tokens differ; automatic rotation refused')
    value=values[0] if values else secrets.token_urlsafe(48)+'\n'
    copy.parent.mkdir(mode=0o700,exist_ok=True)
    private_file(primary,value);private_file(copy,value)
    return 'preserved' if values else 'generated'

def candidate_inventory(plan):
    rows=[];nodes=[];http=[]
    paths={'data-prod-infra':(8848,'/nacos/v1/console/health/readiness','nacos-readiness'),'data-test':(8848,'/nacos/v1/console/health/readiness','nacos-readiness'),'artifact-service':(8081,'/service/rest/v1/status','nexus-status'),'penpot-service':(9001,'/','penpot-frontend-only'),'nas-media':(8096,'/health','jellyfin-health'),'ops-service':(3000,'/api/health','grafana-health')}
    for role in plan['roles']:
        ip=role.get('ip') or role.get('planned_ip')
        vmid=role.get('vmid') or role.get('planned_vmid') or role.get('existing_vmid_candidate')
        labels={'role':role['name'],'zone':role['zone'],'vmid':str(vmid) if vmid is not None else 'pending'}
        row={'role':role['name'],'kind':role['kind'],'vmid':vmid,'candidate_ip':ip,'deployment_status':role['deployment_status'],'monitoring_status':'pending-exporter-http-and-acl-verification','node_exporter':None,'http':None}
        if ip:
            ipaddress.IPv4Address(ip)
            row['node_exporter']=ip+':9100'
            nodes.append({'targets':[row['node_exporter']],'labels':labels})
            if role['name'] in paths:
                port,path,check=paths[role['name']]
                row['http']='http://'+ip+':'+str(port)+path
                http.append({'targets':[row['http']],'labels':{**labels,'check':check,'scope':'endpoint-only'}})
        rows.append(row)
    return {'status':'candidate-not-live-verified','roles':rows,'pve_metrics':{'host':plan['pve']['host'],'status':'pending-separate-authorized-push-or-read-only-api','new_host_port_opened':False,'included_in_scrape_targets':False}},nodes,http

def main():
    os.umask(0o077)
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--service-ip',default='10.63.30.40')
    parser.add_argument('--data-mountpoint',default='/srv/dell-ops')
    parser.add_argument('--data-root',default=None)
    parser.add_argument('--data-uuid',type=uuid.UUID)
    parser.add_argument('--install-dir',default='/opt/dell/ops')
    parser.add_argument('--public-uri',default=None)
    parser.add_argument('--activate-role',action='append',default=[],help='Enable guest node_exporter scrape only')
    parser.add_argument('--activate-http-role',action='append',default=[],help='Explicit optional cross-guest HTTP activation; requires separately approved ACL')
    args=parser.parse_args()
    guard_notification_reprepare(ROOT/'private/ops/bundle',HERE/'config/alertmanager/alertmanager.yml')
    ipaddress.IPv4Address(args.service_ip)
    mount=canonical(args.data_mountpoint);data=canonical(args.data_root or str(mount/'data'));canonical(args.install_dir)
    if mount==Path('/') or data==mount or not data.is_relative_to(mount):raise ValueError('data-root must be below a dedicated mount')
    url=args.public_uri or 'http://'+args.service_ip+':3000'
    parsed=urlsplit(url)
    if parsed.scheme not in ('http','https') or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in ('','/'):
        raise ValueError('Grafana public URI must be a clean HTTP(S) origin')
    plan=json.loads((ROOT/'plan.json').read_text())
    expected=next(r for r in plan['roles'] if r['name']=='ops-service')
    if expected.get('planned_ip')!=args.service_ip:raise ValueError('service IP does not match assigned plan candidate')
    inventory,nodes,http=candidate_inventory(plan)
    available={x['role'] for x in inventory['roles'] if x['candidate_ip']}
    if not set(args.activate_role).issubset(available):raise ValueError('unknown or unaddressed activation role')
    http_available={x['labels']['role'] for x in http}
    if not set(args.activate_http_role).issubset(http_available):raise ValueError('unknown HTTP activation role')
    public=HERE/'config'
    (public/'candidates').mkdir(exist_ok=True)
    (public/'candidates'/'catalog.json').write_text(json.dumps(inventory,ensure_ascii=False,indent=2)+'\n')
    (public/'candidates'/'guest-node.json').write_text(json.dumps(nodes,indent=2)+'\n')
    (public/'candidates'/'http-services.json').write_text(json.dumps(http,indent=2)+'\n')
    external={'status':'optional-read-only-probe-no-scheduler-installed','endpoints':[{'name':'pve-ssh-port','url':'tcp://'+plan['pve']['host']+':22','enabled':True,'scope':'TCP-port-only'},{'name':'pve-ui-port','url':'tcp://'+plan['pve']['host']+':8006','enabled':True,'scope':'TCP-port-only'},{'name':'ops-grafana-candidate','url':'http://'+args.service_ip+':3000/api/health','enabled':False,'scope':'requires-approved-routing-or-explicit-SSH-forward'}]}
    (public/'external-probes.json').write_text(json.dumps(external,indent=2)+'\n')
    private=ROOT/'private'/'ops';private.mkdir(parents=True,exist_ok=True,mode=0o700);private.chmod(0o700)
    secret=private/'grafana-admin-password'
    if secret.is_symlink():raise ValueError('private symlink rejected')
    if not secret.exists():
        fd=os.open(secret,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,'w') as out:out.write(secrets.token_hex(24)+'\n')
    secret.chmod(0o600)
    if not secret.read_text().strip():raise ValueError('empty existing Grafana password; no automatic reset')
    bundle=private/'bundle';bundle.mkdir(exist_ok=True,mode=0o700);bundle.chmod(0o700)
    old={}
    if (bundle/'.env').exists():old=dict(x.split('=',1) for x in (bundle/'.env').read_text().splitlines() if x)
    data_uuid=str(args.data_uuid) if args.data_uuid else old.get('DATA_FS_UUID','')
    if data_uuid:data_uuid=str(uuid.UUID(data_uuid))
    for name in ['config','scripts']:
        shutil.copytree(HERE/name,bundle/name,dirs_exist_ok=True)
        for p in (bundle/name).rglob('*'):
            p.chmod(0o755 if p.is_dir() or p.suffix=='.py' else 0o644)
    for name in ['compose.yaml','images.lock.json']:shutil.copy2(HERE/name,bundle/name)
    (bundle/'secrets').mkdir(exist_ok=True,mode=0o700)
    private_file(bundle/'secrets'/'grafana-admin-password',secret.read_text())
    bridge_token_status=stable_bridge_token(private,bundle)
    active_nodes=[x for x in nodes if x['labels']['role'] in args.activate_role]
    active_http=json.loads((public/'prometheus/targets/http-services.json').read_text())+[x for x in http if x['labels']['role'] in args.activate_http_role]
    (bundle/'config/prometheus/targets/guest-node.json').write_text(json.dumps(active_nodes,indent=2)+'\n')
    (bundle/'config/prometheus/targets/http-services.json').write_text(json.dumps(active_http,indent=2)+'\n')
    env={'ROLE':'ops-service','SERVICE_IP':args.service_ip,'INSTALL_DIR':args.install_dir,'DATA_MOUNTPOINT':str(mount),'DATA_ROOT':str(data),'DATA_FS_UUID':data_uuid,'GRAFANA_ADMIN_USER':'dell_admin','GRAFANA_ROOT_URL':url.rstrip('/'),'GRAFANA_COOKIE_SECURE':'true' if parsed.scheme=='https' else 'false'}
    private_file(bundle/'.env',''.join(k+'='+v+'\n' for k,v in env.items()))
    private_file(bundle/'bundle.json',json.dumps({'status':'prepared-not-deployed','vmid':expected.get('vmid') or expected.get('planned_vmid'),'role':'ops-service','service_ip':args.service_ip,'guest_budget_gib':expected['memory_gib'],'data_fs_uuid':data_uuid or None,'active_guest_roles':sorted(set(args.activate_role)),'active_http_roles':sorted(set(args.activate_http_role)),'candidate_role_count':len(inventory['roles']),'pve_host_metrics':'pending-separate-authorization','external_notification_delivery':'not-configured-not-tested'},indent=2)+'\n')
    print(json.dumps({'status':'prepared-not-deployed','bundle':str(bundle),'candidate_roles':len(inventory['roles']),'active_guest_roles':sorted(set(args.activate_role)),'data_uuid':'configured' if data_uuid else 'pending','secrets':'600; values suppressed','bridge_token':bridge_token_status}))

if __name__=='__main__':main()
