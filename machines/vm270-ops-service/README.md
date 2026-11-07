# VM270 · ops-service

本目录是每机公开合同与来源索引，**不提供秘密或可直接重放的完整部署包**。source of truth为[plan.json](../../plan.json)；最后成功验收为2026-11-07 02:35:01+08:00。当前服务器因UEFI0058/DIMM_B1问题由用户暂停，current_runtime_verified=false，以下均不是live在线声明。

## 职责与实际合同

Prometheus/Grafana/Alertmanager/Blackbox及服务器内部Lark通知；对10 guest与PVE元数据进行监控。

- 实际资源：2 vCPU / 4 GiB；管理/服务地址 `192.168.19.70`，vmbr19、/24、GW/DNS19.1。
- 数据盘：32 GiB / store；`/srv/dell-data`；UUID `01b1f302-27be-4fbd-b4af-b8e782d85dea`。
- 启停登记：order20、up30s/down60s；延时不代替健康。
- Docker：Engine29.9.3 / Compose5.7.0，该角色driver `overlay2`。这是角色specific已验配置，不能拿其它角色/模板profile盲套。

## unit / Compose与依赖

- `dell-ops.service`；运行Compose路径：`/opt/dell/ops/compose.yaml`。
- `dell-lark-notify.service`。

- /srv/dell-data原UUID与/srv/dell-data/ops，Mount/Docker持续监督；四组件所有镜像固定AMD64。
- 既有172.18静态docker IPAM与AM本地认证bridge；公网Lark严格TLS及白名单，不输出hook/token。
- 10角色catalog/installer与source成对，PVE只读QGA路径，不增加宿主Docker/监听。

## 维护与安全

- 2vCPU/4GiB，last02:35为10node+5own=15/15UP；不是当前实时状态。
- 当前Nexus221未退役，不提前改成9node/14targets；未来合并走新配套窗口。
- Lark仅机内active；Mac外部探针明确停用，整机失效时不保证独立外发。
- 不因目标暂down删target或伪造UP；维护结束只取消本次静默，不重发验收消息。
- 硬件稳定、用户明确恢复执行和fresh核验之前不远程变更；F1不能当修复。PVE写/VMID/IP/数据盘归属由root统一，严格SSH/ub管理，不关闭hostkey检查、不复制私钥。
- 目录不含任何.env、secrets、Webhook或key；只引用公开合同和历史证据。CF备份只PVE、发布私钥只220，不能wholebackup220或把private打包提交Git。
- 日常流程见[人工操作手册](../../19-manual-operations.md)与[访问入口](../../12-service-access-and-operations.md)；只读[本机config.json](config.json)与[config-sources.json](config-sources.json)核对，不盲重跑初始化器。

## 配置来源与限制

本目录没有configs快照。某些仓库infra准备文件仍含旧10.63地址或旧默认值，索引已标historical-evidence，不能视作现役完整配置。只有path存在和SHA可复核，不等于当前guest文件逐字相等；硬件故障后须fresh验。pending-candidate仅未来方案，不能冒作active。

- [plan.json](../../plan.json) · `current-contract`：当前资源/地址/数据卷合同唯一来源；运行状态未在硬件故障后复验。
- [11-live-handoff.md](../../11-live-handoff.md) · `current-contract`：最后验收与当前UEFI0058暂停时间线。
- [12-service-access-and-operations.md](../../12-service-access-and-operations.md) · `current-contract`：当前19网入口及凭据保管规则。
- [19-manual-operations.md](../../19-manual-operations.md) · `current-contract`：人工启停、硬件门禁、克隆、备份与受控恢复。
- [cleanup/final-live-check.json](../../cleanup/final-live-check.json) · `historical-evidence`：2026-11-07 02:35综合验收快照，不代表当前在线。
- [cleanup/monitoring/ten-role/final-Prometheus-readback.json](../../cleanup/monitoring/ten-role/final-Prometheus-readback.json) · `historical-evidence`：最新10node+5own15/15UP且221保留，非当前在线。
- [cleanup/monitoring/ten-role/execution-status.json](../../cleanup/monitoring/ten-role/execution-status.json) · `historical-evidence`：十guest/source配套实际应用，原health/collector/timer保持。
- [infra/ops/guest-baseline/guest-targets.json](../../infra/ops/guest-baseline/guest-targets.json) · `current-contract`：当前公开十角色catalog；未来221退役须成对变更，不烘焙秘密。
- [infra/ops/lark-notify/README.md](../../infra/ops/lark-notify/README.md) · `current-contract`：现役机内Lark约束、真实双phase送达及至少一次语义。
- [infra/ops/compose.yaml](../../infra/ops/compose.yaml) · `historical-evidence`：公开四组件/IPAM/secret引用结构，缺受控运行文件不能直接up。
- [cleanup/monitoring/ten-role/future-merge-contract.json](../../cleanup/monitoring/ten-role/future-merge-contract.json) · `pending-candidate`：未来Nexus合并10→9基线门禁，当前不可当已实施。
- [infra/ops/mac-external-probe/README.md](../../infra/ops/mac-external-probe/README.md) · `historical-evidence`：用户明确停用的外部探针与误告警更正历史，禁止据此恢复任务。
