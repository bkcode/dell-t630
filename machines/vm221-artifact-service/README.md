> 2026-11-08恢复：本机已完成基础存活/地址/服务检查，详见[恢复记录](../../recovery/20261108/README.md)；本轮不迁移、不升级应用，不需要Mac外部探针。下列旧验收/暂停描述按原时点解释，配置与最新检查见config.json。

# VM221 · artifact-service

本目录是每机公开合同与来源索引，**不提供秘密或可直接重放的完整部署包**。source of truth为[plan.json](../../plan.json)；最后成功验收为2026-11-07 02:35:01+08:00。11月7日曾因UEFI0058暂停；11月8日用户确认内存已处理且诊断通过，本机恢复检查见顶部记录。

## 职责与实际合同

当前独立Nexus制品仓库，原新身份/EULA/本地hosted数据保持；客户端URI31。

- 实际资源：2 vCPU / 4 GiB；管理/服务地址 `192.168.19.31`，vmbr19、/24、GW/DNS19.1。
- 数据盘：100 GiB / store；`/srv/nexus`；UUID `239dc45a-b1f3-408b-a8ef-7afa77b52204`。
- 启停登记：order21、up90s/down180s；延时不代替健康。
- Docker：Engine29.9.3 / Compose5.7.0，该角色driver `overlay2`。这是角色specific已验配置，不能拿其它角色/模板profile盲套。

## unit / Compose与依赖

- `dell-nexus.service`；运行Compose路径：`/opt/dell/nexus/compose.yaml`, `/opt/dell/nexus/compose.mount-gated.yaml`。

- /srv/nexus原ext4 UUID与UID/GID200数据树；RequiresMountsFor/BindsTo Docker+mount。
- backend internal:true，gateway只固定反代nexus:8081；管理凭据root600，不查询/迁入旧proxy认证。

## 维护与安全

- 当前2vCPU/4GiB、19.31独立归221，尚未向220移盘/地址。
- 原49GAV/234primary SHA、35metadata语义/1076checksum是已验基线，fresh核对时不得删合法新增凑数量。
- 合并知情维护授权已满足，但用户当前暂停硬件及合并；本轮不执行停服/whole221冷备或move-disk，等待用户将来明确恢复迁移。
- 11月8日已按用户恢复指令完成基础检查；新的变更仍须在当前范围内核实，F1本身不代表修复。PVE写/VMID/IP/数据盘归属由root统一，严格SSH/ub管理，不关闭hostkey检查、不复制私钥。
- 目录不含任何.env、secrets、Webhook或key；只引用公开合同和历史证据。CF备份只PVE、发布私钥只220，不能wholebackup220或把private打包提交Git。
- 日常流程见[人工操作手册](../../19-manual-operations.md)与[访问入口](../../12-service-access-and-operations.md)；只读[本机config.json](config.json)与[config-sources.json](config-sources.json)核对，不盲重跑初始化器。

## 生命周期

`pending-retirement`表示仅在未来220合并、原数据/身份/网络与监控验收后才退役；当前不是retired，19.31配置仍属于独立221。见[17目标合同](../../17-publish-artifact-consolidation.md)。源unit停服、冷备、关机与移盘尚未执行，不能凭候选材料提前删VM或监控target。

## 配置来源与限制

本目录没有configs快照。某些仓库infra准备文件仍含旧10.63地址或旧默认值，索引已标historical-evidence，不能视作现役完整配置。只有path存在和SHA可复核，不等于当前guest文件逐字相等；硬件故障后须fresh验。pending-candidate仅未来方案，不能冒作active。

- [plan.json](../../plan.json) · `current-contract`：当前资源/地址/数据卷合同唯一来源；运行状态未在硬件故障后复验。
- [11-live-handoff.md](../../11-live-handoff.md) · `current-contract`：最后验收与当前UEFI0058暂停时间线。
- [12-service-access-and-operations.md](../../12-service-access-and-operations.md) · `current-contract`：当前19网入口及凭据保管规则。
- [19-manual-operations.md](../../19-manual-operations.md) · `current-contract`：人工启停、硬件门禁、克隆、备份与受控恢复。
- [cleanup/final-live-check.json](../../cleanup/final-live-check.json) · `historical-evidence`：2026-11-07 02:35综合验收快照，不代表当前在线。
- [network19/services-media/nexus-post-cutover-verification.json](../../network19/services-media/nexus-post-cutover-verification.json) · `historical-evidence`：实际19.31下49GAV/234SHA/身份/EULA与GET-only验证。
- [infra/nexus/manage.py](../../infra/nexus/manage.py) · `historical-evidence`：监督/权限门禁源码结构参考，现役assignment/env需fresh读回；不能据其本地旧默认部署。
- [infra/nexus/compose.yaml](../../infra/nexus/compose.yaml) · `historical-evidence`：基础Compose源码必须叠mount overlay；不是完整现役参数快照。
- [infra/nexus/compose.mount-gated.yaml](../../infra/nexus/compose.mount-gated.yaml) · `historical-evidence`：restart=no叠层结构，单独存在不代表当前runtime。
- [cleanup/nexus/live-inventory.json](../../cleanup/nexus/live-inventory.json) · `historical-evidence`：实际source221 OS/UUID/监督/公开配置SHA及资源。
- [17-publish-artifact-consolidation.md](../../17-publish-artifact-consolidation.md) · `pending-candidate`：目标是未来并入220，验证后才退役221。
- [cleanup/nexus/resume-preflight.md](../../cleanup/nexus/resume-preflight.md) · `pending-candidate`：硬件恢复后的fresh检查/冷备移盘和监控10→9检查点。
