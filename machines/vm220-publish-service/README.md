> 更新：2026-11-09（Asia/Shanghai）。本轮基础fresh审计已复核；当日实时收尾状态统一见[11月9日交付记录](../../completion/20261109-prod-db-scope/README.md)。本页仅本地同步带时点证据，不执行服务器操作；不迁移数据、不合并Nexus、不启动Java业务、不升级Penpot，不需要Mac外部探针。

# VM220 · publish-service

## 本轮只读状态与备份归属

14:43:07媒体工具采样：仍4vCPU/4GiB、唯一19.30、原build盘UUID，Docker为空、无active Nexus或31 alias；publisher权限/私钥仅stat、未读取。业务仍fenced，不发布JAR或Nacos，不把合并目标当实际。 证据：[本机分项审计](../../completion/20261109/media-audit.json)。

本机全部数据及发布私钥均不纳入自动备份，发布私钥继续只留220；不能wholebackup/snapshot220。 现行仅正式DB/Nacos逻辑SQL导出（非VM snapshot），PVE落点`/mnt/pve/store/dell-artifacts/prod-db-backups` root700/600；新未列白名单数据库拒绝告警、需更新。03:30/GFS最近3＋每日7＋每周4，首轮3301B与timer见[新回执](../../completion/20261109-prod-db-scope/first-success-and-timer-enabled.json)，实际监控/收尾统一见[新中央入口](../../completion/20261109-prod-db-scope/README.md)。旧11来宾job已disabled、原19,747,582,801B档与21回退档保留不自动删；未restore/无异机DR，不迁移/合并/启Java、无Mac探针。

本目录是每机公开合同与来源索引，**不提供秘密或可直接重放的完整部署包**。source of truth为[plan.json](../../plan.json)；11月7日02:35为历史综合基线、UEFI0058为历史事故；用户确认内存处理/诊断通过，11月9日按本页新证据fresh复核，未重验全部应用内容。

## 职责与实际合同

构建/受限发布工具链，publisher→测试基础19.45；当前业务发布fenced，不启动Java业务。

- 实际资源：4 vCPU / 4 GiB；管理/服务地址 `192.168.19.30`，vmbr19、/24、GW/DNS19.1。
- 数据盘：100 GiB / store；`/srv/dell-build`；UUID `16dc6067-56ef-4687-a314-edc6421f9ed4`。
- 启停登记：order30、up15s/down60s；延时不代替健康。
- Docker：Engine29.9.3 / Compose5.7.0，该角色driver `overlay2`。这是角色specific已验配置，不能拿其它角色/模板profile盲套。

## unit / Compose与依赖

- `/usr/local/bin/dell-publish`。
- `prometheus-node-exporter.service`。
- `dell-guest-health.timer`。

- 原构建盘UUID和受限client profile；target19.45/source19.30与forced-command规则。
- Docker仅为空runtime/原两镜像缓存，不含正在运行的Nexus容器；不将publisher加入docker组。

## 维护与安全

- 不运行stage/activate/rollback业务发布；baseline_migrated=false继续冻结。
- 只stat发布私钥元数据；不读取、复制、导出它，不wholebackup或snapshot220夹带它。
- 当前4vCPU/4GiB且只有19.30；已完成11月8日基础复验。
- 11月9日已fresh复核基础状态；新的变更仍须在当前范围内核实，F1本身不代表修复。PVE写/VMID/IP/数据盘归属由root统一，严格SSH/ub管理，不关闭hostkey检查、不复制私钥。
- 目录不含任何.env、secrets、Webhook或key；只引用公开合同和历史证据。CF备份只PVE、发布私钥只220，不能wholebackup220或把private打包提交Git。
- 日常流程见[人工操作手册](../../19-manual-operations.md)与[访问入口](../../12-service-access-and-operations.md)；只读[本机config.json](config.json)与[config-sources.json](config-sources.json)核对，不盲重跑初始化器。

## 合并目标，仅候选

实际仍是4CPU/4GiB、primary19.30、无31 alias、无active Nexus。未来目标为6CPU/8GiB、primary30+服务alias31及原Nexus盘；见[17目标合同](../../17-publish-artifact-consolidation.md)。私有standby存在不等于已合并，当前用户明确不迁移，不能mount/commit/start。

## 配置来源与限制

本目录没有configs快照。某些仓库infra准备文件仍含旧10.63地址或旧默认值，索引已标historical-evidence，不能视作现役完整配置。只有path存在和SHA可复核，不等于当前guest文件逐字相等；源文件与guest的逐字一致性未由索引SHA证明，后续维护仍须fresh核。pending-candidate仅未来方案，不能冒作active。

- [plan.json](../../plan.json) · `current-contract`：当前资源/地址/数据卷合同唯一来源；基础运行状态已在11月9日分项复验；不代表全部应用数据/认证通过。
- [11-live-handoff.md](../../11-live-handoff.md) · `current-contract`：当前不迁移范围、11月9日证据入口及历史UEFI0058时间线。
- [12-service-access-and-operations.md](../../12-service-access-and-operations.md) · `current-contract`：当前19网入口及凭据保管规则。
- [19-manual-operations.md](../../19-manual-operations.md) · `current-contract`：人工启停、硬件门禁、克隆、备份与受控恢复。
- [cleanup/final-live-check.json](../../cleanup/final-live-check.json) · `historical-evidence`：2026-11-07 02:35综合验收快照，不代表当前在线。
- [infra/publisher/README.md](../../infra/publisher/README.md) · `current-contract`：发布受限权限合同；实际安装以deployed和已读回SHA为准。
- [cleanup/nexus/docker220-prepare-result.json](../../cleanup/nexus/docker220-prepare-result.json) · `historical-evidence`：220经典Docker软件准备成功，0containers/无Nexus/无alias31。
- [cleanup/nexus/preparation-readback.json](../../cleanup/nexus/preparation-readback.json) · `historical-evidence`：实际public文件SHA、standby模式布尔、发布key仅stat。
- [network19/services-core/publisher220-key-hostalias-final-readback.json](../../network19/services-core/publisher220-key-hostalias-final-readback.json) · `historical-evidence`：19.30来源/19.45目标及受信key合同迁网读回，不是业务发布许可。
- [17-publish-artifact-consolidation.md](../../17-publish-artifact-consolidation.md) · `pending-candidate`：合并目标6CPU8GiB+服务alias31；尚未移交。
- [cleanup/nexus/PLAN.md](../../cleanup/nexus/PLAN.md) · `pending-candidate`：未来冷备/唯一盘/网络alias/应用切换计划。
- [cleanup/nexus/target.py](../../cleanup/nexus/target.py) · `pending-candidate`：后续应用执行器，不能把已有standby阶段当已完成合并。
