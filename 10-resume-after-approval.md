# 恢复后的继续操作入口

更新：2026-11-09。现行自动备份**仅限VM200正式MySQL数据库与完整Nacos外部元数据库**；当前唯一非系统库为`nacos_prod`（12张BASE TABLE、全InnoDB），正式业务schema尚未创建。新增非系统库不在显式白名单即拒绝并告警，需审核更新策略，不能静默漏备。PVE落点`/mnt/pve/store/dell-artifacts/prod-db-backups`，目录root700/文件600；首轮逻辑SQL gzip **3,301 bytes**已完成CRC/传输SHA校验、DDL锁释放和guest暂存清理，service退出0；03:30（Asia/Shanghai）timer已enabled，下一次2026-11-10 03:30，GFS最近3/每日7/每周4。见[新首轮与timer回执](completion/20261109-prod-db-scope/first-success-and-timer-enabled.json)及[当前中央入口](completion/20261109-prod-db-scope/README.md)。 当前规则/指标和后续操作统一从新中央入口继续，旧9/9与全机方案仅历史，不因旧成功自动启用。 本次仅[该3301B Nacos小档已在VM210临时隔离恢复](completion/20261109-prod-db-restore/README.md)，完整业务恢复/RPO/RTO/异机DR未签，不表示恢复覆盖现役或Nexus回退已执行。

11月8日背景：用户确认内存重新插拔/更换及诊断通过，当前boot EDAC CE/UE0、RAIDOptl，既有基础服务恢复。12实例/3模板、15targets UP及6HTTP200已有分范围证据，见[本次后检](recovery/20261108/host-network-postcheck.json)；不是11/07 POST仍不可达状态。

当前已补齐既有基础服务与仅正式数据库/Nacos逻辑备份、盘点可确认多余项，用户明确**暂不迁移**。Nexus仍221独立服务，220仍standby；历史“短时停机合并”授权保留，但最新指令下不执行停源/冷备迁移/移盘/IP交接或源221退役。只有将来用户明确恢复迁移任务后，才重新安排fresh基线和维护。

## 现在继续时先做什么

1. 对照[plan](plan.json)、[人工手册](19-manual-operations.md)与本次各角色审计，判断是否有具体缺项。现有证据未发现需要重新安装或部署的基础服务。
2. 启动队列中的瞬时no-route/starting已自然恢复；不要重跑installer、初始化、模板封版、旧destroy或业务bootstrap来“补齐”。
3. 230/240各一只保留Java运行基础，旧业务与publisher baseline不激活；不能把旧E2E证据当重新上线指令。
4. 对任何新发现的清理候选先核依赖、数据与回退点，未确认无用不删除；CF归档仅PVE、私钥仅220、不wholebackup220。
5. Mac外部探针用户明确不需要，保持停用并从当前/后续待办移除；不申请隐私权限、安装外部探测任务或发送测试消息。

## 原严格恢复清单的证据边界

| ID | 11/08已有证据 | 原完整用例状态 |
| --- | --- | --- |
| REC-HW-001 | 用户报告维修与诊断通过，当前EDAC0/RAIDOptl/基础运行正常 | pending/partial：未独立收完整离线报告、根因及长期观察 |
| REC-BAK-001 | 原受保护归档保留，本次没有合并冷备/隔离恢复 | pending：随迁移用户暂缓，不是当前补齐缺项 |
| REC-DATA-001 | 数据盘UUID与健康元数据、无Java业务 | pending/partial：未全量账号/内容/制品/素材复验 |
| REC-NET-001 | 基本路径与6HTTP200；forwardguard全0、原配置/路由/ACL不变 | pending/partial：11月9日guard跨重启已复核，VPN/全部正反矩阵未完整重跑 |
| REC-OBS-001 | 15UP、无当前Prom/AMalerts、textfile新、Lark原unit active | pending/partial：没有通知测试；Mac外部明确不需要 |
| REC-ROLL-001 | 未执行Nexus交接/回退/退役 | pending：用户暂缓迁移，不以基础恢复代签 |

这些原严格用例见[结构化验收](cleanup/acceptance.json)，不作为本轮基础服务恢复的新增阻塞门禁。历史38项状态不变，原验收定义不被一次健康GET或文档更新替代。

## 硬件和操作限制

11/07 UEFI0058/B1事故及02:35完整验收、02:44:29最后PVE操作保留为历史。内存维护的精确对象、独立诊断报告与根因没有在此完整复证；不自动按F1、清SEL或以CE/UE0承诺长期硬件稳定。

本次宿主仅补3个forwarding guard文件，修复ifupdown2带IP桥覆盖sysctl的偏差，无network reload/guest restart。将来新网络或迁移仍按其具体窗口处理，不重放本次非幂等安装脚本。

本地文档用`python3 scripts/validate_docs.py --json`检查，Git结果见[交接](20-git-and-handoff.md)。Git或文档通过不等于完整硬件、业务或灾备验收。
