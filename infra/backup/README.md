> 文档状态（2026-11-09）：本页区分历史应用逻辑/fixture工具与新PVE本机自动备份。用户继续基础搭建、先选择本机备份，不迁移数据/合并Nexus/启动Java，Mac外部探针不需要。当日状态见[交付记录](../../completion/20261109/README.md)，旧网段与原通过结果按时点解释，旧初始化器不重跑。

# 应用备份与隔离恢复

本页原应用逻辑工具包含已执行的纯合成fixture验证和新正式初始化环境的本地快照，**这些旧工具不支持CF**、不上传Nexus、不遍历其它私有目录。新子目录[pve-local](pve-local/README.md)是另一层用户授权的PVE原生snapshot备份，包含CF但只留PVE、明确排除220。原Mac临时独立副本与本机快照都不等于持续异地灾备。

## 2026-11-09本机自动备份：首轮成功、计划已启用

[PVE本机备份合同](pve-local/README.md)固定100/190/200/201/210/221/230/240/250/260/270共11项，排除220，CF档只PVE，root700目录/600归档日志状态。native job每日03:30（Asia/Shanghai），最近3份＋每日7点＋每周4点原生组合保留，原21回退档独立保留。

**首轮成功、计划已启用。** 固定11档已全部verified（zstd、tar/vma及SHA验证），原生任务OK、unit退出0；15:56审核后每日03:30计划已启用，合计19,747,582,801字节。证据：[首轮成功](../../completion/20261109/backup-first-success.json)、[计划启用](../../completion/20261109/backup-schedule-enabled.json)。 既有metadata/Lark白名单配套不等于重新发送通知；新增Prom规则实际部署/加载状态以[当日记录](../../completion/20261109/README.md)为准，不提前声称已加载。

这是snapshot/crash-consistent系统恢复点，不是下面的数据库逻辑导出或跨来宾事务一致性保证；本轮未恢复VM，不签独立目的地、RPO/RTO或异机灾备。Nexus221独立、Java不启、Mac外部探针不需要；OW完整规则仅本地，不触/不上传。

## 历史已执行A-D（非本轮重跑）

主AI已审阅PLAN.md并批准仅VM200/201。`run-fixture-validation.py --execute-approved-synthetic-only`已经完成：

- VM200：自建单InnoDB表逻辑导出；仅自建Nacos config_info行过滤导出（不含users/角色/权限/凭据）；在固定MySQL8.4.5的独立空scratch容器恢复并比对synthetic值。
- VM201：仅自建Redis key的DUMP/PTTL；在固定Redis7.4.4临时容器RESTORE并比对；仅自建空durable Rabbit队列topology，导入固定Rabbit3.13.7临时容器验证durable与messages=0，不发布消息。
- 所有临时验证容器network=none、无publish、无源卷，使用独立空目录和新临时秘密；验证结束清理临时容器、scratch和源专属对象，源服务没有停止或重启。
- 仅经过manifest白名单/校验的纯合成归档流入Mac `private/backups/app/<work_id>`，目录700、文件600，不带临时验证秘密。没有实库敏感导出或CF访问。

实际证据：[app-backup-fixture-validation.json](../../evidence/implementation/app-backup-fixture-validation.json)。源容器ID、StartedAt和PID前后完全相同；恢复验证与Mac归档校验通过。

**Nacos过滤行不是完整配置备份；Rabbit topology不是消息备份；fixture成功不证明正式数据全量、RPO/RTO或应用全链路恢复通过。** 只允许用新work-id重复该专属验证，不能把state/manifest改成其他数据库、key或vhost来绕过范围。

## 正式备份工具E：限定本地快照已执行，完整恢复和调度待验

主AI已在无正式业务/DDL或topology变更的初始化窗口执行三项：200 Nacos全元库、201 Redis RDB、201 Rabbit topology。本地备份700/600已创建，未导出、未作全量隔离恢复；正式业务schema数量仍为0。见[本地快照](../../evidence/implementation/prod-local-application-backups.json)。

`application-backup.py`只允许在正式200/201对应hostname、私网IP、数据盘UUID和本地Docker门禁通过后，生成本地700/600备份。它没有跨设备导出功能，不会将备份上传Nexus或其他外部服务。

```bash
# 以下为接口；重跑须新窗口与新批次，不覆盖旧快照：
python3 application-backup.py mysql --database APPROVED_DATABASE \
  --execute-local-backup --ack-sensitive-local-output --confirm-no-ddl
python3 application-backup.py nacos \
  --execute-local-backup --ack-sensitive-local-output --confirm-no-ddl
python3 application-backup.py redis \
  --execute-local-backup --ack-sensitive-local-output --confirm-redis-fork-headroom
python3 application-backup.py rabbit-topology \
  --execute-local-backup --ack-sensitive-local-output --confirm-stable-topology
```

这些参数只表达操作意图，**不替代用户/平台审批**。实库、密码hash、配置或其他敏感信息如被自动审批要求确认，必须停止并报告，不以加密、编码、更换路径或另一种传输方式绕过。

| 对象 | 正式一致性方法 | 还原边界与限制 |
| --- | --- | --- |
| MySQL | 指定非系统DB；确认无DDL窗口、所有base table为InnoDB后single-transaction/quick；包含routine/trigger/event；禁tabelspace/GTID注入 | 生产恢复未执行。只可向隔离新目录恢复，event_scheduler OFF、local_infile OFF、无外网；SQL恢复成功不替代业务不变量验证 |
| Nacos | 外部MySQL `nacos_prod` 同一逻辑快照，包含config/users/roles/permissions | 含敏感hash/配置；与受控秘密库版本配套，JWT/部署秘密文件不混入普通归档；本轮仅验证一条synthetic行恢复 |
| Redis | 测得COW/磁盘余量、无现有RDB/AOF重写后独立RDB full sync | 会触发fork/额外负载，不能承诺零延迟；RDB不含密码/ACL文件；正式恢复应在新隔离实例先按RDB加载验证，AOF转换另验 |
| Rabbit | 确认topology稳定窗口后官方definitions API导出 | 含敏感password hash/parameters，**不含消息**；不停写场景没有完整队列消息一致性保证，需另行quiesce/备机方案，不能直接tar现役Mnesia冒充完整备份 |
| Ops | 主AI负责在线Grafana SQLite backup与network-none恢复；配置/image锁/仪表盘配套 | 主AI已验证在线SQLite备份、network-none Grafana应用恢复和Mac归档（见ops-online-backup-restore.json、ops-private-Mac-backup.json）；Prometheus TSDB、Alertmanager nflog与历史不包括在本轮数据脚本，需受控snapshot或维护窗口；配置与SQLite不等于全部监控历史 |

正式工具提供最低磁盘/估算余量、凭据只文件、敏感stdout抑制和manifest SHA，历史E当时仅运行上述fresh初始化三项。MySQL/Nacos业务不变量、完整真实数据集恢复、Redis大数据fork成本、Rabbit消息恢复及Ops全量历史继续待验。11月9日只补PVE native snapshot调度与metadata/告警配套，不把下述旧应用逻辑工具冒称已自动调度；首轮11档验证与03:30计划启用已完成；新增规则后验见[当日记录](../../completion/20261109/README.md)，恢复时长仍待验。不得据此标记正式应用全量、RPO/RTO或异地灾备已达成。

## 工具与安全

- `fixture-worker.py`：只200/201，受派生名称约束的synthetic对象；仅200可读取其MySQL fixture及一条Nacos fixture行，仅201可读其Redis key/空Rabbit topology。工作目录为数据挂载下独占nonce，既有scratch拒绝覆盖。
- `run-fixture-validation.py`：固定已验证guest目标，通过现有SSH通道发送公开worker；纯合成tar使用二进制SSH流直接写Mac600文件，不经过stdout显示或额外中转目录。
- `application-backup.py`：正式本地备份准备，不自动创建账号、改配置、停业务或导出到Mac。
- `test_safety.py`：离线守卫回归，不调用SSH/Docker/数据服务。

临时验证秘密只在guest独立verify目录600，UID与固定镜像匹配，不放入artifact manifest；源凭据只从现有数据包600文件读取，经进程内部socket/STDIN使用，禁止argv/stdout。归档成员严格白名单，没有CF、源日志、SSH私钥、凭据文件或源数据卷。

## 后续应用逻辑/隔离恢复验收（本轮不执行）

先由任务管理者冻结正式备份数据集、无DDL/topology窗口、恢复对象和容量，再审阅敏感数据导出审批。恢复必须隔离、拒绝非空目标、不启用真实事件/通知/外部连接，只清理本次记录的验证容器/对象。源与目标出现新增写入时，不将回切URL当数据回退。

Mac暂存目录已授权，但Mac关机、磁盘损坏或与T630处于同一地点都仍是风险；本轮不新增购买或替用户选择最终独立目的地，不承诺候选RPO≤5分钟/RTO2～4小时。
