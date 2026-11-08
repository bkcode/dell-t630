# 2026-11-08 基础服务恢复与受控清理

本轮用户范围：**检查并补齐现有基础服务、清理确认多余项；暂不迁移、不合并Nexus、不退役221。** 用户确认内存已重新插拔或更换并通过诊断；此为用户报告，助手另行核对当前启动内存/存储与服务状态，没有独立运行离线内存诊断或压力测试。

## 当前结果

- PVE于20:07:44启动，4×32GB、可用物理内存约125.78GiB；当前启动EDAC纠错/不可纠正计数均0。RAID1/RAID5 Optimal，5盘Onln，3存储active。[硬件摘要](hardware-summary.json)
- 12来宾已按原onboot顺序自然启动，3模板停止保留。源221仍独立19.31；220仍4CPU4GiB/19.30、无31alias或Nexus栈。没有部署Java业务或更新Penpot源码。[核心服务](core-services-audit.md)、[媒体工具](media-tools-audit.md)
- 正式/测试8数据容器、Nexus2、Penpot11、Jellyfin、Ops4健康，原盘UUID和已核镜像保持。界面/健康检查不等于数据库内容全量复验。
- 20:19:38监控15/15UP、Prom/AM无活动告警、内部Lark运行；未发送本轮通知测试。[Ops审计](ops-audit.md)
- 20:20:48新SSH与6个管理/应用入口通过。网关DNS19.1的UDP/TCP三主机A返回19.50/31/30，CF实际20241 ready200/2连接；未签公网originE2E或远端VPN新会话。[网络复测](host-network-postcheck.json)、[DNS/CF复查](network-CF-followup.json)

## 已补齐的项目

启动后仅vmbr0的IPv4/IPv6接口forwarding重新变为1。已读取本机ifupdown2代码确认：带IP的bridge在网络启动阶段自动写1，覆盖早先sysctl的全0设置。

经审查，在PVE新增3个受限文件：关闭转发脚本、仅vmbr0触发的if-up hook、原bridge ACL unit的ExecStartPost drop-in。执行后所有host接口forward=0；原管理interfaces SHA、路由与ACL保持一致，没有network reload、来宾/应用重启或迁移。[原因](host-forwarding-source.json)、[修复receipt](host-forwarding-restored.json)

已验证当前状态、生成shell语法、systemd原生解析与调用hook；**未再次重启宿主或重新上线网桥**来测试持久性，避免为验收中断现役服务。下次正常维护重启后应复查。

开机早期PVE指标投递失败，是Ops/QGA尚未按顺序就绪；随后timer自行成功，未清错误来伪造从未失败。数据/Java/工具首次no-route或starting同样随自动启动自然消失，没有重装或手动重启。

## 清理边界

[只读依赖审计](pve-cleanup-audit.md)确认没有额外实例、unused磁盘、快照或待应用磁盘。共享13.5GB artifacts ISO被10台VM配置/进程引用，21份受保护清理回退归档继续保留。

仅两份无配置/快照/进程FD引用的旧安装ISO，经[发行商SHA验证](unused-ISO-digests.json)确认为原版可重新下载介质，已执行精确清理，回收3,876,812,800字节（约3.61GiB）；见[执行receipt](unused-ISO-cleanup-receipt.json)。Debian12 LXC cache来源完整性尚未确认，存在身份文件名条目但未读取正文，**本轮保留**，不以文件名或mtime推断可删。

## 明确排除

用户明确**不需要Mac外部探针**，从现行方案和后续待办移除；历史代码与诊断记录仅保留。仅做[Mac任务不存在的只读核对](Mac-probe-not-required.json)，原plist与launchd任务均不存在；没有操作后台任务或读取通知凭据。内部Lark是同机告警，不能保证T630整机失效时外发，这是已说明限制，不新增外部探针任务。

不迁移数据、不合并/退役221、不wholebackup220、不导出发布key或CF备份、不新装Java业务、不更新Penpot版本、不执行真实交易/业务写入。长期独立备份、物理TV/PS、多路转码、生产SLO与完整数据恢复仍按既有范围另验。

最终20:34:09清理后复查见[最终验收](final-verification.json)：原12运行/3模板、15/15UP、Prom/AM无告警、EDAC无非零、全hostforward0、宿主failedunits空，仅共享artifactsISO保留。21归档本轮只核名字/元数据与未被清理脚本触碰，未重新读payload或复算SHA。
