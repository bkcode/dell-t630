# 服务部署结果、迁移边界与未完成事项

更新：2026-11-08。**用户确认内存重新插拔/更换并诊断通过，基础服务已在20:16–20:20恢复审计；当前只检查补齐与清理确认多余项，不迁移。** UEFI0058为历史故障；本轮主要检查健康/状态/挂载，没有重做全部应用内容、认证与备份恢复。Nexus221仍独立，Java业务不部署，Mac外部探针从现行方案及后续待办移除、历史保留。整体见[01](01-current-state.md)，证据边界见[08](08-hardware-findings.md)。

## 1. 当前实际服务归属与验收层级

保留的合并目标是一台VM220 `publish-service`承担发布与Nexus；本轮不实施。下表是实际仍分开的220/221，不能按目标删221或把31归220。目标合同见[17](17-publish-artifact-consolidation.md)，本轮当前观察见表后恢复证据。

| 实例 | 必要服务/功能 | 历史功能验收 | 仍未承诺 |
| --- | --- | --- | --- |
| 200 正式DB | MySQL8.4.5、Nacos专用元库/账号、角色授权、持久目录 | 真实认证、权限与fixture重启/重建持久化；正式业务schema空 | 正式业务数据迁入、业务上线、RPO/SLO |
| 201 正式infra | Nacos2.4.3外部MySQL、Redis7.4.4、RabbitMQ3.13.7 | 组件认证、namespace/账号/vhost隔离、必要端口及持久化 | 业务消息全量保全、应用所有消费链 |
| 210 测试 | 独立MySQL/Nacos/Redis/Rabbit和最小测试schema | 测试专用权限及依赖准备；无正式账号/目录复用 | 不代表Java业务允许启动 |
| 220 发布基础 | Git/JDK/构建目录、专用publisher、受限SSH链 | 原传输与B/A试验留证，网络19合同已改、当前发布fenced | 当前不能发布或重启Finger业务；220未承载Nexus31 |
| 221 Nexus | 独立仓库/API、权限、制品保存 | 49 GAV/234主制品SHA读取核对、HTTP与持久化 | 尚未合并220；新写入后的回退需一致性处理 |
| 230/240 Java基础 | JDK/系统用户/运维基线 | 每环境各一，业务五服务已停用 | 不部署任何Java业务程序，不把旧服务列表当运行数 |
| 250 Penpot | 定制前端、backend、resident worker、import/MCP及DB/素材 | 11容器、3设计/973媒体、MCP及受控功能验证 | 实际SMTP、公网域名/HTTPS、全工作负载SLO |
| 260 NAS | OMV、SMB media/games/incoming、Jellyfin | 挂载/权限、原媒体及重启恢复 | 真实TV/PS4/PS5、多路转码、媒体独立备份 |
| 270 Ops | Prometheus/Grafana/AM/Blackbox、OS/PVE/RAID/CF状态、Lark桥 | 原验收firing/resolved code0；本轮15目标UP/0告警 | 不承担整机故障独立外告警；Mac probe不再列入方案或待办 |
| 190 GW / 100 CF | 路由/DNS/DHCP/filter，隧道传输入口 | 网关同key重启、CF连接注册；VPN全19规则与用户远程批量验证 | 未知Cloudflare account-side origin不由注册成功推定 |

本轮恢复证据：

- [核心200/201/210/230/240](recovery/20261108/core-services-audit.json)，20:16:13–20:18:22：三盘UUID/rw相符、数据8容器healthy/RestartCount0；两Java基础JDK21.0.13可执行、finger存在、无Java进程、五旧unit非enabled。未重验DB认证、namespace或业务schema内容。
- [媒体工具220/221/250/260](recovery/20261108/media-tools-audit.json)，20:19:39：220仍4CPU/4GiB/唯一30，无active Nexus；221两容器、250十一容器、260一容器healthy/原镜像保持，原健康GET通过。Penpot实际Git为ff1783e clean，本轮未更新main；MCP、设计/制品内容与SMB写入未复验。
- [Ops270](recovery/20261108/ops-audit.json)，20:19:38：4容器healthy、15/15 targets UP/0告警，内部Lark unit active；未触发新消息测试。首轮onboot尚未完成的no-route/starting自然消失，不是通过重启应用修复。
- [宿主后检](recovery/20261108/host-network-postcheck.json)，20:20:48：保留12来宾运行、主要6入口200、各接口forward0。仅3个owned持久文件用于收敛宿主forward，桥/路由/ACL未变、没有网络reload。PVE HTTPS的curl只证明入口可达，没有认证其自签证书。

- [直接LAN DNS/CF复核](recovery/20261108/network-CF-followup.json)：19.1 UDP/TCP解析三静态A正确；CF实际20241 ready200、连接2，公网origin E2E未验。网关OS resolver走OW Fake-IP、旧CF2000探针假设错误均已有解释，原失败证据不改写。

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

## 4. 发布与制品合并目标保留，本轮不迁移

目标是一台VM220、两个服务职责：管理与发布主IP19.30，Nexus保持19.31:8081作为同NIC服务alias；`artifact-service`仅保留历史/服务DNS兼容含义，旧VM221完成核验后退役。合并后11实例、14监控目标，配置总额43vCPU/85GiB不变，220为6vCPU/8GiB。此目标尚未切换，不能把两IP计作两台机器。

本轮fresh观察Nexus仍在221/19.31、原两容器健康，220只有准备包且无31/active Nexus。没有源停服、alias交接、目标启动或原盘移交；两机当前实际状态已复核，不能再以11月7日不可达写作未知。

Nexus维护停机历史授权保留，但**用户11月8日明确暂不迁移，当前不得合并/移盘/退役221**。恢复可达不自动重开原维护计划。目标仍为220保hostname publish-service、primary19.30、同NIC服务alias19.31、6CPU/8GiB；仅作保留设计。详见[合并整理](18-cleanup-and-consolidation.md)、[网络候选](cleanup/network/README.md)、[Nexus准备](cleanup/nexus/)。

将来只有用户明确恢复迁移任务后，才fresh核硬件有效内存/存储、可信SSH、221源健康、220容量、应用一致性备份及已准备软件版本，并安排切换窗口。31换主需先停/隔离旧221避免双IP，更新同MAC多IP绑定/ARP及logical endpoint，不能因为IP相同就忽略hostkey和运行guard。新目标开始写入后，回退必须保全新写入，不只切回旧IP。没有完成这些步骤时，不能把221标退役或把alias写成当前配置。

## 5. Penpot与NAS迁移后的使用限制

Penpot使用独立目标身份；定制前端便利登录值不能随源配置公开到浏览器，worker/import/MCP保持受控，不把后端、数据库、Mailpit或导入口直接暴露。3设计/973媒体验收覆盖已记录样本，不代表所有未来协作/格式/长任务均通过。公网域名、可信HTTPS、真实SMTP仍为单独交付项。

NAS采用OMV管理专用2TiB虚拟盘，Jellyfin只读媒体；SMB写入/只读账户区分，游戏文件不进入媒体扫库。旧home-cinema-nas仓库中宿主OMV、旧IP或一键拉起MoviePilot/qBittorrent的说明不能当本T630实施入口，详见[05](05-home-nas.md)。

## 6. 备份与恢复证据如何解读

PVE备份与应用逻辑/导出恢复互补。已做的合成MySQL/Nacos/Redis/Rabbit fixture隔离恢复、Grafana SQLite恢复、模板VMA恢复和应用样本验证只覆盖对应范围；Rabbit topology不含消息，单Nacos配置行不是完整元库，JAR回滚不回滚DB/Nacos。

普通应用备份目的地暂为Mac私有目录；受保护清理VMA备份在PVE本机，CF含凭据备份只准PVE，不导出Mac。NAS不是正式灾备。长期生产备份目的地、周期、保留和恢复RPO/RTO尚未达到可承诺SLA；Lark配置恢复也不包含在单份Grafana数据库备份里。

本轮不做重建、压测、数据导入或迁移。恢复审计已核部分挂载/健康，但不以当前Optimal、HTTP200或archive SHA替代数据一致性与完整恢复验证。新的备份/清理按明确范围安排，不从旧脚本推导可整体重跑。

## 7. 运维和验收入口

当前地址与安全入口见[12](12-service-access-and-operations.md)，网络和VPN见[15](15-network19-delivery.md)，清理结果见[18](18-cleanup-and-consolidation.md)，备份见[应用备份](infra/backup/README.md)。各包prepare/stage/commit有环境/时间门禁，不能因服务恢复就直接重跑历史命令；本轮不进入Nexus或业务迁移。

本轮恢复证据见上方[核心](recovery/20261108/core-services-audit.json)、[媒体工具](recovery/20261108/media-tools-audit.json)、[Ops](recovery/20261108/ops-audit.json)、[宿主后检](recovery/20261108/host-network-postcheck.json)；[故障前完整验收](cleanup/final-live-check.json)与[plan](plan.json)分别保存历史结果和配置合同。原本机只读快照、旧10.63私网及Java试验记录保留作历史，不全局替换其中IP/状态，也不称“所有迁移仍pending”。
