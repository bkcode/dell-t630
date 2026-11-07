> 文档状态（2026-11-07）：本页为阶段实施/技术记录，文中“当前”、网段、角色数与通过结果以原执行时点为准。服务器现因UEFI0058内存错误暂停，Nexus合并已授权但未执行；当前配置入口见[访问清单](../../12-service-access-and-operations.md)，恢复门槛见[最新交接](../../11-live-handoff.md)。旧脚本、stage/commit或初始化步骤不得直接重跑。

# Java 部署实施前核查

采集日期：2026-11-06（Asia/Shanghai）。状态：**本地核查与五服务隔离离线构建已完成；目标运行、测试和业务验收尚未通过**。机器可读结果为 [service-inventory.json](service-inventory.json)。角色、内存和目标地址仍以主 AI 管理的 [plan.json](../../plan.json) 及实际分配证据为准；本文件不分配 IP、不改变仓库、不构建、不发布 API、不启动任何服务。

## 首批范围

最小的管理员登录与角色读取链是四个服务：

```text
finger-gateway-mobile → finger-auth → finger-service-system
                    → finger-bff-system → finger-service-system
```

推荐首批增加 `finger-service-coms`，组成 **五服务测试批次**，用于 COMS 权限目录和小文件存储核查。这个范围能验证基础设施、认证和一个真实只读 BFF 链；它不等于管理员后台所有页面均已可用。

| 服务 | 当前源码默认端口 | 首批用途 | 需要运行的 provider / 限制 |
| --- | ---: | --- | --- |
| finger-service-system | 10210 | 专用管理员身份、角色和员工只读查询 | 读取测试库和 Redis；创建员工会调用 MSGS 发邮件，首轮禁止该入口 |
| finger-service-coms | 10202 | COMS 菜单/角色/URL 配置读取、小文件存储 | SUPPER_ADMIN 能力目录只需 BFF-System；商户/MT4/MT5目录另需对应BFF |
| finger-auth | 10000 | 专用管理员客户端认证、签发测试令牌 | 管理员走 System；App/商户/Web登录走 UMS，首轮不开放这些分支 |
| finger-bff-system | 10104 | `/sys-api/v1/role/get-list`、员工列表等已选只读接口 | 这些入口调用 System；其他页面还会调用 UMS、AUDS、SUBS、BCS、CMS、EXS、MKTS、MSGS |
| finger-gateway-mobile | 9999 | 测试入口、认证与 BFF 转发 | 新 Nacos 路由必须以实际 `/sys-api/**`、认证和 COMS 路径为准 |

`finger-service-bcs` 是设置页的可选第六服务，不是管理员登录/角色读取的硬依赖。UMS、AUDS、SUBS 等 API JAR 是 BFF 的编译依赖，不表示所有 provider 都必须随第一批启动。反过来，只启动五服务也不能宣称这些 provider 负责的页面已验收。

第一轮只开放已选的测试认证、只读角色/员工列表、COMS 权限读取和小型合成文件上传。商户、KYC、订阅、支付、交易、创建员工、发送验证码/通知等入口先不开放；缺失 provider 的页面明确标未上线。

## 已核实的调用与启动行为

- [SysUserDetailsService](/Users/yangzhaohui/work/www/finger/finger-master/projects/finger-auth/src/main/kotlin/com/sargia/finger/gateway/auth/service/SysUserDetailsService.kt) 根据账号调用 System 的登录资料接口；System 本地查询 user、role_info。
- [PasswordAuthenticationProvider](/Users/yangzhaohui/work/www/finger/finger-master/projects/finger-auth/src/main/kotlin/com/sargia/finger/gateway/auth/oauth2/extension/password/PasswordAuthenticationProvider.kt) 区分客户端。当前 `finger-admin` 注册配置包含 captcha grant，不能因为代码中存在 password 分支就假设客户端允许 password grant。
- [AuthorizationServerConfig](/Users/yangzhaohui/work/www/finger/finger-master/projects/finger-auth/src/main/kotlin/com/sargia/finger/gateway/auth/config/AuthorizationServerConfig.kt) 启动时读取/保存注册客户端；Redis 缺少 JWK 时生成并保存密钥。管理员登录也会写 OAuth/Redis 状态，不能把认证验收当数据库只读操作。
- 客户端初始化代码包含内嵌初始化参数，并在启动时保存客户端记录。目标测试 client secret、回调地址、授权类型和重启覆盖行为需要单独决定；本文件不输出任何 secret 或既有登录凭据。
- [System UserCreateAction](/Users/yangzhaohui/work/www/finger/finger-master/projects/finger-service-system/system-boot/src/main/kotlin/com/sargia/finger/service/system/action/UserCreateAction.kt) 会发送员工创建邮件，所以首轮使用已初始化的专用测试账号，避免通过创建员工页间接启动通知链。
- [BFF-System RoleController](/Users/yangzhaohui/work/www/finger/finger-master/projects/finger-bff-system/src/main/kotlin/com/sargia/finger/bff/system/controller/RoleController.kt) 当前角色列表、权限列表路径为 `/sys-api/v1/role/**`，调用 System；[SecurityProviderConfig](/Users/yangzhaohui/work/www/finger/finger-master/projects/finger-bff-system/src/main/kotlin/com/sargia/finger/bff/system/config/SecurityProviderConfig.kt) 的角色提供者也调用 System。
- [COMS MenuCapabilityAction](/Users/yangzhaohui/work/www/finger/finger-master/projects/finger-service-coms/coms-boot/src/main/kotlin/com/sargia/finger/service/coms/action/MenuCapabilityAction.kt) 根据 appKey 选择 BFF。超级管理员能力目录只调用 BFF-System，不要求启动商户、MerApp、MT4、MT5 BFF。

这些结论针对选定调用路径。Spring自动配置、第三方SDK和后续Nacos有效值仍须在目标环境观察，不由静态搜索推定“启动没有任何副作用”。

## 数据与 profile 是启动前置条件

当前五个服务的 `application.yaml` 默认 profile 都是 `local`。对应 dev 配置仍有旧 `192.168.1.31:8848` 和同一个硬编码 namespace；local 配置指向本机 Nacos。初始盘点时源码中没有这五个服务完整的 prod 配置文件，部署仓库也未发现 `configs/<repo>/application-*.yaml` 实体文件。

因此不能只修改服务IP后启动，也不能只设置 `NACOS_SERVER_ADDR` 这个通用变量就假设旧 YAML 会引用它。建议主 AI 在目标私有运行配置中明确设置：

| 项目 | 必须核对的实际配置 |
| --- | --- |
| 应用身份 | `spring.application.name` 与 Nacos service 名称一致 |
| profile | 测试使用显式 dev/已选测试配置；正式使用显式 prod 和完整外置配置 |
| 注册发现 | `spring.cloud.nacos.discovery.server-addr`、namespace、group、实际可达的注册 IP |
| 配置中心 | `spring.cloud.nacos.config.server-addr`、namespace、group，以及导入的 data-id |
| Nacos 导入 | finger-common.yaml 与服务配置确实存在且属于目标环境，不能依赖 optional 导入悄悄缺失 |
| 数据库/缓存 | 只连目标测试组件；库、账号、权限、Redis和上传目录与正式隔离 |
| JWT/网关 | JWK 地址、授权服务器、路由和令牌受众均在目标环境闭合 |
| 外部能力 | 默认网络策略拒绝未选外部支付、券商、SMTP/SMS等出口 |

凭据放权限600的目标运行配置或环境文件，不提交到本目录。配置中心地址、发现地址和 namespace 分别核对，不只检查一个总地址。

数据库初始化仍等用户选择和主 AI 的实际方案。Auth 需要 OAuth2 registered_client、authorization、authorization_consent 等表；System 需要 user、role_info、role_permission 等表和专用管理员；COMS 需要 permission_*、file_info、字典/区域等本批次会访问的表。不能将 `db/finger_ums.sql` 当成所有服务的统一初始化脚本。空库、旧数据迁移、只导DDL与正式数据复制会产生不同的权限和任务状态，未决定前不启动Auth进行隐式初始化。

COMS 默认上传目录 `/data/uploads` 需要目标持久化盘和测试域名。首轮即使单实例也应验证重建/重启后文件可读，不能把容器/进程启动当成存储验收。

## Java、构建与现有制品

本机已只读执行 Temurin `java -version`，得到 **21.0.10+7 LTS**。五服务使用 Gradle Wrapper 8.14.3，本机存在对应 wrapper 缓存；它们的 Gradle JVM 默认堆为2GiB、Metaspace512MiB。4GiB发布机需要限制构建并发，避免同时运行多个Gradle/Kotlin构建。

发现 Auth、Gateway、COMS、BFF-System 的现有 boot JAR 均标记 Spring Boot 3.5.4、Build-Jdk-Spec21，入口 class major65。原工作树盘点时System只有API JAR；本轮已在private隔离副本重建System boot JAR，见末节。现有JAR的摘要和时间见JSON，但没有证明它们来自当前 HEAD，不能直接认定是本轮发布版本。

更关键的是，现有 boot JAR 内存在**同名同版本、内容不同**的内部依赖：

| 同名依赖 | 已观察到的不同内容来源 |
| --- | --- |
| common-web-1.0.0-plain.jar | Auth 与 BFF-System/COMS 不同 |
| common-security-1.0.0-plain.jar | Auth 与 BFF-System 不同 |
| ums-api-1.0.0.jar | Auth 与 BFF-System 不同 |
| system-api-1.0.0.jar | Auth 与 BFF-System 不同 |
| coms-api-1.0.0.jar | BFF-System 与 COMS 不同 |

差异由嵌入JAR的SHA-256证实；不推断它们一定ABI不兼容，但足以说明不能按“版本都1.0.0”直接拼装。建议在独立构建目录冻结所选源HEAD，统一公共库/API的来源和摘要，再构建最小批次并记录发布manifest。

五服务声明的 **19 种内部依赖坐标在本机Gradle缓存中均存在二进制JAR**，gradle-conventions 1.0.0及插件marker也有缓存。Maven local并不齐全，且多个坐标有不同缓存内容。缓存存在不证明完整离线构建一定成功，不证明API与当前源码一致；初始盘点未运行Gradle；随后已完成末节所述隔离构建，始终没有清理原缓存或执行publish。

本机Nexus状态接口匿名GET返回200。源码默认外部仓库的 system-api、common-web 匿名HEAD返回403；认证制品可下载性和新目标Nexus制品可用性均未验证。

一次计划携带本地Gradle凭据访问该外部仓库的探测被自动审批拒绝，命令未执行、未发送凭据。此后不通过本机Nexus代理触发同一外部认证访问。若后续确需访问，应由主 AI 集中确认具体仓库和用途；本轮已将可完成部分限制在本地缓存、JAR和源码元数据。

## 现有发布流程不应直接整套执行

[deploy/common.bash](/Users/yangzhaohui/work/www/finger/finger-master/projects/deploy/common.bash) 的环境到分支映射为 dev→dev、prod→main；构建使用 `projects/deploy/repos` 内的独立仓库，不是当前 `projects/<repo>` 工作目录。[deploy-select.bash](/Users/yangzhaohui/work/www/finger/finger-master/projects/deploy/deploy-select.bash) 会走同步、API发布、构建、部署链，不能当纯构建预检。默认构建 `SKIP_TESTS=1`，成功生成JAR不等于测试通过。

当前发布配置 dev 有39个目标、prod有38个；prod缺少Stock，列表仍包含已废弃CUS。`bridge-gateway`、`kyc-gateway` 在当前 `projects/` 下没有同名源码目录，不能猜测它们与现有bridge/KYC项目等价。工作区还缺少gradle-conventions源码目录，虽然本机有已缓存插件。

首批构建建议由主 AI 在隔离发布目录进行：选择明确源HEAD→校验工作区→整理内部契约制品→先尝试离线解析/构建→完成适用测试→生成commit/配置版本/内部依赖摘要/JAR摘要manifest→只向已分配的测试运行机发布。离线缺失依赖时先报告具体坐标与批准目的地，不自动带既有凭据访问源码默认外部地址。

当前发布脚本默认以root运行、Java位于root的mise目录，与模板中deploy用户和另一套目录约定不同。ub登录、发布权限和业务普通用户运行分别验收；不能把ub SSH成功解释为原脚本可直接使用。

## 禁止随首批自动启动的能力

| 项目/类别 | 原因与当前策略 |
| --- | --- |
| FDS、SUBS、EXS | 资金、支付、交易与Outbox/恢复任务；首批不启动，不复制生产待执行状态 |
| Stock | 订单/资金与Broker交接、Inbox/回报补查；当前自动外发由数据库RUNNING/PAUSED控制，不能套用已删除的stock.outbox-enabled |
| Broker、MTFS | 外部券商/交易平台连接；Broker有效enabled连接会被订阅，没有可以假定存在的全局MQ停用开关 |
| MSGS | 邮件、短信、第三方通知与消息消费；首批不启动，禁止真实外发 |
| UMS | 管理员最小链不需要；其Outbox会联动资金/审核/消息等，后续按数据初始化和隔离策略增加 |
| AUDS | 当前存在自动审批定时任务；不能把服务启动等同只读审核查询 |
| MDS、STAS、CMS、MKTS、Bridge、Fundamentals | 定时同步、统计、通知或外部集成候选；逐项查有效配置和数据后采纳 |
| CUS | 工作区规则已废弃，不因旧发布清单仍包含就重新上线 |

测试环境网络出口和账号权限是最终边界，不能仅靠某个应用布尔开关隔离真实外发。MQ账号/vhost、数据库、外部账号、回调地址及待执行记录分别审查。此任务没有获得真实资金、券商或通知外发授权。

## 三台正式Java节点候选分组

每台仍为6vCPU/16GiB。下表是候选位置和内存准入预算，**不是批准39目标同时启动**。第一批只在测试节点运行选定链；正式节点待初始化、制品与业务验收后逐批采纳。

| 节点 | 来宾内存 | JVM最大堆合计准入上限 | 原生内存/Metaspace/线程预算 | 系统预留 | 额外余量 |
| --- | ---: | ---: | ---: | ---: | ---: |
| java-prod-01 | 16 GiB | 8 GiB | 4 GiB | 2 GiB | 2 GiB |
| java-prod-02 | 16 GiB | 9 GiB | 4 GiB | 2 GiB | 1 GiB |
| java-prod-03 | 16 GiB | 8 GiB | 5 GiB | 2 GiB | 1 GiB |

**java-prod-01 候选：** `finger-gateway-mobile`、`finger-auth`、`finger-service-system`、`finger-service-coms`、`finger-service-bcs`、`finger-service-cms`、`finger-bff-system`、`finger-bff-merchant`、`finger-bff-merapp`、`finger-bff-app`、`finger-bff-web`、`finger-bff-developer`、`finger-bff-sargia`。

**java-prod-02 候选：** `finger-service-ums`、`finger-service-fds`、`finger-service-subs`、`finger-service-auds`、`finger-service-exs`、`finger-service-stock`、`finger-service-broker`、`finger-service-mtfs`。

**java-prod-03 候选：** `fundamentals-service`、`finger-gateway-trascan`、`finger-bff-trascan`、`finger-service-trascan`、`finger-service-mds`、`finger-service-mkts`、`finger-service-stas`、`finger-bff-socket`、`finger-service-msgs`、`finger-service-scs`、`finger-bff-trade`、`finger-service-cus`、`bridge-gateway`、`finger-bff-bridge`、`finger-service-bridge`、`finger-bff-mt4`、`finger-bff-mt5`、`kyc-gateway`。

node03中的CUS不采纳，两个无同名源码目标保持未映射。金融组默认不启动。各组预算是计划值，不能替代实测RSS；同一节点的Metaspace最大值、线程栈、Netty/direct buffers、文件缓存和连接池都计入预算。实际超预算时减少并行服务、重新分组或扩容，不能靠宿主swap维持。

当前prod默认38×2GiB最大堆约76GiB，仅堆就超过三台Java节点48GiB。测试默认39×512MiB最大堆约19.5GiB，也超过8GiB测试节点。首批五服务建议每个Xms128MiB，最大堆分别Gateway512、Auth768、System512、COMS768、BFF-System768MiB，合计3328MiB；每个Metaspace上限256MiB另计。这是起始配置，冷启动和业务RSS还需实际观察，未承诺容量或SLO。

## 启动与验收顺序

1. 冻结首批源HEAD和内部契约版本，修复/确认制品一致性与发布用户路径。
2. 由主 AI 依据用户初始化选择准备隔离测试schema、管理员、OAuth客户端和COMS必需数据；拒绝导入真实待发任务。
3. 核对目标MySQL、Redis、Nacos和必要RabbitMQ隔离；生成目标运行配置并验证无旧地址和真实外部凭据。
4. 依次启动System、COMS、Auth、BFF-System、Gateway。这里是后续操作顺序，本次未执行；COMS对BFF的能力目录调用在BFF就绪后再验收。
5. 执行管理员captcha/认证、角色或员工只读查询、COMS权限读取和合成文件上传；只读采集与写测试数据分别留证。
6. 执行被明确指定的重启/持久化演练；记录资源、日志和未上线页面。BCS等provider按选定页面增加。
7. 用户若选择部署全部业务，先补齐源映射、schema与任务隔离，再分批验证；不能直接使用旧39目标清单批量启动。

## 当前仓库状态

以下是本次只读Git快照，主 AI 实施前应再次核对。dirty仅表示存在改动，不自动提交、切分支或清理；Auth和Broker当前dirty项为文档路径，仍须保留。

| 仓库 | 分支 | HEAD | dirty条目 | 首批/限制 |
| --- | --- | --- | ---: | --- |
| deploy | `main` | `81148e8614` | 0 | optional-review-before-start |
| finger-auth | `codex/feat-omva` | `ecb67536e4` | 1 | 首批候选 |
| finger-bff-app | `codex/feat-omva` | `97dfec188b` | 0 | optional-review-before-start |
| finger-bff-bridge | `main` | `2883b2577c` | 0 | optional-review-before-start |
| finger-bff-developer | `codex/bitgo-broker` | `bfa3a25a7f` | 0 | optional-review-before-start |
| finger-bff-merapp | `main` | `bfa6165a96` | 0 | optional-review-before-start |
| finger-bff-merchant | `codex/feat-omva` | `63a59a6f14` | 0 | optional-review-before-start |
| finger-bff-mt4 | `dev` | `190b960a2c` | 0 | optional-review-before-start |
| finger-bff-mt5 | `dev` | `0a6b654b5a` | 0 | optional-review-before-start |
| finger-bff-sargia | `main` | `4c73fb5de0` | 0 | optional-review-before-start |
| finger-bff-socket | `codex/feat-omva` | `0f984ba0f2` | 0 | optional-review-before-start |
| finger-bff-system | `codex/bridge-kyc-review` | `37896647fa` | 0 | 首批候选 |
| finger-bff-trade | `codex/feat-omva` | `33693155f2` | 0 | optional-review-before-start |
| finger-bff-trascan | `main` | `756c26f26d` | 0 | optional-review-before-start |
| finger-bff-web | `codex/feat-omva` | `7b8ecc2e82` | 0 | optional-review-before-start |
| finger-common-lib | `main` | `ffba5364b3` | 0 | optional-review-before-start |
| finger-gateway-mobile | `codex/fix-fund-session` | `5718f44d8c` | 0 | 首批候选 |
| finger-gateway-trascan | `main` | `1df22d7df7` | 0 | optional-review-before-start |
| finger-service-auds | `codex/omva` | `a13bef2c48` | 0 | notifications-or-workflow-or-outbox-review-required |
| finger-service-bcs | `main` | `b1d6ecb48b` | 0 | optional-review-before-start |
| finger-service-bridge | `main` | `94e8fdca1c` | 0 | notifications-or-workflow-or-outbox-review-required |
| finger-service-broker | `codex/feat-omva` | `fde66760c7` | 6 | financial-or-broker-external-execution-restricted |
| finger-service-cms | `main` | `90ab2ee9d3` | 0 | notifications-or-workflow-or-outbox-review-required |
| finger-service-coms | `codex/fix-traditional-city-names` | `53c831d176` | 0 | 首批候选 |
| finger-service-cus | `main` | `ef4a8a5bb1` | 0 | deprecated-do-not-start |
| finger-service-exs | `dev` | `8c6c8a5dcd` | 0 | financial-or-broker-external-execution-restricted |
| finger-service-fds | `codex/feat-omva` | `4b578b5b4b` | 0 | financial-or-broker-external-execution-restricted |
| finger-service-kyc | `main` | `fdc7867187` | 0 | optional-review-before-start |
| finger-service-mds | `codex/feat-omva` | `b51632ad08` | 0 | optional-review-before-start |
| finger-service-mkts | `main` | `f9a0d105cb` | 0 | notifications-or-workflow-or-outbox-review-required |
| finger-service-msgs | `codex/feat-omva` | `1365309ff5` | 0 | notifications-or-workflow-or-outbox-review-required |
| finger-service-mtfs | `main` | `44bee7d9b1` | 0 | financial-or-broker-external-execution-restricted |
| finger-service-scs | `main` | `67629b669a` | 0 | optional-review-before-start |
| finger-service-stas | `main` | `40064d0076` | 0 | notifications-or-workflow-or-outbox-review-required |
| finger-service-stock | `dev` | `67627b531a` | 0 | financial-or-broker-external-execution-restricted |
| finger-service-subs | `main` | `77b75c54fd` | 0 | financial-or-broker-external-execution-restricted |
| finger-service-system | `dev` | `9ec3a82ded` | 0 | 首批候选 |
| finger-service-trascan | `main` | `6266a780ce` | 0 | optional-review-before-start |
| finger-service-ums | `main` | `ada7bfb2f5` | 0 | notifications-or-workflow-or-outbox-review-required |
| fundamentals-service | `main` | `9aecdd1a01` | 0 | optional-review-before-start |

## 本次验证边界

已执行：文件/仓库只读扫描、JAR manifest/class major与内部依赖摘要比较、本机Java查询、缓存检查、无需凭据的Nexus状态/匿名响应检查，以及下述隔离offline构建。未执行：Spring上下文测试、API发布、原缓存清除、目标Java启动、数据库初始化、真实资金/券商/通知外发或切流。

当前仍待主 AI 处理：用户的数据初始化选择、发布源HEAD、相同坐标不同内容的制品收敛、目标Nexus制品访问、新运行profile和schema、客户端secret/回调策略、正式业务SLO与独立备份目的地。这里只表示实施前核查完成，不能据此将部署或业务验收置为passed。


## 独立 offline 构建结果（2026-11-06）

**五服务的compileKotlin和bootJar均已退出0；测试状态统一为 `blocked-missing-isolated-test-config`，运行状态为 `not-started`。** 完整证据见 [build-status.json](build-status.json)。这些制品不包含环境application YAML，必须由主AI提供正确的目标运行配置、schema与账号后才可启动。JAR构建成功不代表Linux AMD64目标运行或业务验收通过。

| 服务 | 新boot JAR大小 | SHA-256前16位 | 测试/运行 |
| --- | ---: | --- | --- |
| finger-gateway-mobile | 91220068 bytes | `971e07f24704a814` | 全上下文blocked / 未启动 |
| finger-auth | 112317676 bytes | `b003de47f326fbe8` | 全上下文blocked / 未启动 |
| finger-service-system | 100405912 bytes | `3ddfff8c5cd6d480` | 全上下文blocked / 未启动 |
| finger-service-coms | 135495088 bytes | `3c124f75c9d1bc20` | 全上下文blocked / 未启动 |
| finger-bff-system | 96981061 bytes | `d6302ef18bb1c526` | 全上下文blocked / 未启动 |

已逐个记录实际构建输入树内容SHA-256、原始HEAD/dirty快照和boot JAR内全部内部库摘要。五份制品中，**同名内部依赖没有发现不同SHA-256**。原工作树的同版不同内容问题通过隔离契约选择/重建解决，没有覆盖原缓存或原JAR。

### 源码、凭据和资源边界

- `offline-build.py`复制五服务当前工作树到 `private/java-build/repos`，不改原分支、HEAD和dirty。排除.git、build、.gradle、runtime application配置、gradle.properties、密钥/凭据文件；合法Password/Credential Kotlin源码保留。
- 首次过滤过宽误排除PasswordDTO等11个合法源码文件，已只在隔离副本补回，并记录 `snapshot-source-correction.json`；该失败不作为真实业务源码错误。原始失败日志仍保留。
- 独立GRADLE_USER_HOME复制既有缓存，不复制用户gradle.properties、init脚本或daemon日志。干净进程环境不继承Nexus/AWS/proxy认证材料。
- 每次Gradle均强制offline、no-daemon、最多2workers、1GiB堆/384MiB Metaspace、Kotlin进程内编译和串行操作。
- Gradle由sandbox-exec限制外部网络，只允许本机锁/daemon loopback通信，并拒绝读取原用户Gradle凭据、Maven settings和SSH目录。初次普通沙箱socket失败后，主AI批准了保留上述网络限制的执行权限。
- 仅在明确出现公开Jackson2.19.0构建依赖缺失后，主AI允许单独从官方Maven Central无凭据下载6组精确JAR/POM及SHA1校验文件，额外记录SHA-256。Gradle本身仍禁止外网；没有重试私有仓库认证。来源和摘要见private的 `public-jackson-download.json`。
- System唯一SpringBootTest需要真实上下文。为避免接触本机源DB/Nacos/Redis，没有执行该测试，也没有随意关闭业务Bean或传入 `-x test`。其余运行上下文测试同样等待专用目标配置。

### 契约统一依据

| 契约 | 本轮采用方式 |
| --- | --- |
| gradle-conventions1.0.0 | 选唯一有效679B marker POM，排除同名50KB HTML；实现JAR与.module的size/SHA256/SHA512一致 |
| common-core/apidoc/web/easyquery/snowflake/redis/security/voucher | 唯一有效module/POM与二进制摘要匹配，复制至私有file repo |
| System、COMS、FDS、AUDS API | 当前源码的API-only/隔离模块编译，生成本地POM/module后普通文件复制，不运行publish |
| MSGS API | 当前源码API-only快照；System使用includeBuild，BFF使用同一新JAR的file repo |
| UMS API | 当前sources.jar与93个源码文件逐字节一致；module同时引用该sources与相同二进制，未按mtime选择 |
| common-sms | 缓存只有JAR且Maven-local源码与当前默认属性不同，故从当前源码离线重建；没有启动或发送短信 |
| EXS API | 当前源码API可构建；原发布配置只声明artifact，没有Java component，POM缺传递依赖且module任务SKIPPED。BFF隔离settings改用includeBuild保留项目依赖语义，没有伪造module或修改原发布配置 |
| BCS/CMS/MKTS/SUBS API | 缓存唯一有效module/POM与二进制摘要匹配 |

方案与实际状态见 [contract-unification.json](contract-unification.json)。缓存或source JAR匹配不替代业务测试；此处只关闭制品来源和编译层问题。

### 脚本与证据

| 脚本 | 作用 |
| --- | --- |
| `offline-build.py` | 准备隔离源码/缓存；按唯一run-id执行tasks、compile、metadata、bootJar，保留每次结果 |
| `prepare-plugin-file-repo.py` | 校验插件marker与实现并注入隔离pluginManagement |
| `extend-file-repo.py` | 将无歧义且经module摘要验证的内部制品加入私有仓库 |
| `prepare-msgs-contract.py` | MSGS API-only快照与System复合构建替换 |
| `prepare-sms-source.py` | 当前common-sms模块隔离源码，不包含其他common运行组件 |
| `prepare-api-source.py` | FDS/AUDS/EXS API-only隔离快照，不包含boot模块 |
| `download-public-jackson.py` | 只下载已批准的官方Jackson2.19.0精确公开依赖与校验 |
| `export-source-api.py` | 从已构建源码和Gradle元数据生成私有file仓库文件，不执行publish |
| `record-artifacts.py` | 汇总五服务输入树、制品和嵌入依赖SHA，检查同名内部依赖一致性 |

private目录下的snapshot、契约选择、官方依赖下载、每次日志/JSON和artifact manifest均保留；原始失败记录没有覆盖。脚本拒绝覆盖已存在的快照、选择manifest和同名日志，后续操作由主AI指定新run-id或独立工作区，不自行删证据。

当前完成的是“可构建的最小五服务制品”。下一步为目标测试库/schema/账号初始化、完整外置profile、隔离Spring测试、目标启动及真实业务链验收；不会因为这批JAR已生成就把这些事项标成passed。


## 目标测试链部署准备

目标VM240/10.63.20.20与data-test VM210/10.63.20.10的外置配置、18表fresh `_test` SQL、合成管理员、独立DB账号、guest-only JDK21、systemd部署/回退脚本已准备。测试issuer候选明确使用 **http://192.168.21.22:19999**，主机9999预留正式网关。新秘密只在private/java，未执行目标SQL、Nacos写入或启动服务。

Auth在隔离副本增加部署配置绑定，缺关键issuer/客户端secret/回调fail-closed，5项纯单元通过，JAR已重建并刷新build-status。全量Spring/目标上下文仍blocked。操作和边界见 [runtime/README.md](runtime/README.md)，升级需保留 [patches/README.md](patches/README.md)。
