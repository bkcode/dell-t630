> 更新：2026-11-09（Asia/Shanghai）。本轮基础fresh审计已复核；当日实时收尾状态统一见[11月9日交付记录](../../completion/20261109-prod-db-scope/README.md)。本页仅本地同步带时点证据，不执行服务器操作；不迁移数据、不合并Nexus、不启动Java业务、不升级Penpot，不需要Mac外部探针。

# PVE物理宿主pve

Git来源唯一入口：**[GIT-REPOSITORIES.md](GIT-REPOSITORIES.md)**（来源/计划与已部署状态分开；不表示本机已clone或已分发key）。

## 本轮只读状态与备份归属

14:24:03自然重启后的14:42–14:44采样：12来宾running、3模板stopped，EDAC CE/UE0、RAID1/5 Optl/5盘Onln；三个forward guard SHA保持，networking→bridge/ExecStartPost→pve-guests真实顺序成功，双栈all/default/全部接口forward0、无host NAT。用户报告内存处理/诊断通过不等于本轮独立离线诊断。 证据：[本机分项审计](../../completion/20261109/pve-audit.json)。

本机承载正式DB备份控制器与目标目录，不是PVE宿主OS或全机备份。 现行仅正式DB/Nacos逻辑SQL导出（非VM snapshot），PVE落点`/mnt/pve/store/dell-artifacts/prod-db-backups` root700/600；新未列白名单数据库拒绝告警、需更新。03:30/GFS最近3＋每日7＋每周4，首轮3301B与timer见[新回执](../../completion/20261109-prod-db-scope/first-success-and-timer-enabled.json)，实际监控/收尾统一见[新中央入口](../../completion/20261109-prod-db-scope/README.md)。旧11来宾job已disabled、原19,747,582,801B档与21回退档保留不自动删；仅[该3301B Nacos小档已在VM210临时隔离恢复](../../completion/20261109-prod-db-restore/README.md)，完整业务恢复/RPO/RTO/异机DR未签，不迁移/合并/启Java、无Mac探针。

**以下仍是配置合同与带日期基础审计，不是全量现场配置导出。** 合同来自[plan](../../plan.json)，11月7日02:35/02:44及UEFI0058/B1保留历史；用户11月8日确认内存处理/诊断通过，11月9日已fresh检查当前boot。助手未独立离线诊断或清SEL，不把EDAC0/可达扩大为唯一物理根因已排除或应用数据全部正确。

本机资料：[配置合同](config.json)、[安全来源索引](config-sources.json)。56是宿主逻辑处理器，28物理核；125GiB是保守规划额度；本轮MemTotal约125.781GiB、SMBIOS四条32GB，额度和实测口径分开。iDRAC独立管理面21.21能访问不代表PVE/来宾已上线。

## 网络与存储合同

- vmbr0管理21.22/24，eno1，默认21.1；SSH22/UI8006。vmbr19为无宿主IPv4/IPv6的纯L2桥，只有190WAN使用21.23。
- hostforward全部0、无应用NAT；bridge dell19_acl继续负责同19网MAC/IP/角色隔离。宿主19客户端路由via21.23不是给其它设备三层转发。网关见[VM190](../vm190-network-gateway/README.md)。
- H730管理SSD RAID1/HDD RAID5；本轮两VD Optl/五盘Onln/BBUOptimal，不能以控制器状态代替文件系统/应用内容全量一致性验证。PVE拥有阵列/store，不能给NAS重复挂同一已挂块设备。
- 本轮PVE审计12运行实例（11VM+1LXC）+3停止模板，43vCPU/85GiB为配置额；15UP由Ops分项审计采样，均有时点，不是永久健康保证。

日常维护遵守[交接](../../11-live-handoff.md)、[硬件发现](../../08-hardware-findings.md)和[人工手册](../../19-manual-operations.md)。Nexus历史许可保留，但当前明确不迁移、不执行合并。此目录只索引公开合同/旧证据，没有复制可能过时的nft/10.63配置、凭据或盘归档。

## 已补齐的公开配置

11月8日转发守卫已安装，三份非秘密快照保存在[configs](configs/)，来源与宿主路径见config-sources.json。**11月9日14:24自然重启后已实际验证持久性**：三个SHA保持、networking14:24:12→bridge/ExecStartPost成功14:24:15→pve-guests14:24:18，双栈all/default/全部接口forward0；原管理interfaces/路由/ACL与无NAT保持。见[本轮PVE审计](../../completion/20261109/pve-audit.json)。本页更新不触发额外重启。另[空闲iperfserver已停用](../../completion/20261109/idle-iperf-disabled.json)、5201关闭、工具包保留。
