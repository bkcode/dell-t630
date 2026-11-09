> **现行备份范围已变更**：用户随后仅保留正式数据库/Nacos配置自动备份。旧11实例整机job已关闭，历史归档保留；当前首轮、定时器与验收见[新交付](../20261109-prod-db-scope/README.md)。下文保留此前实施时点的成功/失败历史，不是重启旧job的授权。

# 2026-11-09 继续基础搭建：不迁移数据

本轮用户要求继续完成搭建，不迁移数据；已明确选择先搭PVE本机自动备份，独立目的地后续接入。Nexus220/221不合并、既有数据不导入/恢复覆盖、Java业务不启用、Mac外部探针不需要。OpenClash规则按用户选择只留本机，不随本次Git提交上传。

## 已完成复核和补齐

- [宿主审计](pve-audit.md)：今天14:24:03自然重启，12来宾/3停止模板、无失败单元、RAID1/5 Optimal、5盘在线、EDAC0。上一轮转发守卫在本次真实启动后仍全0，native顺序与文件SHA匹配。
- [核心服务](core-audit.md)、[媒体工具](media-audit.md)、[监控](ops-audit.md)：现有组件健康、UUID/资源/网络正确、15/15UP，无需重复安装。220仍4CPU4GiB/19.30，221独立19.31；Penpot实际ff1783e不升级main。
- [空闲测速服务清理](idle-iperf-disabled.json)：关闭PVE原生iperf3常驻和自启，5201关闭；保留软件包，未重启来宾/改网络。
- [PVE本机备份](../../infra/backup/pve-local/README.md)：首轮11项全部verified且原生任务OK/退出0，共19,747,582,801 bytes；[15:56计划启用回执](backup-schedule-enabled.json)确认每日03:30，最近3/每日7/每周4原生组合保留。
- [通知白名单已配套](backup-notify-whitelist-result.json)：只增加3个备份故障名及原AM匹配，沿既有Lark接收对象；必要重启仅native通知桥，AM同一容器热载，未发人工测试。
- [备份指标已接入](backup-metrics-installed.json)：保留原PVE/RAID指标与QGA通道，只增加只读状态/年龄/数量；不读归档，不新建listener或外部探针。

## 首轮失败与修正记录

初次CLI调用同步等待超过40秒被中断；随后第一server-run发现严格UMask与非特权LXC临时打包不兼容。保留[首次诊断](backup-first-attempt-diagnostic.json)、[临时目录修正](backup-staging-fix.json)、[后续诊断](backup-LXC-followup-diagnostic.json)及[正常取消后的thaw/锁核查](backup-failed-run-cancelled.json)。没有把失败任务当作通过。

同时50MiB/s对稀疏虚拟零块也限速，NAS2TiB会人为拖成很长窗口；已改原生低优先级串行并解除此逻辑零块限速，archive仍root700/600。新重试unit使用PVE默认临时权限，见[兼容修正](backup-native-compatibility-fix.json)、[重试启动](backup-first-run-retry.json)。

[首轮最终回执](backup-first-success.json)确认15:05:24–15:54:56共49分32秒，固定11档全部zstd/native验证且私有SHA已记录，原生任务OK、unit退出0；15:56:02通过完整门禁启用计划。仅清除本次旧失败unit标志，失败日志及PVE任务历史保留。未重跑或伪造失败记录。

## 边界

本地快照是同机恢复点，不是异机灾备或应用事务一致性承诺；不执行恢复、迁移或真实业务写入。CF档仅PVE；220禁止整机备份/发布key导出；旧21回退档保留。真实电视/PS、长期独立备份和业务SLO仍另行验收。具体文件/状态以本目录新证据时间为准。

通知桥原35项回归使用loopback假凭据/mock sender验证，无真实外发；最初沙箱拒绝本机临时监听，获准loopback后重跑，不降低测试门槛。备份指标46项离线测试、原生Prom规则8组与AM合成路由均通过。配置/合成路由校验不等于新的真实Lark送达验收。

## 最终状态与验收

- [首轮完整回执](backup-first-success.json)：11份约19.75GB（18.39GiB），归档root600/父目录root700；CF归档及其SHA没有离开PVE，220不在任务内。
- [启用回执](backup-schedule-enabled.json)：原生`dell-local-nightly`已enabled，snapshot、zstd2线程、串行来宾；同一私有namespace按3/7/4保留，首轮remove=0。后续日常保留尚未经历多个周期，原生prune先于自定义backup-end验证。
- [告警加载](backup-alerts-installed.json)：新增失败、成功超过36小时、任务关闭/状态无效三条规则，均for10m。原Prom容器精确ID SIGHUP，ID/image/PID/StartedAt/restarts保持，旧规则和接收对象保持，未发人工通知。
- [最后只读检查](final-verification.json)：12running/3templates、forward0、EDAC0、无失败宿主单元、5201关闭；15/15targetsUP，备份enabled/valid/success=1、running=0、verified=11，三规则healthOK/inactive，Prom/AM无活动告警。
- [网络/CF后验](network-audit.json)：CFready200/2连接、190双地址和网关单元正常，三DNS A正确，PVE/Nexus/Penpot/OMV/Jellyfin/Grafana六入口200；不扩签外网WG或Cloudflare公网origin。

当前阶段验收以[9项清单](acceptance.json)为准。原38项和6REC的完整恢复/业务/物理要求继续按原清单解释，不借本次首备扩签。独立目的地、实际恢复演练和RPO/RTO后续接入；Mac外部探针不需要。

- [逐机备份后复核](guests-post-backup.json)：9来宾、22应用容器healthy/restart0/OOMfalse，原UUID/IDs保持；220无Nexus/31alias、230240Java0。
- [下一次执行与目录权限](backup-next-run-and-permissions.json)：Asia/Shanghai，2026-11-10 03:30；新namespace最终26个文件全root600。
- [RAID后验指标](raid-post-backup-metrics.json)：2VD/5PD/BBU全optimal。
- [Git边界](git-scope-exclusion.json)：完整OW规则仅localexclude，非main历史，不纳入本次提交；精确index安全检查在提交前另做。

**本轮9/9通过。** 仅限当前基础搭建和本机备份；不表示原38项/6REC所有未来与恢复条件都已完成。
