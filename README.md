# Dell PowerEdge T630 部署与运维

本仓库保存 T630 / Proxmox VE 8.4 的部署方案、基础设施脚本、验收证据和人工操作手册。最后整理日期：**2026-11-07，Asia/Shanghai**。

**当前服务器工作已由用户暂停，等待内存硬件处理。** iDRAC 控制台停在 `UEFI0058` 不可纠正内存错误提示；此前 SEL 指向 `DIMM_B1`。PVE 尚未恢复可信连接，不能将历史验收的“运行正常”理解为当前在线。Nexus 合并已有明确维护授权，但尚未执行停服、迁盘或目标启动。

## 从这里开始

| 需要做什么 | 阅读入口 |
| --- | --- |
| 按每台机器查看配置与文档 | **[machines目录](machines/README.md)**：宿主、12来宾和3模板各自独立目录 |
| 人工值守、故障处理、启动、备份、克隆、未来合并 | **[人工操作手册](19-manual-operations.md)** |
| 接手本次暂停任务 | [当前交接与恢复条件](11-live-handoff.md) |
| 看完整服务器名称、地址、配置与作用 | [当前状态清单](01-current-state.md)、[机器可读规划](plan.json) |
| 查服务网址、SSH 与凭据保管位置 | [服务访问与日常操作](12-service-access-and-operations.md) |
| 理解路由、虚拟机、Docker 与隔离 | [架构](02-architecture.md)、[网络交付](15-network19-delivery.md)、[WireGuard](16-wireguard-access.md) |
| 查模板与家庭 NAS | [模板](03-templates-and-access.md)、[NAS](05-home-nas.md) |
| 看发布与Nexus合并后的目标架构 | **[17合并架构](17-publish-artifact-consolidation.md)**，目标只保留VM220 publish-service |
| 查已完成清理和未完成的 Nexus 合并 | [整理结果](18-cleanup-and-consolidation.md)、[合并恢复检查](cleanup/nexus/resume-preflight.md) |
| 查验收边界和结果 | [验收总览](06-acceptance.md)、[本轮整理验收](cleanup/acceptance.md) |
| 将仓库交给另一台电脑或下一位管理员 | [Git 与资料交接](20-git-and-handoff.md) |

## 服务目标：发布与制品仓库同机

目标中只保留一台 **VM220 `publish-service`（6vCPU / 8GiB）**：主IP19.30用于管理、构建和受限发布，同NIC的19.31:8081用于Nexus。`artifact-service`不再是目标中的独立VM；旧221验收后退役，既有服务DNS可作为逻辑兼容名保留。目标11实例/14监控目标，总43vCPU/85GiB不变。

**这是目标说明，迁移尚未执行。** 下方12实例表为最后实机快照，两者不能混算。详见[合并架构](17-publish-artifact-consolidation.md)。

## 最后一次成功验收的部署

2026-11-07 **02:35** 验收时：1 台物理服务器，**12 个运行实例（11 VM + 1 LXC）、3 份停止模板**，配置总额 43 vCPU / 85 GiB。**02:44:29** 最后一次成功操作 PVE，仅同步规划文件。09:32 起连接失败；随后控制台确认启动被内存错误拦住。完整时间线见[硬件记录](cleanup/hardware/DIMM_B1-incident.json)。

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

地址前缀为 `192.168.`。PVE 自身管理地址是 `192.168.21.22`，iDRAC 是 `192.168.21.21`。OpenWrt `21.1` 将 `19.0/24` 路由到 `21.23`；PVE 只做管理和二层桥，不做应用端口转发。WireGuard `10.66.66.0/24` 已获准访问服务器网段，应用登录权限继续生效。

模板仅保留 Linux `9010`、Docker `9001`、Java 验收 `9011`。9 台来宾和 3 份模板已安装 fish，默认 Bash；CF、Penpot、Ops 和 PVE 宿主排除。NAS 不另做模板。最后监控验收为 15/15 UP；**当前在线状态未复验**，Mac 外部探针保持停用。

## 文档与证据怎样使用

- `plan.json` 保存现有配置与下一步目标；当前暂停状态以本页、交接页及硬件记录为准。
- `cleanup/final-live-check.json`、网络及应用验收文件是带时间的历史证据，不能代替恢复后的现场检查。
- `infra/`、`network19/`、`cleanup/` 包含分阶段实施代码和旧候选，**不是可整体重跑的一键安装包**。
- `private/` 是本机受保护资料，已排除 Git。Git 不包含数据库、备份归档、服务密码或客户端私钥；新电脑仅克隆仓库不能直接恢复全部服务。
- 合并前维持 12 实例、15 监控目标。合并并验收后才更新为 11 实例、14 目标，不能提前改成完成。

本地检查（仓库根目录执行）：

```sh
python3 scripts/validate_machines.py
python3 scripts/validate_docs.py --json
python3 scripts/check_git_safety.py
```

当前仍待完成：内存维修与复验、Nexus 合并、宿主恢复后的全服务复验、长期独立备份与 RPO/RTO、真实电视/PS 使用验证、公网域名和 HTTPS。Java 业务上线不在当前范围。

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
