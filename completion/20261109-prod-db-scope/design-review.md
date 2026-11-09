# 正式数据库与Nacos配置自动备份：最小范围设计复核

日期：2026-11-09。**仅设计与本地审查，尚未部署或执行。** 用户最新收窄为正式数据库、Nacos配置自动备份到PVE本机；旧全VM job由主AI停用，历史归档保留不删除。本设计不重新启用全VM备份，不迁移/恢复覆盖用户数据，不操作Redis、RabbitMQ、测试库、NAS、CF或220发布私钥，不发通知、不执行Git。

## 建议结论（按实机小库场景修订）

主AI已只读核实PVE8.4本机：公开file-read API有16MiB上限，但内部`PVE::QemuServer::Monitor::mon_cmd`可在PVE进程内调用guest-file-open/read/close。**本期正式业务库仍空、小量配置场景，认可内部QGA以1MiB逐块直接落PVE私有文件**，压缩档上限1GiB、固定总超时。控制和数据均在PVE/VM200之间，不经Mac、不输出payload、不新增HTTP监听或任何客户端私钥。

上限是本期合同而不是性能保证；超过上限/总超时明确失败，不自动退回无TLS网络或大段stdout。未来数据增长再审专用流式通道。本次据主AI实机源码确认调整方案，没有把公开API的16MiB误当内部接口的总文件限制，也不把官方单次最大值当必须使用的块大小。

下面QGA的额外开销/中断边界仍须实现，不能泛称适合无限bulk。既有公开API、pveproxy上传或通用SSH都不作为隐含后备，不复制Mac私钥，也不通过Mac下载再上传。

## 数据集必须先冻结

### 正式业务数据库

唯一业务数据来源是VM200 `data-prod-db` /19.10上现有MySQL8.4.5容器；不抓整VM/原数据目录，不把`--all-databases`当完整范围。

- 部署时只读发现所有非系统schema，再与root拥有的正式业务schema精确白名单比较。排除mysql、sys、performance_schema、information_schema、全部*_test及测试/验收schema；Nacos单独分类。未知新库、漏库或命名冲突一律报告并拒绝该轮，不能自动吞入或静默忽略。
- 已批准的每个业务库备份全部表、视图及明确需要的trigger/routine/event定义。不能只dump有数据的表，不能仅用库名/大小或当前正式空库证明以后覆盖完整。
- 目前正式业务可能仍空；空清单是合法事实，但应明确“本次无正式业务库，仅有Nacos配置”，不能伪造全业务备份数量。以后新库需审核纳入。
- 不导出MySQL全局用户/授权表。仅逻辑数据集不等于完整账号重建，账号/权限恢复说明另行受控维护，不把它悄悄扩为mysql系统库全备。

### Nacos配置：DB表与运行文件分别登记

本地源合同显示正式Nacos运行于201，而其外部MySQL元库在200；因此可以在200备份配置表而不备份201整机，也不访问201的Redis/MQ数据。

配置相关表应以**目标实际schema及当前已审2.4.3结构**冻结，不能只dump `config_info`：候选包括 `config_info`、`config_info_aggr`、`config_info_beta`、`config_info_tag`、`config_tags_relation`、`tenant_info`、`group_capacity`、`tenant_capacity`，以及需要保留配置版本历史时的`his_config_info`。本地vendor SQL供核对，实际表缺失/新增/引擎差异必须解释，不能直接把旧表单当现场真相。

主AI本次已明确选择“全指定业务库+完整Nacos元库”，因此该元库包括`users/roles/permissions`及其hash等敏感元数据，与配置表在同一次dump中保存，只留受保护PVE。这里不再按“仅content表”默认丢弃认证元数据，也不扩展到MySQL系统用户库或201其它组件。交付须称“完整选定Nacos元库”，而不是仅config_info；未知对象仍须盘点归类并纳入精确清单，不能夹带Redis/MQ/测试库。

运行文件若也属于用户所说“Nacos配置”，必须另立**仅Nacos文件/键白名单**：201的vendor application.properties、固定entrypoint、Nacos相关公开env键，以及确实必需的nacos-db-password/nacos-auth-token/nacos-identity-value。不要归档整个prod-infra目录或.env/secrets目录，里面混有Redis/MQ凭据。服务端配置秘密只能经PVE上直接运行的受控通道进入PVE私有归档，不经过Mac。当前本设计不读这些文件，目标实际路径和范围需先核实；没有此部分时明确“仅Nacos数据库配置表，不含运行凭据”，不声称完整服务恢复可用。

## 一致性门禁：不能把no-DDL写成无人确认的timer常量

MySQL官方说明，single-transaction的稳定读取针对InnoDB；并发ALTER/CREATE/DROP/RENAME/TRUNCATE可能破坏转储。一个定时参数`--confirm-no-ddl`、一次“当前无DDL会话”检查或前后schema摘要相同，都不能证明整个dump期间没有DDL。采用single-transaction与quick的边界依据见[MySQL8.4 mysqldump](https://dev.mysql.com/doc/refman/8.4/en/mysqldump.html)。

建议启用自动化前满足以下全部条件：

1. 所有纳入的base table为InnoDB；版本、对象类型和实际权限经只读预检。不支持的引擎/视图/对象不能默默跳过。
2. 业务发布/迁移入口与备份共享DDL互斥协议，备份期间不会启动schema/routine/event变更；不得依赖“Java现在没运行”长期维持这个假设。若无法接管所有DDL路径，当前自动策略不可声称有严格逻辑一致性。
3. 评估并验证MySQL8.4 `LOCK INSTANCE FOR BACKUP`：用独立持久会话持锁，取得后才运行dump；有界等待，失败本轮退出，不改用全局长时间读锁。锁随会话释放，允许业务DML，但会阻挡某些DDL/账户操作；需要BACKUP_ADMIN。官方依据见[LOCK INSTANCE FOR BACKUP](https://dev.mysql.com/doc/refman/8.4/en/lock-instance-for-backup.html)。它不是所有routine/event/元数据变更都安全的空白保证，仍须上一步协调与准确权限/操作覆盖核实。
4. 持锁会话必须活到dump完成，并有独立生存检查；不能启动一个mysql进程执行LOCK后立刻退出，也不能固定SLEEP到期后继续盲dump。锁丢失立即将本轮标失败并终止自己dump客户端，不能kill现役mysqld或其他会话。持锁时间只覆盖元数据盘点与转储，不覆盖后续QGA传输/保留；成功后finally UNLOCK并关闭连接，异常时关闭本次连接释放锁，记录是否真正清理成功。
5. 使用一次mysqldump连接覆盖全部已批准业务库与完整Nacos元库，包含本次已明确纳入的认证表，避免多个独立转储却声称同一快照。用精确`--databases`白名单、不用all-databases；生成前核对象完整清单，不混入MySQL系统库/测试库。确需拆成两份时明示不同快照点，不承诺跨两份原子一致。

固定选项候选为single-transaction、quick、hex-blob、no-tablespaces、set-gtid-purged=OFF、skip-lock-tables及已批准的routines/triggers/events；实际顺序和默认配置需核验，避免外部my.cnf启用额外库或锁。不要顺带flush/purge binlog、锁表停写、重启数据库或宣称PITR已具备。

凭据优先仍在MySQL容器内读取原受控文件，通过本地连接使用，不把数据库密码放argv、进程输出或普通日志，不将root密码复制到PVE。长期自动任务可设计仅本地socket可用的专属账号，按确切schema赋SELECT/SHOW VIEW/TRIGGER及确需对象权限；BACKUP_ADMIN单独审查，不因方便授全局ALL。是否需要新账号/connector实现由主AI确定，本设计不创建账号或读取认证值。

## 本期受限QGA分块传输

### 为什么本期可用

源业务数据小且尚无真实业务行，压缩档严格≤1GiB。采用本机已核internal mon_cmd，避免公开file-read API的封装限制；固定1MiB原始字节/块，PVE进程中完成base64解码和文件写入，内存只保留本块。不能把每块内容放guest-exec stdout、pvesh输出、shell命令参数、日志、普通JSON证据或Mac控制端。正常输出只含runID、阶段、bytes、比较布尔；敏感manifest及SHA只留PVEroot600。

官方QGA仍明确guest-file-read为base64响应、面向有限调试场景，guest-exec捕获输出可能截断；因此本期使用有界的小文件方案，而不声称无限大文件通用传输。[QEMU Guest Agent协议](https://qemu-project.gitlab.io/qemu/interop/qemu-ga-ref.html)

### 必须实现的传输判据

1. producer先完成dump、压缩、退出码检查和guest SHA/size，按本次runID原子封存为不可再写的固定artifact，然后才open。固定VM200/固定spool子树/固定runID，不接受调用方任意路径；拒绝符号链接、非regular、多hardlink及不符owner/mode。
2. 在PVE进程直接mon_cmd open/read/close。handle仅是本次会话状态，不跨run复用；每次read requested count≤1MiB，严格base64校验、实际decoded长度==返回count且≤requested。最终非空且eof=true的块必须先写再结束，不能丢最后一块。
3. 累计字节不能超过源manifest size或1GiB；出现0bytes且eof=false必须有界退出/报告，不能无限循环。结束必须eof=true且累计size恰等于封存size。固定每RPC超时与全任务deadline，设置上限后不能在超时分支偷偷延长。
4. PVE目标用新nonce `.partial`、O_EXCL/O_NOFOLLOW、root600；流式计算SHA并和guest封存SHA在进程内比对，再压缩流完整性校验；fsync文件、原子rename/commit及目录持久化后才写成功manifest/last-success。不得因有EOF或QGA命令exit0就当备份完成。
5. guest handle在finally尝试close；QGA断线/文件不存在/长度变化/校验不符/磁盘满/timeout全部失败，保留有界root600诊断。关闭失败也记录，下一轮不得盲复用旧handle或旧partial。
6. 先不实现断点续传。需要重试时仅在确认源artifact仍同run同size同SHA后重新走明确定义的小文件传输；未确认不得seek拼接不同run，不重跑SQL覆盖原spool。实现初版可直接本轮失败，等待下次调度。
7. QGA占用不得长时间阻塞guestagent：串行、短RPC、块间可让出，状态/心跳限频；PVEbackup/restore等其它QGA使用不能与本次互相无限等待。实测首轮总用时/最大内存后再选频次，不能预先保证1GiB必在某时限完成。
8. 仅PVE成功commit后回告guest ack清理本次spool，失败不prune旧成功。PVE不能拿普通“目录空/新文件名”猜guest清理对象。

公开API分块、guest-exec stdout拼大文件、一次读取48MB上限、base64进入shell/日志均不作为旁路。此设计不新增广泛权限、不开放MySQL3306给PVE新账户，也不备份201整机。持锁会话断开必须让正在运行的本次mysqldump客户端失败退出，不能在锁丢失后继续产生“成功”artifact。

### 未来超过本期上限时再审

届时可比较PVE主动拉取VM200短时固定GET HTTPS，与VM200推到PVE专用接收器。前者不授来宾PVE写入/登录能力，但需要精确ACL/TLS公钥pin；后者新增宿主接收写入面，需要更严格限制。若没有合适的既有TLS证书，短期TLSkey也需明确，不冒称零新key。现阶段不新增这些listener、私钥或API token。

PVE若已存在兼容mysqldump且可做MySQL TLS/最小账号，也可另审直接客户端通道；本地材料未证实它已存在，不安装Docker或复制Mac私钥来拼通道。

## 实施状态机与磁盘门禁

建议PVE每日timer仍由root控制，**单run全程flock**，不是每次RPC各锁一次。来宾也有独立run锁，避免PVE断线后另一个run覆盖活跃spool。固定helper只接受start/status/ack-cleanup与格式化runID，不接受shell、数据库任意名、路径或选项透传。

状态：preflight → DDL保护 → 单次dump → 压缩/本地封存 → QGA小块受限传输 → PVE校验 → 原子commit → 允许retention → ack → 本次临时资源清理。任一步失败都不可更新last-success；只将本轮状态和非秘密失败类别写root600记录。

来宾门禁：VM200 hostname/IP/MAC、MySQL固定容器/镜像、数据挂载 `/srv/dell-data` 与原UUID、spool绝不落根盘替代目录；输出新nonce目录O_EXCL，目录700、文件600、umask077、拒各级symlink/hardlink/path traversal。必须检查数据库估算、现有spool、根盘/数据盘可用空间及保守余量；具体阈值按实际容量审批，不沿用宽泛脚本2GiB即假设够用。

PVE门禁：`/mnt/pve/store`真实ext4/原UUID，固定**新**prod-db逻辑备份namespace，不与旧全VMdump、21回退档、CF归档重叠；root700目录/600文件，磁盘未挂或容量不足立即失败，不在根盘自动mkdir兜底。不能把store与其目录storage的avail相加当双份容量。

dump、压缩、传输分别有超时/退出码，管道任一失败整轮失败；终止仅自己进程组或本次明确容器exec进程，不kill数据库、不删锁强行重试、不跑恢复。杀死PVE/QGA/docker客户端不保证容器内mysqldump已经退出，必须在guest固定worker记录自己容器内PID、proc-starttime及runID并核对后清理，确认本次dump进程/连接已结束；禁止pgrep后批量kill或kill其它备份/业务连接。使用stream/固定buffer，低优先级和资源上限；不要将40秒SSH等待当作整个长任务生命期。日志限大小且脱敏，不输出SQL、表行、配置值、票据、私钥或原HTTP认证头。

## 内容完整性如何验证，哪些不能冒签

1. **可现在设计、首轮实测的层**：完整退出码；压缩流检验；源与目标bytes/SHA相同；冻结schema/表/对象清单与转储内对象集吻合；Nacos配置表包含tenant/dataId/group关联所需字段，转储不含意外schema，Nacos认证表按本次完整元库合同纳入。所有内容级核验只在guest/PVE受保护进程内执行，普通证据仅对象数量/集合比较布尔，不输出配置正文或其敏感摘要。
2. 不把live `COUNT(*)`/config md5在dump前后随意查询后声称等于dump同一快照。并发DML时不同session的计数、摘要可能合法变化；没有共享snapshot证明就只记为参考。SQL含扩展INSERT/转义，禁止`grep INSERT`/按分号拆SQL统计当精确行数证明。
3. **完整恢复证明需将来单独窗口**：同版本MySQL在独立空scratch、无外网、event_scheduler OFF/local_infile OFF，恢复并核业务schema对象/约束及Nacos配置的tenant/dataId/group/content/版本历史；任何用户数据恢复操作都不在本次“仅设计”内。已有SQL规范化器/历史小样本恢复不能自动证明新业务全量dump已恢复。
4. 全逻辑转储成功不等于全实例账号/密钥、PITR、跨服务事务或整机灾备。Nacos配置内容和运行秘密如未同时纳入合同，就明确缺口；自动备份完成不强改原恢复/RPO/RTO pending。

## retention必须与产物提交隔离

- 用户仅收窄备份范围，不等于删除历史全VM归档许可。旧job停用后保留其归档、21回退档和状态历史，不按新保留器清掉旧目录。
- 新保留器只识别自身namespace、固定格式runID、完整成功manifest和已核存储UUID；不跟随symlink，不递归通配`rm -rf`，不根据mtime或“最近文件名”识别有效备份。
- 仅在本轮PVE成功commit后，持全程锁生成确定删除计划，确保获批最低完整成功副本数仍存在；dry-run与实际对象身份再校验，支持隔离quarantine而不是直接删任意目录。先实施元数据dry-run，再批准实删。
- 备份失败、磁盘满、传输中断、DDL锁超时、manifest损坏都不应触发旧成功副本删除；failed partial按独立有界策略处理，不把partial算可恢复副本。磁盘不足不能先删唯一好备份来“腾空间”。
- 频次、保留数量和总容量可以参考原03:30/3-7-4，但本轮数据集/大小变化后仍须重新明确；旧参数不是自动继承许可，更不能据此承诺RPO。容量/失败指标可接原内部监控，首次不新增真实外发测试。

## 部署前最少需要root裁决/核实的事项

1. 正式业务schema白名单实际集合，完整Nacos元库（含认证元数据）已由主AI选择；是否另含201仅Nacos运行文件/秘密仍须精确白名单，不读取混合Redis/MQ目录。
2. 无DDL协调入口与持久backup-lock实现是否可保证；无法保证时先保留手动受控窗口，不给timer盲加confirm参数。
3. 核实internal mon_cmd已安装版本及返回结构，固定1MiB块/压缩档≤1GiB/每RPC与总超时、EOF/长度/SHA/压缩校验和finallyclose；本期无需新listener或key。超过上限失败，不自动换通道。
4. 业务dump大小/运行资源、timer频次、新namespace容量和成功/失败保留策略，及后续恢复验证对象。PVE本机已获用户选择，不再次将独立目的地当当前搭建前提；同时如实保留同机故障域限制。

## 本次审查材料与未执行

本地读取：`infra/backup/application-backup.py`、`infra/data/compose.prod-db.yaml`、`compose.prod-infra.yaml`、`vendor/nacos-mysql-schema-2.4.3.sql`及原逻辑恢复工具。旧application-backup包含Redis/MQ分支与手动确认，不能直接设为新范围timer；新实现必须固定仅200与Nacos配置，不通过宽选项“自觉不调用”约束范围。

官方依据仅核MySQL8.4单事务/backup lock与QGA协议，未查询第三方私有仓库或真实服务。没有SSH、服务器写、秘密读取、备份/恢复/通知或Git；本文件是可审设计，**不是已安装、已传输或已验证成功的实现**。
