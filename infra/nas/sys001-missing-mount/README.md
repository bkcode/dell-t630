> 文档状态（2026-11-07）：本页为阶段实施/技术记录，文中“当前”、网段、角色数与通过结果以原执行时点为准。服务器现因UEFI0058内存错误暂停，Nexus合并已授权但未执行；当前配置入口见[访问清单](../../../12-service-access-and-operations.md)，恢复门槛见[最新交接](../../../11-live-handoff.md)。旧脚本、stage/commit或初始化步骤不得直接重跑。

# SYS001 专用NAS挂载缺失负测结果

已完成主AI批准的专用QA数据防回落范围，所有自身资源已清理，真实NAS连续性保持。权威汇总：`runtime-status.json`；这不是对真实2TiB媒体盘实施拔盘/卸载，也未验证QA失败通知送达。

最终nonce `b5b52c6b0565410ba9c510728ba13f54`，4GiB O_EXCL文件与BACK-FILE精确匹配loop，新UUID `498b2c5a-d912-4884-a9f9-9a460cd2b264`。复用已部署守卫原文件（SHA5ba9fd7c…d01120fc）和实际unit/compose模板，守卫字节与真实1800GiB容量默认值不改。QA仅以CLI minimum-gib1测试4GiB ext4，CPU0.25、512MiB memory/swap、PIDs128、internal network、零published ports；A观察内存峰132481024B/PIDs峰28，没有提高资源。

| 阶段 | 实测结果 |
| --- | --- |
| A | 原守卫exit0；固定QA容器内部原生HTTP连续3次200，Docker healthy，真实Zero PortBindings、仅QA挂载 |
| B1 | 仅停QA并正常umount scratch；同一原守卫exit1，reason为data filesystem is not mounted；暴露根盘目录树/canary不变 |
| B2 | 只detach唯一核对过的QA loop；systemctl start exit1，job result dependency，无QA运行、unit非active，pending jobs清空；0.416秒明确失败，非client timeout，20秒job边界 |
| C | 同文件/UUID/canary恢复后，经主AI一次条件controller纠正，内部连续3×200+Docker healthy；没有再次attach、换nonce或加资源 |
| 清理 | QA容器、network、unit、mount、loop关联、4GiB文件和nonce目录全部移除，无force/lazy/prune |

真实OMV PID824、SMB PID852、NAS unit PID1154、真实Jellyfin PID1308/完整ID/StartedAt以及guard/unit/compose/env/OMV hash、真实2TiB UUID、三共享保留样本SHA，在每阶段和最终完全一致。没有停/重建真实NAS服务，没有改其文件或挂载；PVE/250/原Mac未操作。

失败历史未覆盖：旧nonce因hostlocalhost就绪判据未过而failed并清理；第二轮初始native配置检查把字符串字节值与int直接比较导致false，外层未set-e使A先进入，此顺序偏差保留。随后记录原始类型并精确int规范化，native全true/exit0；runner已failclosed，失败precheck绝不调用phase的回归通过。

原C控制器在systemctl start返回后立即将旧exited判错，failed记录保留。Root基于启动不足1秒即SIGTERM143/OOMfalse、原guard passed/同UUID canary和静态逻辑，条件批准一次纠正；没有伪称捕获了原错误时的旧snapshot frame。修正只允许捕获的同id/StartedAt旧exited在≤15秒内过渡，新的退出/dead或任何OOM仍立即失败。修正运行实际记录0.434秒旧状态后正常running；3个相关反例通过，总9项本地测试。原始`restore.json`仍failed，成功是独立`resume-c.json`。

关键证据均在 `evidence/b5b52c6b0565410ba9c510728ba13f54/`：`prepare.json`、`b1.json`、`b2.json`、`restore.json`、`resume-c.json`、`cleanup.json`。数值类型/顺序异常见`native-merged-v2.json`与`native-merged-v2-normalized.json`；归因边界见`C-correction-basis.json`。

已实测的是guard/systemd非零与结构化journal时间/优先级/job result等**本地失败信号**；未为QA改生产监控或发消息，也未签收Lark送达。真实NAS unit及8096已有监控的整体状态由主AI另行核验。本目录不修改全局acceptance/plan，也不把保存文档或清理成功当作真实媒体拔盘/通知验收。
