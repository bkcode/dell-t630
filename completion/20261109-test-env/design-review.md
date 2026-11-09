# 空测试基础环境：独立Nacos namespace最小增量复核

日期：2026-11-09。仅本地设计/审查，没有SSH、API调用、SQL、账号变更、服务启停或Git。实际producer实施后另取证，本文不构成已建立或已验收声明。

## 范围判断

拟方案符合用户最终范围：**复用VM210既有测试基础服务，保留全部旧数据，仅增加独立空namespace及一条精确权限**。不新增VM/容器/密码/用户/角色，不恢复、迁入或复制Mac源数据，不启动Java业务/旧release，不重启任何现役服务。

现有基线见[preflight.md](preflight.md)与[preflight.json](preflight.json)：

- VM210/data-test/19.20，现有4个MySQL/Nacos/Redis/Rabbit容器健康。
- 旧`finger-test` namespace=`10719261-2641-590a-b821-c8484ca955ac`，`DELL_TEST`组7份yaml，当前配置历史元数据COUNT9。不能按旧文档6配置等数字删回去。
- 正式业务测试schema实际为`finger_auth_test`3表、`finger_coms_test`10表、`finger_system_test`6表，合计19表；`nacos_test`12表，全部保留。这里表数不等于业务行数，本次不读业务行，不建“新空业务库”或truncate。

**“空”只指新`finger-test-empty` namespace当前配置总数0、注册服务总数0**。它不表示整台210、MySQL、Redis/MQ或旧namespace无数据，不表示完全独立身份或物理隔离。继续复用原`finger_test`账号及其原关联角色后，该账号保留旧namespace能力并新增新namespace能力；这是同一测试主体访问两个测试空间，不得写成旧权限被撤销或新账号独占。

## 允许的精确增量

1. root在producer合同固定一个新UUID、name=`finger-test-empty`、明确desc和目标VM210/Nacos endpoint；本设计不自行分配UUID。ID必须非空，且不同于旧namespace、public、正式及其它登记ID；不能把显示名称当ID。
2. 仅管理员`POST /nacos/v1/console/namespaces`，使用`customNamespaceId`、`namespaceName`、`namespaceDesc`。没有PUT旧namespace、DELETE namespace、导入/克隆/发布配置、注册服务等动作。
3. 仅对`finger_test`账号现有关联且已核的client role新增`resource=<newUUID>:*:*`、`action=rw`，通过`POST /nacos/v1/auth/permissions`。role字段必须取已核关联角色名，不能把username `finger_test`直接当role；不使用`*:*:*`，不改旧permission，不重建user-role关联，不新增管理员能力，不给client控制台namespaces/permissions管理权。

这两项API是**持久化管理写**，会改变Nacos元库中的namespace/permission元数据；“不执行SQL”指不直接发SQL/迁移/清理旧库，不应误称本操作完全只读或元库逐字未变。允许差异仅为新namespace和精确新grant，原配置/历史、账号密码/关联及旧grant都应保持。

官方2.4.3源码中namespace创建返回Boolean，空customNamespaceId会自动生成UUID、重复ID可能返回false；必须固定ID、检查响应值和再读回，不能只看HTTP200。[NamespaceController](https://github.com/alibaba/nacos/blob/2.4.3/console/src/main/java/com/alibaba/nacos/console/controller/NamespaceController.java)

权限API参数为role/resource/action，列表有accurate分页形式；成功响应需要应用层检查，并读回唯一精确tuple。不按第一屏或HTTP200假设写入结果。[PermissionController](https://github.com/alibaba/nacos/blob/2.4.3/plugin-default-impl/nacos-default-auth-plugin/src/main/java/com/alibaba/nacos/plugin/auth/impl/controller/PermissionController.java)

## producer前置门禁与幂等

- 来宾/原Nacos容器身份、image ID、endpoint必须匹配210及现有测试实例；不得从参数拼出生产200/201 endpoint。目标HTTP不经默认代理，不从Mac源读取配置或凭据。
- 旧namespace/name、原client username-role关联、精确旧grant均符合当前基线。若找不到或出现多个/宽通配grant，拒绝写入，不能调用旧`manage.py initialize`补用户/重置密码来“修好”。
- 先读取全部namespace和该角色完整分页permissions；新ID与同名namespace均不存在时才create。若同名不同ID、同ID不同owner描述、已有配置/服务、或预期grant漂移，一律停止。不能盲接管/清空碰巧已存在的对象。
- 若新对象已与本次固定合同完整匹配且为空、grant也恰好已有，可作为已存在读回验收，明确created=false、permission_added=false，不再次写入。只有一项存在时按明确差异补另一项，不能删旧重建。
- producer自身持锁防并发运行，记录before及实际成功阶段；每个POST限定endpoint/参数/超时。POST超时可能已经提交，先只读查确切ID/grant，不能因无响应重试多个新UUID或初始化整套环境。
- 复用现有受控管理员/client凭据，登录token只在target私有进程/内存，保持原密码文件stat与内容摘要（摘要仅私有比较）。不把password/token放argv/URL/普通日志，不输出配置值或API原body。不得创建临时新密码来逃避已有身份问题。

## 如何证明旧数据没有被本次改变

操作前后只通过Nacos管理/读取API取小范围基线，producer不执行SQL或业务数据查询：

- namespace列表按ID稳定排序；before/after差集只能是新ID（重跑可为无差集），旧显示名/desc等保持。
- 旧namespace的7份配置元数据及全部分页结果集合保持；若必须取完整内容才能证明，应仅在来宾私有内存比较，不在普通证据存内容/MD5/SHA。已有API字段不足时明确只证明元数据，不虚构逐字内容证明。
- 对旧7配置的history列表/版本ID、时间等元数据分页比对，旧历史仍9且集合相同；不通过发布再删除的方式证明读写，因为删除也可能留下历史。
- 现有user/role/permissions的完整已有集合保持，新增只能是新UUID精确rw tuple。若users API返回敏感hash，仅进程内比较并抑制原body，不记录hash或凭据。没有可观察password hash接口时，以密码文件身份/内容私有比较、原登录仍成功及完全没有密码更新API调用说明边界，不能声称服务端hash逐字已查。
- MySQL业务schema/表及业务行不在此producer查询/修改；现有preflight确认的19表与nacos_test12表作为保留合同，不把“没有发SQL”冒称逐行全库一致性重验。
- 4容器ID/PID/StartedAt/restart/health及原文件SHA/stat前后保持；本次不动.env、Compose、Java配置、Nacos namespace默认指向或发布基线。

列配置/历史API可能在响应中携带content，即便只需要计数也不得打印/保存全响应。计数相同不等于对象集合/内容相同；普通报告只给计数、比较布尔和允许的新namespace公开ID。

## 新空间与权限的可观察通过条件

1. 管理员读回确切新ID/name/desc存在且唯一；权限精确新增1条（或幂等重跑0条），旧所有条目保留。
2. 配置列表明确带`tenant=<newUUID>`、有界分页，`totalCount=0`且items为空；必要的namespace详情configCount也应0。不能漏tenant而检查public，不能只查`DELL_TEST`一个group就声称namespace全空。
3. 服务查询明确带新`namespaceId`，使用namespace全group的catalog列表、无service/group过滤、`hasIpCount=false`，同时包含零实例持久service的可能；总数0且列表空。只查默认group或只看健康实例不足以证明“0服务”。2.4.3的catalog有`/v1/ns/catalog/services`、namespaceId/pageNo/pageSize、groupNameParam/serviceNameParam等参数；producer须按实际响应形态核对，不凭猜测路径或404判空。[CatalogController](https://github.com/alibaba/nacos/blob/2.4.3/naming/src/main/java/com/alibaba/nacos/naming/controllers/CatalogController.java)
4. 用原client现有凭据重新登录，仅GET固定不存在的dataId/group、明确新tenant，期望404；同时已验证namespace真实存在，因此404不是“namespace不存在”的替代证明。control namespace用同一个只读probe，应403，不能把401、登录页302、500或无响应算权限拒绝。
5. 不新增control namespace或control配置，不读取正式服务；control只是目标测试Nacos上的固定未授权namespace resource。先核原client没有控制namespace或全namespace通配权限，避免把权限漂移当probe错误修掉。
6. 鉴权缓存可能延迟；只允许在有限时间内以新登录token复读，不重启Nacos、不反复叠加grant或改密码。若404/403未达预期，记录actual状态并停，不能把200空body或真实配置值当“可访问成功”。

**本次不发布测试配置、不注册实例**，所以rw只证明管理员读回的声明授权，client实际只验证read及越权拒绝；不冒称配置写入/发现注册或Java业务链已经功能验收。已有服务健康可继续独立只读检查。

## 失败与回退边界

最小producer只需要2个创建POST，其余GET与登录，不设计自动DELETE回退。namespace创建成功而grant失败时，保留该空namespace并报partial；权限不完整不是许可去删旧对象/重建账号。

如确需回退，也只能由主AI对本次确证新建的精确grant/namespace审核执行。必须再证0配置/0服务且对象来源明确；不能因本次曾看到空就自动删namespace——其它client可能已开始使用，namespace删除可能清掉后来写入的配置。API超时/对象归属不明时禁止“清理全部新ID/权限”。

旧namespace、7yaml、history、19业务表、nacos_test12表、所有密码/关联、备份timer及正式备份范围不变。新增namespace不会把测试数据纳入正式自动备份，不启新的调度或通知。

## 本期验收表达

可签“现有测试基础服务健康，独立新namespace为空、原client获其精确权限，旧数据保留，无业务部署”；不能签“测试机/数据库全空”“完全独立账号”“业务测试已上线”“迁移完成”。新UUID未来只是可选入口，不自动切旧应用配置或停旧消费者。

producer执行证据至少含时间、target210/Nacos版本、固定ID、created/grant_added实际布尔、新空间config/service counts、client404/control403、原集合保留比较及4容器身份保持；秘密与内容不输出。当前设计尚无服务器动作或passed结果，待producer提供后再审核其具体接口、分页、超时和不可扩大写入范围。
