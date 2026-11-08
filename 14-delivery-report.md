# 交付与恢复报告

更新：2026-11-08（Asia/Shanghai）。用户确认内存已重新插拔/更换且诊断通过；当前boot EDAC CE/UE0、RAIDOptl。既有基础服务已恢复并完成分范围核查，**不再把11/07的POST停机状态当当前现场**；完整物理根因、独立离线诊断与长期稳定性未因此自动签收。

本轮用户范围为检查补齐基础服务并清理可确认多余项，明确**暂不迁移**。Mac外部探针明确不需要，保持停用，移出当前与后续待办。

## 本次结果

- 12实例（11VM+1LXC）运行、3模板保留，43vCPU/85GiB；230/240各一且Java业务不部署，publisher fenced。221继续独立Nexus，220保持standby、没有31alias或Nexus栈。
- 200/201/210原UUID/ext4/rw、8容器healthy；Java两台JDK21.0.13可用、finger账号存在且无Java业务进程。没有重新登录数据库核全部账号/权限/内容，也没有重跑业务初始化。
- 221原2容器healthy；Penpot11healthy、原镜像/Git/worker基础就绪；NAS原UUID与OMV/SMB/Jellyfin基础正常。没有重做全部GAV/EULA、设计/素材、MCP、SMB读写矩阵或真实播放验收。
- Ops270原4容器healthy、systemrunning/failed[]、15/15targets UP、Prom/AM alerts空；textfile自动更新，内部Lark原unit active。未发Lark测试，不能宣称本boot重新验过通知端到端。
- PVE/Nexus/Penpot/OMV/Jellyfin/Grafana共6HTTP入口200；其中PVE自签TLS只验可达，不是证书认证签收。
- 定位ifupdown2在带IP桥写forwarding1覆盖早期sysctl的问题；新增3个owned guard文件后双栈全0。interfaces/routes/ACL保持，无network reload、guest restart或数据迁移；本次未另重启验新guard持久性。

首轮部分目标尚未自然开机，出现no-route/starting和旧周期告警；随后全部恢复。首轮记录保留，没有把启动队列判作需重新部署的故障。本次未发现必须额外补装或重启的基础缺项，多余资源仍以依赖核对后明确无用为清理条件。

## 证据与验收边界

[核心基础](recovery/20261108/core-services-audit.json)、[媒体工具](recovery/20261108/media-tools-audit.json)、[Ops](recovery/20261108/ops-audit.json)、[宿主网络后检](recovery/20261108/host-network-postcheck.json)、[forwardguard修复](recovery/20261108/host-forwarding-restored.json)、[资源盘点](recovery/20261108/pve-cleanup-audit.json)。这些是带时间的基础运行证据，不能代替每个原用例的完整通过条件。

原38项26历史passed/12pending不强改；[清理验收](cleanup/acceptance.json)原9项历史通过保留，Nexus合并pending原因更新为用户暂缓迁移。6项原严格REC用例保持pending，分别说明用户报告/运行部分证据或未执行冷备/回退，不作为本轮基础恢复的额外阻塞门禁。

11/07 02:35:01完整验收、02:44:29最后PVE操作、UEFI0058/B1 SEL事件是历史节点；BMC时区、单条DIMM及物理关机唯一原因未独立完全确认。不能因本bootCE/UE0就承诺长期硬件无故障。

长期独立备份/RPO/RTO、整机灾备、生产SLO、真实电视/PS4/PS5/4K HDR/GPU仍未验。家用NAS不是正式唯一备份；CF归档仅PVE，publisher私钥仅220、禁止wholebackup220；源Mac数据和业务工作树保留。机内监控与T630同故障域，不提供用户不需要的Mac外部探测承诺。

访问与后续人工操作见[运行手册](12-service-access-and-operations.md)、[人工操作手册](19-manual-operations.md)、[继续入口](10-resume-after-approval.md)。本次文档与状态在本地同步，Git实际结果见[交接](20-git-and-handoff.md)及交付证据；文档或Git通过不扩大为全部硬件、业务与灾备验收。
