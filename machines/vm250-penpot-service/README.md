> 更新：2026-11-10（Asia/Shanghai）。个人浏览器记忆方案已撤回；新授权原UI默认填入已通过LAN浏览器与原生验收，核心Git/镜像更新仍等待用户推送；此前基础fresh审计已复核；当日实时收尾状态统一见[11月9日交付记录](../../completion/20261109-prod-db-scope/README.md)。本页仅本地同步带时点证据，不执行服务器操作；不迁移数据、不合并Nexus、不启动Java业务、不升级Penpot核心或镜像，不需要Mac外部探针。

# VM250 · penpot-service

Git来源唯一入口：**[GIT-REPOSITORIES.md](GIT-REPOSITORIES.md)**（来源/计划与已部署状态分开；不表示本机已clone或已分发key）。

## 原UI默认填入（2026-11-10新明确授权）

用户要求原UI、不新增逻辑，并[明确授权](../../evidence/penpot-login-prefill-20261110/explicit-approval.json)LAN21/24、WG10.66.66/24、VM250 self19.50/loopback的未登录访客可读取原owner密码并默认填入。现役沿用ff原helper与表单，只换原JSON运行secret来源、加一个NGINX来源ACL只读挂载并同步监督lock；CF19.5/其他来源拒绝。不新增checkbox/forget/localStorage、不build/换镜像、不取新码、不重置owner/MCP或改设计。打开原页刷新、点击原“继续/登录”，不自动提交。

此前个人浏览器记忆UI/逻辑已[16:05恢复原样](../../evidence/penpot-browser-remember-20261110/restored-original.json)，11healthy、ff clean及镜像保持；其说明只作已撤回历史。[16:13应用](../../evidence/penpot-login-prefill-20261110/approved-applied.json)、[16:19原生后检](../../evidence/penpot-login-prefill-20261110/native-postcheck.json)与[真实LAN浏览器](../../evidence/penpot-login-prefill-20261110/browser-acceptance.json)已通过：11healthy、镜像match lock、Git ff1783e clean、无remember挂载；四种未授权Docker/伪造头请求403。原表单默认值匹配原owner、密码masked，原Continue可登录dashboard，无新增控件；测试cookies/localStorage清理、session关闭。当前WG/CF端到端未签。原账号密码保留，实际值只在受保护Mac/guest文件及guest0600运行JSON，不入文档/Git。源Git更新仍等用户推两条既有改造的独立门禁，详见[本次证据](../../evidence/penpot-login-prefill-20261110/README.md)与[手册](../../evidence/penpot-login-prefill-20261110/usage-manual.md)。

## 本轮只读状态与备份归属

14:43:07媒体工具采样：原数据UUID、11容器running/healthy/RestartCount0，原镜像/容器IDs保持，原健康GET通过，Git仍ff1783e clean；本轮未更新main、不重验设计/素材/MCP内容或SMTP。 证据：[本机分项审计](../../completion/20261109/media-audit.json)。

本机VM/OS及应用数据不纳入现行自动备份；不因旧whole-VM名单而重新启用。 现行仅正式DB/Nacos逻辑SQL导出（非VM snapshot），PVE落点`/mnt/pve/store/dell-artifacts/prod-db-backups` root700/600；新未列白名单数据库拒绝告警、需更新。03:30/GFS最近3＋每日7＋每周4，首轮3301B与timer见[新回执](../../completion/20261109-prod-db-scope/first-success-and-timer-enabled.json)，实际监控/收尾统一见[新中央入口](../../completion/20261109-prod-db-scope/README.md)。旧11来宾job已disabled、原19,747,582,801B档与21回退档保留不自动删；仅[该3301B Nacos小档已在VM210临时隔离恢复](../../completion/20261109-prod-db-restore/README.md)，完整业务恢复/RPO/RTO/异机DR未签，不迁移/合并/启Java、无Mac探针。

本目录是每机公开合同与来源索引，**不提供秘密或可直接重放的完整部署包**。source of truth为[plan.json](../../plan.json)；11月7日02:35为历史综合基线、UEFI0058为历史事故；用户确认内存处理/诊断通过，11月9日按本页新证据fresh复核，未重验全部应用内容。

## 源码仓库：bkcode/penpot · main

Git/main/历史bundle与更新边界统一见上方Git来源页。最新[管理Mac读取与临时工作树验证](../../evidence/git-repositories-20261110/penpot-deploy-key-verification.json)并未部署服务器；[13:20来宾只读现场](../../evidence/git-repositories-20261110/penpot-runtime-readonly.json)仍main/ff1783e、clean、无origin，11容器healthy。unit累计NRestarts22按原证据解释，本任务未诊断或启停；不能称远端main已上线或直接取码已配置。

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
- 11月9日已fresh复核基础状态；新的变更仍须在当前范围内核实，F1本身不代表修复。PVE写/VMID/IP/数据盘归属由root统一，严格SSH/ub管理，不关闭hostkey检查、不复制私钥。
- 目录不含任何.env、secrets、Webhook或key；只引用公开合同和历史证据。CF备份只PVE、发布私钥只220，不能wholebackup220或把private打包提交Git。
- 日常流程见[人工操作手册](../../19-manual-operations.md)与[访问入口](../../12-service-access-and-operations.md)；只读[本机config.json](config.json)与[config-sources.json](config-sources.json)核对，不盲重跑初始化器。

## 配置来源与限制

本目录没有configs快照。某些仓库infra准备文件仍含旧10.63地址或旧默认值，索引已标historical-evidence，不能视作现役完整配置。只有path存在和SHA可复核，不等于当前guest文件逐字相等；源文件与guest的逐字一致性未由索引SHA证明，后续维护仍须fresh核。pending-candidate仅未来方案，不能冒作active。

- [plan.json](../../plan.json) · `current-contract`：当前资源/地址/数据卷合同唯一来源；基础运行状态已在11月9日分项复验；不代表全部应用数据/认证通过。
- [11-live-handoff.md](../../11-live-handoff.md) · `current-contract`：当前不迁移范围、11月9日证据入口及历史UEFI0058时间线。
- [12-service-access-and-operations.md](../../12-service-access-and-operations.md) · `current-contract`：当前19网入口及凭据保管规则。
- [19-manual-operations.md](../../19-manual-operations.md) · `current-contract`：人工启停、硬件门禁、克隆、备份与受控恢复。
- [cleanup/final-live-check.json](../../cleanup/final-live-check.json) · `historical-evidence`：2026-11-07 02:35综合验收快照，不代表当前在线。
- [network19/services-media/penpot-post-cutover-verification.json](../../network19/services-media/penpot-post-cutover-verification.json) · `historical-evidence`：19.50新origin/Git/3设计/973媒体/原身份/MCP只读和既有job实测。
- [infra/penpot/runtime/health-supervision/README.md](../../infra/penpot/runtime/health-supervision/README.md) · `current-contract`：notify持续监督、11健康、镜像ID和受控恢复边界。
- [infra/penpot/runtime/health-supervision/evidence/final-runtime-contract.json](../../infra/penpot/runtime/health-supervision/evidence/final-runtime-contract.json) · `historical-evidence`：11服务资源/镜像/健康合同读回，时间限于证据点。
- [network19/services-media/PLAN.md](../../network19/services-media/PLAN.md) · `historical-evidence`：已执行迁网差异与原source文件说明；不重新执行旧stage/commit。
- [infra/penpot/compose.fresh.yaml](../../infra/penpot/compose.fresh.yaml) · `historical-evidence`：初装结构参考，含旧公开BIND/DoH；不能当作19.50现役完整文件复制部署。
- [infra/penpot/runtime/logging/README.md](../../infra/penpot/runtime/logging/README.md) · `current-contract`：MCP query-safe日志规则与不削弱认证的限制。

## 2026-11-10 Puyu设计导入

VM250 owner工作区新增 **puyu项目 / puyu文件**，包含puyu-mobile、puyu-components、puyu-mobile · 商城三页，共58,240图形、19组件。源为本机rev2821，旧7文件保持，当前11healthy，原代码与默认填入保持；本次未部署首次引导源码或迁账号。详见[导入使用手册](../../evidence/penpot-puyu-import-20261110/usage-manual.md)。这是快照导入，不自动同步，不扩正式DB/Nacos之外的备份。
