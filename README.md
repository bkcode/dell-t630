# Dell PowerEdge T630 部署与运维

本仓库保存 T630 / Proxmox VE 8.4 的部署方案、基础设施脚本、验收证据和人工操作手册。最后整理日期：**2026-11-10，Asia/Shanghai**。

**2026-11-09继续完成基础搭建，并按用户最新范围仅备正式数据库/Nacos配置；随后另获授权完成选定测试Nacos配置及两份Puyu数据库迁移。** 14:24自然重启后的fresh审计确认12来宾运行、3模板停止、15/15UP、EDAC0/RAIDOptl，forward guard文件与启动顺序保持全0。Nexus221继续独立、220保持原standby，Java业务不启，Penpot实际ff提交不更新main，Mac外部探针不需要。当日状态统一见[11月9日交付记录](completion/20261109-prod-db-scope/README.md)；[11月8日恢复](recovery/20261108/README.md)保留历史。

## FileBrowser Quantum管理页面

新增私有管理入口 **https://192.168.19.80:8080/**，仅LAN21/24、WG10.66/24及本机；日常`resources`可浏览/下载/新建上传，delete/edit/override/share/提权直接API已验403；维护`admin`有完整权限，不把日常限制说成它也绝对不能删除。密码只在Mac `dell/private/credentials/filebrowser-management-20261110.json`与guest root `/etc/dell-filebrowser/secrets/login.json`保管，不在文档输出值。首次核[tls.crt](completion/20261110-filebrowser/tls.crt)的SHA256指纹后接受/导入；无公网域名、无系统truststore变更。

官方native固定v2.1.4-beta（不是stable），UID2000/GID2980、UMask0002、文件660/目录2770，DB/cache在非共享的`/var/lib/dell-filebrowser`700；初始化marker在root的`/etc/dell-filebrowser/bootstrap.complete`，正常后续启动不再注入初始化口令。自身metadata自动备份关闭，不扩正式DB/Nacos备份；Docker未装，NFS/PVE/路由不改，不Java、不业务图片URL、不迁旧文件。

[原生API/NFS验收](completion/20261110-filebrowser/native-acceptance.json)passed且fixture已清；[真实浏览器](completion/20261110-filebrowser/browser-acceptance.json)只签登录/列表及观察到href后的96PNG深链渲染，自动点击未导航，未签所有按钮。[只重启新app](completion/20261110-filebrowser/service-restart.json)已保持账号、scope和JWT且不再注入初始化口令，NFS/VM/clients未重启；[06:12最终后检](completion/20261110-filebrowser/final-postcheck.json)已确认13运行来宾、3停止模板、16targets全UP、资源6服务指标及专属CA HTTPS健康均UP，PVE全forward0；未加Promtarget/receiver或外发测试消息。完整[管理页使用手册](completion/20261110-filebrowser/usage-manual.md)含证书指纹、账号、维护/升级与故障步骤；[公开服务包](infra/resources/filebrowser/README.md)。

## 统一资源服务（新增VM280）

用户选择正式/测试共用VM280 `resource-service`（19.80）的同一目录。独立100GiB ext4盘挂`/srv/resources`，系统盘保32GiB；两running 230/240目标挂载均为`/mnt/resources`，240原`/mnt/dell-artifacts`不动。NFSv4.1-only/TCP2049/fsid0，只有19.40/19.45获export与bridge/专属输入许可；root_squash、sync、server根2770/defaultACL、共享resources附属组2980。finger原UID999/GID989保留。

[server启动](completion/20261109-resources/server-installed.json)与[实际盘UUID](completion/20261109-resources/storage-initialized.json)已留证；两客户端真NFS挂载/guard、非root跨机创建/读写/删除、root_squash与240缺挂载根盘写入负测均已通过；仅VM280受控重启约30秒，fsync canary持久、两客户端挂载恢复，未重启两台running。**NFS保留，另加受限FileBrowser管理HTTPS；不提供业务图片URL、不启Java、不迁文件、不扩自动备份。** 资源角色使预算变为13来宾（12VM＋CF LXC）、3模板、45vCPU/87GiB；保守125GiB预算余38GiB。[00:20最终只读后检](completion/20261109-resources/final-postcheck.json)确认13来宾运行、3模板停止、16/16 targets UP、资源5项服务指标UP与PVE全forward0。详见[280机器目录](machines/vm280-resource-service/README.md)与[资源使用手册](completion/20261109-resources/usage-manual.md)。

模板仅能将来预装客户端与disabled挂载候选，clone按真实IP/组/exports/bridge登记后显式激活；**本次没有修改三模板**。

[独立native验收](completion/20261109-resources/native-acceptance.json)与[仅280重启](completion/20261109-resources/reboot-exercise.json)覆盖本次专属fixture，不含真实业务或文件恢复。findmnt允许systemd-1 autofs加唯一真实nfs4的合法stack，可用`-t nfs4`辨识；单独autofs仍不算共享已挂载。客户端文件创建明确用umask0002；首轮失败及清理记录保留，随后仅按已批准UMask重跑fixture，未修改服务来追过。新增280 fish4.0.2、root/ub默认Bash已后检；当前10台guest＋3模板具备fish基线。

应用尚未接入：Finger的`file.upload.path=/mnt/resources`仅建议，未改实际配置/Nacos/profile；业务HTTP domain/公开图片URL未搭。Puyu现有images在MySQL内通过权限接口下载，NFS不会自动迁出，也未随部署改Java或应用连接。


## 从这里开始

| 需要做什么 | 阅读入口 |
| --- | --- |
| 按每台机器查看配置与文档 | **[machines目录](machines/README.md)**：宿主、13来宾和3模板各自独立目录 |
| 人工值守、故障处理、启动、备份、克隆、未来合并 | **[人工操作手册](19-manual-operations.md)** |
| 接手当前基础设施任务 | [当前交接与恢复条件](11-live-handoff.md) |
| 看完整服务器名称、地址、配置与作用 | [当前状态清单](01-current-state.md)、[机器可读规划](plan.json) |
| 查服务网址、SSH 与凭据保管位置 | [服务访问与日常操作](12-service-access-and-operations.md) |
| 理解路由、虚拟机、Docker 与隔离 | [架构](02-architecture.md)、[网络交付](15-network19-delivery.md)、[WireGuard](16-wireguard-access.md) |
| 查模板与家庭 NAS | [模板](03-templates-and-access.md)、[NAS](05-home-nas.md) |
| 看发布与Nexus合并后的目标架构 | **[17合并架构](17-publish-artifact-consolidation.md)**，目标只保留VM220 publish-service |
| 查现行正式数据库/Nacos自动备份 | [新中央入口](completion/20261109-prod-db-scope/README.md)、[首轮与timer](completion/20261109-prod-db-scope/first-success-and-timer-enabled.json) |
| 查已完成清理和未完成的 Nexus 合并 | [整理结果](18-cleanup-and-consolidation.md)、[合并恢复检查](cleanup/nexus/resume-preflight.md) |
| 查验收边界和结果 | [验收总览](06-acceptance.md)、[本轮整理验收](cleanup/acceptance.md) |
| 将仓库交给另一台电脑或下一位管理员 | [Git 与资料交接](20-git-and-handoff.md) |

## 服务目标：发布与制品仓库同机

目标中只保留一台 **VM220 `publish-service`（6vCPU / 8GiB）**：主IP19.30用于管理、构建和受限发布，同NIC的19.31:8081用于Nexus。`artifact-service`不再是目标中的独立VM；旧221验收后退役，既有服务DNS可作为逻辑兼容名保留。加入独立资源280后的合并目标为12实例/15监控目标，总45vCPU/87GiB不变。

**这是目标说明，用户本轮暂不迁移。** 下方清单含新资源280；旧12实例快照只代表新增前，两者不能混算。详见[合并架构](17-publish-artifact-consolidation.md)。

## 当前保留部署与历史基线

2026-11-10 00:20最新后检为1台物理服务器、**13运行实例（12VM+1LXC）和3停止模板**，配置总额45vCPU/87GiB；新增资源前11月9日的12实例/43CPU/85GiB为历史。11月7日02:35/02:44:29及随后UEFI0058停机是历史节点，不能继续称为最后成功现场；时间线见[硬件记录](cleanup/hardware/DIMM_B1-incident.json)，新证据见[当日入口](completion/20261109-prod-db-scope/README.md)。

| VMID | 名称 | 地址 | 主要作用 |
| --- | --- | --- | --- |
| 190 | network-gateway | 21.23 / 19.1 | 专用路由、DNS、DHCP、防火墙 |
| 100 | cf-tunnel（LXC） | 19.5 | Cloudflare Tunnel |
| 200 | data-prod-db | 19.10 | 正式 MySQL，保持空业务数据 |
| 201 | data-prod-infra | 19.11 | 正式 Redis、RabbitMQ、Nacos |
| 210 | data-test | 19.20 | 独立测试数据组件 |
| 220 | publish-service | 19.30 | 发布基础；已准备接收 Nexus，业务发布冻结 |
| 221 | artifact-service | 19.31 | Nexus 制品库；尚未合并 |
| 230 | java-prod-01 | 19.40 | 正式 Java 运行基础，无业务程序 |
| 240 | java-test-01 | 19.45 | 测试 Java 运行基础，五业务已停用 |
| 250 | penpot-service | 19.50 | Git 定制版 Penpot |
| 260 | nas-media | 19.60 | OMV、SMB、Jellyfin 家庭媒体与文件共享 |
| 270 | ops-service | 19.70 | Prometheus、Grafana、Alertmanager、内部 Lark |
| 280 | resource-service | 19.80 | 两running共用NFS资源存储，/mnt/resources |

地址前缀为 `192.168.`。PVE 自身管理地址是 `192.168.21.22`，iDRAC 是 `192.168.21.21`。OpenWrt `21.1` 将 `19.0/24` 路由到 `21.23`；PVE 只做管理和二层桥，不做应用端口转发。受信LAN `192.168.21.0/24` 与WireGuard `10.66.66.0/24` 均已获准IPv4访问服务器网段，应用登录权限继续生效。

模板仅保留 Linux `9010`、Docker `9001`、Java 验收 `9011`。10 台来宾和 3 份模板已安装 fish，默认 Bash；CF、Penpot、Ops 和 PVE 宿主排除。NAS 不另做模板。新增280前11月9日监控复验15/15UP，11月10日00:20最终后检16/16UP；Mac外部探针不需要，不再列入待办。

## 文档与证据怎样使用

- `plan.json` 保存现有配置与下一步目标；当前范围以本页、交接页及恢复记录为准。
- `cleanup/final-live-check.json`、网络及应用验收文件是带时间的历史证据，不能代替恢复后的现场检查。
- `infra/`、`network19/`、`cleanup/` 包含分阶段实施代码和旧候选，**不是可整体重跑的一键安装包**。
- `private/` 是本机受保护资料，已排除 Git。Git 不包含数据库、备份归档、服务密码或客户端私钥；新电脑仅克隆仓库不能直接恢复全部服务。
- 加入资源280后，合并前维持13实例、16监控目标。将来合并并验收后才更新为12实例、15目标，不能提前改成完成。

本地检查（仓库根目录执行）：

```sh
python3 scripts/validate_machines.py
python3 scripts/validate_docs.py --json
python3 scripts/check_git_safety.py
```

## 仅正式数据库/Nacos逻辑备份：首轮成功、timer已启用

现行自动备份**仅限VM200正式MySQL数据库与完整Nacos外部元数据库**；当前唯一非系统库为`nacos_prod`（12张BASE TABLE、全InnoDB），正式业务schema尚未创建。新增非系统库不在显式白名单即拒绝并告警，需审核更新策略，不能静默漏备。PVE落点`/mnt/pve/store/dell-artifacts/prod-db-backups`，目录root700/文件600；首轮逻辑SQL gzip **3,301 bytes**已完成CRC/传输SHA校验、DDL锁释放和guest暂存清理，service退出0；03:30（Asia/Shanghai）timer已enabled，下一次2026-11-10 03:30，GFS最近3/每日7/每周4。见[新首轮与timer回执](completion/20261109-prod-db-scope/first-success-and-timer-enabled.json)及[当前中央入口](completion/20261109-prod-db-scope/README.md)。

其他数据均不纳入自动：不备VM/OS、测试数据、Redis/Rabbit、Nexus、Penpot、NAS、Ops或CF文件，220发布私钥继续只留220。旧11来宾全机job已disabled、旧whole-VM告警组已退役；原19,747,582,801 bytes全机归档和21回退档保留，不自动删除。新指标`dell_prod_db_backup_*`及三条db-only规则已原生校验/热载，原Prom身份、既有三告警名和Lark接收对象不变、无人工testsend，见[规则回执](completion/20261109-prod-db-scope/alerts-installed.json)。这是同机应用逻辑备份，不是VM快照；仅下述小档已临时隔离恢复、未迁移，未签业务恢复/RPO/RTO或异机灾备，Java不启、Nexus不合并、Mac外部探针不需要。

此前[11档全机首轮成功](completion/20261109/backup-first-success.json)及15:56启用是历史事实，已被用户最新“仅正式数据库/Nacos配置”范围取代；原`dell-local-nightly`不再启用，旧[pve-local实现](infra/backup/pve-local/README.md)退役不可重跑。CF历史档只留PVE，任何旧档/配置均不得因此导出。

硬件长期稳定、独立目的地/完整业务恢复与RPO/RTO、真实TV/PS/公网HTTPS仍按原范围另验；OW完整规则只留本地，不触/不上传。

**仅这份3301B `nacos_prod`小快照已完成VM210临时隔离恢复**：12表10行，活跃`config_info`为空，10行为历史、命名空间及认证/权限元数据。源备份SHA、timer及VM210原4服务保持、临时资源已清理；不扩签业务库、RPO/RTO或异机灾备，见[限定恢复收尾](completion/20261109-prod-db-restore/README.md)。

## 全部主题文档

| 分类 | 文档 |
| --- | --- |
| 状态与方案 | [01状态](01-current-state.md)、[02架构](02-architecture.md)、[03模板](03-templates-and-access.md)、[04应用迁移](04-services-and-migration.md)、[05NAS](05-home-nas.md) |
| 验收与实施 | [06验收](06-acceptance.md)、[07任务](07-implementation-and-tasks.md)、[08硬件](08-hardware-findings.md)、[09进展](09-implementation-progress.md)、[10恢复门禁](10-resume-after-approval.md) |
| 交接与交付 | [11当前交接](11-live-handoff.md)、[12访问](12-service-access-and-operations.md)、[13阶段范围](13-phase-scope.md)、[14交付报告](14-delivery-report.md) |
| 现网与运维 | [15网络](15-network19-delivery.md)、[16VPN](16-wireguard-access.md)、[17发布与制品合并](17-publish-artifact-consolidation.md)、[18清理结果](18-cleanup-and-consolidation.md)、[19人工手册](19-manual-operations.md)、[20Git交接](20-git-and-handoff.md) |
| 详细技术记录 | [应用备份](infra/backup/README.md)、[数据](infra/data/README.md)、[Nexus](infra/nexus/README.md)、[Penpot](infra/penpot/README.md)、[NAS](infra/nas/README.md)、[Ops](infra/ops/README.md)、[发布链](infra/publisher/README.md)、[19网实施](network19/README.md)、[本轮清理](cleanup/README.md) |

17号文档统一定义发布与制品合并后的服务归属。详细技术记录中的旧网段、旧数量与旧审批状态均属于对应历史阶段；新一轮操作必须从当前交接和人工手册进入。

本轮本地整理与检查范围见[文档交付记录](evidence/documentation-closeout-20261107.json)。该记录只证明文档与Git候选检查，不是硬件恢复或远程服务验收。

## 测试数据与访问的后续交付

用户后续精确授权的测试Nacos配置迁移见[36配置交付](completion/20261109-nacos-config-import/README.md)；本机两份Puyu数据库迁入210见[数据库交付](completion/20261109-puyu-db-migration/README.md)，源库保留、没有应用连接切换。受信LAN访问策略见[全服务规则](network19/lan-trusted-20261109/README.md)。测试三组件凭据固定为用户指定约定，实施与核验见[凭据记录](completion/20261109-test-credentials/README.md)；文档和Git不保存真实值。正式服务、自动备份范围、Nexus独立部署与Java停用合同不因这些测试操作改变。

## 每台机器对应Git仓库

新增[完整Git来源总览](machines/GIT-REPOSITORIES.md)及17份逐机`GIT-REPOSITORIES.md`，统一登记配置仓库、现役/候选应用源码、组件上游与取码身份。Penpot专属key临时clone验证已通过，但远端main仍缺现役两条改造；不会据此更新程序。发布机后续取deploy＋5个Puyu后端，running收制品，Jellyfin fork仍待接入。
