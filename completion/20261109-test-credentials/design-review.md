# 仅VM210测试凭据同步：在线最小变更设计

日期：2026-11-09。用户最新已明确测试19.20固定凭据应与本机compose约定一致，覆盖此前“测试密码不改”的表述。本文件**不记录任何密码、认证hash或秘密原值**；指定值与旧值仅存guest私有恢复材料，不进入Git、argv、普通日志或聊天。

仅本地设计/公开代码审查，没有SSH、读取源secret/.env值、生成账号凭据、SQL/API写、服务启停、通知或Git。实施脚本需另行审核，本文件不作为已切换或已验收声明。

## 范围与权限所有权

唯一目标VM210/data-test/192.168.19.20，原4容器/UUID和现有数据保持。仅同步指定的MySQL root现有localhost及%账号、Redis默认认证和Rabbit指定管理身份；不改源Mac、正式200/201、Nacos管理员/DB用户、业务应用用户、TLS、认证插件、DB Host授权或网络规则。

已核本地公开合同：

| 组件 | 在线认证所有者 | 持久来源/消费者 | 应保持 |
| --- | --- | --- | --- |
| MySQL | mysql.user中现有root账号 | `secrets/mysql-root-password` bind；mysql-health.sh每次读取该文件；初始化env不能替现有mysql.user轮换密码 | root原plugin/SSL/Host/grants，nacos_test与业务账号不变 |
| Redis | Redis运行时默认用户requirepass | entrypoint每次从`secrets/redis-password`生成`/run/dell-redis/redis.conf`；health脚本每次读secret | 既有ACL/数据/持久文件/其它配置不变 |
| Rabbit | broker用户及vhost权限 | `.env`的管理username、管理secret供工具读取；`rabbit-definitions.json`由`management.load_definitions`供启动导入 | 原账号/app用户/权限、queues/messages、vhost数据不变 |

指定Rabbit管理名若原先不存在，这是**增加新管理账号**，不是把旧账号重命名或删除；切换工具的管理入口不意味着旧管理账号可移除。用户明确需要该身份访问默认`/`及现有`/finger-test`。默认vhost若缺失，可按本次精确需求新增空`/`，应如实计入允许差异，不创建其它vhost。

## P1：不能依赖“healthgap小于1秒”的假设

仓库supervise循环约5秒检查Docker health（实施前核已部署同版本），任何组件unhealthy会退出并在finally停止整组。MySQL/Redis health会读bind secret；认证runtime与文件存在短暂不一致时会失败。Docker有连续失败重试，不是一次失败立刻unhealthy，但**不能以15秒间隔保证切换肯定夹在两次探测之间**。

每组件开始前要求当前health=healthy、FailingStreak=0，保存监督MainPID和4容器ID/PID/StartedAt/restarts/health。预先准备全部新文件字节、恢复字节、验证连接及打开的安全文件描述符，再做最短在线切换；不在runtime/file切换两步之间临时下载/导出/等待API长重试。不停监督器、不mask健康检查、不增加失败阈值来通过。若无法安全控制窗口，停止该组件并报告，不能擅自升级成服务重启方案。

MySQL若可用双密码过渡，可缩短探测错配；Redis没有在这份旧requirepass合同内可直接等同采用的无缝过渡，不应顺带重设计默认ACL。Rabbit diagnostics健康不读取管理secret，风险更小，可先做它获得稳定回退管理入口。

## 所有阶段的前置与私有回退材料

- 固定guest hostname/IP/MAC、ext4挂载UUID、local Docker、4服务实际ID/镜像/健康，拒绝PVE/生产或远程Docker。账号Host、vhost和文件路径是静态白名单，不能由输入透传任意SQL/API路径。
- 在guest root700事务目录保留原secret文件字节/UID/GID/mode/dev/ino、env/definitions及精确账号/授权元数据；旧password/hash/SQL仅root600私有，不导出Mac。备份材料不夹业务数据，不新增自动备份范围。
- MySQL在私有内存核root两个**现有**Host行、plugin、SSL/X509要求、grant、account状态及secondary-password情况。缺失/多义先停，不自动CREATE root@新Host或授ALL。
- Redis核实际config_file、默认用户/requirepass机制与是否已有额外ACL、原配置属主及父目录权限；不假定只有一个认证源。
- Rabbit核当前实际管理账号、旧admin是否已存在、全部vhost/权限/用户/标签元数据和定义文件的startup归属。返回password_hash的API只在内存比较，不输出原body。
- 主体修改有单一事务锁与按阶段持久journal。中断后根据实际runtime+文件状态确认再继续，不盲重跑全部三项。相同指定值已在runtime/文件生效时只验证，不再轮换salt或改无关配置。

## 建议在线顺序

### A. Rabbit：先准备新管理入口，再切持久工具配置

1. 使用现有管理凭据连接固定测试management endpoint。新目标管理名已存在时保留其原tag/perms并只做获准的密码/管理员能力增量；不存在时PUT新增，旧管理与应用账号完整保留。
2. 用户PUT须带password或password_hash之一和明确tags；不能为了只改tags省略认证字段而意外禁掉密码登录。新用户仅所需administrator标签；已有用户额外标签如需保留取并集，不悄悄清掉。凭据与请求正文只走内存/stdin，认证头不打印。[Rabbit3.13 HTTP API](https://github.com/rabbitmq/rabbitmq-server/blob/v3.13.7/deps/rabbitmq_management/priv/www/api/index.html)
3. 只给新管理名在`/`和`/finger-test`的精确授权（按用户所需configure/write/read），API路径正确编码`/`，不批量替换所有用户权限、不删除旧permission。不向其它新vhost扩权。
4. 用新身份读取whoami与两vhost权限；如要AMQP功能验证只完成认证/打开vhost/关闭连接，不publish、consume、declare队列或清消息。保留旧管理连接/凭据作回退。
5. 完整构造并私有校验新definitions：只新增/修改本次目标管理用户的认证条目及其两vhost权限，若`/`缺失仅加该vhost；旧users/hash/permissions/queues/exchanges/bindings等原字段保持。新hash取broker已生效的权威表示，或使用已验证算法并在内存核新密码可认证；不输出hash。
6. 在线**不调用全量definitions import**，也不重启broker。定义文件是后续启动的持久来源，原inode重写其受控JSON，保证parser读回及旧集合+精确增量。同步`.env`中唯一RABBIT_ADMIN_USER键及管理secret，所有其它env键不变。原文件如被bind挂载不能os.replace。
7. 最后以新env/secret路径进行只读工具认证；旧应用AMQP用户与`rabbit-app-password`不变。若失败，先用仍可用的旧管理入口恢复本次目标用户/授权，再还原文件/env；不得批量导入旧definitions覆盖可能新增的队列/消息。

### B. MySQL：显式保plugin，优先审双密码过渡

MySQL8.4在`ALTER USER ... IDENTIFIED BY`未指定插件时使用默认插件；不能泛称“这条语句只改密码”。必须对每个root行用其**原实际plugin**的`IDENTIFIED WITH ... BY`形式，并不修改REQUIRE/SSL/Host/grants。语法不支持或外部认证插件则停审，不改成mysql_native_password或关闭TLS。[MySQL8.4 ALTER USER](https://dev.mysql.com/doc/refman/8.4/en/alter-user.html)

建议在确认没有既有secondary password且原插件支持后，按账户逐项：

1. 用旧root保持一个私有本地socket管理会话；保存本次精确行的原认证元数据，准备恢复但不DROP/CREATE账号。
2. 显式原plugin设置新值并RETAIN CURRENT PASSWORD，确认该行过渡成功；原health仍可用旧值。localhost/%可在已审支持的多账号语句处理，若逐条执行必须journal记录每一行，不能假设两条自动原子。
3. 原inode更新mysql-root-password并fsync，UID999/GID按原实际值、0600、dev/ino保持。新本地socket及远端TCP分别认证，只SELECT1/身份元数据；远端保持原TLS要求，不借此开启allowPublicKeyRetrieval、关闭SSL或改plugin/Host来消除1045。
4. 新健康稳定并新连接验证后，对本次两个root行DISCARD OLD PASSWORD，最终不留旧值继续可登录；再验证新连接/原SSL/plugin/grants保持。若开始已有secondary，不得用RETAIN覆盖它，先报告并选最小受控单密码窗口。
5. 出现问题时以仍可用管理连接/本次新旧凭据之一恢复原plugin对应认证字段，并原inode还原文件；反向验证完整后才结束。不要恢复整个mysql.user或业务表，不FLUSH全库，不重启MySQL。

双密码是可选的降风险步骤，必须先核其实际支持和账户状态；不是为了绕过最终用户指定密码而永久保留两套口令。库中root密码与bind初始化secret都须核，修改env/secret本身不会更新已存在数据库用户。

### C. Redis：runtime与entrypoint secret同步，避免盲CONFIG REWRITE

当前公开entrypoint把`/run/dell-redis`设root:root0711，配置文件归redis用户且0600；官方entrypoint再降权运行redis。Redis7.4 CONFIG REWRITE需要同目录创建临时文件并rename，**父目录0711不给redis写入权限，因此不能只因配置文件可写就认为REWRITE会成功**。[Redis7.4.4源码](https://github.com/redis/redis/blob/7.4.4/src/config.c)

最小路线：

1. 以旧值认证一条固定连接，确认原机制与新值形状符合requirepass配置语法；准备原inode secret及runtime conf的私有恢复字节。禁止CONFIG GET requirepass结果落普通日志。
2. 使用旧认证连接执行CONFIG SET requirepass指定值，立即原inode同步bind `redis-password`并fsync，新独立连接AUTH/PING通过；整个窗口有界，失败用仍有效的本次连接或新值恢复runtime与原文件，不盲重启。
3. **不需要为本次调用CONFIG REWRITE改父目录权限。** 下次容器启动时entrypoint会从更新后的secret重新生成conf，这是实际持久来源。若要求当前运行conf也一致，可用container root只替换该文件唯一requirepass行、保持其它字节/owner/mode并读回；别改/data持久文件或生成额外ACL文件。该步骤需精确文件guard，不调用整套entrypoint重启服务。
4. 若必须选择原生REWRITE，先另审其目录临时写权与atomic rename产生的新file身份，结束恢复原root0711策略，并核其它配置未变；它比上面路径改动更大，不作为自动失败重试旁路。
5. 验证无AUTH错误、newsecret PING和原health，用户/ACL/CONFIG除requirepass预期差异保持，INFO keyspace/持久状态只取元数据；不SET测试key、SAVE/BGSAVE、FLUSH或动AOF/RDB。

配置/runtime切换失败时不能只还原文件而留下server新密码，也不能只恢复CONFIG而让下次entrypoint又覆盖成另一个值。Redis没有单条跨runtime+文件事务，必须靠本次journal与分别读回证明，不能承诺中断时绝对无短暂不一致。

## 原inode文件更新共同规则

Docker文件bind挂载固定inode。先在内存构造完整新字节，使用O_NOFOLLOW打开已有regular singlelink文件，fstat核dev/ino/UID/GID/0600，前后身份相同；写入循环处理短写、ftruncate到精确新长度、fsync并读回。同一调用内尽量缩短窗口，不能truncate后再去请求服务/读取新值。

禁止os.replace/重建secret、广泛chmod/chown或替换整个secrets目录；这可能令宿主路径新值与容器仍读旧inode分叉。`.env`即便未bind也应只改唯一管理键并保留其它字节/权限，defs是bind必须原inode。原inode重写不是对并发读者原子的，不能把它宣称等同rename；应由健康重试与快速、可验证恢复吸收短窗，而非mask监督。

私有journal先持久记录回退字节与阶段，然后才写runtime；全部新内容通过校验后再持久修改文件。重复运行先检查runtime与文件值是否已匹配；不凭普通receipt就跳过fresh认证，也不因receipt存在而覆盖旧回退材料。

## 后验与回退边界

每组件结束立即fresh核原4容器ID/PID/StartedAt/restarts/health、监督MainPID、mysql/Nacos readiness、现有schema表数与Nacos配置/权限元数据保持（不读取业务行/配置正文）。特定账号认证metadata只有获准差异；TLS/plugin及Nacos/app身份仍原样。

新凭据验证必须用**新连接**，既有已认证连接能执行命令不证明新密码有效。禁止在普通证据记录用户名/密码组合、hash、Authorization、SQL或消息正文；只报告认证布尔、账户Host/tag/权限差异范围、文件inode/mode保持与容器状态。

原MySQL root、Redis凭据本次按用户要求替换；Rabbit旧管理账号若被保留则仍按其原凭据可用，不能把管理secret改为新账号后误称旧账号密码也已同步。definitions与tools env作用分开，避免下次启动从旧hash恢复不同口令。

失败仅补偿本次已确认变化的精确账号/权限/文件，不能回放整套初装脚本、旧全definitions或用户表，不能删除queues/messages。跨组件没有全局事务，某项成功、后项失败时如实记录partial；优先恢复该项健康，不盲把已成功其它组件再转一遍。需新窗口/重启才能解决时停报，不擅自扩大。

## 本次可交付与未验收

后续实现可交付限定210的按组件在线轮换与回退、新连接认证、持久文件一致性及源/生产/app身份保护；本设计尚未实施，不把未来重启后的持久认证签成已实测。实际不重启是本轮边界，后续正常维护重启再核即可，不为验收新增停机。

现有测试备份范围、正式prod-db timer、配置导入、数据库内容、Java业务与Nacos账号权限都不因本次改变。公开审查仅依据entrypoint/manage/Compose和官方语义；没有读取Mac真实secret或任何旧密码/hash。
