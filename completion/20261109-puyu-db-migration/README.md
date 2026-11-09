# 本机Puyu数据库迁至测试VM210：交付与验收

更新：2026-11-09。**两库导出点快照已按原名复制到192.168.19.20，native验证和独立只读postcheck通过。** 本机源库、原应用连接和现有测试库均保留；这不是业务上线或连接切换。

| 数据库 | 快照表数 | 快照行数 | 目标 |
| --- | ---: | ---: | --- |
| puyu_auth_local | 4 | 178 | VM210同名库 |
| puyu_erp_local | 47 | 1113 | VM210同名库 |

共51表/1291快照行、4空表，均InnoDB/有主键；schema charset/collation为utf8mb4/utf8mb4_0900_ai_ci，无views/routines/triggers/events。原名_local并未擅改为_test。

## 实际完成

1. [源/目标预检](preflight.md)：源SHOW DATABASES精确筛出两库，目标无同名碰撞；固定sourcecontainer/image、MySQL8.4.5与target一致。
2. [私有导出](source-export.json)：一次--single-transaction导出两库，固定order-by-primary/complete-insert/hex-blob/utf8mb4/tz-utc等flags；DDL独立锁约0.42秒，正常UNLOCK回执和独立connection/backupLock均0。compressed1914871B、expanded4771200B，gzipCRC/privateSHA通过。
3. [真实快照指纹](source-fingerprint.json)：从实际导出SQL取得4/47表及178/1113行；不是把迁移前COUNT当导出点。source/target完整语句与opaque INSERT multiset语义指纹仅private处理。
4. [prepare](prepared.json)与[apply](applied.json)：只创建目标新两库，使用临时受限importer；原账号和服务配置没有由迁移流程重置。
5. [native verify](verified.json)：相同flags目标redump与源完整DDL/行multiset指纹相等，51表CHECK TABLE通过；actual code合同见[target-worker.py](../../infra/data/puyu-db-migration/target-worker.py)。
6. [独立postcheck](postcheck.md)：51表逐个SQL COUNT与private manifest.fp行数相同；全表名、PK/约束DDL语义、charset/collation通过，原finger表3/10/6+nacos12与36配置保持，四容器身份健康不变，临时账号/cnf目录清理。

验收清单：[acceptance.json](acceptance.json)。本任务8个required用例全部passed；这只覆盖本次两库快照复制，不把其它基础服务或未来任务算入。

## 一致性、密码与数据边界

- 源DML允许继续，没有停应用或切连接；数据代表一次singletransaction exportpoint，不承诺目标持续与源同步。后续源COUNT变化不是本快照损坏。
- 只锁DDL并已释放，没有DROP/UPDATE源业务或整体MySQL物理目录迁移；目标同名冲突时拒绝，不覆盖旧库。
- 本次迁移使用已有认证，不修改密码、Host、TLS、plugin或应用配置。用户随后指定测试凭据是独立任务，当前文档不把尚未执行的凭据worker算完成。
- [原认证诊断](mysql-auth-diagnostic.json)和[NoTLS补充](mysql-noTLS-auth-probe.json)显示原私有密码可认证；NoTLS需服务公钥获取/缓存条件，不能把2061误当密码被迁移改掉。此任务未为连接失败重置密码或改TLS。
- 原preflight缺PID/StartedAt基线，因此只签ID/image/restart0/健康与当前metadata；未采源密码/配置beforehash，不能独立声称hash字节不变。限制见postcheck，不降低或伪造检查。

## 私有制品与再次执行

实际run为`e28bf9aa3e8f44328eab71190a5a93a8`。Mac私有路径`private/puyu-db-migration/20261109/<run>/source.sql.gz`、manifest及目标sourcefingerprint材料，目录700/文件600；target自有run保留在root私有目录。普通证据只给计数/布尔/代码SHA，不含SQL正文、业务行、真实数据hash或凭据。私有内容不进Git。

迁移代码入口：[source-export.py](../../infra/data/puyu-db-migration/source-export.py)、[fingerprint.py](../../infra/data/puyu-db-migration/fingerprint.py)、[target-worker.py](../../infra/data/puyu-db-migration/target-worker.py)。**不要把本README当再次执行指令**：现有目标两库已存在，prepare/apply非覆盖工具，不能DROP它们或重复导入来凑幂等。后续增量、覆盖、清理或应用切换需另有明确范围和fresh基线。

## 未签范围

没有启动Java或Puyu应用、没有改前端/Gateway/BFF/Core/API/DTO/源码或运行连接配置，没有Nacos新发布/正式200201写。没有做生产切换、连续同步、并发SLO、独立设备灾备或获批RPO/RTO，也没有实演自动回滚/删除目标库。此前合同/影响分析见[task-contract.yml](task-contract.yml)、[cross-project-impact.md](cross-project-impact.md)；其初始步骤状态属于执行前合同，最终结果以本README、acceptance及native/独立证据为准。
