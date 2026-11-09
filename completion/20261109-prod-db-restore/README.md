# 正式数据库备份隔离恢复演练：已通过

2026-11-09（Asia/Shanghai）。用户明确授权执行下一步第1项：对既有正式数据库/Nacos备份做隔离恢复。最后一轮原生任务已成功退出0，临时资源已清理，原备份与调度保持。

## 本次实际结果

| 项目 | 实证 |
| --- | --- |
| 源 | PVE现有b16d1ed9ff0a4ff1877179428bd592c6备份，nacos_prod/3301B，fresh SHA和CRC通过，原档前后SHA不变 |
| 目标 | VM210独立临时MySQL，同生产精确缓存ImageID，不pull、不复用源密码、不导入任何现役库 |
| 隔离 | 非root、networknone/无发布端口、独立新数据与秘密目录，1CPU/1GiB，事件DISABLED/MySQLX关闭/local-infile关闭/FILE操作禁用 |
| 内容 | 12张表、10条既有元数据；完整DDL语义、列顺序、所有列的内容摘要及CHECK TABLE通过 |
| 持久化 | 仅重启自己的临时实例，再次完整核对通过 |
| 清理 | 自有临时容器、SQL副本、数据和密码均删除；只保留root600脱敏reports；原4个test-data服务身份/健康不变 |
| 耗时 | guest内恢复/验证/重启/清理47.522秒；PVE含传输与控制总59.857秒，仅本份小档测量 |
| 调度 | 正式DB备份timer前后相同；原11来宾全机job保持关闭，不新增自动恢复任务 |

[最终原生收据](native-success.json)、[目标预检](target-preflight.json)、[设计复审](design-review.md)、[目标安装](target-install.json)、[PVE控制安装](host-install.json)。最后run为f9ffa0866ba748cfb9e8c8c54470cf3f，18:41:53–18:42:53。

## 失败与修正保留

第一次[原始失败](run-observation.json)在created临时容器无Health字段时触发Go模板错误，未执行SQL导入；初次清理也被同一模板阻断。[只读定位](inspect-template-diagnostic.json)明确错误后，改安全index读取并[核实归属后精确清理](health-template-fix-and-cleanup.json)，源4服务不变，原报告保留。恢复诊断中对source_snapshot的4容器门禁不适用于临时容器尚在场的阶段，随后使用明确排除本run的4服务对照，未绕过清理身份校验。

第二次[DDL严格比对失败](retry-observation.json)和第三次[显式utf8mb4仍失败](utf8-attempt-observation.json)均在导入后compare阶段停止，正常清理；失败没有改写为passed。它们证明不能把仅导入完成当验收完成。

[定位记录](ddl-display-investigation.json)结合MySQL官方[bug110825](https://bugs.mysql.com/bug.php?id=110825)与[8.4列字符集规则](https://dev.mysql.com/doc/refman/8.4/en/charset-column.html)：SHOW CREATE重放会额外显式化冗余CHARACTER SET。最终仅在scratch实际COLLATIONS映射证明相邻CHARACTER SET/COLLATE完全等价时做引号感知规范化，保留实际排序规则、类型、索引、约束、COMMENT和全部数据严格校验。这个修正没有修改生产schema，也没有忽略实际字符集差异；最后原生成功回执验证了完整语义/内容/重启一致。

各尝试的unit失败标志仅在记录并清理后单独reset-failed，日志和private报告保留。

## 范围与限制

当前快照活跃config_info为0，10条是Nacos历史、命名空间、用户/角色/权限等元数据；正式业务schema尚未创建，不能把本份小档恢复扩签为未来业务数据集恢复。没有启动Nacos JVM或重新登录HTTP；源运行密钥/凭据不属于本档。

未迁移、未覆盖现役数据库、未创建永久测试副本，SQL与秘密不经过Mac/Git；只留下脱敏证据。本次耗时不是获批RTO，仍未签完整业务RPO/RTO或独立设备灾备。自动备份范围继续仅正式数据库/Nacos配置。

维护源码见[演练实现](../../infra/backup/prod-db/restore/README.md)，当前验收见[四项清单](acceptance.json)。

## 独立后验与最终签收

[来宾后检](postcheck.json)核200/201/210原8容器healthy/restart0/OOMfalse，ID/镜像符合基线，启动早于演练；210只剩reports与固定.worker.lock，没有恢复容器/SQL/password/data残留。预检未保存全部旧PID，后检不编造逐个精确旧PID对比；targetworker自身已有原4服务完整frame前后相等证明。

[PVE/Ops后检](host-ops-postcheck.json)无failed units，原DB timer active/enabled、旧全机jobdisabled；15/15UP，无Prom/AM活动告警，新备份指标仍有效成功，内部Larkactive且未人工发消息。

**当前四项恢复验收4/4通过。** 原38项与6REC未因此改写为完整业务或硬件灾备通过。
