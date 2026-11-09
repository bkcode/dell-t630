# 交付与恢复报告

更新：2026-11-09（Asia/Shanghai）。用户此前确认内存已重新插拔/更换且诊断通过；本次14:24自然重启后fresh核EDAC0、RAIDOptl、12running/3tpl与15targets UP。既有基础服务完成分范围核查，**不再把11/07的POST停机状态当当前现场**；完整物理根因、独立离线诊断与长期稳定性未因此自动签收。

本轮用户要求继续完成基础搭建，并选择先建PVE本机自动备份，明确**不迁移数据、不合并Nexus**。当日状态入口：[completion/20261109/README.md](completion/20261109/README.md)。Mac外部探针明确不需要，保持停用，移出当前与后续待办。

## 本次结果

- 12实例（11VM+1LXC）运行、3模板保留，43vCPU/85GiB；230/240各一且Java业务不部署，publisher fenced。221继续独立Nexus，220保持standby、没有31alias或Nexus栈。
- 200/201/210原UUID/ext4/rw、8容器healthy；Java两台JDK21.0.13可用、finger账号存在且无Java业务进程。没有重新登录数据库核全部账号/权限/内容，也没有重跑业务初始化。
- 221原2容器healthy；Penpot11healthy、原镜像/Git/worker基础就绪；NAS原UUID与OMV/SMB/Jellyfin基础正常。没有重做全部GAV/EULA、设计/素材、MCP、SMB读写矩阵或真实播放验收。
- Ops270原4容器healthy、systemrunning/failed[]、15/15targets UP、Prom/AM alerts空；textfile自动更新，内部Lark原unit active。未发Lark测试，不能宣称本boot重新验过通知端到端。
- PVE/Nexus/Penpot/OMV/Jellyfin/Grafana共6HTTP入口200；其中PVE自签TLS只验可达，不是证书认证签收。
- 上轮定位ifupdown2覆写forwarding后补3个owned guard；本次14:24自然重启后SHA、networking→bridge/ExecStartPost→pve-guests顺序与全forward0实际读回，已验证本次重启保持。原interfaces/routes/ACL和无host NAT不变。
- [空闲iperfserver停用](completion/20261109/idle-iperf-disabled.json)、5201关闭、包保留，未重启来宾或改网络。

11月8日初查的启动no-route/starting保留为历史，11月9日fresh基础健康不需要重装。新增本机自动备份首轮已验证并启用计划；规则后验和整个本期签收仍以[当日记录](completion/20261109/README.md)的实际结果为准，不以部分模块通过代签全部。多余资源仍须依赖核对。

## 新增本机自动备份：进行中

[PVE本机备份合同](infra/backup/pve-local/README.md)固定11项、排除220、CF档只留PVE，目录root700/归档日志状态600、最近3/每日7/每周4保留；旧21回退档保留。首轮固定11档已全部verified（zstd、tar/vma及SHA验证），原生任务OK、unit退出0；15:56审核后每日03:30计划已启用，合计19,747,582,801字节。证据：[首轮成功](completion/20261109/backup-first-success.json)、[计划启用](completion/20261109/backup-schedule-enabled.json)。 metadata/Lark白名单已有配套，无人工通知测试；新增Prom规则实际部署/加载状态见[当日记录](completion/20261109/README.md)，不提前签收。

这是snapshot/crash-consistent系统恢复点，不是数据库逻辑或跨VM事务一致性；本轮不恢复、不迁移，不签独立灾备/RPO/RTO。

## 证据与验收边界

[11/09核心](completion/20261109/core-audit.json)、[媒体](completion/20261109/media-audit.json)、[Ops](completion/20261109/ops-audit.json)、[PVE](completion/20261109/pve-audit.json)，以及[11/08forwardguard原修复](recovery/20261108/host-forwarding-restored.json)与[新备份合同](infra/backup/pve-local/README.md)。这些是带时间的基础运行证据，不能代替每个原用例的完整通过条件。

原38项26历史passed/12pending不强改；[清理验收](cleanup/acceptance.json)原9项历史通过保留，Nexus合并pending原因更新为用户暂缓迁移。6项原严格REC用例保持pending，分别说明用户报告/运行部分证据或未执行冷备/回退，不作为本轮基础恢复的额外阻塞门禁。

11/07 02:35:01完整验收、02:44:29最后PVE操作、UEFI0058/B1 SEL事件是历史节点；BMC时区、单条DIMM及物理关机唯一原因未独立完全确认。不能因本bootCE/UE0就承诺长期硬件无故障。

长期独立备份/RPO/RTO、整机灾备、生产SLO、真实电视/PS4/PS5/4K HDR/GPU仍未验。家用NAS不是正式唯一备份；CF归档仅PVE，publisher私钥仅220、禁止wholebackup220；源Mac数据和业务工作树保留。机内监控与T630同故障域，不提供用户不需要的Mac外部探测承诺。

OW完整规则仅本地保留，本轮不触/不上传或push其local-only分支。访问与后续人工操作见[运行手册](12-service-access-and-operations.md)、[人工操作手册](19-manual-operations.md)、[继续入口](10-resume-after-approval.md)。本次文档与状态在本地同步，Git实际结果见[交接](20-git-and-handoff.md)及交付证据；文档或Git通过不扩大为全部硬件、业务与灾备验收。
