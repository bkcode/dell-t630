# 当前交接：硬件维修前暂停，Nexus 合并尚未执行

更新：2026-11-07，Asia/Shanghai。**用户已明确暂停服务器工作，本期只整理文档、编写人工手册并提交Git。硬件处理完并收到恢复指令前，不执行远程检查、停服、迁盘或部署。**

## 当前状态与证据

| 时间/事实 | 可确定的结论 | 限制 |
| --- | --- | --- |
| 11月7日02:35综合验收 | 12运行实例、3停止模板、监控15/15UP | 是最后成功验收快照，不是当前实时状态 |
| 02:44:29最后成功PVE操作 | 读取实例状态并同步宿主规划文件 | 未执行物理宿主关机、重启或Nexus迁移 |
| 09:32起连接检查失败 | PVE管理与虚拟网关不可达 | 无法单凭网络失败确定关机时刻/原因 |
| 用户iDRAC截图：PowerOff与B1 SEL错误 | 曾显示整机关机，B1有多位/纠错率超限事件 | BMC时区未核，不能直接对齐00:02:38与北京时间 |
| 用户开机后控制台：UEFI0058 | 固件因不可纠正内存错误停在F1/F2提示，未正常进入PVE | 当前截图未直接点名插槽；B1定位来自此前SEL |
| 用户决定后续处理硬件 | 服务器操作暂停，合并许可保留 | 内存条、接触、插槽/通道尚未隔离确诊 |

证据：[最后验收](cleanup/final-live-check.json)、[最后规划同步](cleanup/PVE-plan-synced.json)、[硬件事件](cleanup/hardware/DIMM_B1-incident.json)、[最后连通性](cleanup/hardware/resume-connectivity-20261107.json)。

## 保留的部署合同

- **12个实例（11VM+1LXC）+3份模板**；完整名称、IP、CPU/RAM与作用见[01清单](01-current-state.md)与[plan](plan.json)。资源配置总额43vCPU/85GiB；如维修减少内存，必须重算预算，不能自动启动全部来宾。
- 正式230、测试240各1，无Java业务；测试五服务已停止/禁自启。Publisher仍fenced，不发布新Nacos dataId、不activate旧JAR；9011为唯一无业务Java验收模板。
- 旧15对象及临时9040–9045已受保护备份后删除；仅保留9001/9010/9011。不要重放destroy或模板替换流程。
- fish4.0.2已装190/200/201/210/220/221/230/240/260及3模板；root/ub默认Bash，publisher原shell保持；100/250/270/PVE排除。
- Docker模板保留overlayfs/containerd-store/live-restore=true；Nexus等应用VM的classic-overlay2为角色特定设置，不能覆盖模板。
- PVE21.22只管理/L2；190WAN21.23/LAN19.1负责路由、DNS/DHCP；OW19/24经21.23，无宿主应用NAT。VPN10.66.66/24已受信，peer各/32。
- 最后验收为10node+5Ops=15targets；Nexus221独立抓取，220只有30:9100。内部Lark配置保留，Mac外部探针停用，整机故障不保证机内通知能外发。

## Nexus 合并的准确进度

短时停机维护**已获用户明确授权**，无需重复确认同项许可；原拒绝记录保留作历史。本轮因硬件与用户暂停而未执行，不再把授权写成pending。

| 项目 | 已完成 | 尚未执行 |
| --- | --- | --- |
| 目标220 | Docker/Compose/classic-overlay2、原两镜像、root私有standby最小材料 | 改6CPU8GiB、31alias、挂Nexus盘、安装/启动现役Nexus |
| 源221 | 原身份、独立数据盘与历史数据验收 | 迁移停服、冷备、关机、磁盘所有权移交、退役 |
| 网络/监控 | helper具备显式多IP合同支持；10角色监控已验 | 220双IP ACL/IPAM配套，监控10→9、15→14 |

目标方案：220保留hostname/管理主IP19.30，Nexus继续19.31:8081服务alias，原UUID `239dc45a-b1f3-408b-a8ef-7afa77b52204` 数据盘唯一移交。220当前配置仍4CPU4GiB；不是已合并，也不计成11实例。

恢复前须读[最小恢复检查](cleanup/nexus/resume-preflight.md)、[本地复核](cleanup/nexus/local-resume-review-20261107.md)、[人工手册](19-manual-operations.md)。本地target.py比先前上传版有更新，须fresh SHA/CAS。`quiesce221.py`不存在；不能调用虚构工具。prepared stage不能重跑；mount/commit部分执行须按journal/manifest先核现场。验证器原49GAV/234主件若有合法新增，必须扩新基线，不能删数据凑通过。

## 恢复执行的门槛与顺序

1. 用户完成硬件处理并指示恢复。保留SEL/Lifecycle与维修记录，内存诊断通过，确认有效容量、无新增不可纠正内存错误。
2. 严格SSH恢复，核启动ID/时间、RAID/文件系统/数据盘及各服务健康；不清日志、不把F1或一次成功启动当修复证明。
3. 冻结源Nexus与目标发布机新鲜基线；创建新维护窗。仅按最小变更停源、冷备校验、唯一原盘/IP所有权交接。
4. 新220验证原数据SHA、身份/EULA/权限、默认源IP30、发布key元数据、双IP ACL、网络入口和监控；全部通过再退221。
5. 新的验收记录和plan/docs一致后解除本次维护静默。失败按原盘回退，不能双写或恢复旧空库覆盖新数据。

## 凭据、归档与交接

- 严格SSH用ub/客户端key与本机私有known_hosts；不关闭hostkey检查、不复制SSH身份伪装221。
- 21份清理归档仅PVE `/mnt/pve/store/dell-artifacts/cleanup-backups-20261107`，root700/files600；已校完整性，不代表所有旧VM逐一恢复。不能当异机灾备。
- CF备份仅PVE，publisher私钥仅220，禁止220整机备份/快照导出；Nexus未来源221冷备亦仅PVE受保护存放。
- Git不包含private和密码/归档。新机器克隆后需安全交接凭据与受信指纹，见[Git交接](20-git-and-handoff.md)。本轮不改全局记忆。
