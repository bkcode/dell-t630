> 更新：2026-11-10（Asia/Shanghai）。本轮基础fresh审计已复核；当日实时收尾状态统一见[11月9日交付记录](../../completion/20261109-prod-db-scope/README.md)。11月10日用户新增授权的免登录导航已部署，详见下方；其余不迁移数据、不合并Nexus、不启动Java业务、不升级Penpot，不需要Mac外部探针。

# VM220 · publish-service

## Puyu local发布器与MCP：2026-11-10已安装

VM220已从`bkcode/deploy-public main`通过专属Git身份拉取到`/opt/deploy-public`，最终`f3991ad` clean；以ub运行`puyu-deploy-mcp.service`，仅127.0.0.1:18765，enabled/active。5后端服务与commonlib源码main已拉取；bff-admin在用户后续新增登记DeployKey后接入。Linux60测试通过，MCP匿名401/Origin403、4工具、5服务只读预检通过；真实发布关闭，旧forced-chain保持fenced，未构建或启动Java。

真实YAML在VM220 `/opt/deploy-public/config.local.yaml`（ub600/ignored），MCPkey只留服务器。源码/产物/队列在现有100GiB构建盘`/srv/dell-build/deploy-public`专属目录，带UUID启动门禁。初次公开门禁目录权限导致启动失败已纠正为root0755；密钥目录700/文件600不变，日志和修正证据保留。导航PID18640仍保持，不合并Nexus、不修改原publisher私钥/链、不做220整机备份。

[本轮交付与验收](../../evidence/deploy-public-publisher-20261110/README.md)；[源码安装手册](https://github.com/bkcode/deploy-public/blob/main/docs/PUBLISHER.md)。下文旧“尚未clone/待接入Puyu”属于此前阶段，不得据它覆盖当前私有配置或重跑安装。


Git来源唯一入口：**[GIT-REPOSITORIES.md](GIT-REPOSITORIES.md)**（来源/计划与已部署状态分开；不表示本机已clone或已分发key）。

## 2026-11-10新增免登录导航

当前 **[http://192.168.19.30:9080/](http://192.168.19.30:9080/)**，按用户要求取消导航HTTPS，移除“个人内网 / 服务导航”顶部栏、压缩标题/外侧留白并采用全宽布局。只预览14个Web入口，支持搜索/分组/环境筛选/复制与外链跳转，无账号密码、CRUD或健康探测；目标各自认证保持；自建应用默认HTTP，FileBrowser已切HTTP但仍需原账号密码，PVE/iDRAC内置HTTPS本轮保留。只部署 `bkcode/deploy/service-directory` 当前提交 `d56cae553bf95ce0e2c3fe8f258a2f99389aae7c`，不表示五个Puyu后端已上线或publisher解冻。

Python3原生unit `dell-service-directory.service`、OS用户 `servicedirectory` UID/GID2001只读运行；Linux进程身份不是页面登录账号。root-owned固定release为 `/opt/dell/service-directory/releases/d56cae553bf95ce0e2c3fe8f258a2f99389aae7c/`，manifest在 `/etc/dell-service-directory/`。显式 `--http`，不加载TLS或登录凭据，无应用状态。旧证书/私钥仅留未启用历史，不再配置TLS LoadCredential。专属firewall unit只管理自有nft输入表9080来源，允许LAN21/24、WG10.66.66/24、本机19.30/lo，不改PVE或路由。

最新[统一内网HTTP交付](../../evidence/internal-http-20261110/README.md)、[导航链接应用](../../evidence/internal-http-20261110/navigation-links-applied.json)与[14:28最终后检](../../evidence/internal-http-20261110/final-postcheck.json)通过，FileBrowser链接改HTTP、14条清单/topbar0/fullwidth保持，原服务不变；ddccc2b只保留为此前布局验证阶段。`63b8c08`的[原生/重启/浏览器/TLS验收](../../evidence/service-directory-20261110/README.md)保留为首次历史。[使用手册](../../evidence/service-directory-20261110/usage-manual.md)已改HTTP操作。源码本机提交未push，原4条用户提交未捎带发布；后续取已审查精确提交，不git pull旧main覆盖。清单维护只重启导航，不调用业务发布链。原4CPU/4GiB、build盘和Nexus standby边界保持。

## 本轮只读状态与备份归属

14:43:07媒体工具采样：仍4vCPU/4GiB、唯一19.30、原build盘UUID，Docker为空、无active Nexus或31 alias；publisher权限/私钥仅stat、未读取。业务仍fenced，不发布JAR或Nacos，不把合并目标当实际。 证据：[本机分项审计](../../completion/20261109/media-audit.json)。

本机全部数据及发布私钥均不纳入自动备份，发布私钥继续只留220；不能wholebackup/snapshot220。 现行仅正式DB/Nacos逻辑SQL导出（非VM snapshot），PVE落点`/mnt/pve/store/dell-artifacts/prod-db-backups` root700/600；新未列白名单数据库拒绝告警、需更新。03:30/GFS最近3＋每日7＋每周4，首轮3301B与timer见[新回执](../../completion/20261109-prod-db-scope/first-success-and-timer-enabled.json)，实际监控/收尾统一见[新中央入口](../../completion/20261109-prod-db-scope/README.md)。旧11来宾job已disabled、原19,747,582,801B档与21回退档保留不自动删；仅[该3301B Nacos小档已在VM210临时隔离恢复](../../completion/20261109-prod-db-restore/README.md)，完整业务恢复/RPO/RTO/异机DR未签，不迁移/合并/启Java、无Mac探针。

本目录是每机公开合同与来源索引，**不提供秘密或可直接重放的完整部署包**。source of truth为[plan.json](../../plan.json)；11月7日02:35为历史综合基线、UEFI0058为历史事故；用户确认内存处理/诊断通过，11月9日按本页新证据fresh复核，未重验全部应用内容。

## 职责与实际合同

构建/受限发布工具链和匿名只读服务导航，publisher→测试基础19.45；当前业务发布fenced，不启动Java业务。

- 实际资源：4 vCPU / 4 GiB；管理/服务地址 `192.168.19.30`，vmbr19、/24、GW/DNS19.1。
- 数据盘：100 GiB / store；`/srv/dell-build`；UUID `16dc6067-56ef-4687-a314-edc6421f9ed4`。
- 启停登记：order30、up15s/down60s；延时不代替健康。
- Docker：Engine29.9.3 / Compose5.7.0，该角色driver `overlay2`。这是角色specific已验配置，不能拿其它角色/模板profile盲套。

## unit / Compose与依赖

- `dell-service-directory.service` 与 `dell-service-directory-firewall.service`（原生Python3，只读导航）。
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
