> 文档状态（2026-11-07）：本页为阶段实施/技术记录，文中“当前”、网段、角色数与通过结果以原执行时点为准。服务器现因UEFI0058内存错误暂停，Nexus合并已授权但未执行；当前配置入口见[访问清单](../../12-service-access-and-operations.md)，恢复门槛见[最新交接](../../11-live-handoff.md)。旧脚本、stage/commit或初始化步骤不得直接重跑。

# network19迁移验收

更新：2026-11-06T18:17:27.272046+08:00。**本期25项全部passed；另1项CF原公网源站保持pending。** 26个既有ID不删除/重编号。本轮只读核收据并更新文档，没有主动探针或host/guest动作。

**Java范围：不部署或启动任何Java业务程序，测试五服务停用，Publisher fenced。交付单个新Java验收基础模板9011；旧五服务E2E仅历史，不再是本期门槛。**

最终身份与host收据、维护解除回执已实际落盘。本期LAN/路由/隔离/基础服务迁移已签收；CF remote ingress原源站未获配置，不宣称公网业务全通。

| ID | 验收项 | 状态 | 范围 |
| --- | --- | --- | --- |
| N19-SCOPE-001 | 最新范围与身份/秘密边界 | passed | 本期25项 |
| N19-INV-001 | 迁移前全量对象及冲突盘点 | passed | 本期25项 |
| N19-GW-001 | 专用190网关与安全配置实际激活 | passed | 本期25项 |
| N19-ROUTE-001 | OW静态路径与PVE客户端路由 | passed | 本期25项 |
| N19-DNS-001 | 19网DNS及普通出网有限正控 | passed | 本期25项 |
| N19-DHCP-001 | LAN DHCP真实DORA与客户端网络 | passed | 本期25项 |
| N19-L2-001 | 独立bridge ACL原生预检与安装 | passed | 本期25项 |
| N19-L2-002 | 管理正控、来宾拒绝及有限WAN负例 | passed | 本期25项 |
| N19-L2-003 | 端口MAC与源IP反欺骗有限raw测试 | passed | 本期25项 |
| N19-L2-004 | 宿主弱主机模型有限L2路径旁证 | passed | 本期25项 |
| N19-L2-005 | 新网MySQL五条依赖正负矩阵 | passed | 本期25项 |
| N19-ID-001 | CloudInit主机密钥保留与230可信身份 | passed | 本期25项 |
| N19-OS-001 | 十二个角色最终OS新网与严格SSH | passed | 本期25项 |
| N19-DATA-001 | 正式/测试基础数据服务恢复 | passed | 本期25项 |
| N19-JAVA-001 | Java业务全部停用与本期门槛收口 | passed | 本期25项 |
| N19-PUB-001 | Publisher受限链迁地址并保持fenced | passed | 本期25项 |
| N19-NEXUS-001 | Nexus新网只读数据/身份/角色与LAN入口 | passed | 本期25项 |
| N19-NAS-001 | NAS新网SMB权限与Jellyfin媒体/身份 | passed | 本期25项 |
| N19-PENPOT-001 | Penpot250迁移与新origin功能验收 | passed | 本期25项 |
| N19-OPS-001 | Ops270完整目标与服务器Lark运行 | passed | 本期25项 |
| N19-CF-001 | CF100新网与隧道注册有限签收 | passed | 本期25项 |
| N19-CF-002 | 原Cloudflare源站/公网业务可达 | pending | CF公网独立未签 |
| N19-DORMANT-001 | 旧101/104与七个停止QA真实OS | passed | 本期25项 |
| N19-TPL-001 | 模板最终NIC/克隆与无业务Java验收模板 | passed | 本期25项 |
| N19-HOST-001 | PVE最终仅管理、旧桥/NAT/forward清理 | passed | 本期25项 |
| N19-FINAL-001 | 新网最终清单与验收收据一致性 | passed | 本期25项 |

## N19-SCOPE-001 — 最新范围与身份/秘密边界

**状态：passed**；本期必需范围。

**前置：** 用户网络重构及最新Java指令已明确。

**步骤：** 读取AGENTS与migration-plan；区分旧五服务E2E历史。 → 确认本轮不部署任何Java业务，Publisher保持fenced；原数据/秘密边界保留。

**可观察通过条件：** 网关21.23/19.1、PVE21.22管理边界明确；Java旧E2E不再是本期门槛。

**现有结果：** 最新范围已纳入本验收集；不引用旧五服务UP作为新目标。

**证据：** [AGENTS.md](/Users/yangzhaohui/work/www/harness/dell/AGENTS.md)（最新Java范围覆盖旧计划）、[migration-plan.json](/Users/yangzhaohui/work/www/harness/dell/network19/migration-plan.json)、[java240-final-hold-evidence.json](/Users/yangzhaohui/work/www/harness/dell/network19/services-core/java240-final-hold-evidence.json)、[publisher240-fenced-readback-evidence.json](/Users/yangzhaohui/work/www/harness/dell/network19/services-core/publisher240-fenced-readback-evidence.json)

## N19-INV-001 — 迁移前全量对象及冲突盘点

**状态：passed**；本期必需范围。

**前置：** 可信PVE只读控制通道。

**步骤：** 按白名单枚举qm/pct、模板/状态、NIC/CloudInit。 → 核旧10421.23冲突、CT100 DHCP及停止QA/模板。

**可观察通过条件：** 初始28对象完整记录，190当时空闲；未输出sshkeys/cipassword/token/args。

**现有结果：** 初始27QEMU+1CT、6模板均覆盖。

**证据：** [current-inventory.json](/Users/yangzhaohui/work/www/harness/dell/network19/audit/current-inventory.json)、[ct-firewall-supplement.json](/Users/yangzhaohui/work/www/harness/dell/network19/audit/ct-firewall-supplement.json)、[inventory.md](/Users/yangzhaohui/work/www/harness/dell/network19/audit/inventory.md)

**限制：** 此为初始时点；后增190/9011与最终对象总数另由最终inventory验收，不能拿28作最终固定数。

## N19-GW-001 — 专用190网关与安全配置实际激活

**状态：passed**；本期必需范围。

**前置：** 190已由主AI创建；旧104已释放21.23。

**步骤：** 核WAN21.23/LAN19.1、按MAC对应接口及严格ubSSH。 → 核专用nft默认拒绝、IPv4 forward、无NAT、DNS绑定LAN、WAN/LAN IPv6关闭而lo保持。

**可观察通过条件：** 双IP/严格SSH及已确认事务成立；路由功能在190；无pending回退事务。

**现有结果：** 实际2vCPU/512MiB、32G thin clone；未缩9010模板盘。

**证据：** [gateway-initial-access.json](/Users/yangzhaohui/work/www/harness/dell/network19/evidence/gateway-initial-access.json)、[active-audit.json](/Users/yangzhaohui/work/www/harness/dell/network19/gateway/active-audit.json)、[live-check.json](/Users/yangzhaohui/work/www/harness/dell/network19/gateway/live-check.json)、[live-confirm.json](/Users/yangzhaohui/work/www/harness/dell/network19/gateway/live-confirm.json)

**限制：** 配置/服务与有限包测试不等于吞吐SLO或DHCP全DORA通过。

## N19-ROUTE-001 — OW静态路径与PVE客户端路由

**状态：passed**；本期必需范围。

**前置：** OW用户静态route19/24via21.23已配置，GW双IP在位。

**步骤：** 核Mac至19.1 ping/TCP22的实际结果。 → 核PVE route get19地址经21.23、源21.22；管理默认网关不作为该测试修改对象。

**可观察通过条件：** Mac能到GW LAN地址，PVE本机管理流量有经21.23路径；无需给vmbr19宿主IP。

**现有结果：** Mac路径与PVE到230/231严格管理正控均实际成功。

**证据：** [OW-route-to-gateway-initial.json](/Users/yangzhaohui/work/www/harness/dell/network19/evidence/OW-route-to-gateway-initial.json)、[host-client-route.json](/Users/yangzhaohui/work/www/harness/dell/network19/evidence/host-client-route.json)、[packet-acceptance.json](/Users/yangzhaohui/work/www/harness/dell/network19/audit/packet-acceptance.json)

**限制：** 该项不证明宿主旧forward/NAT已删除，也不证明host重启持久性。

## N19-DNS-001 — 19网DNS及普通出网有限正控

**状态：passed**；本期必需范围。

**前置：** 190DNS已在计划重启后重新监听；选定无业务canary。

**步骤：** 匿名UDP/TCP DNS核对既定记录。 → 230发送固定.invalid一次DNS正控，读取响应header；核已有重启后deb.debian.org TLS/HTTP200收据。

**可观察通过条件：** DNS返回匹配请求；canary经新网关能正常解析并访问固定公开HTTPS入口。

**现有结果：** 有限raw窗口DNS匹配ID/RCODE3；重启后公开HTTP200。

**证据：** [active-audit.json](/Users/yangzhaohui/work/www/harness/dell/network19/gateway/active-audit.json)、[packet-acceptance.json](/Users/yangzhaohui/work/www/harness/dell/network19/audit/packet-acceptance.json)、[canary230-reboot-readback.json](/Users/yangzhaohui/work/www/harness/dell/network19/evidence/canary230-reboot-readback.json)

**限制：** 不代表全部公网目的地或Cloudflare源站业务可达。

## N19-DHCP-001 — LAN DHCP真实DORA与客户端网络

**状态：passed**；本期必需范围。

**前置：** 主AI另开专用QA；不能改变正式来宾静态地址。

**步骤：** 核主AI专用QA原生抓包阶段与实际lease地址/默认路由/DNS。 → 核新租约地址上的严格ubSSH/HTTPS并核QA结束清理。

**可观察通过条件：** 真实完整LAN DORA，不以dnsmasq --test冒充；yiaddr属于19动态池、GW/DNS均19.1，严格SSH和HTTPS成功。

**现有结果：** 专用QA实际取得19.229/24，DHCP default19.1、DNS19.1；原生被动捕获完整Discover/Offer/Request/ACK；随后严格ubSSH与HTTPS200。

**证据：** [lease-probe-evidence.json](/Users/yangzhaohui/work/www/harness/dell/network19/gateway/lease-probe-evidence.json)（仅同UID lease写权限与dnsmasq --test）、[live-confirm.json](/Users/yangzhaohui/work/www/harness/dell/network19/gateway/live-confirm.json)（DHCP_WAN_negative_packet_test仍pending）、[DHCP-real-QA-native-capture.json](/Users/yangzhaohui/work/www/harness/dell/network19/evidence/DHCP-real-QA-native-capture.json)、[DHCP-QA-strict-SSH-HTTPS.json](/Users/yangzhaohui/work/www/harness/dell/network19/evidence/DHCP-QA-strict-SSH-HTTPS.json)

**限制：** 此项只签真实LAN DHCP；WAN DHCP不应答尚未实包验证，不能用单条WAN TCP负例替代。；pcap保留PVE-only，普通文档只引用脱敏阶段/地址元数据。

## N19-L2-001 — 独立bridge ACL原生预检与安装

**状态：passed**；本期必需范围。

**前置：** PVE FW实际disabled；所有目标采用firewall0直接tap/veth。

**步骤：** 主AI执行本专用bridge表native预检与原子安装。 → 核新ACL在pve-guests前加载，未flush其它规则或开启bridge-nf。

**可观察通过条件：** bridge dell19_acl实际存在，源MAC/IP校验先于ct，startup依赖已配置。

**现有结果：** 原生预检/安装与实际counter读回成立。

**证据：** [bridge-native-syntax-initial.json](/Users/yangzhaohui/work/www/harness/dell/network19/evidence/bridge-native-syntax-initial.json)、[bridge-ACL-applied.json](/Users/yangzhaohui/work/www/harness/dell/network19/evidence/bridge-ACL-applied.json)、[readiness-passive-state.json](/Users/yangzhaohui/work/www/harness/dell/network19/audit/readiness-passive-state.json)

**限制：** 该启动依赖为静态/运行安装证据，不声称PVE宿主重启已实演。后续9011等ACL刷新以各次receipt为准。

## N19-L2-002 — 管理正控、来宾拒绝及有限WAN负例

**状态：passed**；本期必需范围。

**前置：** 230/231新19地址，22/9100真实可用；ACL窗口稳定。

**步骤：** PVE来源连接两guest22/9100并严格SSH230。 → 两guest各测试peer22/9100及host21.22:22/8006，读counter前后。 → 核主AI单个TEST-NET源192.0.2.19的WAN unicast SYN到健康200:3306，真实PVE来源同期正控。

**可观察通过条件：** 四管理正控成功，八负向拒绝且east-west/management-new-session drop有旁证。；该唯一不信任WAN SYN命中网关最终drop精确+1；不泛化其它WAN端口。

**现有结果：** 四正控通过；八negative均拒，两个drop计数分别+8、+8。 主AI另完成1个保留文档地址源WAN SYN，GWfinaldrop精确+1，真实PVE→健康200:3306正控成功。

**证据：** [packet-acceptance.json](/Users/yangzhaohui/work/www/harness/dell/network19/audit/packet-acceptance.json)、[WAN-untrusted-source-negative.json](/Users/yangzhaohui/work/www/harness/dell/network19/evidence/WAN-untrusted-source-negative.json)

**限制：** 仅这些明确端口/来源，不是全网扫描。；WAN只覆盖此1个特定来源/3306负例，其余WAN端口为配置验证；没有冒用真实LAN客户端源IP。

## N19-L2-003 — 端口MAC与源IP反欺骗有限raw测试

**状态：passed**；本期必需范围。

**前置：** 主AI批准3个UDP总预算；190现有DNS为接收端。

**步骤：** 230分别发送1合法DNS、1未登记合成MAC、1错误srcIP19.41的unicastUDP。 → 确认没有ARP/接口改动；对比专用drop计数。

**可观察通过条件：** 合法DNS响应，错MAC与错IP专用drop各+1，UDP总数恰3。

**现有结果：** 3UDP/0ARP，错MAC与源IP各命中1次专用drop。

**证据：** [packet-acceptance.json](/Users/yangzhaohui/work/www/harness/dell/network19/audit/packet-acceptance.json)

**限制：** 未执行ARP广播欺骗、VLAN/IPv6注入或真实角色MAC冒用。

## N19-L2-004 — 宿主弱主机模型有限L2路径旁证

**状态：passed**；本期必需范围。

**前置：** host bridge MAC由只读获取；主AI仅批准1个SYN。

**步骤：** 230用真实MAC/IP、Ether目的PVE vmbr19 MAC、IP目的21.22:22发送1SYN。 → 核无payload与host_input无条件拒绝规则/共享counter变化。

**可观察通过条件：** 1个直达L2测试发送完成，host_input规则已部署且窗口counter增长；不得宣称精确+1独占归因。

**现有结果：** 1SYN/0auth，host_input窗口+10。

**证据：** [packet-acceptance.json](/Users/yangzhaohui/work/www/harness/dell/network19/audit/packet-acceptance.json)

**限制：** 背景广播导致计数非独占；本项签有限路径/规则旁证，不冒称捕获了该单包的独占trace或穷举所有旁路。

## N19-L2-005 — 新网MySQL五条依赖正负矩阵

**状态：passed**；本期必需范围。

**前置：** 20019.10与21019.20独立核监听3306且healthy。

**步骤：** 230→prod通/test拒；240→test通/prod拒；NAS260→prod拒。 → 只socket短连接立即close；读取角色allow与east-west drop增量。

**可观察通过条件：** 两授权连接成功，三非授权timeout，目标不是closed；无握手读取/认证/SQL。

**现有结果：** 5/5通过，allow+2、drop+6（含重传）。

**证据：** [data-tcp-matrix.json](/Users/yangzhaohui/work/www/harness/dell/network19/audit/data-tcp-matrix.json)

**限制：** 本轮限定3306五条，不把旧10.63的30例矩阵冒充新网全端口已复测。

## N19-ID-001 — CloudInit主机密钥保留与230可信身份

**状态：passed**；本期必需范围。

**前置：** 主AI提供PVE内旧profile备份；不导出完整profile/私钥。

**步骤：** 13个已部署VM实际snippet与旧profile在RAM逐字节比。 → 读取两核心模板实际cicustom布尔；QGA核230原machine-id/MAC与新IP/key记录。

**可观察通过条件：** 13/13仅ssh_deletekeys true→false，模板实际仍true；230身份匹配并承认一次已核验rotation。

**现有结果：** 13单行修改已独立核验，machine-id原值三处历史与当前一致。

**证据：** [hostkey-profile-independent-verification.json](/Users/yangzhaohui/work/www/harness/dell/network19/audit/hostkey-profile-independent-verification.json)、[template-hostkey-flags.json](/Users/yangzhaohui/work/www/harness/dell/network19/audit/template-hostkey-flags.json)、[cloud-init-hostkey-preservation.json](/Users/yangzhaohui/work/www/harness/dell/network19/evidence/cloud-init-hostkey-preservation.json)、[host-key-rotations.json](/Users/yangzhaohui/work/www/harness/dell/evidence/implementation/host-key-rotations.json)

**限制：** generated cloudinit dump不作为custom snippet证明；不声称所有13VM都已在新网重启。

## N19-OS-001 — 十二个角色最终OS新网与严格SSH

**状态：passed**；本期必需范围。

**前置：** 主AI已完成所有十二角色OS迁移，NAS使用官方OMV流程。

**步骤：** 核最终12角色逐台ub严格SSH/hostname/唯一19地址/24/default/DNS19.1。 → 核232在模板维护后恢复，原停止QA单独验收。

**可观察通过条件：** 十二角色新网身份读回全passed；不以OS网络成功冒充Java业务运行。

**现有结果：** final-live-network-identity中12角色均exit0/strict ub/19地址/default与DNS19.1；232已在模板维护后恢复19.42与9100。

**证据：** [OS-200-apply.json](/Users/yangzhaohui/work/www/harness/dell/network19/evidence/OS-200-apply.json)、[OS-201-apply.json](/Users/yangzhaohui/work/www/harness/dell/network19/evidence/OS-201-apply.json)、[OS-210-apply.json](/Users/yangzhaohui/work/www/harness/dell/network19/evidence/OS-210-apply.json)、[OS-220-apply.json](/Users/yangzhaohui/work/www/harness/dell/network19/evidence/OS-220-apply.json)、[OS-221-apply.json](/Users/yangzhaohui/work/www/harness/dell/network19/evidence/OS-221-apply.json)、[OS-231-apply.json](/Users/yangzhaohui/work/www/harness/dell/network19/evidence/OS-231-apply.json)、[OS-232-apply.json](/Users/yangzhaohui/work/www/harness/dell/network19/evidence/OS-232-apply.json)、[OS-240-apply.json](/Users/yangzhaohui/work/www/harness/dell/network19/evidence/OS-240-apply.json)、[canary230-reboot-readback.json](/Users/yangzhaohui/work/www/harness/dell/network19/evidence/canary230-reboot-readback.json)、[NAS-OS-apply.json](/Users/yangzhaohui/work/www/harness/dell/network19/evidence/NAS-OS-apply.json)、[final-live-network-identity.json](/Users/yangzhaohui/work/www/harness/dell/network19/evidence/final-live-network-identity.json)、[232-restored-post-template.json](/Users/yangzhaohui/work/www/harness/dell/network19/evidence/232-restored-post-template.json)

**限制：** 宿主重启未实演；Java业务保持停用。

## N19-DATA-001 — 正式/测试基础数据服务恢复

**状态：passed**；本期必需范围。

**前置：** 对应来宾OS已新网；磁盘/身份保持。

**步骤：** 核200/201/210 commit-start收据。 → 核新服务端点、1/3/4容器healthy及持久MySQL server身份；核201→200新源连接。

**可观察通过条件：** 8个基础容器healthy；新端点；namespace/vhost/秘密未因改网轮换或重建。

**现有结果：** 正式MySQL1、正式infra3、测试data4健康；201→200新19源实际匹配。

**证据：** [role200-commit-start-evidence.json](/Users/yangzhaohui/work/www/harness/dell/network19/services-core/role200-commit-start-evidence.json)、[role201-commit-start-evidence.json](/Users/yangzhaohui/work/www/harness/dell/network19/services-core/role201-commit-start-evidence.json)、[role210-commit-start-evidence.json](/Users/yangzhaohui/work/www/harness/dell/network19/services-core/role210-commit-start-evidence.json)、[data201-to200-identity-evidence.json](/Users/yangzhaohui/work/www/harness/dell/network19/services-core/data201-to200-identity-evidence.json)

**限制：** 不宣称源业务全量迁移/全量脱敏，亦不要求启动Java业务。

## N19-JAVA-001 — Java业务全部停用与本期门槛收口

**状态：passed**；本期必需范围。

**前置：** 最新用户要求不部署/启动任何Java业务；旧制品私有保留。

**步骤：** 核240五unit inactive/MainPID0/非enabled/cgroup空与监控仅base三项。 → 核网络/监控迁移没有重新启业务，旧五服务E2E标历史不再门槛。

**可观察通过条件：** 测试五服务不运行，正式Java继续不启动业务；新模板仅运行基础。

**现有结果：** 五unitinactive、MainPID0、enablementnot-found，base3/HTTP0。

**证据：** [AGENTS.md](/Users/yangzhaohui/work/www/harness/dell/AGENTS.md)、[java240-final-hold-evidence.json](/Users/yangzhaohui/work/www/harness/dell/network19/services-core/java240-final-hold-evidence.json)、[monitoring240-window-evidence.json](/Users/yangzhaohui/work/www/harness/dell/network19/services-core/monitoring240-window-evidence.json)

**限制：** 旧E2E通过仍为历史事实，但不作为本期恢复程序或业务UP要求；验收模板完整交付另pending。

## N19-PUB-001 — Publisher受限链迁地址并保持fenced

**状态：passed**；本期必需范围。

**前置：** 主AI不开放业务发布窗口。

**步骤：** 核220/240已安装公开代码目标/来源更新与native sshd/visudo通过。 → 核baselinefalse/fenced，未发业务部署请求、未变私钥/授权材料。

**可观察通过条件：** 发布器不能在无新批准baseline时部署业务；key不复制、不放宽sudo/SSH。

**现有结果：** 双方fenced/readback成立，业务请求0。

**证据：** [publisher220-fenced-evidence.json](/Users/yangzhaohui/work/www/harness/dell/network19/services-core/publisher220-fenced-evidence.json)、[publisher240-fenced-readback-evidence.json](/Users/yangzhaohui/work/www/harness/dell/network19/services-core/publisher240-fenced-readback-evidence.json)

## N19-NEXUS-001 — Nexus新网只读数据/身份/角色与LAN入口

**状态：passed**；本期必需范围。

**前置：** 221 OS完成；保留新目标独立身份和数据。

**步骤：** 核新origin与MacLAN HTTP200、两容器healthy。 → 核新网GET-only复验49组件、234主文件、35metadata语义、1076校验文件及GAV集一致。 → 核reader/publisher读取、匿名401、原权限/身份字节不变；不发新增写请求。

**可观察通过条件：** 新网数据/metadata/身份读取一致，原角色范围保留，未走proxy上游或新增写入。

**现有结果：** 新网GET-only复验通过：49components、234primary SHA、35metadata语义、1076checksums；身份/数据UUID保持，两容器healthy，Mac入口200。

**证据：** [nexus-commit-start-result.json](/Users/yangzhaohui/work/www/harness/dell/network19/services-media/nexus-commit-start-result.json)、[Mac-new-services-initial.json](/Users/yangzhaohui/work/www/harness/dell/network19/evidence/Mac-new-services-initial.json)、[nexus-post-cutover-verification.json](/Users/yangzhaohui/work/www/harness/dell/network19/services-media/nexus-post-cutover-verification.json)、[Mac-final-management-and-services.json](/Users/yangzhaohui/work/www/harness/dell/network19/evidence/Mac-final-management-and-services.json)

**限制：** 本轮GET-only；legacy/formal写删拒绝来自不变角色校验，没有重新发送负向写请求或真实publish。

## N19-NAS-001 — NAS新网SMB权限与Jellyfin媒体/身份

**状态：passed**；本期必需范围。

**前置：** OMV网络所有者流程完成，文件系统UUID未改变。

**步骤：** 核OMV OS、新19.60/public URI与原卷UUID。 → 核三SMB share专用nonce读SHA、reader四类写操作拒绝、writer操作、匿名拒绝。 → 核原Jellyfin管理员/viewer、原媒体库及静态DirectPlay流SHA，保持无转码/无新库。

**可观察通过条件：** SMB权限/原fixture SHA保持，Jellyfin原身份/媒体API验证通过，原真实媒体无修改。

**现有结果：** 三share权限与SHA复验passed；Jellyfin原admin/viewer登录、DirectPlay能力/原静态流SHA验证通过，秘密/原媒体未改；MacOMV/Jellyfin200。

**证据：** [NAS-OS-apply.json](/Users/yangzhaohui/work/www/harness/dell/network19/evidence/NAS-OS-apply.json)、[nas-commit-start-result.json](/Users/yangzhaohui/work/www/harness/dell/network19/services-media/nas-commit-start-result.json)、[Mac-new-services-initial.json](/Users/yangzhaohui/work/www/harness/dell/network19/evidence/Mac-new-services-initial.json)、[nas-smb-post-cutover-verification.json](/Users/yangzhaohui/work/www/harness/dell/network19/services-media/nas-smb-post-cutover-verification.json)、[nas-jellyfin-post-cutover-verification.json](/Users/yangzhaohui/work/www/harness/dell/network19/services-media/nas-jellyfin-post-cutover-verification.json)、[Mac-final-management-and-services.json](/Users/yangzhaohui/work/www/harness/dell/network19/evidence/Mac-final-management-and-services.json)

**限制：** 仅原生客户端/API/静态流验证，不宣称实体TV/PS设备实播、转码性能或主机直接运行游戏。；NAS是家庭媒体/游戏文件共享，不是正式独立故障域备份。

## N19-PENPOT-001 — Penpot250迁移与新origin功能验收

**状态：passed**；本期必需范围。

**前置：** owner完成静默/OS/运行配置迁移；保持数据/独立秘密。

**步骤：** 核新OS/19.50 origin与11容器healthy。 → 核原设计/media/Git/身份保持及新网只读MCP认证与匿名拒绝。 → 核既有async任务已完成且未重试/重复导入，Mac入口200。

**可观察通过条件：** 原设计/资产/身份完整，新origin与DNS正确，必需只读功能验证通过。

**现有结果：** 19.50新origin/DNS19.1生效，11容器healthy；3原design数据/revn统计、973asset路径与SHA、GitHEAD/clean及新身份映射不变；只读MCP认证上下文与匿名拒绝、既有async completed验证通过。

**证据：** [OS-250-stage.json](/Users/yangzhaohui/work/www/harness/dell/network19/evidence/OS-250-stage.json)（阶段准备历史；本项passed依据另列最终commit/readback/clone收据。）、[standby-stage-result.json](/Users/yangzhaohui/work/www/harness/dell/network19/services-media/standby-stage-result.json)（阶段准备历史；本项passed依据另列最终commit/readback/clone收据。）、[penpot-post-cutover-verification.json](/Users/yangzhaohui/work/www/harness/dell/network19/services-media/penpot-post-cutover-verification.json)、[final-live-network-identity.json](/Users/yangzhaohui/work/www/harness/dell/network19/evidence/final-live-network-identity.json)、[Mac-final-management-and-services.json](/Users/yangzhaohui/work/www/harness/dell/network19/evidence/Mac-final-management-and-services.json)

**限制：** 本轮无设计写入、无重复import/retry或Git变更；不宣称重新运行所有编辑功能。

## N19-OPS-001 — Ops270完整目标与服务器Lark运行

**状态：passed**；本期必需范围。

**前置：** Ops OS/配置与当前监控目录已迁新网，Java业务检查已停用。

**步骤：** 核最终精确12node与Ops自有5目标全UP、Grafana及PVE QGA freshness。 → 核Lark原生unit/固定策略；核解除本site限时silence与Macprobe仍disabled。

**可观察通过条件：** 17/17目标与freshness成立，Java仅base，服务器Lark运行及维护收口正确。

**现有结果：** 精确12node目标与Ops自身5目标共17/17UP，Grafana数据库OK、PVE QGA指标55.9s新鲜；Java240仅base3/HTTP0；Lark原生unitactive/NRestarts0/固定172策略，site静默已解除，Macprobe仍disabled。

**证据：** [OS-270-stage.json](/Users/yangzhaohui/work/www/harness/dell/network19/evidence/OS-270-stage.json)、[stage270-evidence.json](/Users/yangzhaohui/work/www/harness/dell/network19/services-core/stage270-evidence.json)（阶段准备历史；本项passed依据另列最终commit/readback/clone收据。）、[maintenance-silence.json](/Users/yangzhaohui/work/www/harness/dell/network19/evidence/maintenance-silence.json)、[ops270-new-network-allup-readback.json](/Users/yangzhaohui/work/www/harness/dell/network19/services-core/ops270-new-network-allup-readback.json)、[final-live-network-identity.json](/Users/yangzhaohui/work/www/harness/dell/network19/evidence/final-live-network-identity.json)、[Mac-final-management-and-services.json](/Users/yangzhaohui/work/www/harness/dell/network19/evidence/Mac-final-management-and-services.json)、[maintenance-ended.json](/Users/yangzhaohui/work/www/harness/dell/network19/evidence/maintenance-ended.json)

**限制：** 迁网后未新发送Lark测试通知或重测vendor连通性；本项签运行/配置与维护状态，不凭active虚报新code0。；先前232维护造成11/12快照保留为历史，后续allup收据覆盖当前状态，不删除失败历史。

## N19-CF-001 — CF100新网与隧道注册有限签收

**状态：passed**；本期必需范围。

**前置：** 原含秘密备份仅PVE，user允许网络迁移；token不读取/导出。

**步骤：** 核CT19.5/default19.1、cloudflared active及最近registered事件。 → 保留hot失败与受控container restart事实，核服务原字节不变。

**可观察通过条件：** 新网及至少一次注册确认成立；不宣称原PID不变或源站全通。

**现有结果：** CT19.5/default19.1、cloudflaredactive与注册事件成立；最终root读取本地readyHTTP200/readyConnections2。hot失败与受控CT重启均保留，token/原服务字节不导出/不改。

**证据：** [CF-network-move.json](/Users/yangzhaohui/work/www/harness/dell/network19/evidence/CF-network-move.json)、[CF-post-fakeIP-check.json](/Users/yangzhaohui/work/www/harness/dell/network19/evidence/CF-post-fakeIP-check.json)、[final-live-network-identity.json](/Users/yangzhaohui/work/www/harness/dell/network19/evidence/final-live-network-identity.json)

**限制：** 只签CT新网、服务/注册及本地ready2连接；未知remote ingress源站与公网业务端到端仍独立pending。；早期7844socket计数0不作为最终连接判据，亦不冒称原PID全程不变。

## N19-CF-002 — 原Cloudflare源站/公网业务可达

**状态：pending**；CF公网原源站独立未签范围。

**前置：** 需要可靠remote ingress配置或受控已知业务入口；禁止输出token。

**步骤：** 主AI获得可靠origin集合后脱敏核每个scheme/host/port。 → 按明确域名/源站做授权端到端验证，不能猜测新域名。

**可观察通过条件：** 配置与新地址一致且对应业务真实可达，不能仅注册成功。

**现有结果：** retained日志没有remote config更新，origin集合未知；本期不虚报公网业务全通。

**证据：** [CF-origin-metadata.json](/Users/yangzhaohui/work/www/harness/dell/network19/evidence/CF-origin-metadata.json)、[CF-origin-after-restart-metadata.json](/Users/yangzhaohui/work/www/harness/dell/network19/evidence/CF-origin-after-restart-metadata.json)

## N19-DORMANT-001 — 旧101/104与七个停止QA真实OS

**状态：passed**；本期必需范围。

**前置：** 维护预算由主AI控制；测试后正常关闭。

**步骤：** 读取101/104实际boot网络/严格SSH及最终stopped收据。 → 核七QA逐个boot实测新19唯一IP/default19.1后正常shutdown。

**可观察通过条件：** 不是只看CI元数据；各实际OS新网与最终stop状态成立。

**现有结果：** 101/104与七QA实际新IP/default已证实、全部回stopped。

**证据：** [legacy101-real-OS.json](/Users/yangzhaohui/work/www/harness/dell/network19/evidence/legacy101-real-OS.json)、[legacy104-real-OS.json](/Users/yangzhaohui/work/www/harness/dell/network19/evidence/legacy104-real-OS.json)、[dormant-QA-real-OS.json](/Users/yangzhaohui/work/www/harness/dell/network19/evidence/dormant-QA-real-OS.json)

## N19-TPL-001 — 模板最终NIC/克隆与无业务Java验收模板

**状态：passed**；本期必需范围。

**前置：** 最终VMID/版本由主AI登记；不复制业务配置/秘密或客户端私钥。

**步骤：** 核原模板NIC19/firewall0与单个新Java验收模板9011 sealed状态。 → 核9012新hostname、独立machine-id/hostkey、JDK21/java用户非root临时编译验收与无业务/parked exporter。 → 核实际DHCP/SSH/HTTPS及QA9012清理、232恢复。

**可观察通过条件：** 可克隆的新Java验收基础模板成立，不携带业务artifacts/配置/凭据，不启动业务；临时QA已关闭清理。

**现有结果：** 单个新交付Java验收模板9011已sealed-stopped，专用9012clone身份与JDK清洁度/非root临时编译运行通过；无业务artifacts/unit/listener、exporter parked；真实DHCP与严格SSH/HTTPS通过；9012结束删除、原模板/QA保留，232恢复运行。

**证据：** [dormant-direct-vnic-ACL.json](/Users/yangzhaohui/work/www/harness/dell/network19/evidence/dormant-direct-vnic-ACL.json)、[java-template-created-stopped.json](/Users/yangzhaohui/work/www/harness/dell/network19/evidence/java-template-created-stopped.json)（阶段准备历史；本项passed依据另列最终commit/readback/clone收据。）、[hostkey-profile-independent-verification.json](/Users/yangzhaohui/work/www/harness/dell/network19/audit/hostkey-profile-independent-verification.json)、[seal-and-clone.json](/Users/yangzhaohui/work/www/harness/dell/network19/java-template/seal-and-clone.json)、[clone-evidence.json](/Users/yangzhaohui/work/www/harness/dell/network19/java-template/clone-evidence.json)、[QA-closeout.json](/Users/yangzhaohui/work/www/harness/dell/network19/java-template/QA-closeout.json)、[DHCP-real-QA-native-capture.json](/Users/yangzhaohui/work/www/harness/dell/network19/evidence/DHCP-real-QA-native-capture.json)、[DHCP-QA-strict-SSH-HTTPS.json](/Users/yangzhaohui/work/www/harness/dell/network19/evidence/DHCP-QA-strict-SSH-HTTPS.json)、[232-restored-post-template.json](/Users/yangzhaohui/work/www/harness/dell/network19/evidence/232-restored-post-template.json)、[final-live-network-identity.json](/Users/yangzhaohui/work/www/harness/dell/network19/evidence/final-live-network-identity.json)

**限制：** 旧原始模板保留为历史，不作为新增第二份Java验收交付；新模板的监控默认parked，不能声称clone后已自动对网开放9100。

## N19-HOST-001 — PVE最终仅管理、旧桥/NAT/forward清理

**状态：passed**；本期必需范围。

**前置：** 全部需迁角色/隔离/基础服务已验，救援与备份可靠。

**步骤：** 接收主AI最终hostcleanup收据；按final-host-cleanup-checklist只读核地址/全表路由/旧loader/nft/sysctl。 → 核PVE21.22/22/8006保留、vmbr19无IPv4/IPv6、19客户端route经21.23；旧10.63桥/NAT/hostforward不再生效。 → 精确验证旧PVE应用入口不再DNAT；保留bridge ACL与GW转发。

**可观察通过条件：** 所有旧host路由器职责退出，持久设置正确，不能把临时hostforward1阶段算完成。

**现有结果：** 主AI17:51收据phasecomplete：31对象前置核验后四旧桥/旧NAT_filter消失，hostIPv4及all/default/所有接口IPv4IPv6forward0，旧loader masked，vmbr19无host地址，19客户端route经21.23；随后Mac22/8006通、旧7入口关闭、新5基础服务200。

**证据：** [final-host-cleanup-checklist.md](/Users/yangzhaohui/work/www/harness/dell/network19/audit/final-host-cleanup-checklist.md)、[readiness-passive-state.json](/Users/yangzhaohui/work/www/harness/dell/network19/audit/readiness-passive-state.json)、[host-management-only-retirement.json](/Users/yangzhaohui/work/www/harness/dell/network19/evidence/host-management-only-retirement.json)、[Mac-final-management-and-services.json](/Users/yangzhaohui/work/www/harness/dell/network19/evidence/Mac-final-management-and-services.json)、[final-live-network-identity.json](/Users/yangzhaohui/work/www/harness/dell/network19/evidence/final-live-network-identity.json)

**限制：** 未执行PVE宿主重启/断电；持久配置/启动依赖及当前状态已核，不能标hostreboot/RPO_RTO实演通过。；31为清理时包含临时9012的对象数；最终9012已删除，不能固定为最终总数。

## N19-FINAL-001 — 新网最终清单与验收收据一致性

**状态：passed**；本期必需范围。

**前置：** 主AI最终live身份/host状态及maintenance解除两份收据均已落盘、为肯定结果。

**步骤：** 核最终12角色严格SSH及14永久运行/7模板/QA清理，与主AIplan/access一致。 → 合并host全NIC硬前置、原始/停止QA真实OS与新模板clone收据。 → 核维护解除与17目标UP；保留CF公网origin独立未签及所有非实演限制。

**可观察通过条件：** 本期25项必需验收均passed；源站公网未知不冒称；Java业务全部停用、Publisherfenced，Macprobe不恢复。

**现有结果：** 最终root收据18:09确认12角色严格ub/new19/default/DNS、14永久实例运行、7模板含9011、9012不存在，host管理/L2边界成立；18:11本site维护silence解除、17目标UP，Mac外部probe仍停用。active plan/access已由主AI同步新19与单个新Java验收模板。

**证据：** [migration-plan.json](/Users/yangzhaohui/work/www/harness/dell/network19/migration-plan.json)、[final-live-network-identity.json](/Users/yangzhaohui/work/www/harness/dell/network19/evidence/final-live-network-identity.json)、[maintenance-ended.json](/Users/yangzhaohui/work/www/harness/dell/network19/evidence/maintenance-ended.json)、[host-management-only-retirement.json](/Users/yangzhaohui/work/www/harness/dell/network19/evidence/host-management-only-retirement.json)、[Mac-final-management-and-services.json](/Users/yangzhaohui/work/www/harness/dell/network19/evidence/Mac-final-management-and-services.json)、[QA-closeout.json](/Users/yangzhaohui/work/www/harness/dell/network19/java-template/QA-closeout.json)

**限制：** 此为当前网络迁移与无Java业务基础范围收口，不能扩展为PVEhost重启/灾备或CF未知源站公网业务全通。

## 收口边界

本期25项均有实际收据，CF原公网源站独立pending不藏进通过结论。LAN DHCP有真实完整DORA；WAN仅1个明确SYN负例，WAN DHCP反向与其它端口不能泛化。host未重启、未断电，未作RPO/RTO灾备承诺。所有Java业务继续停用，不以旧E2E诱导重新部署。进一步扩大范围需新目标/证据，不能改写本期历史。
