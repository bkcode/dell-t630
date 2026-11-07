# 实施顺序、任务管理与交接

更新：2026-11-07（Asia/Shanghai）。本轮在本地同步文档、规则与暂停状态，编写人工手册并进行Git交付；服务器操作暂停。用户控制台显示UEFI0058停在POST，先前SEL记录DIMM_B1多位内存错误。事件与解释见[硬件记录](cleanup/hardware/DIMM_B1-incident.json)，不能据此断言单条DIMM已确诊或整机物理关机唯一原因。

最后完整服务验收是2026-11-07 02:35:01+08，最后成功PVE操作是02:44:29+08。后者不等于再次完成服务验收；当前PVE/来宾/应用在线状态均未重新确认。

## 当前任务合同

| 工作 | 记录状态 | 下一门禁 |
| --- | --- | --- |
| 原部署与network19 | 历史阶段完成，证据保留 | 硬件恢复后重新取fresh运行基线 |
| 清理、fish与模板 | 清理9项历史通过；12角色+3模板，fish9guest+3tpl，默认Bash | 不重跑已完成清理或初始化 |
| Java | 230正式/240测试各一运行基础；不部署业务，单一Java验收模板9011 | 不启动旧五服务、不激活Nacos候选或publisher baseline |
| Nexus合并 | 短时停机维护已明确授权，尚未执行 | 硬件稳定、可信管理、fresh基线及本次冷备 |
| 硬件恢复验收 | 6项REC用例pending，尚未操作服务器 | 见[恢复入口](10-resume-after-approval.md)和[清理/恢复验收](cleanup/acceptance.md) |
| 本轮Git交付 | 本地资料、规则、暂停状态与人工手册同步后交付 | 实际提交/推送结果见[Git与交接](20-git-and-handoff.md)及交付证据 |

角色和预算唯一来源为[plan.json](plan.json)，任务状态为[tasks.json](tasks.json)，当前验收为[cleanup/acceptance.json](cleanup/acceptance.json)。原[38项验收](acceptance.json)中26项passed是相应历史阶段结果，12项future/manual仍pending，不能用它们代替当前健康检查。

## 恢复与实施顺序

1. 现场保留SEL/Lifecycle/POST证据，处理内存路径并完成适用离线诊断；硬件门禁未通过前不搬数据库、不加压，不自动按F1绕过。
2. root在可信管理恢复后核硬件、内存容量、RAID/BBU、文件系统和原数据盘UUID。PVE可连接只证明管理恢复的一部分。
3. 重新验证数据身份、网络/隔离、15监控目标与Java base-only状态。所有新结果须有对象、时间、观察及限制。
4. 仅在以上门禁及fresh冷备通过后，继续已获授权的Nexus合并；唯一原盘与IP31只允许一个owner，失败按已审方案回退。
5. 真实结果由主AI审核后更新验收，不把文档保存、程序存在、旧passed或授权存在当作实施成功。

## 权限、证据与回退

PVE写操作、VMID/IP分配和现场物理维护协调由主AI集中处理。CF归档仅PVE；publisher私钥仅220，不wholebackup220；不输出凭据，不上传客户端私钥。NAS不是正式唯一备份目标。

本机源数据与业务仓库保留。旧归档SHA/VMA/zstd通过不等于所有旧VM均已恢复启动；初始应用快照不等于长期独立调度或获批RPO/RTO。镜像/JAR回退与数据库回退分别验证，不双挂或双写。

原DOC-01～05及IMP-01～10分工、历史完成记录保存在[tasks.json](tasks.json)。本轮在本地同步文档、规则和plan暂停状态，编写[人工操作手册](19-manual-operations.md)，经审核与本地门禁后进行Git交付，不远程修改服务器。实际提交、推送与资料排除结果以[Git与交接](20-git-and-handoff.md)及交付证据为准。
