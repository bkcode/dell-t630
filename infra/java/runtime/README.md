> 文档状态（2026-11-07）：本页为阶段实施/技术记录，文中“当前”、网段、角色数与通过结果以原执行时点为准。服务器现因UEFI0058内存错误暂停，Nexus合并已授权但未执行；当前配置入口见[访问清单](../../../12-service-access-and-operations.md)，恢复门槛见[最新交接](../../../11-live-handoff.md)。旧脚本、stage/commit或初始化步骤不得直接重跑。

# 最小 Java 测试链准备与部署

状态（2026-11-06）：**五JAR已在VM240校验stage，VM210的18表/合成管理员及六份Nacos配置已初始化与摘要复核，正在激活服务。** 以下准备阶段“未执行”叙述保留为脚本设计说明，实时结果以evidence/implementation/java-test-*.json为准。 主AI管理网络授权和来宾操作。本目录不启动正式资金、券商或通知服务，不修改原源码仓库。

## 目标和边界

| 对象 | 已确定目标 |
| --- | --- |
| Java测试节点 | VM240，`java-test-01`，`10.63.20.20` |
| 测试数据节点 | VM210，`10.63.20.10` |
| Java测试内网网关 | VM240端口9999 |
| LAN测试入口/issuer候选 | **http://192.168.21.22:19999**，DNAT至测试9999；主机9999留给正式环境 |
| 运行身份 | `finger`专用非root用户；`ub`仅用于部署 |
| Java路径 | `/opt/finger/java/bin/java`，指向普通用户可读的系统Java21 |
| 发布方式 | JAR + 外置YAML + systemd，五服务，环境配置不进入JAR |

实际OIDC metadata、回调和浏览器入口仍待目标验证。正式域名未确认，不能把LAN候选视为正式验收通过。上下文测试应在VM240执行，或使用VM240自身出口；业务MySQL账号Host严格为10.63.20.20，不放宽为PVE出口或Mac。

## Auth最小部署适配

[patches目录](../patches/)保存可重放转换脚本、`AuthBootstrapProperties.kt`和纯单元测试。补丁只作用于private的Auth副本，原`AuthorizationServerConfig.kt`受原SHA保护，升级时必须重新审查，不能静默沿用。

- `finger.auth.bootstrap.issuer`必填，直接绑定自定义AuthorizationServerSettings。
- 四个既有clientId的secret、redirect和post-logout URI必填，缺配置fail-closed；clientId/grant/scope不变。
- 同一配置重启时复用能匹配的既有编码secret；不使用DB触发器或post-start覆盖。
- 新随机秘密只在private/java。补丁源码和JAR不包含这些值；properties的toString已脱敏。
- 5项不启动Spring上下文的单元测试已通过：缺issuer、缺client/secret拒绝、外置值和URI、同secret重启稳定/变更轮换、Binder生效。完整Spring上下文仍blocked，不能借此声称DB/Redis/Nacos已验证。

最新Auth制品、源树和单元结果见 [build-status.json](../build-status.json)。补丁前后源树摘要见private的 `auth-deployment-patch-manifest.json`。

## 私有准备包

`prepare-test-chain.py`读取的已有基础设施秘密仅来自 `private/data/bundles/test-data`。只从本机Nacos采集键结构和白名单框架枚举，不拷贝源第三方API凭据或真实用户记录。

准备结果位于 `private/java/test-chain`：

- `runtime/<service>/application.yaml`：显式应用名、port、dell-test profile、强制Nacos imports、目标namespace/group/地址、注册IP；Auth/System/COMS各用自己的测试库账号。Gateway/BFF没有JDBC依赖，不创建无用途DB账号。
- `nacos-configs/DELL_TEST`：一份公共基础配置和五份服务配置。仅包含目标基础设施和本批次选定路由；不导入源完整配置。服务发现定位器关闭，不自动暴露其他微服务。
- `sql/databases-admin.sql`先建三个测试schema，结构DDL完成后执行`sql/accounts-admin.sql`。三个独立账号Host限定`.20`，只对所属组件18张明确表授予SELECT/INSERT/UPDATE/DELETE，避免数据库级下划线通配权限；DDL和账号管理由管理员单独执行。
- `sql/*-structure.sql`：目标18张应用表；无源业务DML、触发器或系统账号。
- `sql/synthetic-admin.sql`：仅合成管理员`FNTEST0001`和合成角色。`type=0`、`status=0`按当前ADMIN/ENABLE枚举。密码采用实际Spring delegating bcrypt，保留编码前缀且适配当前char(76)字段。
- `metadata.json`、`sql-package-manifest.json`：目标、账号名、schema、秘密路径、结构差异和SHA。秘密值不进入公开元数据或命令行。

随机密码保存在权限600的 `private/java/secrets`，重复配置准备会保留原值并验证已存管理员hash匹配，不会因issuer调整轮换秘密。目标SQL包只引用合成账号，不复制任何源用户行。

结构来源：对本机MySQL执行只读`mysqldump --no-data --skip-lock-tables --no-tablespaces --skip-triggers`，只导出指定表；不全局锁表，不导出mysql系统库，不执行源写入。Auth3表、COMS10表和System3表已采集；System源库缺当前实体的`admin_notice`、`admin_notice_delivery`。COMS的`menu_key`类型和新增`label_key`也与源结构不同。目标 fresh `_test` DDL按当前实体补齐，复用匹配源列的NOT NULL约束并记录差异，**必须由主AI审查后再执行**，不能将来源DDL当当前源码完全一致。

## 来宾JDK基础

`install-jdk21.sh`只接受Debian13 AMD64、指定角色hostname和guest root，拒绝PVE。支持三个正式Java节点、测试Java节点和publisher。它不启动任何应用或执行SQL。

脚本从已配置的Debian签名APT源安装`openjdk-21-jdk-headless`、Python/YAML工具，以及 **fonts-dejavu-core/fontconfig** 支持无GUI图形验证码；记录实际包版本，可用`--package-version`固定版本。Java系统路径不依赖root的mise目录。业务运行目录和账号由脚本建立，publisher只建立Java基础。

参考：[Debian Java21包](https://packages.debian.org/trixie/openjdk-21-jdk-headless)、[AMD64系统Java路径](https://packages.debian.org/trixie/amd64/openjdk-21-jre-headless/filelist)。本方案使用Debian OpenJDK21，原发布脚本的Temurin/root私有路径要求不能直接沿用。

```bash
sudo bash install-jdk21.sh --check --role java-test-01
sudo bash install-jdk21.sh --apply --role java-test-01
```

`--check`不安装，缺基础时明确失败；apply需主AI通过已验证的来宾SSH执行，不在本机或PVE运行。正式三个节点和publisher替换对应role，仍不启动业务。

## 目标初始化与Nacos配置

当前网络私网授权仍由主AI处理。这些脚本均已准备，以下apply步骤**尚未执行**。

1. 数据侧只接收metadata、SQL、Nacos配置和所需脚本，不接收本机源数据或Java runtime目录里的OAuth秘密。
2. 先审查18表DDL、两个缺表和COMS差异；核对SQL包完整SHA。`apply-test-sql.py`默认仅校验；显式apply要求目标数据来宾root、正确hostname/IP、正确test-data bundle和`--reviewed-structure`。
3. 初始化通过容器自己的root secret文件传入MYSQL_PWD，不把密码放argv或日志。首次只接受空的目标测试schema；有未标记对象则停下审查。成功后记录结构hash注册表，重复运行要求同结构，不盲目覆盖或删除现有数据；若失败留下部分表，先审查而不自动强行续跑。
4. 应用账号只有DML。合成管理员由固定测试ID幂等插入，不覆盖碰撞记录；记录种子验证。结构或秘密需变更时走单独迁移，不能用旧初始化包隐式处理。
5. `publish-test-nacos.py`使用目标test-data的管理员秘密，只发往10.63.20.10，token仅在Authorization header，URL/日志不含token。只发布本namespace的DELL_TEST六份配置，并GET核对完整SHA。
6. 同名配置已存在且内容不同会拒绝覆盖，以免破坏回退输入；后续配置变更应采用另行审查的版本dataId/group或独立回退方案。现有发布脚本的回退不会修改数据库或任意覆盖Nacos配置。
7. 数据与Nacos各自结果仍不能代替业务验收。主AI在验证网络、schema、Nacos权限后，为Java节点组合root专用readiness marker。

SQL包hash从private的 `sql-package-manifest.json`读取；不要复制带真实秘密的SQL内容到对话。执行程序需传目标数据bundle的实际安装目录，不能猜路径或连接本机源MySQL。

## 发布与回退

`package-test-release.py`只打包已校验的新JAR和外置配置到private/java/releases，输出唯一release ID。每个文件都有SHA，包权限600；不部署。

`deploy-test-chain.py`分四个动作：

| 动作 | 效果 |
| --- | --- |
| check | 在目标来宾核对角色、IP、JAR/config SHA、显式profile和数据依赖，不启动 |
| stage | 写新immutable release，不切换当前指针、不启动 |
| activate | 需真实readiness marker，停五服务、原子切换当前release，按System→COMS→Auth→BFF→Gateway启动并核对health |
| rollback | 选择已存在的旧release，复用同样门禁与健康检查；不回滚数据库，不自动改Nacos |

运行用户为finger，JAR/root目录不可被应用写；配置finger可读600。systemd提供明确Xms/Xmx/Metaspace、MemoryMax、无root家目录依赖、headless/时区和受限写目录。网络隔离依赖主AI验证的有效防火墙，不以systemd active或局部配置存在替代证明。

激活失败会停下新版本；存在先前managed release时恢复其指针并重新核对health。全程保留新旧release，不自动清理。数据库、Nacos配置和凭据变化必须与旧版本兼容，不能将JAR回退当全栈恢复。

readiness marker由主AI依据真实证据生成，至少含target_ip=.20，以及database_schemas_ready、nacos_configs_ready、network_policy_ready、issuer_candidate_acknowledged。模板默认应为false；不能为了启动而把尚未验证项改成true。

上传文件由COMS持久化到 `/var/lib/finger/finger-service-coms/uploads`，标准静态资源配置保留classpath页面资源。测试Gateway只为 `/dell-test-files/**` 提供GET并剥离前缀；读取仍需要测试Bearer身份，URL和字节完整性待目标验证。内部COMS写API不对LAN自动开放。

## 当前验收状态

- Auth部署适配5项纯单元：passed；全量Spring/DB/Redis/Nacos上下文：blocked。
- 五服务最新制品：已打包，未在目标启动。
- 配置解析、目标账号分离、SQL仅结构与合成DML、秘密权限及JAR不含新秘密：本地静态检查。
- 目标SQL、Nacos写入、OIDC metadata、captcha图形、登录/角色、文件读写、重启/回退：未执行，待主AI网络授权和后续验收。

## LAN V2契约与已运行状态（2026-11-06）

初版平铺`/sys-api`路由与真实finger-admin默认clientRouteMap不符，登录成功后被Gateway10016拒绝。已保留原dataId，为Gateway新建`finger-gateway-mobile-lan-v2.yaml`，系统API通过`/finger-bff-system/sys-api/...`及StripPrefix1，文件GET通过`/finger-bff-system/dell-test-files/**`及StripPrefix2；COMS返回域名同步。默认clientRouteMap和JWT验证均保持，不以白名单放通业务API。Auth保留标准root OAuth/OIDC端点，并增加精确`/finger-auth`公共认证别名。

当前release20261106T121030已五health UP。正常验证码/登录、角色与权限读取、无Bearer/伪造签名拒绝、169字节合成PNG上传及认证读回SHA已通过；COMS单服务重启持久性验收由QA agent继续。前两轮真实失败（Gateway Bean加载、字体native库、未前缀403）已保留证据。准备metadata现标已初始化/versioned，原prepare --refresh会拒绝覆盖已执行包；后续配置需新dataId与release，不能重跑DDL或覆盖回退输入。

用户明确本期正式230/231/232仅交付运行环境，业务仅测试验收。三正式节点finger非root Java21字体/PNG诊断、NTP synchronized和OS running通过，未启动正式业务。
