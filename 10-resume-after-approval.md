# 硬件暂停后的恢复入口

更新：2026-11-07（Asia/Shanghai）。本轮同步本地文档、规则与暂停状态，编写人工手册并进行Git交付，服务器操作暂停；实际Git结果见[交接记录](20-git-and-handoff.md)及交付证据。Nexus“短时停机合并”[明确授权](cleanup/nexus/maintenance-authorized.json)仍有效，但迁移未开始；阻塞是UEFI0058 POST/先前DIMM_B1内存路径错误，**不是再次等待同项维护授权**。

最后完整服务验收：2026-11-07 **02:35:01+08**；最后成功PVE操作：**02:44:29+08**。之后用户iDRAC/控制台及管理连接证据不证明服务恢复。当前PVE/guest/application状态均未重新验证；见[硬件事故](cleanup/hardware/DIMM_B1-incident.json)。

## 恢复门禁与顺序

| ID | 对象与门禁 | 当前状态 |
| --- | --- | --- |
| REC-HW-001 | 现场保留SEL/Lifecycle与POST；核B1内存路径，按Dell流程断电维护和离线诊断；正常POST后root再可信核内存/RAID/BBU/文件系统 | pending，未执行 |
| REC-BAK-001 | 硬件稳定后fresh核221/220，批准维护内制作本次221冷备及校验，受控隔离恢复点；禁止wholebackup220/导出发布私钥 | pending，未执行 |
| REC-DATA-001 | 数据盘UUID、既有身份/账号/权限/素材/制品摘要保持，Java不部署业务、publisher fenced | pending，未执行 |
| REC-NET-001 | PVE管理/L2、190网关、19地址/MAC/GW/DNS、VPN路径与角色正反隔离fresh验证 | pending，未执行 |
| REC-OBS-001 | 10guest+5Ops的15targets、硬件指标、Java base-only语义及内部Lark配置fresh核验；不外发 | pending，未执行 |
| REC-ROLL-001 | 合并回退、原盘/IP31唯一owner、数据兼容性与最终签收真实记录 | pending，未执行 |

逐例前置、步骤、可观察通过条件、失败条件和计划证据路径见[结构化验收](cleanup/acceptance.json)。这些是恢复计划，未生成任何新的恢复passed结果。

不自动按F1绕过POST，不远程powercycle或清SEL，不据“PVE又能连上”直接搬数据库或加压。B1事件尚未确诊到单条DIMM，也不足以证明是物理关机唯一原因；BMC显示时间时区未核。物理维护与稳定观察条件由主AI和具备资质的现场人员明确，不擅定通过时长或数值。

## 硬件门禁通过后

主AI先恢复可信管理与fresh事实，再根据已审[Nexus计划](cleanup/nexus/PLAN.md)安排现有授权维护：冷备、干净停源、220资源与唯一原盘/IP31交接、账号/EULA/制品与权限复验、监控及回退，最后才签收221退役。未有本次执行证据前，220仍只能称“最后验收为standby”，不能称已接管Nexus。

当前唯一角色预算来源为[plan](plan.json)：12角色+3模板，230/240各一、Java业务不部署。禁止重跑旧bootstrap、初始化数据库、复制旧第三方凭据或激活旧五服务/Nacos候选。旧passed记录仅证明当时完成。

CF归档仅PVE，发布私钥仅220；源Mac数据及Git工作树保留。Mac外部探针继续停用，本期内部Lark不等于整机外部告警。本地检查用`python3 dell/scripts/validate_docs.py`，只校文档，不校服务恢复；新运行结果必须另有对象、时间、观察、退出状态和限制。
