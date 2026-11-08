> 文档状态（2026-11-08）：本页为阶段实施/技术记录，旧网段、角色数和通过结果按原时点解释。基础已恢复；本轮仅补齐与清理，用户暂不迁移/合并，Mac外部探针不需要。当前配置见[访问清单](../../../12-service-access-and-operations.md)，范围与恢复证据见[最新交接](../../../11-live-handoff.md)；旧初始化器不得重跑。

# 既有完整快照恢复验收

2026-11-06主 AI已审阅并批准 [PLAN.md](PLAN.md)。执行范围只有VM200/201各自已经生成的本地快照，Mac仅返回脱敏结果；没有重新查询现役业务数据库/API、停止现役容器、导出SQL/RDB/definitions或读取CF。

新增脚本独立于旧E/fixture工具：

- `run.py`：严格受信SSH到固定来宾，只下发公开脚本，收集元数据。
- `worker.py`：固定快照路径/镜像/资源；network none、无发布端口、非root、只挂本轮scratch；恢复、临时重启、私有内容比对和自己对象清理。
- `sql_snapshot.py`：解析本轮实际mysqldump格式，SQL INSERT值和恢复后每列二进制表示规范化比对；不支持语法明确失败，不能降级表数量。
- `test_sql_snapshot.py` / `test_rabbit_normalization.py`：转义、注释、NULL/空串、行顺序、拒绝表达式，以及Rabbit等价字段/冲突值/非空limits/未知字段反例，共10项通过。

运行前置：

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s dell/infra/backup/full-snapshot-restore -p 'test_*.py'
python3 dell/infra/backup/full-snapshot-restore/run.py nacos
python3 dell/infra/backup/full-snapshot-restore/run.py redis
python3 dell/infra/backup/full-snapshot-restore/run.py rabbit-topology
```

主AI批准后每组件串行运行 `run.py <component> --execute-approved-local-restore`。该参数只表达执行意图，不能替代授权。检查前置或未知SQL/runtime参数失败即停。结果保存到 `evidence/implementation/full-snapshot-<component>-restore.json`；覆盖前保留带时间的previous文件，首轮失败不会被抹掉。

## 已验证的内容与边界

Nacos完整元库已通过：12表共10行，users2、roles2、permissions1、tenant_info1、his_config_info4；逐列内容摘要全部匹配，包括用户密码hash和权限，CHECK TABLE通过，event_scheduler保持OFF，临时实例重启后再比对一致。当前快照的活跃config_info为0，不能声称包含非空正式业务配置。没有启动Nacos JVM，HTTP登录/运行配置和额外服务密钥不属于此项。

Redis完整RDB已通过checksum和临时实例启动、SAVE、重启加载。快照本身0 keys，因此仅证明这个空RDB可恢复；非空key/value/TTL恢复不能用本次结果冒充。ACL/password/config不在RDB内。首轮失败为redis-cli INFO不遵循普通JSON回复的兼容问题；改INFO专用raw采集后通过，失败元数据保留。

Rabbit快照含users2、vhosts1、permissions2，queues/exchanges/bindings均0，不包含任何消息。HTTP定义与CLI导出对vhost字段存在表示差异：HTTP重复description/tags于顶层，CLI增加空limits；严格规范化只折叠与metadata等价的重复值及空{} / [] limits。name/metadata完整保留，非空限制/冲突值/未知字段不能被忽略。最初两轮因vhost结构差异停止，第三轮发现CLI过滤内部参数而停止，证据均保留。最终完整导入和重启验证已通过；对内部参数不靠CLI定义导出判断，而是用只读list_global_parameters在进程内比较原值摘要，internal_cluster_id一致，其他参数继续严格全比对。

全部成功结果均要求实际inspect隔离通过、原快照SHA不变、现役容器ID/PID/StartedAt/health不变、临时容器删除。恢复数据及本轮随机密码只在来宾scratch，清理后仅保留600的脱敏result.json。原三个快照原地保留。

这些是本机恢复验证，不是独立设备灾备、异地副本或经批准的RPO/RTO。测得elapsed_seconds仅是这次演练耗时。家庭NAS不作为正式备份目标；CF完全排除。

## 最终结果

三个恢复项均passed，详见本目录 `runtime-status.json`。Nacos耗时35.804秒，Redis3.496秒，Rabbit72.101秒；这些只是这次本机演练耗时，不是获批RTO。每项均已核对原快照SHA和现役容器身份/健康不变，临时容器、恢复数据和本轮随机密码已清理，只有脱敏result留在来宾本机。

Rabbit官方3.13.7实现的 `list_global_runtime_parameters` 过滤internal前缀，`add_global_parameter`仍调用set_global；CLI runtime列表的value再经过一层JSON编码。官方来源URL/hash记录在 `official-references.json`。本轮没有主动set内部身份，也没有忽略其实际值。
