# 当前实施进展

更新：2026-11-07（Asia/Shanghai）。**当前暂停于硬件恢复门禁，不能宣称服务正在运行。** 用户控制台UEFI0058停在POST，先前SEL记录DIMM_B1多位不可纠正错误及correctable阈值超限；BMC显示时间时区未核，尚未隔离到具体模块/槽位/通道或证明物理关机唯一根因。见[事故记录](cleanup/hardware/DIMM_B1-incident.json)。

最后完整服务验收为**02:35:01+08**，最后成功PVE操作为**02:44:29+08**。后续截图与10:15左右管理连接失败是不同证据，不能把旧通过续写成当前live健康。本轮在本地同步文档、规则和暂停状态，编写人工手册并进行Git交付，没有远程修改服务器；Git实际结果见[交接记录](20-git-and-handoff.md)及交付证据。

## 最后成功验收基线

| 领域 | 已有证据证明的历史结果 | 证据 |
| --- | --- | --- |
| 角色与资源 | 12角色（11VM+1LXC），43vCPU/85GiB；230/240各一，3模板9001/9010/9011；15旧对象及6临时对象已归档清理 | [最终检查](cleanup/final-live-check.json)、[清理验收](cleanup/acceptance.json) |
| 网络 | 19/24经190，PVE21.22仅管理/L2、宿主旧NAT/forward撤除；WireGuard10.66.66/24路径与角色ACL已验 | [network19验收](network19/audit/network19-acceptance.json)、[VPN验收](network19/wireguard/full-access-verification.json) |
| fish与模板 | 9guest+3模板fish4.0.2-1，默认Bash；先candidate QA再替换原模板，机器/hostkey/DockerID独立 | [fish](cleanup/fish/runtime-status.json)、[QA](cleanup/fish/template-QA-summary.json)、[替换](cleanup/fish/core-template-replacement.json) |
| Java | 当前用户范围不部署业务；230/240仅运行基础，publisher fenced；9011为唯一Java验收模板 | [范围](plan.json)、[模板](network19/java-template/clone-evidence.json) |
| 数据 | 200/201正式与210测试的实例/账号/namespace/网络隔离、认证、持久化与受控恢复曾验；正式业务空库 | [数据](evidence/implementation/data-deployment-acceptance.json)、[恢复](infra/backup/full-snapshot-restore/runtime-status.json) |
| Nexus | 221原应用49GAV/234主制品、账号/EULA及重建恢复曾验；220仅standby，无alias31或Nexus运行栈 | [重建](infra/nexus/rebuild-acceptance-result.json)、[准备读回](cleanup/nexus/preparation-readback.json) |
| Penpot/NAS | Penpot原3设计/971原媒体保护及新身份、MCP与监督恢复曾验；NAS软件/权限/合成DirectPlay与隔离缺挂载保护曾验 | [Penpot](infra/penpot/application/acceptance-summary.json)、[NAS](infra/nas/runtime-status.json) |
| 监控 | 清理后10guest+5Ops共15targets曾UP，内部Lark已验并启用；Mac外部探针按用户选择停用 | [维护结束](cleanup/maintenance-ended.json)、[10节点](cleanup/monitoring/ten-role/execution-status.json) |

## 尚未执行

Nexus合并已经获得[明确短停维护授权](cleanup/nexus/maintenance-authorized.json)，迁移仍未开始，助手未执行本次停源/重启/移盘/IP交接。当前不再等待同项用户授权；要先处理硬件并fresh确认221/220状态、冷备和回退点。最后验收时221在运行，但现在不可现场确认其状态。

[原38项](acceptance.json)保留26历史passed/12future/manual pending；当前清理10项保留9历史passed/1Nexus pending，另新增6恢复门禁均pending。详见[验收](cleanup/acceptance.md)与[恢复入口](10-resume-after-approval.md)。

## 历史与限制

旧四个10.63私网、三正式Java节点、五服务E2E/发布回退、17targets等有原阶段真实证据，但已被后续network19及不部署Java业务的范围覆盖，不作为现役配置。原中间失败不追改为一直成功。

当前仍无长期独立备份调度、获批RPO/RTO、整机灾备或业务SLO；真实电视/PS4/PS5/4K HDR/GPU与混合负载未验。机内监控与T630同故障域，整机停机可能同时失去通知；Mac外部探针不因本次事故自动恢复。
