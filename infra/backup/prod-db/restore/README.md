# 正式Nacos元库单次隔离恢复演练

本目录执行用户明确批准的单次恢复演练，不是自动恢复任务。当前执行结果以[当日演练证据](../../../../completion/20261109-prod-db-restore/README.md)为准；备份机制仍仅正式数据库/Nacos配置。

## 数据流与隔离

PVE从现有prod-db-backups中选取last-success对应档，重新核root700/600、regular/single-link、receipt/manifest/实际SHA及完整gzip CRC。原档只读，前后再次核SHA。SQL只通过既有QGA文件接口分块送入VM210独立nonce目录，不经Mac、Git或外部HTTP，不复制源运行密码或SSH私钥。

VM210复用与生产完全相同的缓存MySQL ImageID（不pull），临时实例1CPU/1GiB、独立新data目录、新随机root/importer密码，非root、只读镜像层、capdropall、networknone且无发布端口。禁用事件调度（DISABLED）、MySQLX、网络、local-infile、server file import/export及binlog。每次SQL/重启/删除前均核精确容器ID、owner/run标签、image、资源配置与只属于本run的host bind路径；现役四个Compose服务不进入临时实例集合。

导入账号只获nacos_prod.*权限，无global、FILE或GRANT OPTION，mysql客户端binary-mode，原SQL通过stdin导入，不挂到容器或initdb目录；不回退root导入，不预建数据库以保留dump定义的schema默认属性。source业务数据、配置值、密码及内容摘要均不出现在公开报告。

## 验证与清理

仅复用旧实现的纯SQL INSERT解析模块，不执行旧含10.63地址的恢复worker。原SQL的12表定义、列顺序、逐列值（含NULL/空值/二进制）生成私有期望；临时实例核完整DDL语义、所有行的顺序无关内容摘要和CHECK TABLE。重启仅本次临时实例，再次完成同样核对。

DDL比较保留类型、索引、约束、排序规则和COMMENT。MySQL官方[问题110825](https://bugs.mysql.com/bug.php?id=110825)描述SHOW CREATE TABLE输出重放后会把CHARACTER SET额外显式化；[8.4字符集规则](https://dev.mysql.com/doc/refman/8.4/en/charset-column.html)明确COLLATE本身确定所属字符集。若遇此展示差异，只有临时实例INFORMATION_SCHEMA.COLLATIONS映射证明等价的冗余CHARACTER SET才可做引号感知的语义规范化，不能忽略真实字符集/排序规则、列类型或注释变化；原生结果须证明比较通过。

成功或失败均进入精确清理：核marker/nonce/容器归属及其他容器无本run挂载引用后，只删除自己的临时容器、恢复数据、密码和SQL副本。未知文件/不匹配身份会拒绝删除并报告失败。保留的guest reports与PVE结果都是root600脱敏元数据。PVE备份timer及原归档内容必须前后不变，现役源服务身份与健康须保持。

## 执行边界

- `host-drill.py`及`qga-restore.pl`只在PVE root运行；`target-worker.py`只允许VM210。由主AI核对当次授权、数据源、镜像和余量后实施，不是通用恢复入口。
- 不恢复现役库，不执行迁移、Nacos JVM启动/登录或业务程序，不新增恢复cron/timer。
- 当前快照活跃业务配置为空，仅有12表和既有Nacos元数据；耗时只属于这个小档与缓存镜像，不是未来业务RPO/RTO或独立灾备承诺。
- 失败尝试与修正记录保留；不能将导入成功或临时container已删除单独写为完整恢复通过。
