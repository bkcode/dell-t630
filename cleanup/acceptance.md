# 清理、fish与硬件恢复验收

更新：2026-11-07。当前服务器操作暂停，live状态未重新验证。最后完整服务验收为02:35:01+08，最后成功PVE操作为02:44:29+08；用户控制台UEFI0058停于POST，先前SEL指向DIMM_B1。BMC时区未核，单条DIMM与物理关机唯一根因未确诊。

原清理10项保留9项历史passed，Nexus合并1项pending。合并[已获明确短停授权](nexus/maintenance-authorized.json)但未执行，当前阻塞是硬件恢复及fresh基线，不再等待同项用户许可。另有6项恢复门禁均pending，未执行。完整条件见[JSON](acceptance.json)，事件见[硬件记录](hardware/DIMM_B1-incident.json)。

## 原清理记录（历史，不是当前在线证明）

| ID | 项目 | 历史状态 | 记录与证据 |
| --- | --- | --- | --- |
| CLN-JAVA-001 | 正式测试各保留一个运行基础 | passed | PVE中230/240各一且无业务Java进程，231/232已归档清理；原生产测试隔离保持。 [final-live-check.json](../cleanup/final-live-check.json), [redundant-Java-stopped.json](../cleanup/redundant-Java-stopped.json) |
| CLN-BAK-001 | 21份受保护原/候选归档完整性 | passed | 15旧对象+3原core+3fish候选归档均zstd/VMA/SHA验证，root700/600，排除CF100与整机220。 [backup-summary.json](../cleanup/backup-summary.json) |
| CLN-DEL-001 | 精确15旧对象依赖顺序清理 | passed | 15个确切对象已删，104先103，无force/skiplock或共享ISO删除。 [deleted-candidates.json](../cleanup/deleted-candidates.json), [delete-script-review.md](../cleanup/audit/delete-script-review.md) |
| CLN-FISH-001 | 9运行来宾安装fish并保默认shell | passed | 190200201210220221230240260 fish4.0.2-1，默认Bash未改，CF/Penpot/Ops与PVEhost排除不动。 [runtime-status.json](../cleanup/fish/runtime-status.json) |
| CLN-TPL-001 | 三模板fish升级与独立QA | passed | 三独立candidate QA验证新机器/hostkey/DockerID、Java原基线和fish；原备份后恢复到9001/9010/9011，stopped/DHCP/genericCI。 [template-QA-summary.json](../cleanup/fish/template-QA-summary.json), [core-template-replacement.json](../cleanup/fish/core-template-replacement.json) |
| CLN-TMP-001 | 临时构建验收对象无残留 | passed | 本任务9040–9045已清除，PVE仅12运行+3模板，无额外停止VM。 [temp-closeout.json](../cleanup/fish/temp-closeout.json), [final-live-check.json](../cleanup/final-live-check.json) |
| CLN-DNS-001 | 退役DNS与身份同步 | passed | 11退休名UDP/TCP NXDOMAIN、11保留A正确，artifact31/publisher30保留；WGfull/NATnone/hostforward0及MACIP/role隔离保持。 [summary.json](../cleanup/network/dns-runtime/summary.json), [final-live-check.json](../cleanup/final-live-check.json) |
| CLN-OBS-001 | 10节点15目标与维护恢复 | passed | 15/15UP、221保留UP，10份catalog/installer配套；health/collector/业务身份不变，清理site静默仅本任务项解除，0activealerts/no testsend。 [execution-status.json](../cleanup/monitoring/ten-role/execution-status.json), [maintenance-ended.json](../cleanup/maintenance-ended.json) |
| CLN-REG-001 | 保留SSH与原应用入口回归 | passed | 10guest新strictSSH/唯一19地址/默认GW正确，五原web入口200、数据/身份未被fish/模板清理改变，Java业务不启动。 [final-live-check.json](../cleanup/final-live-check.json) |
| CLN-NEXUS-001 | Nexus同机合并与源221退役 | pending | 用户已明确授权短时停机合并，但迁移未开始。iDRAC先示PowerOff，随后控制台UEFI0058停在POST；此前SEL指向DIMM_B1。当前阻塞是硬件恢复和fresh验收，不是再次等待同项维护授权。 [PLAN.md](../cleanup/nexus/PLAN.md), [preparation-readback.json](../cleanup/nexus/preparation-readback.json), [approval-block.json](../cleanup/nexus/approval-block.json), [maintenance-authorized.json](../cleanup/nexus/maintenance-authorized.json), [DIMM_B1-incident.json](../cleanup/hardware/DIMM_B1-incident.json) |

## 硬件恢复新增门禁（全部未执行）

| ID | 项目 | 状态 | 通过边界 |
| --- | --- | --- | --- |
| REC-HW-001 | 硬件POST、内存路径与可信管理恢复 | pending | POST正常进入OS、内存诊断与fresh错误检查达成现场批准条件、可信管理身份匹配、存储无新异常；根因未完全定位时限制明确。 |
| REC-BAK-001 | 合并前冷备完整性与隔离恢复点 | pending | 本次221冷备与磁盘/config对应，校验通过且受保护；批准的隔离恢复对象能读取预期数据，源副本不被修改。 |
| REC-DATA-001 | 恢复后的数据和服务身份一致性 | pending | 既有数据/身份/权限/UUID与批准基线一致，Java业务仍未部署，差异逐项可解释且获审。 |
| REC-NET-001 | 恢复后的19网段、WireGuard和宿主管理边界 | pending | 登记地址和MAC匹配，无冲突/旧NAT复活，管理与既有VPN路由、角色隔离正反检查通过。 |
| REC-OBS-001 | 恢复后的监控15目标与内部通知边界 | pending | 15targets fresh采样符合预期、硬件指标可观测、当前告警逐项处理，内部通知配置身份保持且无未授权外发。 |
| REC-ROLL-001 | Nexus合并回退与最终签收 | pending | 回退与最终切换有真实对象/时间/步骤/结果，数据身份和唯一owner保持，审批范围内最终验收完整。 |

这些用例不授权本轮远程或物理操作。必须先由主AI与具备资质的现场人员完成硬件门禁，再在原批准范围核可信管理、冷备、数据身份、网络、监控和回退。不能自动按F1绕过、清SEL或以PVE端口可达代替硬件稳定。计划结果路径尚无执行结果，不签passed。

最后核验清单为12角色+3模板、230/240各一且Java业务不部署、fish9guest+3tpl、15targets。源221最后验收时运行，当前不可确认；助手未执行本次合并停服/移盘/IP交接。内部Lark仍属同机故障域，Mac外部探针保持停用；家用NAS不是正式唯一备份。
