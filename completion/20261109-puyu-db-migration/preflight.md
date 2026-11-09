# 本机puyu数据库迁测试：只读源/目标预检

采集：2026-11-09T14:31:59.117421+00:00。用户已明确要求将本机puyu_*迁到测试210；本次仅盘点，**没有dump、备份、建库、导入、重启、源/目标写或Git操作**。

## 来源实际范围

已确认现役container `mysql`、ID1fee5c…5788、imageIDb2f81a…2764、hostnetwork，数据bind为`/Users/yangzhaohui/work/nacos/mysql/data → /var/lib/mysql`。源SQL版本8.4.5。认证仅在container内使用已有MYSQL_ROOT_PASSWORD_FILE或MYSQL_ROOT_PASSWORD；没有读取compose密码值到输出、猜密码、dump Env或Cmd。

先SHOW DATABASES元数据，再Python `^puyu_`精确过滤，只有：

| 实际schema | BASE TABLE | 精确COUNT行总数 | 表+索引估算bytes |
| --- | ---: | ---: | ---: |
| `puyu_auth_local` | 4 | 178 | 1654784 |
| `puyu_erp_local` | 47 | 1113 | 4276224 |

共51表、1291行，估算约5.66MiB。两库schema charset均utf8mb4、collation均utf8mb4_0900_ai_ci。全部表InnoDB，视图/routines/triggers/events均0；每表均有PRIMARY且至少1个unique索引。JSON逐表保存表名/engine/COUNT/估算bytes和PK/unique及列结构指纹，**不含业务行值、列默认业务值、routinebody或密码hash**。

## 写入与一致性风险

采样active InnoDB trx0、当前DDL0、pending metadata lock0、选定schema当前write statements0；其它非Sleep session1。没有输出SQL text/事务值。源event_scheduler为ON，但选定库events0。以上都是观察，不是未来无写/DDL承诺，COUNT逐表执行也不是跨表一致性快照。

root在实际导出前仍须定义一致性窗口/写入协调，保证DDL与业务写处理明确；不能凭本次0计数跳过。如果迁移期间源仍写，需明确点时导入和后续增量/停写策略，不能把行数变化当工具错误清数据。

## 测试目标VM210

- data-test /192.168.19.20，原/srv/dell-data ext4 UUID `dd1773f9-aa48-4401-a9c8-caf0f66845f3`匹配。
- SQL版本8.4.5，实际AMD64镜像ID与既有测试MySQL保持，源/目标同版本但架构不同不会让逻辑数据自动丢失或要求物理拷贝。
- **当前无任何puyu_*库，无同名冲突**。已有finger_auth_test、finger_coms_test、finger_system_test、nacos_test等非puyu库保留，不能drop/覆盖。
- MemAvailable2,469,367,808B（约2.30GiB），datafree39,869,243,392B（约37.1GiB）；原mysql/Nacos/Redis/Rabbit四container runninghealthy/restart0/OOMfalse。容量是当时采样，不是导入吞吐或并发SLO保证。
- 只用了installed acceptance.mysql({}, SELECT...)直接subprocess查询，无m.cfg/preflight/run/auth/fixture调用；未写deploymentlog、未读.env值或业务行。

## 下一步由root明确窗口

当前元数据条件通过，不等于已迁移：实际操作前fresh再核源写/DDL、目标collision及资源，明确目标schema命名映射（不要擅自把_local改_test或覆盖其它库）。未来逻辑导出/导入只限这2库，保留charset/collation、完整DDL、PKunique及行语义，不能搬MySQL全局账号/密码或整container物理data目录。导入后逐表结构、COUNT及规范化行指纹在受控内存/私有文件比较，不能输出业务内容。

不触正式200/201、不再Nacosconfig发布或权限变更，不启动Java/移动端应用；app连接配置改动属于后续明确范围。若出现同名目标库或源合法变化，先停手报告，不用DROP/覆盖消冲突。机器证据：[preflight.json](preflight.json)。
