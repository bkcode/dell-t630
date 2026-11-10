# Dell T630 仓库操作规则

## 入口与当前状态

- 本仓库位于 `/Users/yangzhaohui/work/www/harness/dell`，独立 Git 远端为 `git@github.com:bkcode/dell-t630.git`；harness 父目录不是本仓库。
- 每台机器的配置与文档入口是 `machines/README.md`；保留宿主、合并后12来宾和3模板的离线合同/来源索引，不能把新目录当现场配置导出。机器身份与资源仍由plan约束，新增/修改后运行 `python3 scripts/validate_machines.py`。
- 先读 `README.md`、`11-live-handoff.md`、`19-manual-operations.md`、`plan.json`；资源/IP/角色以 plan 为准，历史证据必须带时间解释。
- **2026-11-09 用户继续授权完成基础搭建，并选择先搭PVE本机自动备份、独立目的地后续；其后明确仅正式数据库/Nacos配置纳入备份，其他暂排除；不迁移数据。11月8日确认服务器恢复，授权检查补齐基础与清理。11月8日暂缓为历史；11月10日用户明确恢复Nexus合并与源221退役，当前以completion/20261110-nexus-merge回执为准，其他数据迁移不扩围。先只读核验硬件/服务和清理依赖，不把恢复可达当内存已确诊修复。Mac外部探针仍停用，Java业务不部署。**
- 11月7日iDRAC控制台曾因UEFI0058阻止启动，SEL指向DIMM_B1；11月8日用户确认内存已重新插拔/更换且诊断通过，本轮EDAC计数0与基础服务恢复记录见recovery/20261108。不得把 F1、一次开机或网络恢复当成内存已修复，不清日志掩盖错误，不远程 powercycle，不指导带电插拔。
- 现行备份验收以completion/20261109-prod-db-scope/acceptance.json及带时间证据为准；此前基础阶段9项仅保留历史；用户最新收窄备份为正式MySQL数据库与Nacos配置；原11实例整机job已disabled，对应专属规则退役，已有归档保留。当前仅VM200/nacos_prod逻辑备份，不备其他来宾/测试/Redis/MQ/NAS/CF/220整机；新增未列白名单的库须拒绝告警。旧11实例整机备份验收只作此前实施历史，不得据旧policy重启整机job。历史基础验收2026-11-08：12运行实例(11VM+1LXC)+3停止模板、15/15targetsUP；原11月7日02:35/02:44记录仅历史。新scope仅基础维护/清理及正式数据库/Nacos逻辑备份，不扩签完整数据恢复/外网E2E。
- 用户已进一步授权并完成单份Nacos备份隔离恢复：VM210临时无网络MySQL，12表/10条元数据的完整DDL语义及逐列内容/重启校验通过，临时资源已清，源档与timer不变。当前验收completion/20261109-prod-db-restore/acceptance.json；仅此小快照，不扩签正式业务数据/RPO/RTO/独立DR，也不得据此覆盖现役库。
- 2026-11-10用户已明确恢复Nexus合并与独立221退役，覆盖早前暂缓；源停服/PVE冷备/唯一盘与31交接/目标验证集中在completion/20261110-nexus-merge。最终数据/身份/网络/监控通过后才退役源，不能提前签完成或盲重放旧迁移器。

- 用户此前测试环境范围仅空基础服务；其后已明确授权下述选定Nacos配置迁移，仍不做业务DB初始化/迁移或Java启动。VM210已有四组件，新增finger-test-empty（23836f2e-9553-5948-84cd-431b2f241bd6）为空起点；旧域10719261-2641-590a-b821-c8484ca955ac与7配置/19业务表保留，原health/bundle默认namespace不变。新域测试角色只精确rw授权，不重置账号；当前验收completion/20261109-test-env/acceptance.json。不得据“空”清库或重跑业务bootstrap。

- 用户随后明确授权仅Nacos配置迁移：清理测试210所有配置items，导入Mac finger-cloud-dev(08e7191f-3ccd-411a-be00-56798d237533)32项及finger-trascan(7bfe03c6-0590-4ff0-8def-e07015016b54)4项；原namespace ID/name/group/body保留，不适配连接地址、不启动Java。原7配置已在guest受保护完整备份，删除后Nacos缓存异步读回曾暂停，必须以journal/现况安全续作，不盲重跑；保留namespace/账号/权限/历史与业务DB，正式不动。源码/配置body与真实MD5仅private/SSH，不进Git。此最新授权只覆盖测试Nacos配置，不是业务DB迁移。

## 2026-11-09 后续明确授权（覆盖较早范围限制）

- 用户随后指定将本机实际存在的`puyu_auth_local`与`puyu_erp_local`迁至测试210，保留源、原库名/结构/内容；本次已完成2库51表1291快照行的导入与独立核验。此精确例外不授权其它业务迁移、Nexus合并、Java启动或自动备份扩围；快照之后源DML不持续同步。
- 用户指定测试210三项组件凭据沿用本机Compose约定，并再次要求“保持这个密码设置”。只同步MySQL既有root@localhost/%、Redis默认认证和指定Rabbit管理身份；真实值只存private/guest受保护来源，不写普通文档/Git。正式、源Mac、Nacos管理员/DB用户和原应用账号密码、TLS/插件保持；不得再生成值覆盖本次指定设置。实现与验收入口`completion/20261109-test-credentials/`，实施状态以实际回执为准。
- `192.168.21.0/24`现已按用户要求作为受信LAN，允许IPv4访问整个`192.168.19.0/24`及网关21.23/19.1本机。GW与PVE bridge双层确认；宿主forwarding全0、无NAT，WG10.66.66/24全服务许可不变。此项取代较早Nacos-only来源限制，不能回放旧narrow配置；应用身份/密钥权限仍生效。

## 范围与安全边界

- 用户允许子 AI；主 AI 分配范围并验收。主 AI 独占 PVE 写、VMID/IP 分配；子 AI 默认只读宿主，来宾写必须有明确窗口。
- PVE root 为 `192.168.21.22`；来宾用户 `ub`，客户端密钥 `~/.ssh/yang_local_rsa`。严格校验 host key；可信来源为已有记录或受信 PVE QGA，不能关闭校验。
- `private/`、凭据、webhook、数据库和归档不得进 Git。秘密只放目录700/文件600；不打印真实值，不复制客户端私钥。
- CF 备份只留 PVE，禁止导出 Mac。发布专用私钥只留220：不读取/复制，不做会包含该私钥的220整机备份或快照导出。
- PVE/H730/store 保留；不得格式化现役卷、将宿主已挂载块设备并交 NAS 或允许两个实例同时写原 Nexus 数据盘。
- 原 Mac 数据与源环境保留；正式库空业务数据，本机数据只用于测试迁移。部署不自动授权真实交易或第三方外发。
- Lark 内部通知已授权且按原配置保留；Mac外部探针用户已明确不需要，移出现行方案与后续待办；仅保留历史资料，不自动恢复或要求系统隐私授权。

## 已交付合同

- PVE 只管理/二层桥，host forwarding 全0、无旧应用NAT；190 WAN21.23/LAN19.1 路由/DNS/DHCP，无NAT。OW route19/24 via21.23。
- 所有服务来宾在19网；同网东西向由 bridge MAC/IP/角色ACL隔离。10.66.66.0/24 已授权全服务访问，WireGuard peer 继续每客户端/32。
- 230/240 正式/测试运行基础各1；**不部署或启动Java业务**，测试五服务停用，publisher fenced；唯一Java验收模板9011无业务配置/秘密。
- 核心模板9010/9001，Java验收9011。旧15对象与临时9040–9045已受保护备份后清理，不重放destroy/stage/commit。备份完整性不等于每个旧实例都已恢复演练。
- fish 已装10来宾+3模板，默认 Bash 不变；排除100/250/270与PVE宿主，不自动chsh。
- Nexus当前由220承接：6CPU8GiB、primary30+同NIC alias31、原build与Nexus各100GiB独立UUID卷；221已按本次回执退役。管理SSH固定30/220 host key，31仅服务兼容地址，不能复制221身份或形成双writer。
- 合并工具非一键幂等；不能重跑prepared stage，部分mount/commit须先按journal核对。不得并启两个31地址/两个数据库写者。

## 验证与交付

- 本地文档：`python3 scripts/validate_docs.py --json`；提交前：`python3 scripts/check_git_safety.py --staged`。
- 所有 live 结果标日期/时区、命令、成功/失败和限制；历史通过与当前暂停分开，未验收保持pending。
- 文档、计划、验收状态需同步；不降低校验门槛凑通过。旧10.63/DNAT/14角色/17targets只作历史，不再当部署入口。
- 用户已明确要求本轮整理并提交Git；仅提交本仓库经检查的非秘密资料。不得改全局memory，默认不删除唯一历史证据。

- OpenClash完整规则由用户明确只留本地：openwrt/rules-20261108/已本地exclude，local/openclash-rules-20261108分支不得push；禁止push --all/强加ignored规则。

## 2026-11-10统一资源服务

- 用户新增并完成VM280 resource-service/19.80，2CPU2GiB＋32GiB系统/100GiB独立数据盘；正式230和测试240明确共用同一根，不拆环境。server /srv/resources真UUID57d8158e-5fcf-4dd2-8cb4-b47b1e54ed7b，client /mnt/resources源19.80:/，NFSv4.1 TCP2049精确双client、root_squash、group2980，finger999:989不改、只附组。当前13guests/3tpl、45CPU87GiB，16targetsUP。
- 未挂载时禁止应用写本机底目录；保守卫/真实挂载校验。默认ACL不保证NFS客户端0022产生groupwrite，未来服务与手册采用UMask0002。新client需VMID/IP/MAC/exports/本机输入/PVEpeer/策略逐层登记，模板克隆不自动授权；三模板本次未改。
- 资源不纳自动备份，不迁旧文件/不公开HTTP/不改Nacos应用上传配置/不启动Java；原Nexus暂缓。两running的/mnt/dell-artifacts等原有状态保留。新VM受控重启实证仅此资源服务，不是客户端OS重启/物理PVE重启或完整灾备。见completion/20261109-resources/acceptance.json与usage-manual.md，禁止重放空盘格式化器或旧全量bootstrap。

## 2026-11-10资源Web管理增量

- 用户选型后明确授权补FileBrowser Quantum与文档，现VM280原生fixed2.1.4-beta/官方SHA锁，HTTPS19.80:8080仅LAN21/24、WG10.66/24、本机；自有输入表，不改NFS/PVE、不装Docker、不增加VM或Prom目标。13guests/3tpl/16UP，资源6服务＋专属CA HTTPS健康。此前不启HTTP指业务/公开图片入口，不能误读成要删除本次已授权管理HTTPS。
- 日常resources仅view/download/create，modify/delete/share/admin/API-token权限关闭，原生API/NFS负测已验；maintenanceadmin完整应用权限，不冒绝对禁删。资源root同目录，UID2000/GID2980新文件660/目录2770，stateDB/cache在/var/lib/dell-filebrowser700不在导出内。真实口令/JWT/TLSkey只private/rootsecret/LoadCredential，不入Git或stdout。
- root-owned/etc/dell-filebrowser/bootstrap.complete之后启动不再注入初始admin口令，勿删除marker盲重置密码。systemd运行时root0:0的0550/0440带namedUID2000只读ACL是合法形式，守卫精确核ACL；不得chmod/chown runtimecred来追过。
- Beta选用原因是官方稳定2.0.2受已公告问题影响且2.1stable release查询404；固定已修复2.1.4-beta，不称稳定版、不自动跟可变tag升级。证书本地自签，首访核公开指纹；无全局trust变更，健康探测专属CA验证链/hostname，不-k。
- 仅管理界面，不改业务上传参数/Java/Nacos，不公开图片URL、不迁文件、不扩自动备份；原MySQL/Redis/Rabbit密码合同保持。实际验收completion/20261110-filebrowser/acceptance.json，使用手册同目录usage-manual.md；初始化/安装one-shot不得盲重放。浏览器只签真实login/list/观察href的PNG预览，pointer全路径未签，旧失败完整保留。

## 逐机Git来源与DeployKey维护

- `machines/git-repositories.json`为合并后16机Git归属主表，逐机GIT-REPOSITORIES.md/config指针与其保持一致；每次改动运行scripts/validate_git_repositories.py。配置库bkcode/dell-t630与应用库/待接入库/上游参考严格区分。
- 220候选拉bkcode/deploy＋5个Puyu后端，common-lib仅共享库；230/240当前运行基础、收构建制品，不能因文档登记就启动Java/放Git私钥或替换受限publisher。Jellyfin fork是服务端候选，当前260仍官方镜像，不冒称已部署或为电视客户端。
- 管理Mac仓库key目录~/.ssh/deploy-keys/bkcode，Penpot旧deploy(.pub)已移成penpot_ed25519(.pub)，bkcode/deploy另用deploy_ed25519。本轮用户报告GitHub已配，实际只验证Penpot仓库SSH身份和临时浅clone；不代表server已配认证、writeflag已测。不得将私钥或公钥正文纳Git。
- Penpot远端main本轮仍9aedbb0而本地/服务器为ff1783e，先保两条改造，不能自动pull/reset退回远端旧版或自动push本地。VM250本轮只读clean/noorigin/11healthy，supervisor累计重启22如实记历史，不据此签零重启或扩大诊断。

- Penpot-only/等待用户推两条ff改造是13:20历史阶段，后续已明确授权并完成8a取码/部署。当前维护以各精确后续授权为准，Nexus已合并并退役221，现役16机文档；旧证据evidence/git-repositories-20261110/penpot-deployment-state.json不可作为当前阻塞。

## 2026-11-10发布机服务导航例外

- 用户另明确授权在220发布机使用bkcode/deploy新增服务导航页，随后明确无需账号密码、只预览跳转。现HTTPS19.30:9080、LAN21/24/WG10.66/24/本机，无登录/CRUD/可写JSON状态、无target健康探测，只分组/search/envfilter/copy/链接。此精确新授权不是其他服务器Git部署或解除Javafence。
- source本地commit63b8c08，运行只打包gitshow该提交5个公开模块文件，不能夹带原deploy/config/MCP/Gitkey。deploy本地main在任务前已有4条未推送用户commit，故没有代push/rebase/amend/force；不能把门户已部署说成源码已推GitHubmain。未来维护先用户确认Git发布范围，再选不可变commit替换release。
- Linux专用OSuser2001+systemdreadonly，TLSkey仅LoadCredential，不是应用账号。清单在source services.json，修改后经review+新release重启本导航，不重跑fresh安装器覆盖。原publisher/Java/Nexus/Penpot不因此启停；Penpot继续等用户push两改造并通知。监控目标仍16，220本机多1导航unit检查，不外发人工告警/扩备份。
- 验收evidence/service-directory-20261110/acceptance.json，手册usage-manual.md。浏览器只签匿名列表/search/copy/mobile和外链href/target，自动化new-window动作失去响应未冒签完整跳转；原生GET API14/写405/旧auth404/Host400及原服务身份保持均实测。

- 导航最新合同按用户要求为HTTP19.30:9080，移除顶部栏、全宽/紧凑标题，source本地ddccc2b。旧TLS证书/启动回执仅历史，runtime不加载TLS凭据，不误恢复HTTPS或大留白顶部栏。其它目标服务协议不跟随改变。最新证据evidence/service-directory-http-20261110，实际访问不再需要导航证书。

## 内部自建应用HTTP默认

- 用户明确内部服务无需HTTPS。当前导航HTTP19.30:9080(免登录只读无顶栏全宽，source本地d56cae5)、FileBrowserHTTP19.80:8080(原resources/admin认证/权限保留)。PVE/iDRAC内置HTTPS本轮不强改；外部CloudflareTLS不是此内部范围。不得把HTTP等同无认证或自动关闭其它管理安全机制。
- FileBrowser仅移除configTLSfields、launcherTLS读key、unitTLScredential；JWT/marker/UID2000/GID2980/NFS/state不动，原账号fresh登录与scope完整比对通过。health名filebrowser-http-health，不带ca_file，16targets与6资源服务保持。旧TLS材料/证据保留inactive，不作当前证书要求，不能回放旧HTTPS配置或freshinit重置原账号。
- 本轮回执evidence/internal-http-20261110，源码Deploy4个本任务commit均本地，原4条用户未发布commit不代push；只同步导航FileBrowser链接HTTP，不启Java/Nexus合并/Penpot更新或改其它VM运行。

## 2026-11-10 Penpot原表单默认填入

- 用户明确拒绝新增UI/记住逻辑，随后明确授权原helper默认填入现有owner账号密码，并允许LAN192.168.21.0/24、WG10.66.66.0/24及本机未登录读取。该精确授权覆盖此前不公开选择；不可扩大至CF或任意Docker来源。秘密仅guest受保护文件，不写Git/普通文档。
- 原UI已恢复，无checkbox/forget/localStorage保存逻辑；沿用镜像现有helper，不改其代码、不改密码、不迁设计数据。VM250仍Git ff1783e clean/同镜像，11healthy；授权LAN默认值与原继续按钮登录进入dashboard实测通过。非授权Docker来源四种伪造头组合均403；WG仅规则允许，未签本轮异地E2E。
- 当前交付evidence/penpot-login-prefill-20261110/acceptance.json和usage-manual.md；browser-remember目录仅撤回历史，代码已归档private/deferred而非可部署方案。当前public脚本approved-worker.py是已执行的一次性事务，不盲重跑。后续bkcode/penpot main源码更新仍等用户推两条改造并通知，不因本次运行配置部署而自动拉旧远端。

## 2026-11-10 Puyu设计导入授权与交付

- 用户明确本机Penpot的Puyu设计导入19.50；确认本机“Penpot MCP 验证”rev2821的三页全部为Puyu，仅这一文件官方导出/导入。目标owner默认team新增puyu项目与puyu文件，旧7文件data/版本/名称/项目保持，不删除或覆盖。
- 新事务/etc/penpot/puyu-import-20261110.json与私有归档独立；不改旧application-id-map、不迁源身份、不PG整库覆盖、不盲重跑import。首次CLI启动回执20秒等待超时但实际unit继续，后台完成且已验证，不得按历史inflight重复导入。
- 当前验收evidence/penpot-puyu-import-20261110/acceptance.json、手册同目录usage-manual.md。3页/58240图形/19组件统计一致，旧7文件完整data哈希保持，浏览器仅抽查组件/商城详情。此授权不是首次引导源码push：ec6f032仍本地且自动推送审批冲突待明确授权，不因此执行Git部署。自动备份仍仅正式DB/Nacos。

## 2026-11-10 Penpot原生首次引导关闭上线

- 用户在说明Penpot AGENTS禁止代理push及main变更影响后明确“进行推送”，覆盖本次该早期约定。已非force推ec6f及权限修正8a9b961到bkcode/penpot main，VM250公开HTTPS取固定8a，无Git私钥/token分发。不要再将9aed缺改造或等待用户push作为当前阻塞。
- 当前source main/8a clean、frontend6cbd1f7，其它10镜像保持、11healthy；原生disable-onboarding关闭调研/团队欢迎/自动版本说明，手动建团队保留。新浏览器原预填登录直接dashboard，DOM引导0、欢迎/团队false，Puyu可见；账号/秘密/素材聚合/DB对象数保持，Puyu3页58240图形19组件后检通过。
- 首次ec候选因umask077使COPY公开文件600不可读而失败；旧ff恢复经原生11healthy证明，启动限频仅reset该unit未删日志/关guard。8a显式COPY0644，v2增加BuildKit UID1001读取门禁，切换成功。失败源码/image/记录与回退恢复点保留；不盲重跑本次一次性脚本、fresh-init或改lock规避检查。
- 当前验收evidence/penpot-onboarding-20261110/acceptance.json，手册同目录usage-manual.md。只构建selfhost包装，不声称全库2.19升级/全部组件同版重编；本轮数据保护检查不等于全设计像素/交互或完整灾备。备份仍仅正式DB/Nacos，其它VM运行不扩。

## 2026-11-10 本地Penpot MCP服务器连接

- 用户授权两项本地skill MCP切VM250，并指定刚导入Puyu。Mac私有config.toml改SSH stdio，原审批/其他配置保持、备份600；严格现有VM250公钥，原RSA留Mac。服务器MCPkey仅在既有import容器内读取，无token导出或新端口/容器。
- resident默认Puyu01b文件/组件页0c6166…e31e54275406，仅.env公开file/page ID改动，秘密/team保持，原设计stats/revn保持、11healthy、Git8a镜像合同不变。新进程协议真实通过；当前聊天注册工具仍读Mac9eb旧缓存，需用户重载MCP/重启Codex。GUI工具禁止控制Codex，不绕过、不伪称当前会话已切换。
- 当前验收evidence/penpot-client-mcp-20261110/acceptance.json为4通过/1待重载；文档手册同目录usage-manual.md。重载后先overview再只读验证fileId01b，成功再签最后项。旧MCP专用验收文件/旧硬编码只作历史，不用旧readFile断言误判新Puyu上下文。Mac原实例保持，不因本次连接配置授权删除数据或停本机源。

## 2026-11-10 VM220独立Puyu发布器Git安装

- 用户明确deploy-public main提交/push、发布机Git拉取、配置Puyu和补文档；原Finger deploy不动。实际main/a0c7529 clean，/opt/deploy-public，Userub；GitHub指定deploy_ed.pub已改绑newrepo，服务器新名deploy-public_ed私有600。另5个仓库专属只读Git身份按用户先前后端源码用途安装；不读/导出原220发布私钥。服务器repo pushURLdisabled。
- /srv/dell-build原100GiB UUID16dc保留，新deploy-public子树容纳源码/build/mcp-state。root-owned挂载门禁公开目录初次因umask700失败，纠正755后ub检查通过；不得放宽秘密目录700/文件600或盲重跑已完成bootstrap。
- puyu-deploy-mcp.service enabled/active、仅127.0.0.1:18765，APIkey只在服务器YAML生成600/ignored。源码5repo main干净、4服务只读preflight成功，Linux60tests通过；puyu-auth初次权限失败经用户加.pub后用原key补拉，bffadmin用户指定暂不处理。
- 本次没有Go/Java编译/启动或运行机SSH部署；deploy-services关闭并实测拒绝，旧forced-chainfenced且尚未适配Puyu，不能按新工具已安装自动解冻或给deployer扩权。原模式验证时导航PID18640保持仅为重启前历史。Nexus随后按明确恢复授权完成合并，220重启后PID变化正常；备份不扩围，原Finger源码本轮清单两文件未提交/推送。
- 当前交付evidence/deploy-public-publisher-20261110/acceptance.json；源码库docs/PUBLISHER.md与OPERATIONS.md有安装/更新步骤。主机Git取码/本地验证/MCP可用不等于真实业务发布或Nacos健康验收。

- 同轮后续用户新增puyu-bff-admin专属SSHkey并登记DeployKey，已复用对应私有身份克隆其main3638b8f，私有YAML只新增该项目，MCPkey/其它配置保持。MCP重启加载五服务、合并只读预检validated5通过，commonlib仍只是库；先前四服务/暂不处理bffadmin为历史，不据旧摘要覆盖现状。

## 2026-11-10 deploy-public标准双环境

- 用户要求CLI prod→main、dev→dev；MCP仍仅dev，拒绝prod和请求环境覆盖。发布器自身仍从deploy-public/main取码，不随业务分支切换。新源码213f1f4已推并VM同步clean，Linux65tests与实际新探针已核：缺origin/dev预检failed、prod覆盖与真实deploy拒绝。不能将旧dev/main五服务成功当新dev就绪。
- 本轮VM220只读ls-remote审计六个后端/公共库：main存在、dev全部缺失，工作树仍main。不创建/push/切业务分支，不fallback main；缺本地origin配置分支的预检在build/SSH前拒绝，显式sync才获取。
- prod目标身份留空、真实deploy关闭、旧链fenced、Java不启；MCPkey/私有路径/测试目标与原Git身份保护保持。模式文档evidence/deploy-public-modes-20261110/README.md；一次性set/apply脚本不盲重跑，不输出私有YAML。

## 2026-11-10 Nexus合并最终状态与NFS-only

- 本次已完成Nexus原盘/身份/账号/EULA/全1347资产保持、220受控重启、双UUID/双IP/source30/原MCP配置及key保持；15targetsUP、220七项与280五项全UP。221已在最终核验后删除，原OS盘也删，活Nexus盘在220保留，原221只留PVE冷备2,400,054,202字节恢复点；归档machines资料移archive/machines-vm221-artifact-service-20261110，不可重放。
- 现役12来宾＋3模板＋宿主共16目录、45CPU87GiB；2206CPU8GiB/primary30+alias31，两独立100G卷，管理用220自身host key。NexusURL31:8081保持。旧13来宾/16UP和4CPU4GiB/standby均仅历史。
- 280仅NFS，FileBrowser两unit已masked/8080无监听、原state/秘密保护留存，5项服务无HTTP。导航已更新13入口release、去FileBrowser并改Nexus描述，HTTP/UI保持；原deploy两文件未提交/推送。不要回放旧FileBrowser安装器恢复网页。
- 自动备份仍只正式DB/Nacos；冷备仅PVE、不wholebackup220，Java业务不启/旧链fenced，deploy-public原私有设置/APIkey/6main源保持，upstreamdev缺失保护不变。当前维护入口completion/20261110-nexus-merge/usage-manual.md及最终回执。

## 2026-11-10 FileBrowser现役移除

- 用户明确FileBrowser可以移除；VM280程序/配置/状态从现役路径移出、两unit已not-found/inactive、闲置UID2000删除，共享GID2980及NFS原配置/进程/双客户端挂载保持。原资料仅VM280/root/dell-filebrowser-removed-20261110受保护归档；旧retired目录已归入其中，不再当活路径。
- 用户说Nexus不用迁移后已暂停Nexus后续；此前合并状态已存在，本次不操作或回退Nexus，不能因FileBrowser移除自动恢复221。当前交付completion/20261110-filebrowser-remove/acceptance.json，旧NFS-only停用阶段留历史。
