> 文档状态（2026-11-08）：本页为阶段实施/技术记录，旧网段、角色数和通过结果按原时点解释。基础已恢复；本轮仅补齐与清理，用户暂不迁移/合并，Mac外部探针不需要。当前配置见[访问清单](../../../12-service-access-and-operations.md)，范围与恢复证据见[最新交接](../../../11-live-handoff.md)；旧初始化器不得重跑。

# SYS001 v2：唯一批准的NAS QA重试

状态：主AI明确批准一次新nonce执行，当前先原生Compose合并检查，再A/B1/B2/C与清理。旧轮3d7d910a5c6b4ae7906819363460ed20保持failed，已完整清理，真实NAS连续性保持；不追改旧结果。旧方案保留于PLAN-v1.md。

## v2仅变更测试就绪口径

保持同一缓存Jellyfin镜像、internal专用网络、512MiB memory/memory-swap、CPU0.25、PIDs128、原guard字节与实际unit/compose模板。**取消全部published ports**，不创建host listener，真实8096不动。合并配置原生检查只有一个QA服务、zero ports、only QA mount sources，再进入唯一新nonce。

A/C由固定QA容器内原生curl读取127.0.0.1:8096/health，连续三次HTTP200且Docker healthy才ready。不输出正文/随机key；同步保存running时PortBindings/net/health、memory.current/peak、pids.current/peak与cpu.stat。无字段就记unavailable，不能造峰值。

## 不变的对象和安全边界

仍为O_EXCL 4GiB loopfile、精确BACK-FILE的loop设备、新UUID/QA路径/run unit/project；拒真实磁盘、分区、by-id或真实2TiB UUID。真实guard `/usr/local/libexec/dell-nas-check-data` SHA5ba9fd7c…d01120fc，QA参数仅mountpoint/新UUID/minimum-gib1。生产默认1800不改，不复制假guard、不改生产unit/env/compose/OMV。PID1/guard与dockerd保持同mount namespace。

执行前MemAvailable≥1.5GiB/root available≥8GiB，执行中MemAvailable≥1GiB，真实OMV/SMB/Jellyfin unit PID、容器ID/PID/start time/Health、guard/unit/compose/env/OMV hash和三share既有合成样本每阶段保持。任何差异只停QA并报告。

## 唯一批准顺序

1. A：新4GiB loop挂载，原守卫真实exit0，在卷内新建空QA config/cache/media，原生内部HTTP3次200+Docker healthy。
2. B1：仅停QA，正常umount scratch；原guard必须exit1/data filesystem is not mounted，根盘暴露目录canary/完整树无变化，loop暂仍关联。
3. B2：仅detach该已核对QA loop，保留文件/UUID；QAunit start必须明确非零，20秒job管理边界，unit非active、无运行QA容器、根盘目录无应用回落写。没有host port，不能再用host连接失败作为断言。保存systemd Result/退出码、QA journal时间/级别/结构metadata，不读MESSAGE原文或现役日志。
4. 取消所有QA pending job，再把同文件恢复loop映射和同UUID mount，卷内canary保持，C重新内部3×200+healthy。
5. 只清理该nonce容器/network/unit/mount/loop/file，正常umount、无force/lazy，无prune。最终真实连续性仍保持。

A/C新版若仍失败，立即停止、清理并报告，不再重试、不升资源，由主AI决定专用VM。失败日志仅记录非秘密类别/退出metadata。QA本地失败信号与通知接入分开：不改生产监控、不发Lark/任何消息，通知送达不属于已验收内容。PVE/250/原Mac/真实RootMedia不操作。
