> 文档状态（2026-11-08）：本页为阶段实施/技术记录，旧网段、角色数和通过结果按原时点解释。基础已恢复；本轮仅补齐与清理，用户暂不迁移/合并，Mac外部探针不需要。当前配置见[访问清单](../../12-service-access-and-operations.md)，范围与恢复证据见[最新交接](../../11-live-handoff.md)；旧初始化器不得重跑。

# Core执行最小入口与顺序

> 最新用户范围覆盖下文旧Java上线计划：本期不部署任何Java业务程序，只保留一个由root另行指定的验收模板。240五服务已stop/disable，监控active仅基础3unit/HTTP空，Publisher始终baseline=false。新release/Nacos candidate只保留为私有未部署备份，禁止publish/activate/enable/E2E。旧段落保留作准备历史，不是执行授权。SQL新19.45 Host暂保留、未做新连接CURRENT_USER验收、不撤旧。

所有命令通过既有严格hostkey和root提供的`network19/evidence/migrated-access.json`新target；不得继续用旧IP info，不ssh-keyscan放宽信任。源/template/永久guest SSH key策略由root统一维护，发现key变化先交QGA身份链，不自动改known_hosts。

## 已完成的明确窗口

- 210仅新增3个192.168.19.45 Host，同plugin/auth、18逐表DML；3旧Host保留、Nacos%不变。初次opaque TAB parser失败已补偿回收，纠正一次后成功，原失败留档。
- 230/231/232仅监控六文件在root OScommit后apply/sample，分别19.40/41/42:9100，正式业务unit没有启动。230随后root计划内关机/reboot/hostkey可信更新不按故障处置。
- 200/201/210/220/240/270私有candidate与backup已stage于各guest `/root/dell-network19/staged/services-core-v1`；Data/Ops env位于 `/root/dell-network19/service-env/<vmid>/{old.env,new.env,stage.json}`，全root600/私有目录。没有commit/activate。
- 240私有primary/compatible rollback pair为20261106T085840/20261106T085841，位于 `/root/dell-network19/private-stage`，同JAR/秘密/namespace/vhost、6个fresh dataId配置已在guest内准备，未publish/安装/启动。

## root统一事务阶段

| 阶段 | IP/guard原则 | 允许操作 |
| --- | --- | --- |
| S0 frozen | 已审old地址/active SHA，不改活动配置 | 只读、stage-only、root600备份/候选；Publisher frozen待切 |
| S1 quiesce | 当前OS可仍old；只停止已授权role/依赖 | 先停关联客户端，再role supervisor；必须观察该role所有容器停止，不删volume |
| S2 root OS | root原MAC/NIC/桥/IP/GW/DNS事务 | child不改OS/PVE；new严格SSH/源key链由root确认 |
| S3 service commit | exact newIP/24已UP；Data/Ops supervisor必须inactive | private env白名单原子提交，挂载UUID/路径不变；不运行generic prepare/bootstrap |
| S4 start/health | 配置仅指new网络；旧alias存在不作为可达性证明 | 启动该role原supervisor、完整容器healthy、Nacos readiness200；独立迁六监控文件 |
| S5 dependencies/E2E | fresh dataIds、Root600 LoadCredential、new issuer/COMS | 240新release上线后功能验证，fresh root readiness，不把旧proof只改IP |
| S6 publisher/ops/cleanup | 新网络compatible rollback存在 | 启publisher新policy baseline；Ops12targets最后更新；SQL旧Host最后仅撤3条 |

所有root600收据均是root当前窗口的声明，不替代用户/协调员授权；每role action精确。Data manage本身从env SERVICE_IP读取并验证实际地址，因此不需放宽成“任意10/19网段”；阶段转换依赖真实OScommit，不能把双alias简单当零停机。

**旧桥搬至vmbr19后，保留旧10.63地址不等于旧L2邻居仍可达。** 不假设old/new alias保证跨旧桥通路，root以维护窗和依赖quiesce协调。统一19/24后OW路由器看不到同L2流量，角色隔离须继续由root的PVE/guest ACL保证。

## 第一组：200/201（root指定先201停、再200停）

```text
python3 dell/network19/services-core/role-window.py --vmid 201 --action quiesce
python3 dell/network19/services-core/role-window.py --vmid 200 --action quiesce
```

helper先核既有全量应用backup manifest/SHA，仅原地保留不导出，然后只stop对应supervisor。unit精确为 `dell-data-prod-infra.service`（nacos/redis/rabbitmq）与 `dell-data-prod-db.service`（mysql）。不stop Docker，不删除/格式化盘或volume。root必须收到两role stopped后才切200 OS。

root OScommit200并提供new target后：

```text
python3 dell/network19/services-core/role-window.py --vmid 200 --action commit-start
python3 dell/network19/services-core/monitoring-role-window.py --vmid 200 --apply-authorized-role
```

200只改env SERVICE_IP/MYSQL_HOST到19.10，role仍quiesced才允许提交，随后原supervisor恢复并等mysql healthy。root再切201 OS、新target后执行相同两命令vmid201；201 env SERVICE_IP19.11、MYSQL_HOST19.10，Nacos密码/namespace/vhost与`nacos_prod@%`保留，3容器healthy、Nacos readiness200。没有主动调用会建账户/权限的bootstrap-nacos。

每role `role-window.py`由当前主AI窗口授权后才执行，它只在该guest私有目录写本次action收据并调用已审executor，公开回执不含秘密。失败在原授权role窗口可修本工具guard但不能扩scope，活动服务失败保留具体非秘密类别，root协调回退。

## 210与240

先240 quiesce五服务（由root单独给窗口，保持正式230/231/232不启动），再迁210相同Data流程；210 env仅SERVICE_IP19.20，MYSQL_HOST=mysql和172.18 Docker网络不改。

240旧immutable release20261106T121030以及历史Nacos ID绝不就地改。stage-java240.py默认inspect无写；已stage的新pair使用new19.45 server/discovery、new19.20 datasource/Nacos/Redis/MQ、issuer `http://192.168.19.45:9999`、COMS `http://192.168.19.45:9999/finger-bff-system/dell-test-files`。上传路径/Snowflake/账号/密码/namespace/group/vhost不变。client callbacks仅既有owned issuer前缀更新，禁用第三方URL端口9仍保持禁用。

Root新网络Ready后才发布6个新dataId（network19-v1），不得覆盖源/历史ID；然后用prepared canonical fixed/protocol阶段验证→安装新release→fresh本机OIDC issuer/JWKS、captcha/授权/角色/文件链E2E。Root持久YAML600和LoadCredential模板不变。切换后旧issuer token可能无效，需要重新登录，不改历史token/文件URL行。已存旧文件URL可由root明确的临时旧入口兼容处理，不能盲SQL替换历史。

## Publisher220/240

候选源严格由实际installed SHA且等于deployed快照生成；工作目录pending cgroup-quiescence候选没有使用。`prepared-public-contract.json`给出5文件准确路径/SHA与edit表，prepared/publisher为可审代码。变更仅固定IP/owned issuer-COMS URI与fresh ID whitelist，不引入新停止策略。

在独占publisher frozen窗口，先240持修改lock并把baseline=false，再commit固定执行器/protocol/dispatch/RPC新IP与policy SHA、authorized_keys精确from19.30（原key/restrict/forcecommand不变）；220只commit client/profile target19.45/source19.30。已有240 hostkey alias及私钥保持，若root因CI可信换key需单独身份链更新known_hosts。

`commit-publisher.py`默认inspect；commit-fenced必须new IP已赋、root600冻结收据，旧/新source SHA均精确。它不启动应用/写DB/Nacos/修改old release。baseline最后才启用：fresh network19 readiness与功能proof齐全，当前new release+另一个new-network rollback release皆通过同protocol/namespace/root600，五health真实UP。不能拿旧proof只改targetIP。

## SQL Host与回退

只迁`finger_auth_test/system/coms_test`的旧Host10.63.20.20→新19.45，Auth3/System5/COMS10逐表DML完整、同认证plugin/hash仅guestRAM。当前add-new已成功，不可再执行未经授权retire-old。Retire要root600 `allowed_phase=retire-old`且新19.45实际CURRENT_USER/连接来源、18grant、无旧连接、新网络rollback基线均真；只撤3旧Host，不碰两个Nacos@%。

MySQL账户DDL是autocommit，不伪称可整体事务回滚；helper幂等比对，失败仅补偿自己本轮新增行，ledger不含auth正文。`mysql-hosts.py --phase restore-old`仅用于root批准的整网回退先恢复旧Host，不能独立把旧app恢复到新-only数据源。

回退分层：**新网络内**用另一个同new issuer/dataId/数据源release；**整网回退**root先恢复旧OS/路由/必要3个旧Host，再Data env旧backup/旧Nacos引用/旧Java release/旧Publisher code+policy+SSHfrom成套恢复。单独回指10.63 release会网络不兼容，禁止自动这么做。任何rollback均不回滚数据库内容/不删媒体/上传文件。

## Ops270最后切

Ops envSERVICE_IP19.70、完整12node target host更新，其它实际HTTP targets为Docker服务名不变。guest基线的本机HTTP URL随owner OScommit配对更新；candidate不激活。PVE metrics脚本通过QGA VMID270写 `/var/lib/prometheus/node-exporter-textfile/dell-pve.prom`，已知source无IP字面量，无需盲改PVE；root核实际hash和下次时间新鲜度。

172.18.0.0/16/gateway .1/四固定container地址、AM→172.18.0.1:19093/native入站仅.3、stable token/webhook/LoadCredential、active renderer全部保留。不重装通用Lark、不重置marker、无acceptance firing/resolved、无外发验证。只读核mode/listener/source/SHA/active与已存在回执；本次不以旧receipt宣称新发送发生。6h maintenance silence由root控制，切换完成后确认真实服务与targets稳定再解除。

最后root同步active plan/已验证access/源commonprofile当前map；准备副本在prepared/source-commonprofile和source-sync-contract.json。旧inventory/历史evidence不可覆盖。190新GW/104 enrollment待另定，当前12targets不自动扩。所有正式业务app持续不启动。
