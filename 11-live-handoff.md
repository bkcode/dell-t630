# 当前交接：基础已恢复，本轮不迁移

更新：2026-11-09，Asia/Shanghai。用户继续授权完成基础搭建，并明确先建PVE本机自动备份；内存现场处理/诊断通过由用户此前确认。**不合并Nexus、不搬数据、不退役221。** 以前短停合并许可保留为历史，不覆盖这次明确暂缓。

当日执行状态唯一入口：[11月9日交付记录](completion/20261109/README.md)。[11月8日恢复记录](recovery/20261108/README.md)为上轮历史。

## 已核事实与实际变更

- 12来宾自然onboot启动、3模板停止；15监控目标UP，Prom/AM无活动告警；主要6HTTP入口通过。盘UUID、容器镜像与健康按角色复核，不能扩写成全量内容/认证/外网E2E验收。
- 当前启动4×32GB/EDAC ce/ue均0，RAID1/5 Optimal/5盘在线；内存维修诊断是用户报告，助手未独立做离线诊断/压力测试。
- PVE桥转发启动漂移已由3个owned guard补齐；11月9日14:24自然重启后，SHA相同、networking→bridge/ExecStartPost→pve-guests实际顺序与全forward0已读回，不再仅为待验候选。管理interfaces/路由/ACL、无NAT边界保持。
- 本轮[空闲iperfserver已停用自启](completion/20261109/idle-iperf-disabled.json)、5201关闭，软件包保留，没有应用/来宾重启。
- 原15旧对象/6临时对象已在此前清理，本轮无多余实例或unused磁盘；只清确认无引用且发行商SHA一致的旧安装ISO，执行结果以恢复记录receipt为准。共享ISO、21回退档、来源不明LXC cache保留。

## 配置与业务边界

221仍独立19.31/原Nexus卷，220仍4CPU4GiB/主IP19.30、0Nexus容器；6CPU8GiB+31alias只在[目标架构](17-publish-artifact-consolidation.md)中，未应用。发布key只220，CF备份只PVE；不得整机备份220或以清理名义删除源221数据。

230/240各一，仅运行基础，无Java业务进程/自启；publisher仍fenced。Penpot保留实际ff1783e版本，用户指定的bkcode/penpot main是未来更新合同，本轮未取码/构建/升级。

## PVE本机自动备份交接

已安装新私有storage/native job，固定11项100/190/200/201/210/221/230/240/250/260/270，220排除、CF仅PVE，目录root700/归档日志状态600。03:30、最近3＋每日7＋每周4的原生保留策略，旧21档独立保留；合同见[本机备份](infra/backup/pve-local/README.md)。

**首轮成功、计划已启用。** 固定11档已全部verified（zstd、tar/vma及SHA验证），原生任务OK、unit退出0；15:56审核后每日03:30计划已启用，合计19,747,582,801字节。证据：[首轮成功](completion/20261109/backup-first-success.json)、[计划启用](completion/20261109/backup-schedule-enabled.json)。 新增Prom规则实际部署/加载状态统一见[当日记录](completion/20261109/README.md)，此处不提前签加载或真实通知送达；既有metadata与Lark白名单配套，无本轮人工外发。

本机snapshot不是应用逻辑/跨来宾一致性、独立目的地或恢复演练。本轮不恢复VM/导入数据，真实RPO/RTO与独立灾备继续待验。

## 告警与待办

用户明确不需要Mac外部探针，现行及后续不配置/恢复；只留内部Prometheus/Grafana/Lark。历史probe文件保留供追溯，不能因此创建恢复任务。同机告警不保证整机失联外发。

继续事项为基础补齐、已授权本机备份收尾及具体已审清理；未来迁移须用户另行恢复该任务，再fresh基线/冷备/唯一盘地址交接/原身份数据验证与回退。真实家庭设备、完整灾备与业务SLO仍未签收。OW完整规则只留本地，不触/不上传，不push local-only分支。

原11月7日02:35验收、02:44:29规划同步和随后UEFI0058记录保留在[硬件事故](cleanup/hardware/DIMM_B1-incident.json)，不改写历史。当前操作手册见[19](19-manual-operations.md)，逐机配置见[machines](machines/README.md)。
