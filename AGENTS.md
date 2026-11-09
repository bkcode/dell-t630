# Dell T630 仓库操作规则

## 入口与当前状态

- 本仓库位于 `/Users/yangzhaohui/work/www/harness/dell`，独立 Git 远端为 `git@github.com:bkcode/dell-t630.git`；harness 父目录不是本仓库。
- 每台机器的配置与文档入口是 `machines/README.md`；保留宿主、12来宾和3模板的离线合同/来源索引，不能把新目录当现场配置导出。机器身份与资源仍由plan约束，新增/修改后运行 `python3 scripts/validate_machines.py`。
- 先读 `README.md`、`11-live-handoff.md`、`19-manual-operations.md`、`plan.json`；资源/IP/角色以 plan 为准，历史证据必须带时间解释。
- **2026-11-09 用户继续授权完成基础搭建，并选择先搭PVE本机自动备份、独立目的地后续；其后明确仅正式数据库/Nacos配置纳入备份，其他暂排除；不迁移数据。11月8日确认服务器恢复，授权检查补齐基础与清理。用户明确暂不迁移：不执行Nexus合并、数据迁移或源221退役。先只读核验硬件/服务和清理依赖，不把恢复可达当内存已确诊修复。Mac外部探针仍停用，Java业务不部署。**
- 11月7日iDRAC控制台曾因UEFI0058阻止启动，SEL指向DIMM_B1；11月8日用户确认内存已重新插拔/更换且诊断通过，本轮EDAC计数0与基础服务恢复记录见recovery/20261108。不得把 F1、一次开机或网络恢复当成内存已修复，不清日志掩盖错误，不远程 powercycle，不指导带电插拔。
- 现行备份验收以completion/20261109-prod-db-scope/acceptance.json及带时间证据为准；此前基础阶段9项仅保留历史；用户最新收窄备份为正式MySQL数据库与Nacos配置；原11实例整机job已disabled，对应专属规则退役，已有归档保留。当前仅VM200/nacos_prod逻辑备份，不备其他来宾/测试/Redis/MQ/NAS/CF/220整机；新增未列白名单的库须拒绝告警。旧11实例整机备份验收只作此前实施历史，不得据旧policy重启整机job。历史基础验收2026-11-08：12运行实例(11VM+1LXC)+3停止模板、15/15targetsUP；原11月7日02:35/02:44记录仅历史。新scope仅基础维护/清理及正式数据库/Nacos逻辑备份，不扩签完整数据恢复/外网E2E。
- 用户已进一步授权并完成单份Nacos备份隔离恢复：VM210临时无网络MySQL，12表/10条元数据的完整DDL语义及逐列内容/重启校验通过，临时资源已清，源档与timer不变。当前验收completion/20261109-prod-db-restore/acceptance.json；仅此小快照，不扩签正式业务数据/RPO/RTO/独立DR，也不得据此覆盖现役库。
- Nexus短停合并的历史授权保留，但2026-11-08用户明确暂不迁移，当前不得合并/迁盘/退役221。将来用户明确恢复迁移任务后再fresh核验；本轮补齐与清理不能绕过该边界。

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
- fish 已装9来宾+3模板，默认 Bash 不变；排除100/250/270与PVE宿主，不自动chsh。
- Nexus 目前仍独立221/19.31；220/19.30仅准备。目标2206CPU8GiB、primary30+alias31、原UUID盘移交，验收后才退221；详情见cleanup/nexus/resume-preflight.md。
- 合并工具非一键幂等；不能重跑prepared stage，部分mount/commit须先按journal核对。不得并启两个31地址/两个数据库写者。

## 验证与交付

- 本地文档：`python3 scripts/validate_docs.py --json`；提交前：`python3 scripts/check_git_safety.py --staged`。
- 所有 live 结果标日期/时区、命令、成功/失败和限制；历史通过与当前暂停分开，未验收保持pending。
- 文档、计划、验收状态需同步；不降低校验门槛凑通过。旧10.63/DNAT/14角色/17targets只作历史，不再当部署入口。
- 用户已明确要求本轮整理并提交Git；仅提交本仓库经检查的非秘密资料。不得改全局memory，默认不删除唯一历史证据。

- OpenClash完整规则由用户明确只留本地：openwrt/rules-20261108/已本地exclude，local/openclash-rules-20261108分支不得push；禁止push --all/强加ignored规则。
