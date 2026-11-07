# VM250 · penpot-service

本目录是每机公开合同与来源索引，**不提供秘密或可直接重放的完整部署包**。source of truth为[plan.json](../../plan.json)；最后成功验收为2026-11-07 02:35:01+08:00。当前服务器因UEFI0058/DIMM_B1问题由用户暂停，current_runtime_verified=false，以下均不是live在线声明。

## 源码仓库：bkcode/penpot · main

使用 **[bkcode/penpot](https://github.com/bkcode/penpot) 的 `main` 分支**，HTTPS为`https://github.com/bkcode/penpot.git`，SSH为`git@github.com:bkcode/penpot.git`。服务器只读取码；显式指定main，不跟随默认分支或改用官方上游。最后验收commit为`ff1783e7865af7aae571c985f03e057631b7af63`，不代表远端main最新位置。

详细更新与版本保留流程见[源码与更新说明](SOURCE-AND-UPDATES.md)，机器可读合同见[git-source.json](git-source.json)。PAT自动认证后续单独处理，本轮未取码、构建或部署。

## 职责与实际合同

Git改造Penpot与常驻worker/import/MCP服务，保存3活动设计和原素材；源Mac/Git保留。

- 实际资源：6 vCPU / 16 GiB；管理/服务地址 `192.168.19.50`，vmbr19、/24、GW/DNS19.1。
- 数据盘：100 GiB / store；`/srv/penpot`；UUID `ccccda03-bffd-4054-afd3-e0e22f0c607e`。
- 启停登记：order22、up90s/down180s；延时不代替健康。
- Docker：Engine29.9.3 / Compose5.7.0，该角色driver `overlay2`。这是角色specific已验配置，不能拿其它角色/模板profile盲套。

## unit / Compose与依赖

- `dell-penpot.service`；运行Compose路径：`/opt/dell/penpot/compose.fresh.yaml`, `/opt/dell/penpot/runtime/health-supervision/compose.health-supervision.yaml`。

- /srv/penpot UUID、DockerRootDir与11image IDs/资源/mount清单；notify监督及BindsTo Docker+mount。
- 公开URI19.50:9001；worker/import内部frontend:8080，dnsproxy内部172.30.250.53→19.1:53。
- query-safe只读NGINX overlay；只记录path不泄露MCP查询token，不关闭认证。

## 维护与安全

- 6vCPU/16GiB；原Gitff1783e含两本地提交、目标worktree clean；不擅自升级2.19源码对应的运行依赖。
- 3设计data/revn/stats与原971媒体已迁，当前已验973包含2官方导出缓存；不能删除额外文件来凑971。
- 原新owner/worker/MCP身份保持，秘密仅guest受控文件；客户端旧Mac connector不会自动指向这里。
- 停启只用原unit，禁止fresh初始化、旧source.env/key复制或PG整库覆盖现有数据。
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
- [network19/services-media/penpot-post-cutover-verification.json](../../network19/services-media/penpot-post-cutover-verification.json) · `historical-evidence`：19.50新origin/Git/3设计/973媒体/原身份/MCP只读和既有job实测。
- [infra/penpot/runtime/health-supervision/README.md](../../infra/penpot/runtime/health-supervision/README.md) · `current-contract`：notify持续监督、11健康、镜像ID和受控恢复边界。
- [infra/penpot/runtime/health-supervision/evidence/final-runtime-contract.json](../../infra/penpot/runtime/health-supervision/evidence/final-runtime-contract.json) · `historical-evidence`：11服务资源/镜像/健康合同读回，时间限于证据点。
- [network19/services-media/PLAN.md](../../network19/services-media/PLAN.md) · `historical-evidence`：已执行迁网差异与原source文件说明；不重新执行旧stage/commit。
- [infra/penpot/compose.fresh.yaml](../../infra/penpot/compose.fresh.yaml) · `historical-evidence`：初装结构参考，含旧公开BIND/DoH；不能当作19.50现役完整文件复制部署。
- [infra/penpot/runtime/logging/README.md](../../infra/penpot/runtime/logging/README.md) · `current-contract`：MCP query-safe日志规则与不削弱认证的限制。
