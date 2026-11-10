# Penpot main更新计划：等待用户推送保留改造

更新：2026-11-10，Asia/Shanghai。状态：**pending-user-main-update**。用户已选择保留现役两条改造，由用户先推送到`bkcode/penpot`的main，再通知继续。本轮只读分析并新增此文件；没有服务器认证/密钥复制、fetch/clone/pull、build、源码切换、服务操作或nativecheck。17机Git来源文档继续保留，但实际Git取码部署只处理Penpot，其它机器不扩为部署任务。

最新选择以[部署范围与用户选择回执](../../../evidence/git-repositories-20261110/penpot-deployment-state.json)为准；本计划保持pending，不构成更新已执行证明。

## 当前基线与阻塞条件

- [13:20来宾只读证据](../../../evidence/git-repositories-20261110/penpot-runtime-readonly.json)：VM250/19.50，`/opt/dell/penpot/source`为main、HEAD `ff1783e7865af7aae571c985f03e057631b7af63`、clean、无origin；11容器running/healthy。unit累计NRestarts22，不等同容器RestartCount0，也不在此轮诊断或重启。
- [管理Mac临时读取](../../../evidence/git-repositories-20261110/penpot-deploy-key-verification.json)：main为`9aedbb011cd803eb615225ca21f7f47cb8c2fa09`，浅历史/完整工作树验证通过，临时目录已清；没有服务器key安装、push或部署。
- 远端观察的9aed缺现役ff的两条改造。不能把“取main”解释成退回旧代码；先等待用户推送，再重新只读核main的不可变commit及改造保留。若用户只推了原ff而代码完全不变，更新主要是建立受信Git来源/remote合同，不应为了“已部署”强行重建全部镜像。
- Penpot源码仓库`AGENTS.md`（管理机Penpot源码根目录）要求agent不push或修改origin；本计划遵守只读边界，后续服务器remote配置仅主AI按本次用户明确取码授权实施，不能顺手改管理机原仓库remote。

## 关键发现：运行来源不是整个main编译出的同版套件

| 服务/来源 | 当前已登记产物 | 更新时最小处理 |
| --- | --- | --- |
| 自建frontend | `sha256:bd020fb6bddfd77449c26f76ee04ca7b2b50a0ffe8562ebc7b9e294bfcd38b89`；Git ff frontend/selfhost，OCI revision匹配 | 只有该context/基础digest或产物契约变化才需重建；新commit必须记录实际source与context，不能仅换label声称已编译 |
| 自建worker | `sha256:c0bead679c3fe7a4b80d2485f87bdce0e5a6acc26a9c2a001b0e4e3270dadee5` | 历史17个Git代码文件与编译产物复用已归因；新版本比较resident-worker整个context、锁文件、工具链/base与运行合同，全部相同可继续复用并明确来源，变化则顺序新建不可变镜像 |
| 自建import | `sha256:d4414e3f2e41ac4f5eb4b2c146c05cbc9f9754b179d6b63efa3af95c005b1261` | 历史10个Git代码文件匹配后复用；相同原则，不因换main名义强制重编或无条件复用 |
| backend/exporter/admin-console/MCP | 现有官方固定digest，历史backend bundle_version `2.18.5-RC1`，MCP等组件标签并非统一同一值 | 保留现场实际11imageID/引用，不能从源码含2.19就推断这些组件应升级 |
| PostgreSQL/Valkey/DNS/Mailpit | 现役固定镜像及数据volume/私有配置 | 本期不换DB版本、不跑schema升级、不删volume、不全量迁移数据；网络/DNS/query-safe日志继续按19网现役合同 |

[来源归因](../application/git-runtime-provenance.json)已经明确三自建产物的不同构建/复用路径；[旧源运行锁](../source-runtime.lock.json)是原Mac迁移时的daemon/容器锁，**不是VM250本次更新的新运行合同**。`source_guard.py`校验原Mac Docker context/daemon ID及混合源容器，不能直接搬到guest或重写成“全栈同版”。当前“源码包含2.19”与旧官方2.18.5运行层并存是已知事实，不在此次Git更新顺手抹平。

## 运行监督与文件锁的最小适配面

| 文件/机制 | 实际约束 | 必要增量/禁止事项 |
| --- | --- | --- |
| 现役`runtime/health-supervision/supervisor.py` | `verify_files_and_images`每60秒检查source HEAD/clean、package/supervision SHA、每服务image reference及imageID；`validate_frame`校资源/mount/restart=no与11服务健康 | 活跃监督器下直接pull会触发失配并stop整个受控组。取码先用独立候选目录，切换必须短维护窗口、停止本unit并精确更新本次允许变化的lock；不能删除/跳过guard |
| `deployment-lock.json` | Git HEAD、package_file_sha256、supervision_file_sha256、11服务imageID/引用/资源/mount，以及storage UUID | HEAD换新immutable commit；只更新真正变化的公开文件SHA及变化镜像条目，保留全部不变量。image_reference_before与ID双检，旧tag若重指向会失败，因此新镜像用新名并保留旧tag/ID |
| `compose.fresh.yaml`＋`compose.health-supervision.yaml` | 前者含source login-defaults.example.json secret-file路径、官方digest/端口/私有引用；后者以imageID覆盖三自建并保pids/healthcheck | 只改本次真正变化的image引用与必要source文件路径；要同时适配覆盖层，不能只改base tag就以为新镜像会生效。不输出resolved全config以免Env泄漏 |
| `/opt/dell/penpot/source` | 当前clean Git checkout；source内公开example文件被Compose引用 | 不替换成symlink：现有owned/路径检查可能拒symlink；保目录路径与root权限，停监督后在受控阶段精确切换真实目录，保旧checkout供回退。不得引入真实登录口令到example |
| fresh-target/init/target_guard | `application/fresh-target.py`固定ff HEAD、frontend tag，init还会处理新身份、marker、unit与原构建；target_guard另核assignment/运行条件 | 这是初始部署工具，不是本次更新器，禁止重跑init/accounts/application-import或重新生成身份。若未来保留该工具供check，须由主AI明确哪些只读固定值需适配，不能用全局替换ff绕过保护 |
| query-safe runtime logging | `runtime_logging.py`精确锁两模板SHA、0644、只读bind、create_host_path=false与MCP路由等价 | 保留不泄query/token的补丁。新frontend入口/模板不兼容时停止，先评审最小差异，不能丢补丁或恢复旧完整URI日志 |
| 19网有效代码 | 本仓库旧supervisor与lock仍含10.63.30.30；`network19/services-media/patches.py`曾对现场精确改19.50及公开URI/源SHA | **现场已迁19的owned字节与SHA才是下一次CAS基线**，不可上传旧infra整包覆盖运行文件。本文只列待核合同，未读取当前私有配置或修改旧历史证据 |

Supervisor自身错误码含`clean-Git-ff1783e-required`历史名称，实际比较的是`lock['Git']['HEAD']`；改lock后机制可支持新HEAD，错误信息若改也要重新计算其supervision SHA。不能让字符串名称误导为只需删除硬编码。supervision启动是notify READY，restart=on-failure、止损stop_group保留；不能改成Compose restart=unless-stopped或独立绕过unit启动容器。

## 构建入口及复用判据

1. **Frontend**：实际历史入口是Git `frontend/selfhost/Dockerfile`，COPY sidebar、login-defaults.js/conf，基于固定官方frontend2.18.5 digest；历史`application/fresh-target.py`给`PENPOT_VERSION=2.18.5@<锁digest>`与OCI revision。它只是Nginx/静态覆盖包装，不是从整个ClojureScript源码重编前端。候选main变更若只在未进入此context的CLJS源码，复用旧base不会包含该变更，必须明确报告“未进入交付产物”，不能只贴新commitlabel冒称生效。
2. **Worker**：Git `mcp/resident-worker/`与Dell `contexts/worker/`有相关构建来源；TypeScript build和测试在build stage，runtime基于固定exporter/Playwright。保持pnpm lock、Node/Chromium/base关系；源码/context变化才构建新的linux/amd64产物，先离线模块/语法/纯测试，随后受控真实只读MCP健康。
3. **Import**：Git `mcp/file-import/`与Dell `contexts/import/`；pnpm frozen install、build/tests、prune生产依赖和pure-JS检查，runtime基于固定MCP。保API/private-network/归档大小与认证边界；不为部署验证向真实项目导入或重复业务操作。
4. Dell `local-build.py`固定**Mac ARM64 daemon/原17源容器/三个历史tag**，不是可直接在VM250执行的通用builder。禁止重跑它更改原Mac源标签；若需要guest AMD64新构建，应另审小型受限builder，选独立context和新tag，不挂secret/数据/原Dockerroot、不把buildargs当secret通道。VM250仍6CPU/16GiB，不编造headroom；逐个构建并核磁盘/内存与源服务不受扰动。
5. 对三context做源文件/lock/base digest/toolchain的稳定指纹，记录与旧产物匹配或变化的原因；不要只比`src/*.ts`数量。运行时镜像平台必须amd64/linux，tag与ID关系不覆盖旧值。没有变化的组件明确复用旧ID；变化的只重建对应组件，其余官方imageID严格保持。
6. 若用户新main含backend/schema或完整frontend发行升级需求，本小方案停止扩大：单独说明需要不同build/版本兼容与DB恢复策略，不默许执行2.19全栈升级。

## 用户通知后才可执行的步骤

1. **只读确认远端版本**：主AI使用已验证repo-specific读取身份，重新读取main SHA，验证所需两条改造存在且新commit来自用户指定main。当前main未更新前继续等待，不复制key到服务器或提前fetch。repo权限/账号不通过push探测。
2. **新鲜现场基线**：仅250核strict SSH/已知host key、HEAD/clean、19.50地址、UUID`ccccda03-bffd-4054-afd3-e0e22f0c607e`、DockerRootDir`/srv/penpot/docker`、overlay2、11服务ID/image/health、unit frame与有效Compose/lock/source SHA。只选metadata，禁止raw Env/Cmd/health logs或私有配置正文出证据。
3. **保留恢复点**：root私有目录保存旧真实source目录/公开包/lock/三image引用与ID；DB/素材需要本机应用一致性恢复点时，准确声明短暂停写与范围，不据此扩大跨主机迁移/备份任务。不导出CF/其它机或publisher私钥。没有完整恢复点时只读检查，不能先换版本再补救。
4. **候选取码与构建**：在独立候选目录固定checkout新SHA，核clean和改造保留；私钥不进context/镜像/普通证据、不agentforward。先得差异矩阵，决定0–3个自建镜像重建或复用；保全部官方组件/DB不变。所有候选checks先通过，不能盲目重试失败或补全栈pull。
5. **精确维护切换**：获对应短维护窗口后，正常停止`dell-penpot.service`以保监督一致性（其停止组行为意味着可能短暂影响11服务，应据实际告知，而非声称只前端无影响）。核停止/无writer后，切source与审核过的公开文件/lock/覆盖层；不执行down-v、不删volume、不重建账号、不更改数据路径。
6. **原路径启动和gate**：先跑新的只读supervisor check，沿现有notify unit启动，`up -d --no-build --pull never`只用已存在已锁产物，等11/11healthy且READY；重新核package/image/资源/mount/日志安全及新commit产物归因。若无须镜像变化，明确“来源配置更新，运行image不变”，不能虚构新版本代码上线。
7. **功能验收**：LAN9001、backend/exporter/admin/MCP/worker/import健康；既有身份/项目/素材只读存在性与计数/权属不漂移（业务内容不进普通日志）。实际MCP设计写入或导入仅在明确的临时项目验收窗口，不能任意修改真实设计。留新unit PID/重启/11ID与保护对象状态；不以历史973media或旧三设计证明今天全内容通过。
8. **故障回退**：停止本unit，用本次前置恢复点恢复旧source真实目录、旧public package/lock和旧imageID引用，再走原check/start等11healthy。数据库/素材无迁移前提才可安全软件回退；若检测到意外schema/data变更，停止并报告，不能自动把旧DB或素材回写覆盖现役数据。旧main9aed不是回退目标，回退基线应为现役ff与原mixedimage组。
9. **收口**：只实际成功后更新250 Git来源/版本与监督lock、sourceindex、部署receipt及只读postcheck。读取成功、构建成功、服务替换、功能验收分开记；其它16机仍仅文档，不启Java、不改Nexus/NAS/资源服务。

## 需要主AI准备/审阅的最小交付

- 不可变新main与现役ff的改造保留证明、context差异/复用或新建三image矩阵。
- 以现场19网SHA为基线的source/Compose覆盖层/deployment-lock最小CAS差异；保旧imageID/volume/身份与query-safe模板。
- 单guest有界构建与一次短维护切换/回退工具及离线guard测试；不能复用fresh初始化器或旧Mac迁移脚本当更新器。
- 新阶段metadata/check/start/11health/只读功能/回退证据计划，秘密不输出；成功再更新逐机current文档。

当前没有这些新执行产物，也没有启动任何更新流程。**等待用户推送main并明确通知后，主AI才继续本计划第一步。**
