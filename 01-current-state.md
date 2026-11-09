# T630 当前状态、恢复验收与操作边界

更新：2026-11-10（Asia/Shanghai）。当前已完成统一资源VM280/NFS、两running同根挂载及受认证FileBrowser管理页：[最新后检](completion/20261109-resources/final-postcheck.json)确认13来宾运行、3模板停止、16/16监控UP，宿主各接口双栈forward0。资源用法见[手册](completion/20261109-resources/usage-manual.md)。用户后续另明确授权的测试Nacos36配置/Puyu两库迁移与固定测试凭据均已完成，源保留；不执行Nexus合并，不启动Java，不迁旧资源文件、不启业务图片HTTP（管理HTTPS已另获授权），自动备份仍仅正式MySQL/Nacos。

此前11月9日14:24自然重启后的12来宾/15UP、EDAC0/RAIDOptl是新增资源之前的硬件基础审计，见下方历史；新资源VM单独重启约30秒验证了自身共享持久性，没有重启物理PVE或两running OS。

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
| 2026-11-09 15:54:56/15:56（已退役方案历史） | 固定11项全部zstd/native verified、原生任务OK/退出0，共19,747,582,801 bytes；03:30计划已enabled | [首轮成功](completion/20261109/backup-first-success.json)、[计划启用](completion/20261109/backup-schedule-enabled.json)；后续已停用，旧档保留；不等于恢复通过或异机灾备 |
| 2026-11-09 16:57–17:01 新范围收尾 | 仅VM200 nacos_prod/12表逻辑首轮3301B成功，03:30 timer enabled、db-only三规则已加载；旧whole-VM job停用且档保留 | [新首轮](completion/20261109-prod-db-scope/first-success-and-timer-enabled.json)、[规则热载](completion/20261109-prod-db-scope/alerts-installed.json)，不签恢复/独立DR |

[plan.json](plan.json)是保留角色、地址和配置预算的机器可读来源；deployment_status不代替带时间的现场健康证据。[机器目录](machines/README.md)保存逐机合同与公开来源索引，不是实时配置导出。历史事故与本轮恢复证据边界见[硬件发现](08-hardware-findings.md)，日常检查见[操作手册](19-manual-operations.md)。

## 2. 本轮恢复后保留角色

已设计的合并目标仍是一台VM220 `publish-service`承担发布与Nexus，6vCPU/8GiB、主IP19.30+服务alias19.31，新增资源280后目标12实例/15监控目标，详见[17目标合同](17-publish-artifact-consolidation.md)。**用户11月8日明确暂不迁移；该目标本轮不实施，221保持独立，不退役、不移盘、不加alias。**

以下13角色为现役12个VM和1个LXC；[最新资源后检](completion/20261109-resources/final-postcheck.json)观察到全部运行。运行不等于所有业务/数据已重新验收，各服务范围见下节。

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
| 280 | resource-service | 19.80 | 2 / 2 | 统一NFSv4.1上传资源存储；230/240同根/mnt/resources，未启HTTP/业务 |
| **合计** | **13角色** | 均为192.168.* | **45 / 87** | 配置预算，非负载或吞吐承诺 |

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

硬件已识别为双E5-2680 v4，28物理核心/56线程；观察内存约125.78GiB，规划预算保守125GiB。新增资源后87GiB来宾配置约留38GiB给主机/余量，最低保留8GiB，不能以配置空闲推导当前DIMM健康或容量SLO。

H730暴露SSD RAID1和HDD RAID5，PVE管理`local/local-lvm/store`；主AI本轮只读报告RAID Optimal，各应用审计核其分配挂载UUID。当前控制器状态不等于逐文件/数据库一致性证明。NAS只管理专用虚拟盘，不能再挂载PVE的sdb/store或直通承载宿主存储的整卡。

## 5. 正式数据库/Nacos自动备份：首轮完成、timer已启用

现行自动备份**仅限VM200正式MySQL数据库与完整Nacos外部元数据库**；当前唯一非系统库为`nacos_prod`（12张BASE TABLE、全InnoDB），正式业务schema尚未创建。新增非系统库不在显式白名单即拒绝并告警，需审核更新策略，不能静默漏备。PVE落点`/mnt/pve/store/dell-artifacts/prod-db-backups`，目录root700/文件600；首轮逻辑SQL gzip **3,301 bytes**已完成CRC/传输SHA校验、DDL锁释放和guest暂存清理，service退出0；03:30（Asia/Shanghai）timer已enabled，下一次2026-11-10 03:30，GFS最近3/每日7/每周4。见[新首轮与timer回执](completion/20261109-prod-db-scope/first-success-and-timer-enabled.json)及[当前中央入口](completion/20261109-prod-db-scope/README.md)。

其他数据均不纳入自动：不备VM/OS、测试数据、Redis/Rabbit、Nexus、Penpot、NAS、Ops或CF文件，220发布私钥继续只留220。旧11来宾全机job已disabled、旧whole-VM告警组已退役；原19,747,582,801 bytes全机归档和21回退档保留，不自动删除。新指标`dell_prod_db_backup_*`及三条db-only规则已原生校验/热载，原Prom身份、既有三告警名和Lark接收对象不变、无人工testsend，见[规则回执](completion/20261109-prod-db-scope/alerts-installed.json)。这是同机应用逻辑备份，不是VM快照；仅下述小档已临时隔离恢复、未迁移，未签业务恢复/RPO/RTO或异机灾备，Java不启、Nexus不合并、Mac外部探针不需要。

此前[11档全机首轮成功](completion/20261109/backup-first-success.json)及15:56启用是历史事实，已被用户最新“仅正式数据库/Nacos配置”范围取代；原`dell-local-nightly`不再启用，旧[pve-local实现](infra/backup/pve-local/README.md)退役不可重跑。CF历史档只留PVE，任何旧档/配置均不得因此导出。

**仅这份3301B `nacos_prod`小快照已完成VM210临时隔离恢复**：12表10行，活跃`config_info`为空，10行为历史、命名空间及认证/权限元数据。源备份SHA、timer及VM210原4服务保持、临时资源已清理；不扩签业务库、RPO/RTO或异机灾备，见[限定恢复收尾](completion/20261109-prod-db-restore/README.md)。

## 6. 当前授权、保留目标与后续核查

用户最新要求是继续完成基础搭建并仅自动备份正式数据库/Nacos配置，另已逐项授权测试Nacos/Puyu迁移及统一资源服务；新资源不迁旧文件、未切应用，其他现有业务边界保留。Nexus历史维护授权和220 primary30+alias31/6CPU8GiB目标保留，但不能覆盖本轮不迁移指令。221继续独立提供Nexus，220仅待机材料；不因恢复可达自动进入原切换窗口。未来仅在用户明确恢复迁移任务后fresh核验，不以本轮基础健康检查替代应用一致性备份与迁移门禁。

11月7日02:35验收JSON标题中的“merge pending approval”是当时旧状态；历史授权后来满足，而11月8日用户又明确暂不迁移。两次决定均保留，不修改历史原始证据。

本轮基础恢复已经带时间复核；没有清SEL、强制阵列Online或通过重装覆盖应用。仍需保留维修/诊断与硬件事件供长期观察，记录任何新CE/UE或IO错误。新的清理动作先核依赖、唯一回退与精确范围；不重复删除已清对象、不重新启动Java业务。认证/内容一致性、长期备份、真实客户端及负载SLO未因本次健康GET自动完成。

OW完整规则仅本地保存，不触碰/上传，不push local-only分支。初始11月5日盘点、10.63过渡网络、旧模板/Java五服务试验均只作历史证据保留，不再占本文当前清单。旧资料见[evidence](evidence/)、[实施日志](09-implementation-progress.md)，不要重跑已完成bootstrap。

## 最新资源管理页

现有280新增https://192.168.19.80:8080/，日常resources受限上传/浏览、维护admin完整，口令只private保管；native程序不改NFS/VM预算，16targets保持，资源6服务＋专属CA HTTPS检查通过。见[管理交付](completion/20261110-filebrowser/README.md)、[使用手册](completion/20261110-filebrowser/usage-manual.md)。只重启新app，旧服务与两机挂载保持，未接业务图片或扩备份。
