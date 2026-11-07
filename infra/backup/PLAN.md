> 文档状态（2026-11-07）：本页为阶段实施/技术记录，文中“当前”、网段、角色数与通过结果以原执行时点为准。服务器现因UEFI0058内存错误暂停，Nexus合并已授权但未执行；当前配置入口见[访问清单](../../12-service-access-and-operations.md)，恢复门槛见[最新交接](../../11-live-handoff.md)。旧脚本、stage/commit或初始化步骤不得直接重跑。

# 应用备份与隔离恢复执行范围

2026-11-06 主 AI 已审阅并认可本轮A-D：仅VM200/201专属纯合成fixture，逻辑导出、无外网/无端口映射临时容器恢复验证，结束清理专属对象。Mac的private/backups/app仅接收纯合成归档或脱敏证据。CF所有资料完全排除；不访问210/270或其他来宾，不停止现役数据服务，不发Nexus或外部凭据。

本轮fixture：200独立InnoDB表；201独立Nacos config行、Redis key、Rabbit独立vhost空durable队列。Nacos只过滤config_info这条自建行，不含users/角色/凭据，不是完整配置备份；Rabbit仅自建vhost topology，不含用户/权限/消息，不是消息备份。

验证容器仅固定已部署版本AMD64 digest，network=none，无publish，无源数据卷，只使用独立空scratch；验证临时秘密仅600文件或STDIN，不进入归档/argv/stdout。只移除自己创建的临时容器与fixture。导出如果被自动审批要求具体用户确认，应停止并报告，不以编码/加密或换路径绕过。

正式脚本E仅准备：MySQL/Nacos在无DDL窗口下InnoDB single-transaction逻辑备份；Redis独立RDB；Rabbit topology明确不包含消息；Ops配置与Grafana SQLite在线backup，Prometheus TSDB/Alertmanager nflog历史需另行维护窗口或受控snapshot。E不在本轮执行，不声称应用全量、RPO/RTO、异地灾备或真实告警送达达成。
