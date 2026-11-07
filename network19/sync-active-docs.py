from pathlib import Path
import json,datetime,shutil
R=Path(__file__).resolve().parents[1];now=datetime.datetime.now().astimezone().isoformat()
p=R/'plan.json';x=json.loads(p.read_text());snapshot=R/'network19/evidence/plan-before-current-signoff.json'
if not snapshot.exists():snapshot.write_text(p.read_text())
m=json.loads((R/'network19/migration-plan.json').read_text());ipmap={r['vmid']:r['new_ip'] for r in m['guest_addresses']}
for role in x['roles']:
 vmid=role.get('vmid',role.get('planned_vmid',role.get('existing_vmid_candidate')))
 if vmid is None:continue
 role['vmid']=vmid;new=ipmap[vmid];role.update(ip=new,planned_ip=new,configured_ip=new,planned_bridge='vmbr19',gateway='192.168.19.1',DNS='192.168.19.1',network_revision='network19',network_status='OS-and-strict-access-verified',allocation_status='network19-active')
 if vmid==190:role.update(ip='192.168.19.1',management_ip='192.168.21.23',WAN_ip='192.168.21.23',gateway='192.168.21.1',DNS='192.168.21.1',deployment_status='routed-no-NAT-firewall-DNS-DHCP-reboot-verified',startup_order={'vmid':190,'order':1,'up_seconds':30,'down_seconds':120})
 elif vmid==100:role.update(deployment_status='network19-cloudflared-registered-secret-unit-unchanged-controlled-restart',startup_order={'vmid':100,'order':5,'up_seconds':10,'down_seconds':60})
 elif vmid in [230,231,232,240]:role.update(deployment_status='runtime-foundation-only-no-active-Java-business-apps',business_apps='not deployed or started; old240 immutable files are private backups',active_business_HTTP_checks=0)
 elif vmid==220:role['deployment_status']='network19-publisher-contract-verified-fenced-no-business-publish'
 elif vmid==221:role['deployment_status']='network19-Nexus-49GAV-234primary-SHA-readback-verified'
 elif vmid==250:role['deployment_status']='network19-Penpot-11healthy-3designs-973media-MCP-verified'
 elif vmid==270:role['deployment_status']='network19-12node-plus5Ops-UP-server-internal-Lark-unchanged'
 elif vmid==260:role['deployment_status']='network19-OMV-Jellyfin-verified-SMB-new-subnet-signoff-in-progress'
x.update(date='2026-11-06',updated_at=now,status='network19-operational-Java-business-disabled-final-signoff',scope='network19-infrastructure-and-single-Java-acceptance-template',expected_role_count=14)
x['decisions'].update(java='No Java business program deployment in either environment; preserve one clean acceptance template9011 and runtime foundations only',production_java_delivery='Runtime foundation only; test business apps also stopped/disabled by latest user instruction',network19_routed_gateway='OW19/24 via21.23,router19019.1;PVE21.22management/L2only,nohostNAT/L3forward')
x['acceptance_templates']=[{'name':'tpl-java-acceptance','vmid':9011,'count':1,'status':'sealed-and-full-clone-identity-JDK-smoke-verified','JDK':'21.0.13','nonroot_user':'java','business_apps_configs_credentials':False,'node_exporter':'installed but masked until per-instance IP/role enrollment','network':'vmbr19,CloudInitDHCP; assign IP/MAC ACL and explicit hostname per clone','evidence':'network19/java-template/clone-evidence.json'}]
x['existing_role_templates']['105']='legacy original preserved; not the current accepted Java template, use9011'
x['network']={'status':'network19-verified-host-NAT-and-forwarding-retired','mode':'dedicated-routing-VM-no-host-NAT','management_unchanged':'192.168.21.22/24 vmbr0','router_vmid':190,'router_WAN':'192.168.21.23/24','router_LAN':'192.168.19.1/24','OW_route':'192.168.19.0/24 via192.168.21.23','guest_default_gateway':'192.168.19.1','dns':'192.168.19.1 → 192.168.21.1','bridges':{'vmbr0':'PVEmanagement21.22 and onlyGW WAN21.23','vmbr19':'internalL2only,NOhostIP'},'PVE_host_L3_forwarding':False,'PVE_NAT':False,'gateway_NAT':False,'host_management_client_route':'19/24 via21.23 devvmbr0 source21.22','same_subnet_isolation':'bridge dell19_acl exact MAC/IP+role matrix; router alone cannot isolate same19/24','evidence':['network19/evidence/host-management-only-retirement.json','network19/evidence/Mac-final-management-and-services.json','network19/audit/data-tcp-matrix.json']}
x['guest_ssh']['verification']='12 permanent single-NIC guests strict ub original-key SSH on actual19addresses;230 one documented QGA-verified rotation;GW dualIPseparate known alias;CIDHCPidentity preserved on deployedVMs'
x['guest_ssh']['nas_iso_requirement']='NAS installed OMV; original root/data UUID and ub key-only SSH preserved, no ISO pending'
x['notifications']['network19_evidence']='network19/services-core/ops270-new-network-allup-readback.json'
x['notifications']['maintenance']='network19 silence pending root final cleanup; no new test messages sent'
x['delivery_scope_manifest']='network19/audit/network19-acceptance.json'
p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n')
# Preserve historical bootstrap access receipt before updating the active operator entry point.
p=R/'evidence/implementation/private-guest-access.json';old=json.loads(p.read_text());backup=R/'network19/evidence/guest-access-before-current-signoff.json'
if not backup.exists():backup.write_text(p.read_text())
new=json.loads((R/'network19/evidence/migrated-access.json').read_text())['targets']
for row in old['roles']:
 vmid=row['target']['vmid'];assert str(vmid) in new;row['target']=new[str(vmid)]
old.update(network_revision='network19',updated_at=now,historical_original='network19/evidence/guest-access-before-current-signoff.json');p.write_text(json.dumps(old,indent=2,ensure_ascii=False)+'\n')
(R/'network19/README.md').write_text('''# network19当前网络与验收

实际网络已迁入192.168.19.0/24。OW静态route经192.168.21.23（VM190 WAN），虚拟网关LAN19.1；PVE21.22只管理/二层交换，旧四桥/NAT已清除，宿主IPv4/IPv6 forwarding全部0，vmbr19无宿主IP。

最新范围：**不部署或启动Java业务程序，测试五服务也已停用，Publisher保持fenced；只保留一份9011 Java验收模板。** Linux9010/Docker9001两个核心模板与NAS独立安装方式不变。

当前阅读入口：[交付与边界](../15-network19-delivery.md)、[访问与操作](../12-service-access-and-operations.md)、[网络验收](audit/network19-acceptance.md)、[Java模板](java-template/README.md)、[active plan](../plan.json)。迁移历史与失败/修正回执保留，不能把旧10.63证据当当前网络证据。

同19/24东西向流量由PVE bridge-family ACL精确绑定MAC/IP与role矩阵，原生rule预检及实际正负/反欺骗发包已验。网关不对LAN之间SNAT；OW负责上游分流，保留实际Fake-IP代理DNS兼容。旧104与101、七个停止QA都已实际启动确认19地址再恢复停机。

秘密不进镜像/普通文档；CF归档只在PVE，publisher私钥只在220，Mac外部探针仍停用。CF只验新网注册，未知remote ingress与公网域名仍未签。PVE宿主整机重启、断电/真实TV主机/SLO/长期独立备份属于明确后续范围。
''')
# Archive existing access page and preserve its credential location guidance.
p=R/'12-service-access-and-operations.md';oldtext=p.read_text();archive=R/'network19/evidence/service-access-before-current-signoff.md'
if not archive.exists():archive.write_text(oldtext)
creds=oldtext.split('## 凭据位置',1)[1].split('## 发布与回退',1)[0]
access='''# 当前访问入口与日常操作

2026-11-06 network19版本。应用直接访问真实19地址；PVE21.22只用于宿主管理，原应用DNAT端口已关闭。详见[当前交付](15-network19-delivery.md)与[新网络验收](network19/audit/network19-acceptance.md)。

| 服务 | 当前入口 | 范围 |
| --- | --- | --- |
| PVE | https://192.168.21.22:8006/ | 管理SSH22保留 |
| 虚拟网关190 | WAN192.168.21.23 / LAN192.168.19.1 | 路由、19DNS/DHCP，无NAT |
| Penpot | http://192.168.19.50:9001/ | Git定制版、3设计/973媒体、11服务 |
| Nexus | http://192.168.19.31:8081/ | 原49GAV/234primary内容保持 |
| OMV | http://192.168.19.60/ | 家庭NAS管理 |
| Jellyfin | http://192.168.19.60:8096/ | 媒体库、DirectPlay协议已验 |
| SMB | `smb://192.168.19.60/media`、`/games`、`/incoming` | writer/reader分离，匿名拒绝；使用固定IP连接 |
| Grafana | http://192.168.19.70:3000/ | 真实内网入口，无需旧13000隧道 |
| Prometheus / Alertmanager | 192.168.19.70:9090 / :9093 | 仅批准管理来源，不公开 |
| Java业务 | **停用** | 测试五服务无进程/自启，正式无业务应用 |
| Java验收模板 | PVE VMID9011 `tpl-java-acceptance` | 唯一验收模板，无应用/业务配置/秘密 |

HTTP入口是用户同意的LAN阶段；公网域名/HTTPS/SMTP尚未配置。跨子网的发现广播不作为已验能力，电视/播放器请手动填写19.60。NAS用于文件保存/整理/传输，不承诺主机直接从NAS运行游戏。

| VMID | 角色 | IP |
| --- | --- | --- |
| 100 | cf-tunnel CT | 192.168.19.5 |
| 200 / 201 | 正式MySQL / Redis+Rabbit+Nacos | 192.168.19.10 / .11 |
| 210 | 测试MySQL+Redis+Rabbit+Nacos | 192.168.19.20 |
| 220 / 221 | 发布机 / Nexus | 192.168.19.30 / .31 |
| 230 / 231 / 232 | 正式JDK运行基础，无业务 | 192.168.19.40 / .41 / .42 |
| 240 | 测试JDK基础，五业务已停用 | 192.168.19.45 |
| 250 / 260 / 270 | Penpot / NAS / Ops | 192.168.19.50 / .60 / .70 |

所有19来宾默认GW/DNS为19.1；仅网关WAN使用21.23。OW route为19/24经21.23。旧101/104分别19.101/19.104，保持原停机状态。原核心/旧模板均只接vmbr19；未知clone须先分配IP、登记MAC/IP ACL，不能直接访问正式数据。

SSH使用ub和`~/.ssh/yang_local_rsa`，严格已核host key；受控目标见`evidence/implementation/private-guest-access.json`，代码见`scripts/control.py`。PVE root只用于管理/QGA，不复制客户端私钥，不关闭主机密钥检查。模板克隆按[Java模板说明](network19/java-template/README.md)注入独立hostname与地址。

## 凭据位置
''' + creds + '''
Java合成账号与旧配置仅作受控历史备份，不能据此启动业务。旧Mac Penpot MCP连接不自动改写；服务器新origin为19.50，对应客户端接入需使用新目标身份。

## 发布与应用状态

Publisher目标19.45、来源限制19.30、公钥/强制命令与最小权限保留，但`baseline_migrated=false`，业务发布保持冻结。没有发布新Nacos dataId、激活新release或重启五服务。旧immutable JAR/root600配置保留为私有备份；未来上线必须另立明确业务范围、验证新网配置和回退基线，不能直接回指旧10.63配置。

## 监控与备份边界

12node+5Ops目标全部UP；本机textfile采集业务范围已移除Java五HTTP检查。服务器内部Lark active，172.18内部链与凭据保持；未发送新的验收消息。Mac外部探针继续停用，整机故障无法由机内监控保证外发。

正式业务数据未从开发环境导入。初始OS/应用备份与测试迁移证据保留，Mac只是临时独立副本目的地；长期调度/容量/保留与真实恢复RPO/RTO尚未签。CF归档仅PVE，发布私钥仅220，NAS家庭媒体不作正式业务备份。物理电视/PS主机、4K/HDR/字幕/硬件转码和生产并发仍待实际验收。
'''
p.write_text(access)
readme='''# Dell PowerEdge T630 当前交付

2026-11-06：服务器已调整为 **OW → 网关VM190（21.23/19.1）→ server19**。PVE21.22只承担管理与二层桥，旧NAT/四个10.63桥和宿主三层转发已移除；实际应用直接用19地址访问。

**最新Java范围：不部署或启动任何Java业务程序。测试五服务也已停用，发布入口保持冻结；仅保留一份9011 Java验收模板。** JDK基础节点保留，Linux/Docker核心模板及数据、Penpot/Nexus/NAS/Ops基础服务继续运行。

| 当前入口 | 内容 |
| --- | --- |
| [交付结果与限制](15-network19-delivery.md) | 当前网络、资源、业务范围与验证证据 |
| [访问与日常操作](12-service-access-and-operations.md) | 真实19地址、SSH、凭据位置与操作边界 |
| [Java唯一验收模板](network19/java-template/README.md) | VM9011、JDK21、nonroot、独立身份克隆验收 |
| [当前网络验收](network19/audit/network19-acceptance.md) | ID/前置/步骤/可观察条件/证据/状态 |
| [机器可读规划](plan.json) | 当前14角色55vCPU/117GiB、8GiB宿主预算余量 |
| [当前交接](11-live-handoff.md) | 继续工作前需读的有效范围和源路径 |
| [迁移与修正证据](network19/README.md) | 旧104/CF/QA迁移、网关/ACL/应用与回退历史 |

两个核心模板为Linux9010、Docker9001；Java专用验收模板只有9011，不制作NAS模板。Docker Engine/Compose运行于各角色VM中；Java业务应用当前不运行。模板停止时不占运行内存，VM资源预算不是已验证的业务并发能力。

本机源环境、既有原模板与停止QA均保留；专为Java新建的9012已完成身份/JDK/DHCP验收后删除。CF受保护归档只在PVE，发布私钥只在220，凭据只在目录700/文件600的受控位置。

01–10及14保留原方案/部署基线与历史验收，旧10.63或21.22应用入口不代表当前状态。当前以本页、12、15、plan与network19验收为准；原38项历史验收不等于新网或全部未来项通过。

本地文档检查：`python3 dell/scripts/validate_docs.py --json`。不自动提交Git；harness根不是Git仓库。PVE宿主整机重启、公网原CF源站、真实电视/主机和生产SLO/长期独立备份未冒称完成。
'''
(R/'README.md').write_text(readme)
# Add current-authority banner without overwriting historical evidence or detailed original design.
banner='> 2026-11-06范围更新：网络改用19/24经独立VM190；Java业务全部停用，仅9011验收模板。本文保留原阶段基线，当前地址/状态以[最新交付](15-network19-delivery.md)和[访问入口](12-service-access-and-operations.md)为准。\n\n'
for name in ['01-current-state.md','02-architecture.md','03-templates-and-access.md','04-services-and-migration.md','05-home-nas.md','06-acceptance.md','07-implementation-and-tasks.md','10-resume-after-approval.md','13-phase-scope.md','14-delivery-report.md']:
 p=R/name;s=p.read_text()
 if not s.startswith(banner):p.write_text(banner+s)
print(json.dumps({'status':'active-plan-access-index-synced-current-Java-scope','historical_snapshots_preserved':True,'network19_case_status_owner':'audit agent','NAS_SMB_signoff':'pending-current-exact-allowlist-revalidation'}))
