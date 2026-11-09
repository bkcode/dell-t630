# 正式数据库与Nacos配置备份范围调整

2026-11-09（Asia/Shanghai）。用户最新要求仅正式环境数据库与Nacos配置纳入自动备份，其他数据暂不纳入。新范围已完成实际首轮、调度与监控验收；这取代此前11实例整机自动备份方案。

## 实际结果

| 项目 | 结果 |
| --- | --- |
| 源 | VM200/192.168.19.10，当前唯一非系统库nacos_prod，12张InnoDB基础表；正式业务schema尚未创建 |
| Nacos | VM201的配置实际存于VM200/nacos_prod，保存完整Nacos元库（配置/命名空间/历史及库内权限元数据） |
| 首轮 | 16:56:04–16:56:17，3301 bytes；gzip完整CRC、QGA传输SHA及dump结束标记通过，任务退出0 |
| 目的地 | PVE `/mnt/pve/store/dell-artifacts/prod-db-backups/<run-id>/`，root700目录/600文件；SQL及SHA没有经Mac或Git |
| 新计划 | dell-prod-db-backup.timer，daily03:30 Asia/Shanghai，enabled/active；下一次2026-11-10 03:30 |
| 保留 | 最近3份/每天7点/每周4点并集；只在新档verified、fsync提交后清本namespace超额成功档，永保本轮；跨多个周期仍待观察 |
| 旧机制 | 原dell-local-nightly整机job已disabled，旧专属规则组移除；已有19.75GB整机档和21个旧回退档保留，不自动清理 |
| 配套 | 六个DB专属指标有效成功，原三条备份告警改看DB任务；同Prom容器热载，既有Lark接收对象保持，无人工通知 |

## 证据

- [停旧整机job](whole-vm-job-disabled.json)、[旧规则退役](whole-vm-rules-retired.json)。
- [正式库盘点](inventory.json)：SHOWDATABASES/表引擎/计数与固定容器身份，没有读取输出业务行或.env值。
- [安装](guest-install.json)、[PVE单元/原生校验](host-install.json)、[首轮和调度](first-success-and-timer-enabled.json)。
- [元数据接入](metrics-installed.json)、[规则实际加载](alerts-installed.json)、[最终健康](final-verification.json)。
- [源端后验](source-postcheck.json)：原4容器healthy/restart0，MySQLserver正常，dump/mysql/timeout工作进程0，备份锁/待锁/DDL/事务计数0；guest本run与container临时标记均清，仅root600固定.worker.lock保留。
- [设计审查](design-review.md)、[mysqldump实际参数能力](mysqldump-capability.json)、[容器timeout能力](container-timeout-capability.json)。

告警安装曾遇模板替换解析失败及一次未确认加载；新增文件按已知范围回退，显式文件权限与步骤检查修正后原生校验/热载成功，保留[修正记录](alert-activation-correction.json)和[只读诊断](alert-activation-diagnostic.json)。未因此改接收对象/认证或发送测试通知。

## 范围边界

其他VM、整机、测试库、Redis/MQ、NAS媒体、Penpot、Nexus、CF和发布数据不纳入当前自动备份。SQL含Nacos元库必要数据，但不备MySQL系统库/全局账号或凭据文件。新增非系统库未列入白名单会使任务失败并告警，需明确纳入，不能静默漏备。

这是同机逻辑恢复点，未执行SQL恢复、迁移、覆盖现役或独立灾备/RPO/RTO验收；没有启动Java业务。当前小库受限QGA传输，不新增端口/SSH私钥，1GiB压缩与8GiB展开上限之外须另审大库方案。Mac外部探针不需要。原11实例备份的成功收据作为历史保留，不能再据它启用旧job。

维护及实现：[新备份说明](../../infra/backup/prod-db/README.md)、[当前6项验收](acceptance.json)。
