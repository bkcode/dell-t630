# T630 当前状态、恢复验收与操作边界

更新：2026-11-09（Asia/Shanghai）。**当前继续完成基础搭建，不迁移数据、不合并Nexus、不启动Java业务。** 14:24:03自然重启后，[本轮PVE审计](completion/20261109/pve-audit.json)确认12来宾运行、3模板停止、EDAC计数0与RAID Optimal，上一轮forward guard实际跨重启保持全0；[Ops审计](completion/20261109/ops-audit.json)15/15 targets UP。用户已确认此前内存重新插拔/更换并诊断通过，这与助手本轮只读观察分别记录。[首轮11项备份已完整验证](completion/20261109/backup-first-success.json)，原生任务OK/退出0；[每日计划已启用](completion/20261109/backup-schedule-enabled.json)，按03:30和3/7/4策略运行。本文只同步本地证据，不发起远程动作。

## 1. 时间线和证据层级

| 时间（+08:00） | 已记录事实 | 如何使用 |
| --- | --- | --- |
| 2026-11-07 02:35:01 | 清理后的独立验收通过：12运行角色、3停止模板，15监控目标UP、0活动告警及主要HTTP入口200 | [故障前完整验收](cleanup/final-live-check.json)，保留作历史基线 |
| 2026-11-07 02:44:29 | 最后成功PVE plan同步 | [同步记录](cleanup/PVE-plan-synced.json)，不代表09:32以后仍正常 |
| 2026-11-07 09:32起 | PVE管理网络不可达，随后用户暂停工作 | 当时运行态未知，现已由11月8日新鲜检查更新；不改写原失败证据 |
| 2026-11-07 10:23记录 | 用户控制台截图UEFI0058，正常OS启动前停住；截图本身未标出具体DIMM | [B1事故记录](cleanup/hardware/DIMM_B1-incident.json)，结合历史SEL安排离线硬件评估 |
| 2026-11-08 用户确认 | 内存已重新插拔/更换并诊断通过；要求恢复检查与补齐清理，暂不迁移 | 物理处理及诊断结论来自用户；本轮EDAC0/RAIDOptl是当前boot读数 |
| 2026-11-08 20:16:13–20:18:22 | 200/201/210/230/240严格SSH、网络与基础检查通过；数据8容器healthy，Java无业务进程 | [核心审计](recovery/20261108/core-services-audit.json)，不包含DB认证、业务内容或备份恢复重测 |
| 2026-11-08 20:19:38–20:20:48 | 12来宾启动完成；15/15 UP、0告警；主要6入口200；各接口forward恢复0 | [08恢复审计](recovery/20261108/ops-audit.json)、[08后检](recovery/20261108/host-network-postcheck.json)，保留上轮时点 |
| 2026-11-09 14:24:03开机、14:42–14:44审计 | 12running/3tpl停止、15UP，EDAC0、两VD Optl；guard SHA与networking→bridge/ExecStartPost→pve-guests顺序保持，各接口forward0 | [PVE](completion/20261109/pve-audit.json)、[核心](completion/20261109/core-audit.json)、[媒体](completion/20261109/media-audit.json)、[Ops](completion/20261109/ops-audit.json)，新鲜基础范围，不是业务恢复全验 |
| 2026-11-09 14:45:56 | 空闲iperf3 server已stop/disable，工具包保留，5201关闭 | [清理回执](completion/20261109/idle-iperf-disabled.json)，无应用/来宾重启 |
| 2026-11-09 15:54:56完成，15:56:02收据 | 固定11项全部zstd/native verified、原生任务OK/退出0，共19,747,582,801 bytes；03:30计划已enabled | [首轮成功](completion/20261109/backup-first-success.json)、[计划启用](completion/20261109/backup-schedule-enabled.json)；不等于恢复通过或异机灾备 |

[plan.json](plan.json)是保留角色、地址和配置预算的机器可读来源；deployment_status不代替带时间的现场健康证据。[机器目录](machines/README.md)保存逐机合同与公开来源索引，不是实时配置导出。历史事故与本轮恢复证据边界见[硬件发现](08-hardware-findings.md)，日常检查见[操作手册](19-manual-operations.md)。

## 2. 本轮恢复后保留角色

已设计的合并目标仍是一台VM220 `publish-service`承担发布与Nexus，6vCPU/8GiB、主IP19.30+服务alias19.31，目标11实例/14监控目标，详见[17目标合同](17-publish-artifact-consolidation.md)。**用户11月8日明确暂不迁移；该目标本轮不实施，221保持独立，不退役、不移盘、不加alias。**

以下12角色为保留的11个VM和1个LXC；[11月9日PVE审计](completion/20261109/pve-audit.json)再次观察到全部运行。运行不等于所有业务/数据已重新验收，各服务范围见下节。

| ID | 角色 | 地址 | vCPU / GiB | 已交付职责与边界 |
| --- | --- | --- | ---: | --- |
| 100 | cf-tunnel，LXC | 19.5 | 1 / 0.5 | cloudflared；token留原位，备份仅PVE；account-side origin全链路仍另验 |
| 190 | network-gateway | WAN21.23、LAN19.1 | 2 / 0.5 | 19↔21/公网路由、LAN DNS/DHCP、无NAT、防火墙、先于其它来宾启动 |
| 200 | data-prod-db | 19.10 | 6 / 16 | MySQL正式基础，业务schema保持空，不导入Mac真实业务数据 |
| 201 | data-prod-infra | 19.11 | 4 / 8 | 正式Nacos/Redis/RabbitMQ，外部MySQL元库、独立身份与权限 |
| 210 | data-test | 19.20 | 2 / 4 | 独立测试MySQL/Nacos/Redis/RabbitMQ及最小测试schema |
| 220 | publish-service | 19.30 | 4 / 4 | 构建/受限发布基础；当前业务发布fenced；Nexus合并仅准备 |
| 221 | artifact-service | 19.31 | 2 / 4 | 当前Nexus来源节点，49 GAV/234主制品SHA核对；尚未迁入220 |
| 230 | java-prod-01 | 19.40 | 6 / 16 | 正式Java运行基础，无Java业务程序 |
| 240 | java-test-01 | 19.45 | 4 / 8 | 测试Java运行基础，旧五服务已停用，不部署业务程序 |
| 250 | penpot-service | 19.50 | 6 / 16 | 定制Penpot全套、3份设计/973媒体与MCP验收 |
| 260 | nas-media | 19.60 | 4 / 4 | OMV、SMB三共享及Jellyfin家庭媒体；不作为正式业务备份目标 |
| 270 | ops-service | 19.70 | 2 / 4 | Prometheus/Grafana/Alertmanager/Blackbox及服务器内Lark |
| **合计** | **12角色** | 均为192.168.* | **43 / 85** | 配置预算，非负载或吞吐承诺 |

三份保留停止模板是`9001 tpl-docker-base`、`9010 tpl-linux-base`、`9011 tpl-java-acceptance`。旧模板102/103/105/106、重复Java231/232、旧101/104和已完成QA/临时builder均在受保护备份后清理；完整ID和备份入口见[清理结果](18-cleanup-and-consolidation.md)。不能再按原14角色、三台prod Java或旧模板清单执行部署。

## 3. 本轮恢复观察与历史功能验收

- 数据组件：[11月9日核心审计](completion/20261109/core-audit.json)再次核200/201/210数据UUID/rw挂载、监督单元、8容器running/healthy/RestartCount0；认证、namespace/vhost隔离及fixture持久化是原验收，未重做。正式业务schema空、测试独立为保留合同，本轮未读库内容。Nacos/Nexus/Penpot可能使用JVM，不属于“Java业务程序”。230/240本轮JDK21.0.13可执行、Java进程0、旧五业务unit未加载/未启用。
- 工具：[11月9日媒体工具审计](completion/20261109/media-audit.json)核221两容器、250十一容器健康且原镜像IDs保持；Nexus/定制Penpot匿名健康GET200。原设计/媒体/MCP、制品SHA/身份验收保留，本轮未重新读取这些内容。Penpot实际仍为历史ff1783e clean，本轮没有更新到main；ff/main目标与实际版本分别记录。220仍4CPU/4GiB、只有30、Nexus待机未启动；发布业务继续fenced。
- 家庭：本轮媒体审计再次核260原2TiB盘UUID/ext4、OMV/SMB/Jellyfin及Jellyfin容器健康，原健康GET通过。SMB权限与样本stat已在11月8日观察；未读内容、认证写共享或播放。真实电视/主机、多路转码与混合负载仍待人工验收。
- 网络：本轮190双地址/路由与网关单元正常；[直接LAN DNS/CF复核](recovery/20261108/network-CF-followup.json)确认19.1 UDP/TCP三静态A正确、CF实际20241 ready200/连接2，公网account-side origin未验。11月8日forward漂移由主AI补3个owned文件；11月9日14:24开机后的SHA、执行顺序及全forward0读回已实际验证该guard跨重启保持，不再只是静态候选。原桥/路由/ACL和无NAT边界保持，见[本轮PVE审计](completion/20261109/pve-audit.json)。同19网仍由bridge MAC/IP/role ACL隔离。
- 远程：用户已明确授权`10.66.66.0/24`访问整个19网及网关两个本机IPv4地址，服务认证不变；最终远程验证入口见[网络交付](15-network19-delivery.md)。
- 监控：[11月9日Ops审计](completion/20261109/ops-audit.json)十个guest node加五个Ops目标15/15 UP、无活动告警，内部Lark unit active；未重发外部验收消息，进程active不代表本boot重验送达。整台T630无法运行时不依赖同机发失联通知。用户明确不需要Mac外部探针，已从现行方案和后续待办移除，仅保留历史记录。
- fish：9个Linux来宾及3模板仅安装4.0.2，root/ub默认仍Bash；CF100、Penpot250、Ops270排除，PVE未安装或改shell。

## 4. 管理、网络与存储基线

PVE管理地址`192.168.21.22`，BMC/iDRAC记录地址`192.168.21.21`；GW190管理WAN为21.23。PVE的vmbr19无宿主IP，host IPv4/IPv6转发为0，无宿主NAT，旧四个10.63桥和应用DNAT已退出；主机自身到19的客户端路由经21.23。19网来宾网关/DNS为19.1，公网出口NAT由OW21.1负责。

硬件已识别为双E5-2680 v4，28物理核心/56线程；观察内存约125.78GiB，规划预算保守125GiB。85GiB来宾配置约留40GiB给主机/余量，最低保留8GiB，不能以配置空闲推导当前DIMM健康或容量SLO。

H730暴露SSD RAID1和HDD RAID5，PVE管理`local/local-lvm/store`；主AI本轮只读报告RAID Optimal，各应用审计核其分配挂载UUID。当前控制器状态不等于逐文件/数据库一致性证明。NAS只管理专用虚拟盘，不能再挂载PVE的sdb/store或直通承载宿主存储的整卡。

## 5. PVE本机自动备份：首轮验证完成、每日计划已启用

用户选择先建本机恢复点，策略入口为[PVE本机自动备份](infra/backup/pve-local/README.md)与[policy](infra/backup/pve-local/policy.json)。固定100/190/200/201/210/221/230/240/250/260/270共11项，220始终排除；CF100仅PVE保存，归档/日志root600、目录root700，原21档不纳入新namespace保留策略。每日03:30，最近3份＋每日7点＋每周4点按PVE原生组合执行。

**首轮11项全部完成zstd/native完整性检查，原生任务status=OK、unit退出0，计划已启用。** [首轮回执](completion/20261109/backup-first-success.json)记录归档总19,747,582,801 bytes；[计划回执](completion/20261109/backup-schedule-enabled.json)确认native job enabled=1、03:30与3/7/4保留。先前失败和进行中证据继续保留历史，不再作为现状；后续健康及规则状态统一见[本轮交付](completion/20261109/README.md)。

[备份metadata指标已接入原collector](completion/20261109/backup-metrics-installed.json)，复用QGA、不加监听；[三名Lark告警白名单已配套](completion/20261109/backup-notify-whitelist-result.json)，没有人工测试外发。Prom规则的实际加载与后验结果只以[当日中央记录](completion/20261109/README.md)为准，本页不提前声明已加载。

这是snapshot/crash-consistent系统恢复点；QGA freeze不等于数据库逻辑一致、跨来宾事务一致或恢复演练。归档在同一T630/store，异机目的地、真实RPO/RTO和独立灾备仍未完成，本轮不恢复VM或导入数据。

## 6. 当前授权、保留目标与后续核查

用户最新要求是继续完成基础搭建并先采用PVE本机自动备份，保持不迁移数据与现有业务边界。Nexus历史维护授权和220 primary30+alias31/6CPU8GiB目标保留，但不能覆盖本轮不迁移指令。221继续独立提供Nexus，220仅待机材料；不因恢复可达自动进入原切换窗口。未来仅在用户明确恢复迁移任务后fresh核验，不以本轮基础健康检查替代应用一致性备份与迁移门禁。

11月7日02:35验收JSON标题中的“merge pending approval”是当时旧状态；历史授权后来满足，而11月8日用户又明确暂不迁移。两次决定均保留，不修改历史原始证据。

本轮基础恢复已经带时间复核；没有清SEL、强制阵列Online或通过重装覆盖应用。仍需保留维修/诊断与硬件事件供长期观察，记录任何新CE/UE或IO错误。新的清理动作先核依赖、唯一回退与精确范围；不重复删除已清对象、不重新启动Java业务。认证/内容一致性、长期备份、真实客户端及负载SLO未因本次健康GET自动完成。

OW完整规则仅本地保存，不触碰/上传，不push local-only分支。初始11月5日盘点、10.63过渡网络、旧模板/Java五服务试验均只作历史证据保留，不再占本文当前清单。旧资料见[evidence](evidence/)、[实施日志](09-implementation-progress.md)，不要重跑已完成bootstrap。
