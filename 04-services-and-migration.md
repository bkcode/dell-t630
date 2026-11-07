# 服务部署结果、迁移边界与未完成事项

更新：2026-11-07。**最后完整软件验收为02:35；当前POST内存错误、管理不可达，用户已暂停服务器工作。** 下列“已验”均指故障前有证据的功能，不表示此刻在线。现在不连接服务器、停启服务或继续Nexus合并。当前整体状态见[01](01-current-state.md)，硬件门禁见[08](08-hardware-findings.md)。

## 1. 最后验收快照中的服务功能与归属

合并后的目标只保留VM220 `publish-service`承担构建/发布与Nexus两项职责；`artifact-service`不再独立规划。下表220/221是未迁移前的快照，目标与变更合同见[17合并架构](17-publish-artifact-consolidation.md)。

| 实例 | 必要服务/功能 | 最后已验收 | 仍未承诺 |
| --- | --- | --- | --- |
| 200 正式DB | MySQL8.4.5、Nacos专用元库/账号、角色授权、持久目录 | 真实认证、权限与fixture重启/重建持久化；正式业务schema空 | 正式业务数据迁入、业务上线、RPO/SLO |
| 201 正式infra | Nacos2.4.3外部MySQL、Redis7.4.4、RabbitMQ3.13.7 | 组件认证、namespace/账号/vhost隔离、必要端口及持久化 | 业务消息全量保全、应用所有消费链 |
| 210 测试 | 独立MySQL/Nacos/Redis/Rabbit和最小测试schema | 测试专用权限及依赖准备；无正式账号/目录复用 | 不代表Java业务允许启动 |
| 220 发布基础 | Git/JDK/构建目录、专用publisher、受限SSH链 | 原传输与B/A试验留证，网络19合同已改、当前发布fenced | 当前不能发布或重启Finger业务；220未承载Nexus31 |
| 221 Nexus | 独立仓库/API、权限、制品保存 | 49 GAV/234主制品SHA读取核对、HTTP与持久化 | 尚未合并220；新写入后的回退需一致性处理 |
| 230/240 Java基础 | JDK/系统用户/运维基线 | 每环境各一，业务五服务已停用 | 不部署任何Java业务程序，不把旧服务列表当运行数 |
| 250 Penpot | 定制前端、backend、resident worker、import/MCP及DB/素材 | 11容器、3设计/973媒体、MCP及受控功能验证 | 实际SMTP、公网域名/HTTPS、全工作负载SLO |
| 260 NAS | OMV、SMB media/games/incoming、Jellyfin | 挂载/权限、原媒体及重启恢复 | 真实TV/PS4/PS5、多路转码、媒体独立备份 |
| 270 Ops | Prometheus/Grafana/AM/Blackbox、OS/PVE/RAID/CF状态、Lark桥 | 清理后15目标UP/0告警、真实验收firing/resolved code0 | 整机故障外部告警；Mac probe本期停用 |
| 190 GW / 100 CF | 路由/DNS/DHCP/filter，隧道传输入口 | 网关同key重启、CF连接注册；VPN全19规则与用户远程批量验证 | 未知Cloudflare account-side origin不由注册成功推定 |

Nacos、Nexus及Penpot backend/worker使用JVM是其实现方式；用户禁止的是Finger等Java业务程序。不能看到201/210/221/250的java进程就误认为业务五服务被启动。

## 2. ARM64源与AMD64目标

Mac原环境与T630不是相同平台。原`work/nacos`/定制Penpot镜像主要ARM64；目标按AMD64官方digest或定制源码重建，记录平台、ConfigID、归档/文件SHA及工具版本。不得直接把ARM64镜像或运行中数据目录当成目标可用恢复。

用户选择保留Penpot/Nexus定制源码Git，并以应用导出/导入交付目标数据；目标使用独立账号/密钥，没有把旧.env/MCP身份整体搬入。源Mac数据保留，不因PVE最初“干净”而可删除。正式业务库不导入Mac真实业务数据，本机数据只用于测试。

MySQL逻辑一致性、Redis持久化和Rabbit消息/definitions分别处理；Nacos配置行导出不等于完整账号/权限/元库。镜像与volume/data路径、应用身份和挂载UUID分开核对。重建容器只替换程序，不自动恢复数据，也不自动重置所有应用ID。

## 3. 当前持久化与启动合同

- 正式/测试独立VM、实例、目录和凭据；库名/namespace/vhost只是附加边界，不能代替MAC/IP/role ACL。
- 数据等Compose角色固定镜像，restart=no，bind不自动建缺失目录；systemd核真实mountpoint/source/UUID后才启动，避免缺盘写根盘。
- Nacos使用对应2.4.3 schema与专用MySQL身份；业务用户不使用root或Nacos账户。配置/密码仅600私有文件/受控STDIN，不写普通证据。
- Java旧程序/配置只留私有备份，不启动；运行配置曾采用root600+LoadCredential、非root与固定unit，不能因为保留这些文件就推导当前仍部署业务。
- 定制Penpot数据库、assets、import job与所有可能写入者有一致性边界；Nexus元数据库/blob/仓库权限也需同一恢复点，不单独随意copy热目录。

正式生产负载、真实支付/券商/通知任务和完整多模块发布属于未来单独授权阶段，当前组件认证/HTTP200不代替该验收。

## 4. 发布与制品合并目标：VM220 publish-service

目标是一台VM220、两个服务职责：管理与发布主IP19.30，Nexus保持19.31:8081作为同NIC服务alias；`artifact-service`仅保留历史/服务DNS兼容含义，旧VM221完成核验后退役。合并后11实例、14监控目标，配置总额43vCPU/85GiB不变，220为6vCPU/8GiB。此目标尚未切换，不能把两IP计作两台机器。

最后验收服务仍在221/19.31，220只有准备包；代理没有执行源停服、alias31交接或目标启动。现在源/目标实际运行态因硬件不可达而未知。

用户已经明确给出Nexus维护停机授权，**当前gate是DIMM_B1/UEFI0058与管理不可达，不是缺少同一授权**。预期后续目标是220保hostname publish-service、primary19.30，单NIC增加服务alias19.31，计划6CPU/8GiB，保留客户端URL。方案与验证分别见[合并整理](18-cleanup-and-consolidation.md)、[网络候选](cleanup/network/README.md)、[Nexus准备](cleanup/nexus/)。

恢复后先重新确认硬件有效内存/存储、可信SSH、221源健康、220容量、应用一致性备份及已准备软件版本，再进入原维护计划。31换主需先停/隔离旧221避免双IP，更新同MAC多IP绑定/ARP及logical endpoint，不能因为IP相同就忽略hostkey和运行guard。新目标开始写入后，回退必须保全新写入，不只切回旧IP。没有完成这些步骤时，不能把221标退役或把alias写成当前配置。

## 5. Penpot与NAS迁移后的使用限制

Penpot使用独立目标身份；定制前端便利登录值不能随源配置公开到浏览器，worker/import/MCP保持受控，不把后端、数据库、Mailpit或导入口直接暴露。3设计/973媒体验收覆盖已记录样本，不代表所有未来协作/格式/长任务均通过。公网域名、可信HTTPS、真实SMTP仍为单独交付项。

NAS采用OMV管理专用2TiB虚拟盘，Jellyfin只读媒体；SMB写入/只读账户区分，游戏文件不进入媒体扫库。旧home-cinema-nas仓库中宿主OMV、旧IP或一键拉起MoviePilot/qBittorrent的说明不能当本T630实施入口，详见[05](05-home-nas.md)。

## 6. 备份与恢复证据如何解读

PVE备份与应用逻辑/导出恢复互补。已做的合成MySQL/Nacos/Redis/Rabbit fixture隔离恢复、Grafana SQLite恢复、模板VMA恢复和应用样本验证只覆盖对应范围；Rabbit topology不含消息，单Nacos配置行不是完整元库，JAR回滚不回滚DB/Nacos。

普通应用备份目的地暂为Mac私有目录；受保护清理VMA备份在PVE本机，CF含凭据备份只准PVE，不导出Mac。NAS不是正式灾备。长期生产备份目的地、周期、保留和恢复RPO/RTO尚未达到可承诺SLA；Lark配置恢复也不包含在单份Grafana数据库备份里。

硬件暂停期间不做热备份/重建/压测。恢复后先检有效RAM、阵列/文件系统、数据盘UUID/一致性和原配置，再决定恢复服务或迁移，不用历史Optimal、HTTP200或archive SHA代替当前复验。

## 7. 运维和验收入口

当前地址与安全入口见[12](12-service-access-and-operations.md)，网络和VPN见[15](15-network19-delivery.md)，清理结果见[18](18-cleanup-and-consolidation.md)，备份见[应用备份](infra/backup/README.md)。各包的prepare/stage/commit是带环境/时间门禁的工具，当前暂停时不能直接运行历史命令。

最后验收证据：[cleanup/final-live-check.json](cleanup/final-live-check.json)、[plan.json](plan.json)。原本机只读快照、旧10.63私网及Java试验记录保留作历史，不全局替换其中IP/状态，也不称“所有迁移仍pending”。
