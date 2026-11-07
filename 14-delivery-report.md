# 交付与硬件暂停报告

更新：2026-11-07（Asia/Shanghai）。软件部署、网络和清理的历史验收保留；**当前处于硬件暂停，不能宣称PVE、来宾或服务正在运行。** 最后完整服务验收为02:35:01+08，最后成功PVE操作为02:44:29+08，二者不是同一项验收。

用户iDRAC/控制台证据先示PowerOff，后示UEFI0058停在POST；先前SEL记录DIMM_B1多位不可纠正错误及correctable阈值超限。BMC显示时间时区未核，内存模块/槽位/通道/控制器仍需隔离，不能断言单条DIMM已确诊或是物理关机唯一原因。[事故记录](cleanup/hardware/DIMM_B1-incident.json)与[恢复入口](10-resume-after-approval.md)为当前门禁。

## 最后验收结果

- 12角色（11VM+1LXC）、43vCPU/85GiB、3模板9001/9010/9011；正式230和测试240各一。15旧对象与6临时对象已保护归档清理，受保护备份完整性有证据，不等于所有旧对象恢复启动都实演。
- network19经独立网关190路由，PVE21.22保留管理/L2，旧宿主四桥/NAT/forward撤除；WireGuard10.66.66/24路径与原角色隔离验收完成。
- fish9guest+3模板为4.0.2-1，默认shell保持Bash；CF/Penpot/Ops与PVEhost排除。candidate独立QA在替换原模板前完成，机器/hostkey/DockerID去重，Java原JDK/非root验收基线保持。
- Java业务按最新用户范围不部署，230/240只有运行基础，单一Java验收模板9011；原测试五服务E2E、发布B/A回退是历史证据，publisher继续fenced，不能据此自动启动业务。
- 200/201正式与210测试隔离、认证及受控持久/恢复曾通过，正式空业务数据。Penpot原3设计/971原媒体保护、新身份/MCP/监督恢复及NAS软件权限/合成DirectPlay/隔离缺挂载保护曾通过；真实家庭设备和混合负载未验。
- Nexus221原身份/EULA、49GAV/234主制品SHA、重建恢复曾通过；220最后仅standby。用户随后已明确授权短停合并，但硬件暂停前未开始迁移，未执行本次停源、重启、移盘或IP31交接。
- 清理后15targets（10guest+5Ops）曾UP，内部Lark已验启用；这只是最后基线。Mac外部探针按用户选择停用，T630整机故障可能同时失去机内监控与通知。

## 仍待完成

[原38项验收](acceptance.json)保留26历史passed、12future/manual pending。本轮[清理验收](cleanup/acceptance.json)保留9历史passed、1已授权但未执行的Nexus合并，并新增6项未执行恢复门禁：硬件、冷备、数据身份、网络、监控、回退。当前应先恢复硬件并fresh核验，不能只因管理端口重新可达就继续搬数据库。

长期独立备份目的地/调度、获批RPO/RTO、整机灾备、生产业务SLO、真实电视/PS4/PS5/4K HDR/GPU仍未验。家用NAS不是正式唯一备份；CF归档仅PVE，publisher私钥仅220，禁止wholebackup220或跨设备夹带私钥。源Mac数据和业务Git工作树保留。

访问地址与操作细节只引用[运行手册](12-service-access-and-operations.md)，不复活旧21.22 DNAT或旧10.63地址。本轮在本地同步文档、规则及plan暂停状态，编写[人工操作手册](19-manual-operations.md)，经审核与本地校验后进行Git交付，不远程修改服务器。实际提交、推送及交付证据见[Git与交接](20-git-and-handoff.md)；本地文档通过或Git交付不等于当前live恢复。

## 证据入口

- [最后完整检查](cleanup/final-live-check.json)、[清理验收](cleanup/acceptance.md)、[阶段状态](phase-delivery.json)
- [fish与模板QA](cleanup/fish/template-QA-summary.json)、[模板替换](cleanup/fish/core-template-replacement.json)
- [Nexus维护授权](cleanup/nexus/maintenance-authorized.json)、[合并准备](cleanup/nexus/preparation-readback.json)
- [硬件事故](cleanup/hardware/DIMM_B1-incident.json)、[恢复门禁](10-resume-after-approval.md)、[任务状态](tasks.json)

历史真实失败及修正均保留，未改写为一直成功；本次没有新的服务验收或恢复passed记录。
