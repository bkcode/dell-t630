# 当前交接：基础已恢复，本轮不迁移

更新：2026-11-08，Asia/Shanghai。用户已确认服务器恢复、内存重新插拔/更换且诊断通过；当前只授权检查补齐现有基础服务与清理确认多余资源。**不合并Nexus、不搬数据、不退役221。** 以前短停合并许可保留为历史，不覆盖这次明确暂缓。

完整执行与证据入口：[11月8日恢复记录](recovery/20261108/README.md)。

## 已核事实与实际变更

- 12来宾自然onboot启动、3模板停止；15监控目标UP，Prom/AM无活动告警；主要6HTTP入口通过。盘UUID、容器镜像与健康按角色复核，不能扩写成全量内容/认证/外网E2E验收。
- 当前启动4×32GB/EDAC ce/ue均0，RAID1/5 Optimal/5盘在线；内存维修诊断是用户报告，助手未独立做离线诊断/压力测试。
- PVE桥转发启动漂移已通过3个受限owned文件补齐，全部hostforward0；未改管理interfaces/路由/ACL、未network reload或重启来宾。下一次正常维护重启还需确认持久性。
- 原15旧对象/6临时对象已在此前清理，本轮无多余实例或unused磁盘；只清确认无引用且发行商SHA一致的旧安装ISO，执行结果以恢复记录receipt为准。共享ISO、21回退档、来源不明LXC cache保留。

## 配置与业务边界

221仍独立19.31/原Nexus卷，220仍4CPU4GiB/主IP19.30、0Nexus容器；6CPU8GiB+31alias只在[目标架构](17-publish-artifact-consolidation.md)中，未应用。发布key只220，CF备份只PVE；不得整机备份220或以清理名义删除源221数据。

230/240各一，仅运行基础，无Java业务进程/自启；publisher仍fenced。Penpot保留实际ff1783e版本，用户指定的bkcode/penpot main是未来更新合同，本轮未取码/构建/升级。

## 告警与待办

用户明确不需要Mac外部探针，现行及后续不配置/恢复；只留内部Prometheus/Grafana/Lark。历史probe文件保留供追溯，不能因此创建恢复任务。同机告警不保证整机失联外发。

继续事项仅为基础维护和具体已审清理；未来迁移须用户另行恢复该任务，再fresh基线/冷备/唯一盘地址交接/原身份数据验证与回退。真实家庭设备、完整灾备与业务SLO仍未签收。

原11月7日02:35验收、02:44:29规划同步和随后UEFI0058记录保留在[硬件事故](cleanup/hardware/DIMM_B1-incident.json)，不改写历史。当前操作手册见[19](19-manual-operations.md)，逐机配置见[machines](machines/README.md)。
