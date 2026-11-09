# 正式数据库与Nacos配置自动备份

2026-11-09。用户最新范围：**仅正式MySQL数据库与Nacos配置**；其他来宾、整机、测试、Redis/MQ、NAS媒体、Penpot、Nexus、CF和发布机数据不纳入本期自动备份。当前正式VM200唯一非系统库为`nacos_prod`，12张InnoDB基础表，正式业务schema尚未创建。Nacos运行于VM201，配置实际存于VM200外部MySQL元库。

实际首轮、定时器和监控结果见[本次交付](../../../completion/20261109-prod-db-scope/README.md)。首轮已成功，原整机计划已关闭，旧归档保留。这里的脚本是单次实施/维护源码，不是无条件重跑入口。

## 目录与调度

- PVE根目录：`/mnt/pve/store/dell-artifacts/prod-db-backups/<32hex run-id>/`。位于原store，UUID必须匹配，禁止缺盘落到根盘。
- 每轮只包含`mysql.sql.gz`、私有`manifest.json`与`receipt.json`，root700目录/600文件。SQL、配置值和归档SHA不导出Mac或Git。PVE原生存储UI中的VM恢复档与本目录SQL不是一种格式，不能用qmrestore恢复SQL。
- `dell-prod-db-backup.timer`每日03:30 Asia/Shanghai，Persistent=false；`dell-prod-db-backup.service`最多40分钟，原`dell-local-nightly`整机job保持disabled。
- 最近3份、每天7个点、每周4个点按上海日期取最新成功的并集；每次新档校验、fsync并提交后才清超额成功档，永保本轮。只处理本目录精确已知且SHA有效的成功run；不动partial/未知文件或旧wholeVM/cleanup归档。多个日历周期的保留效果仍须长期观察。
- PVE至少100GiB可用并预留2GiB传输余量，guest至少1GiB＋64MiB临时空间余量；本期小库上限1GiB压缩、PVE校验展开最多8GiB/300秒。超限任务失败告警，不能截断后标成功；未来大库应改专用备份通道/重新核容量窗口。

## 一致性与传输

VM200固定helper校验主机/IP、挂载UUID、容器名/Compose身份和数据bind，完全不读取.env或重跑部署器。凭据只在既有容器内从固定secret文件进入临时MYSQL_PWD，不在参数/日志/普通证据中显示。独立mysql连接持有LOCK INSTANCE FOR BACKUP，另一连接以single-transaction导出指定库；不停止MySQL/Nacos，不改变数据内容。锁针对持久表文件DDL，并非泛化的所有元数据DDL保障，所以本期只接受InnoDB BASE TABLE且零视图/存储程序/事件/触发器，并检查前后结构元数据相同；出现不支持对象或新未列库立即失败，管理员需先更新白名单/一致性策略，禁止静默漏备。

导出有container timeout及本次PID/namespace/starttime/pidfd清理；先确认自有dump退出再确认备份锁连接释放。失败不会生成complete或删除旧成功档，不杀mysqld/他人进程。

完成后gzip CRC+SHA封存，PVE经既有QGA内部接口每次至多1MiB读入PVE私有partial文件，校count/base64/EOF/总大小、SHA与完整gzip/结束标记；归档和目录fsync后原子提交。PVE确认本地副本后才清guest临时副本。过程不经Mac、不新增SSH私钥或网络端口。QGA用于当前小库受限数据量，不宣称大规模流传输通道。

完整Nacos元库包含配置、命名空间、历史及其库内用户/角色权限元数据；不备MySQL系统库/全局账号、宿主凭据文件或201整机配置文件。源系统重新部署仍依赖另行保管的凭据。本轮未执行SQL恢复、迁移或覆盖现役，CRC/SHA和mysqldump退出0不等于完整业务恢复/RPO/RTO通过。

## 监控与人工检查

原PVE collector只增加`dell_prod_db_backup_*`六个数值指标，经原QGA→Ops通道采集。三条既有备份告警名复用原Lark白名单/接收对象，表达式只看新的数据库任务：失败、成功超过36h、任务关闭/状态无效，for10m。旧wholeVM规则组已移除。没有人工发通知；同机失效仍可能同时失去服务、备份和通知。

以下仅在PVE只读检查：

```sh
systemctl status dell-prod-db-backup.timer dell-prod-db-backup.service
systemctl list-timers dell-prod-db-backup.timer
pvesh get /cluster/backup/dell-local-nightly --output-format json
```

日常不要重跑install.py/install-metrics.py/install-alerts.py，不运行旧11VM启用器。暂停未来计划用对应timer stop/disable；这不等于取消已执行中的任务。异常先查PVE/guest私有状态和精确run ID，不能通配删目录、强制解数据库锁或杀他人进程。恢复必须选隔离目标、重新核CRC/SHA并控制事件/外部副作用；本轮不提供自动恢复或覆盖生产入口。

源码：[guest-worker](guest-worker.py)、[host-worker](host-worker.py)、[QGA桥](qga-bridge.pl)、[host policy](policy-host.json)、[guest policy](policy-guest.json)、[service](dell-prod-db-backup.service)、[timer](dell-prod-db-backup.timer)。安装器都是有前置与拒绝覆盖保护的实施记录。
