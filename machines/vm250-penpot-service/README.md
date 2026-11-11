> 最新更新：2026-11-11（Asia/Shanghai）。DNS原Init=false使BusyBox健康探针孤儿成为僵尸，14:31首先DNS unhealthy后原3bad策略停全11。现仅DNS加init:true与严格lock/runtime门禁，最终supervisor51004305已部署，只recreateDNS/其它10ID保持；38离线测试、原生amd64原探针140次0→0僵尸、PID端点8/128/max0与原8file/1661media保护后检均通过。第一次optionalInit点模板native失败被guard阻断，已回退恢复11healthy，补safeindex后成功；不是误报。70分钟只读观察已通过4200秒/119采样，全11healthy/0僵尸/NRestarts0保持，PID范围8–14/128，首尾8；有限窗口不签长期SLO。[修复记录](../../completion/20261111-penpot-hourly/README.md)、[操作说明](../../completion/20261111-penpot-hourly/usage-manual.md)。

> 更新：2026-11-10（Asia/Shanghai）。VM250已部署bkcode/penpot main/8a9b9615并关闭首次引导；17:41应用、17:44浏览器与17:46最终后检通过，11healthy。原UI默认填入与Puyu8文件保持，首轮失败/恢复历史保留；不合并Nexus、不启动Java、无Mac外部探针。

# VM250 · penpot-service

Git来源唯一入口：**[GIT-REPOSITORIES.md](GIT-REPOSITORIES.md)**（来源/计划与已部署状态分开；不表示本机已clone或已分发key）。

## 首次登录引导已关闭：当前main/8a9b9615

当前部署提交为`8a9b96154d9dd81dcc373155ae30dba094127cc8`，main工作树clean；frontend为`sha256:6cbd1f7f3b90b77b3dcd4f6a65fa9c117861d2de0781df22bd8bad40f19c61bc`（`dell-penpot-frontend:2.18.5-8a9b96154d9d-amd64`）。只重建固定官方2.18.5 base上的selfhost wrapper，其余10个镜像不变；没有编译完整2.19套件或迁移数据库。Git-owned入口追加官方`disable-onboarding`再exec原官方入口/CMD，关闭首次调研、首次团队设置及自动版本说明，保留手动创建团队与原登录表单/默认填入。

[17:41应用](../../evidence/penpot-onboarding-20261110/v2-applied.json)确认新source与frontend切换、11healthy、其它10镜像及受保护私有文件/素材/对象计数保持；[17:44真实浏览器](../../evidence/penpot-onboarding-20261110/browser-acceptance.json)从原表单预填登录进入dashboard，`disable-onboarding`为true、引导元素0、欢迎及首次团队设置均未出现、Puyu项目可见、无Internal Error。截图仅private且已人工视觉复核，测试cookies/localStorage已清、session关闭，没有修改profile或设计。

[17:46最终后检](../../evidence/penpot-onboarding-20261110/final-postcheck.json)再次确认HEAD/clean、11healthy且镜像match lock、unit active与监督check通过、原生flags启用、Puyu仍3页/58,240图形/19组件；未授权Docker伪造头请求403。应用回执中的browser pending仅是17:41阶段状态，已由随后浏览器证据补齐，不改写历史回执。

## 首轮失败与恢复历史

用户在风险说明后明确“进行推送”，[授权/非force推送复核](../../evidence/penpot-onboarding-20261110/push-approved-and-verified.json)记录main由9aed先到ec6f，保留37da/ff两条原登录改造。ec6f首次prepare通过后实际启动失败：[诊断](../../evidence/penpot-onboarding-20261110/startup-diagnostic-first.json)显示umask077产生0600公开文件，Docker COPY保留该权限，penpot UID无法读取wrapper；不能将该候选称为成功上线。

[旧服务恢复实证](../../evidence/penpot-onboarding-20261110/old-service-restored.json)随后确认ff与11healthy，专门rollback receipt缺失如实保留；[失败速率计数复位](../../evidence/penpot-onboarding-20261110/recovery-rate-limit-reset.json)没有删除日志或关闭guard。修复commit8a为四项COPY显式加`--chmod=0644`，[v2准备](../../evidence/penpot-onboarding-20261110/v2-prepare-status.json)增加UID1001对wrapper/JS/CSS/conf的可读检查，通过后才切换。旧ff/9aed证据、首次失败及恢复证据仍保留，不冒称首次部署即成功。

## 原UI默认填入（2026-11-10新明确授权）

用户要求原UI、不新增逻辑，并[明确授权](../../evidence/penpot-login-prefill-20261110/explicit-approval.json)LAN21/24、WG10.66.66/24、VM250 self19.50/loopback的未登录访客可读取原owner密码并默认填入。现役保留原helper与表单；16:13预填任务只换原JSON运行secret来源、加一个NGINX来源ACL只读挂载并同步监督lock；CF19.5/其他来源拒绝。该预填任务未新增checkbox/forget/localStorage、未build/换镜像或取新码，未重置owner/MCP或改设计；后续去引导source/frontend更新见上节。打开原页刷新、点击原“继续/登录”，不自动提交。

此前个人浏览器记忆UI/逻辑已[16:05恢复原样](../../evidence/penpot-browser-remember-20261110/restored-original.json)，11healthy、ff clean及镜像保持；其说明只作已撤回历史。[16:13应用](../../evidence/penpot-login-prefill-20261110/approved-applied.json)、[16:19原生后检](../../evidence/penpot-login-prefill-20261110/native-postcheck.json)与[真实LAN浏览器](../../evidence/penpot-login-prefill-20261110/browser-acceptance.json)已通过：11healthy、镜像match lock、Git ff1783e clean、无remember挂载；四种未授权Docker/伪造头请求403。原表单默认值匹配原owner、密码masked，原Continue可登录dashboard，无新增控件；测试cookies/localStorage清理、session关闭。当前WG/CF端到端未签。原账号密码保留，实际值只在受保护Mac/guest文件及guest0600运行JSON，不入文档/Git。本段的ff/镜像保持是16:13–16:19预填验收时点；去首次引导main/8a当前部署见上节，详见[本次证据](../../evidence/penpot-login-prefill-20261110/README.md)与[手册](../../evidence/penpot-login-prefill-20261110/usage-manual.md)。

## 11月9日历史审计与当前备份归属

2026-11-09 14:43:07媒体工具历史采样：原数据UUID、11容器running/healthy/RestartCount0，原镜像/容器IDs保持，原健康GET通过，Git仍ff1783e clean；本轮未更新main、不重验设计/素材/MCP内容或SMTP。 证据：[本机分项审计](../../completion/20261109/media-audit.json)。

本机VM/OS及应用数据不纳入现行自动备份；不因旧whole-VM名单而重新启用。 现行仅正式DB/Nacos逻辑SQL导出（非VM snapshot），PVE落点`/mnt/pve/store/dell-artifacts/prod-db-backups` root700/600；新未列白名单数据库拒绝告警、需更新。03:30/GFS最近3＋每日7＋每周4，首轮3301B与timer见[新回执](../../completion/20261109-prod-db-scope/first-success-and-timer-enabled.json)，实际监控/收尾统一见[新中央入口](../../completion/20261109-prod-db-scope/README.md)。旧11来宾job已disabled、原19,747,582,801B档与21回退档保留不自动删；仅[该3301B Nacos小档已在VM210临时隔离恢复](../../completion/20261109-prod-db-restore/README.md)，完整业务恢复/RPO/RTO/异机DR未签，不迁移/合并/启Java、无Mac探针。

本目录是每机公开合同与来源索引，**不提供秘密或可直接重放的完整部署包**。source of truth为[plan.json](../../plan.json)；11月7日02:35为历史综合基线、UEFI0058为历史事故；用户确认内存处理/诊断通过，11月9日按本页新证据fresh复核，未重验全部应用内容。

## 源码仓库：bkcode/penpot · main

当前Git取码来源为`https://github.com/bkcode/penpot.git`的main，固定运行提交8a9b9615；使用公开HTTPS，没有向来宾分发Git私钥/Token。原13:18管理Mac读取9aed和13:20来宾ff/clean/noorigin仅为历史来源证明，不能作现行main或origin状态。旧unit累计NRestarts22仍按当时记录保留；17:46现役unit active、NRestarts0为新时点，不抹去历史。详见[源码与更新](SOURCE-AND-UPDATES.md)。

## 职责与实际合同

Git改造Penpot与常驻worker/import/MCP服务，原3设计为初装基线；Puyu独立导入后现有8文件，旧7文件受保护。源Mac/Git保留。

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

- 6vCPU/16GiB；当前main/8a9b9615 clean且保留37da/ff改造，仅frontend wrapper更新；不擅自升级2.19源码对应的运行依赖。
- 初装3设计data/revn/stats与原971媒体已迁，973为当时资产基线；Puyu导入后为8文件，旧7保持，不删除合法新增内容凑历史计数。
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

VM250 owner工作区新增 **puyu项目 / puyu文件**，包含puyu-mobile、puyu-components、puyu-mobile · 商城三页，共58,240图形、19组件。源为本机rev2821，旧7文件保持，当前11healthy，原代码与默认填入保持；此导入任务当时未部署首次引导源码或迁账号；后续8a部署保持其数据，见上节。详见[导入使用手册](../../evidence/penpot-puyu-import-20261110/usage-manual.md)。这是快照导入，不自动同步，不扩正式DB/Nacos之外的备份。

## 本地Penpot MCP切服务器

Codex私有配置两项MCP已改SSH stdio到VM250，密钥只在服务器；实际新进程返回puyu/组件页，原生11healthy、原设计/密码保持。当前聊天旧连接缓存仍在，需客户端重载MCP或重启Codex，最后一项验收pending；无法通过受限GUI代点重载。见[连接手册](../../evidence/penpot-client-mcp-20261110/usage-manual.md)。Mac原实例仍运行。
