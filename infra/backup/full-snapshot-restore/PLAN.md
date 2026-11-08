> 文档状态（2026-11-08）：本页为阶段实施/技术记录，旧网段、角色数和通过结果按原时点解释。基础已恢复；本轮仅补齐与清理，用户暂不迁移/合并，Mac外部探针不需要。当前配置见[访问清单](../../../12-service-access-and-operations.md)，范围与恢复证据见[最新交接](../../../11-live-handoff.md)；旧初始化器不得重跑。

# 已有完整快照的本机隔离恢复验收方案（待主 AI 审阅）

本阶段只恢复主 AI 在 fresh200/201 已生成的三个快照，不再次连接现役数据库、Nacos、Redis 或 Rabbit API，不重新导出，不修改原备份，不读取 CF，不导出到 Mac。原 E 脚本及既有 fixture 验收脚本保持。新增代码只在本目录；执行脚本下发对应来宾，Mac 只接收脱敏元数据。

## 固定输入与执行面

来源由 `evidence/implementation/prod-local-application-backups.json` 唯一确定，禁止任意路径参数：

| 来宾 | 组件 | 已有本机输入 |
| --- | --- | --- |
| 200 / data-prod-db / 10.63.10.10 | Nacos 完整外置 MySQL 元库 | `/srv/dell-data/_app_backups/f106e23107d34c0bba39a4c006dd1891/mysql.sql.gz` 和同目录 manifest |
| 201 / data-prod-infra / 10.63.10.11 | Redis 完整 RDB | `/srv/dell-data/_app_backups/6c706257613d40228cf2611d94276e26/redis.rdb` 和同目录 manifest |
| 201 / data-prod-infra / 10.63.10.11 | Rabbit 定义/拓扑（无消息） | `/srv/dell-data/_app_backups/b260debe1b5a4e0d9ea6657226a927cb/rabbit-definitions.json` 和同目录 manifest |

执行前再次核对 root、来宾 hostname/IP、独立数据挂载和固定角色；拒绝 `/etc/pve`、符号链接、group/world 可写输入、manifest 覆盖不符、SHA256 不符。只加载 images.lock.json 和角色标识，不加载现役服务密码、不调用 manage.preflight（避免间接探测现役应用）。镜像仅 `--pull=never` 使用已有本地固定 amd64 digest，缺镜像即停止。检查可用磁盘、MemAvailable 和现役容器健康元数据；验收按组件串行，不能与其他资源密集任务并行。

镜像固定为已部署版本：MySQL8.4.5 (`bd045a5e…d55840`)、Redis7.4.4 (`bf8a5a41…0440a`)、Rabbit3.13.7-management (`9cfb7e92…f1c920`)；完整 digest 以同来宾 images.lock.json 为准且在脚本内固定匹配，不能只信可变 tag。

## 容器与秘密边界

每轮新 nonce，使用 `/srv/dell-data/_dell_full_snapshot_restore/<nonce>/`，父目录和轮次700，文件600。每个恢复数据目录必须新建且为空；只将原快照只读打开并复制到本轮工作区，不挂现役数据卷或服务 secret，不挂 Docker socket。容器只挂本轮 scratch 和本轮随机密码/config 文件。

统一 `--network=none --pull=never --platform=linux/amd64`、不 publish、不 host network、非 root 服务 UID/GID、cap-drop ALL、no-new-privileges、root filesystem 只读和有限 tmpfs。MySQL1CPU/768MiB、Redis1CPU/256MiB、Rabbit1CPU/512MiB（Erlang +S2:2）、pids256，按阶段串行；资源不足则暂停给主 AI，不扩大限额碰生产资源。Docker inspect 必须实际确认 network none、Ports 空、只允许 scratch 挂载、无危险 cap/privileged，不能只依据命令字符串。

随机恢复 root/临时 Redis 密码只写600文件（容器 UID 可读）或 stdin；不复用现役 root密码，不把秘密写 env 参数/argv/stdout。MySQL socket `/var/run/mysqld` 为 tmpfs，Redis/Rabbit 仅容器内部 loopback/exec。日志仅保留本机700目录内且不回传真实值；普通 evidence 只包含数量、哈希匹配布尔、退出类别、耗时、清理结果和限制。

## Nacos 完整元库验证（200）

1. 校验原压缩文件、manifest SHA、gzip 完整性；只私有检查 dump 仅一个 `nacos_prod` schema，拒绝系统库/额外 schema，若发现预期之外的 UDF/存储过程/触发器/事件定义则停止审阅。不使用 dump 中凭据连接任何服务。
2. 在空 MySQL scratch 初始化全新随机恢复 root，启动加 `--skip-networking --skip-log-bin --event-scheduler=OFF --local-infile=0 --secure-file-priv=NULL --performance-schema=OFF --innodb-buffer-pool-size=128M`。确认 event_scheduler OFF、network none，socket readiness。
3. 将已有 SQL 经 stdin 导入此容器，保留原 schema 名；这只在独立空实例内执行，不对现役卷运行 SQL。不启动 Nacos JVM/注册客户端，不运行任何导入后的计划任务。
4. 验证所有 dump CREATE TABLE 都恢复、CHECK TABLE 健康；对每表统计行数，完整覆盖 config/history/tenant/users/roles/permissions（以实际2.4.3 dump 表集合为准）。对 dump 的 INSERT 行做本机私有解析，与恢复后规范化行逐表比较行数/摘要，尤其用户 password hash、enabled、角色与权限；不输出 username/password hash/config content。若 SQL 文本超出受支持解析语法，停止并报告，不能降级为只检查文件存在。
5. 同一恢复实例受控重启后，重新检查表计数/摘要保持和服务就绪。结果仅说明完整 Nacos 元库快照可恢复，未证明 Nacos HTTP 登录/运行配置/密钥独立归档（这些另有边界），也不把源用户 hash 和新测试账号迁入其他服务。

## Redis RDB 验证（201）

1. 对原 RDB SHA 对照 manifest；在同固定镜像 `redis-check-rdb` 检验格式与 checksum，输出只记成功与 key/expiry 计数。
2. 将 RDB 复制到空 scratch 的 dump.rdb，配置全新临时密码、AOF off/save off、无 replicaof、模块、外部 ACL 或源路径，startup 从该 RDB 加载。
3. 实测 loading=0、DB/key/expired 计数符合校验器与恢复时点，逐 DB 计算 key/type/DUMP 的私有聚合摘要，不将 key名或value回传；TTL 只按经过时间和到期情况比较。空库明确记录 keys=0，不冒充非空数据验收。
4. 在此 scratch 实例内再次 SAVE 后受控重启，验证有效 key 摘要和TTL语义保持。只写 scratch，不触发源 BGSAVE。RDB不包含源 ACL/password/config，这部分不宣称已恢复。

## Rabbit 完整拓扑验证（201）

1. 校验 JSON 文件与 manifest SHA，读取 users/hash/vhosts/permissions/topic_permissions/queues/exchanges/bindings/policies/parameters/global_parameters 的数量与私有规范摘要，任何值不输出。definitions 不含消息，不创建/发布真实消息。
2. 风险检查：原文件保留不改；若存在 shovel、federation 或其他外连/事件驱动 runtime parameters，先报告主 AI，不直接启这些插件。network none 是第一道边界；隔离 Rabbit 使用最小插件，仅管理/定义导入必需，不启 shovel/federation/MQTT/STOMP/stream 等外发功能。
3. 空 scratch 固定 hostname localhost/nodename rabbit@localhost，启动后用 docker exec 的 rabbitmqctl 从 stdin 写本轮600临时 definitions 并 import_definitions。无需现役 API 或原密码。内部仅有默认 guest 账户是恢复启动基线，验收时将其与导入集合单独区分；不拿默认账号暴露端口。
4. 导出 scratch definitions 到本机本轮600文件，按已知服务生成项/默认用户规范化后，对全部用户 password_hash/hash_algorithm/tags、权限、vhost及拓扑逐项比较；对 queues 检查 messages=0，记录旧快照本就无消息恢复能力。若未知字段不等，停止给出字段名/对象数，不打印敏感值。
5. 受控重启 scratch 后再次比对，确认 users/permissions/topology 可持久化。关闭插件参数的检查不能被写成原参数的业务功能已验收。

## 清理、失败和验收证据

容器名称/label/ID 与 nonce 固定绑定；任何失败只删除自己创建的容器，不运行系统 prune、compose down 或按模糊前缀批量删除。先 inspect 验证 ID/label/挂载归属，再 remove；仅删除本轮 scratch，原三个快照继续原地保留。原文件前后 SHA 必须相同；现役容器健康元数据前后相同（不查询现役业务数据）。清理失败保留私有 state 并通知主 AI，不隐瞒残留。

验收状态初始 pending；批准后按 Nacos→Redis→Rabbit 单项执行并汇报。结果记录开始/结束UTC时间、对象/镜像digest、真实容器隔离、计数/hash比较布尔、重启持久化、原文件未改、临时对象清理、耗时与限制。测得耗时只是本次本机恢复时长；无用户认可RPO/RTO、独立设备或异地故障演练，不能标灾备或SLO验收通过。全部快照内容只留来宾；CF完全排除。
