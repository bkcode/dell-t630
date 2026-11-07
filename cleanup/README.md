# 整理记录入口

2026-11-07：当前服务器因UEFI0058内存错误暂停，等待用户处理硬件。本目录保存已完成清理与未执行合并的证据，不代表当前在线。

最后02:35验收为12实例+3模板；正式230/测试240各1无Java业务。15个旧对象和6个临时对象已清理，21份受保护归档仍保留。9来宾+3模板fish4.0.2，默认Bash，CF/Penpot/Ops及PVE排除。

Nexus220仅准备，源221未按迁移停服/迁盘；用户已明确授权短停，当前阻塞是硬件及用户暂停。合并并验收后才变11实例/14targets，不能提前删除源221或监控目标。

阅读：[当前交接](../11-live-handoff.md)、[整理结果](../18-cleanup-and-consolidation.md)、[验收](acceptance.md)、[状态登记](runtime-status.json)、[历史实机检查](final-live-check.json)、[备份](backup-summary.json)、[Nexus恢复计划](nexus/resume-preflight.md)、[硬件事件](hardware/DIMM_B1-incident.json)、[人工手册](../19-manual-operations.md)。

历史清理维护已[解除](maintenance-ended.json)；恢复合并必须新建维护窗。内部Lark配置保留，Mac外部probe停用；本轮文档工作不连接服务器或发通知。
