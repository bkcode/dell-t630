> 文档状态（2026-11-07）：本页为阶段实施/技术记录，文中“当前”、网段、角色数与通过结果以原执行时点为准。服务器现因UEFI0058内存错误暂停，Nexus合并已授权但未执行；当前配置入口见[访问清单](../../12-service-access-and-operations.md)，恢复门槛见[最新交接](../../11-live-handoff.md)。旧脚本、stage/commit或初始化步骤不得直接重跑。

# 删除脚本只读复核

时间：2026-11-07T02:04:15.125562+08:00。文件SHA256 `4afec6cc25760e444063d1a74b1c284f998efacb15538eed2c31cb1e86598db6`，当时51行。**本agent只读/AST提取，未运行dryrun或execute，未host/guest写。** 根任务的dryrun大档SHA进度不等于本agent执行。

结论：在已完成DAG、无真实PVE/qcow快照、无pending disk/opaque设备引用事实仍成立，以及root独占PVE写的本轮窗口中，未发现阻断级P1。

- 行5 exact15 ID/name allowlist正确，104先于103；没有221/100/220、任何保留业务或核心9001/9010/9011。旧102→9000当前已知是独立卷，不要求父先后；103→104两类依赖严格子先父。
- 行37–40仅选trusted backupmanifest verified记录；要求zstd/VMA全档验证标记，现场重算完整archiveSHA并核size、root权限/同目录；再核原qmconfigSHA、name、stopped、无lock/protection。这使此前producer的zstd/VMA校验能通过未变archive SHA链继承；不能称脚本自己重新解压/vma，也不等于restore实演。
- 行45–47每步再读cfg完全一致与stopped，并fresh检查其它当前cfg的精确卷/linkedclone前缀、103的104conf不存在、LVMthin origin后代不存在。当前唯一硬backing103/104与thin谱系均覆盖；DISK regex实际测试可匹配scsi/ide/virtio/unused/EFI/TPM，不存在误转义导致空guard。
- 行48仅native`qm destroy VMID --purge1`，没有skiplock、force、destroy-unreferenced或手工rm/LV通配操作。shared ISO被排出data磁盘集合，且没有任何ISO路径删除动作；PVE对象生命周期负责本VM卷，公共ISO保留。
- 行49每个删除后核conf消失再更新PVE-only report，最后才宣称exactcleaned，未自动处理Nexus221。backupworker本身也硬排100/220，源running会拒绝而非擅自stop；不会绕过Nexus维护审批拒绝。

非阻断限界：

1. fresh dependencyguard只扫描其它VM当前顶层cfg的disk字段与thin origins，没有重新枚举其它VM snapshot/pending/CT挂载/args或未注册qcow header。当前完整审计这些均无风险引用，故不要求另起全新测试；本次后不得把这个脚本当任意未来拓扑的通用安全删除器。若并发产生新disk/snapshot/clone引用，必须停并先新审，不能只相信旧DAG。
2. CDROM过滤同时排除了cloudinit引用；当前所有候选cloudinit唯一、共享只有已保护ISO，不构成当前P1。未来若有跨VM共享CI/特殊media配置，应显式复核而非照搬判断。
3. dryrun行44在dependencyguard之前返回，输出名称准确为backup/config preflight，不代表103等freshguard已实际跑通；真正execute会在各步立即检查。若中途guard拒绝，已完成的前序删除不会自动复活，依据PVE-only备份恢复，由root决定，不blindretry或跳锁。

仅给本轮15候选审查结论，Nexus221审批仍pending，不含源221清理；220publisher私钥不备份/导出，不对核心模板/保留业务盘发新生命周期命令。
