# 硬件发现、历史UEFI0058与恢复观察

更新：2026-11-09（Asia/Shanghai）。**当前继续完成基础搭建并按用户最新范围仅备正式数据库/Nacos配置，不迁移数据。** [本轮PVE审计](completion/20261109/pve-audit.json)于14:42–14:44读取14:24自然重启后的4×32GiB、EDAC0、RAIDOptl和12running/3tpl；上一轮guard已实际跨重启保持全forward0。用户此前确认内存重新插拔/更换及诊断通过，与助手只读短期计数分别记录，没有独立离线诊断或压力测试。UEFI0058/B1保留为历史；本页本次仅本地同步，无新远程动作。

## 1. 历史内存事件与证据强度

原始事故记录：[DIMM_B1-incident.json](cleanup/hardware/DIMM_B1-incident.json)。

| 证据 | 能确认什么 | 不能直接推导什么 |
| --- | --- | --- |
| 11月7日用户iDRAC recent-events/SEL截图 | B1曾有multi-bit memory error及correctable rate exceeded事件 | 不能单靠recent events证明具体关机机制，或锁定模块/接触/插槽/通道/控制器中的唯一根因 |
| 11月7日10:23记录的UEFI0058截图 | 当时固件报告不可纠正内存错误、停在正常OS启动前 | 截图未点名槽位；B1定位来自此前SEL，不能混成同一现场结论 |
| 11月7日09:32后不可达及用户暂停 | 当时PVE/GW未恢复可信连接，停止服务器工作 | 是历史故障阶段，已由11月8日恢复证据更新；不再断言当前不可达 |
| 11月8日用户确认重新插拔/更换并诊断通过 | 用户已完成现场处理并允许检查补齐/清理 | 助手没有独立执行或旁观离线诊断，不能补造具体更换序列号、步骤或测试报告 |
| [20:12硬件摘要](recovery/20261108/hardware-summary.json) | 同host key严格SSH成功、内存inventory/当前EDAC及RAID读数 | 当前boot CE/UE0不证明永久修复或异常期间应用数据全部正确 |

BMC历史显示时间`Sat Nov07 2026 00:02:38`的时区未核，不直接与本地09:32或OS时间做因果排序。原B1事故按T630手册关联CPU2/channel0的分析留在证据中；现场处理前后的具体替换记录应由用户维护，不凭恢复可达反推当时唯一坏件。

## 2. 本轮内存、存储与范围

11月9日[PVE审计](completion/20261109/pve-audit.json)boot时间14:24:03、采集14:42–14:44，MemTotal约125.781GiB，4个MC的CE/UE全0，当前boot内核不可纠正/MCE/EDAC/FSIO分类0；两VD Optl、5盘Onln、BBUOptimal。A1/A2/B1/B2各32GB保持。该boot被动读取，不是agent触发reboot，也不单独证明长期稳定；以下11月8日摘要作为上一轮证据保留。

主AI的[硬件摘要](recovery/20261108/hardware-summary.json)采于2026-11-08 20:12:15 +08，PVE记录本boot开始于20:07:44：

- DIMM inventory为A1、A2、B1、B2各32GB，共128GiB标称容量；DDR4、配置速度2133MT/s。OS报告`memory_bytes=135056269312`，与DIMM标称容量不是同一统计口径；规划保守预算125GiB保持。
- 当前boot可读EDAC控制器/DIMM CE、UE及noinfo计数全部0；这只是该boot和采样时点，不能据此清除历史SEL或签认长期稳定。
- SSD RAID1与HDD RAID5两VD均Optl、RW、Consist=Yes；本轮没有rebuild、改阵列参数、强制Online、刷固件或清日志。
- BMC工具缺失，本轮未fresh下载SEL；没有压力测试或代理物理DIMM操作。用户报告诊断通过与OS只读观察分别记录。

保留12来宾43vCPU/85GiB的预算，不扩大资源；若未来有效内存下降，先重新核预算和最低8GiB宿主预留。用户明确暂不迁移，所以Nexus221仍独立、220保持原准备状态；硬件恢复不自动触发原合并窗口，也不新开Java业务。

## 3. 平台基线与本轮限制

初始盘点：[pve-audit-2026-11-05.json](evidence/pve-audit-2026-11-05.json)。

| 项目 | 保留基线或本轮观察 | 限制 |
| --- | --- | --- |
| 型号 | Dell PowerEdge T630 | 未宣称已重新审计所有固件/部件 |
| CPU | 双Xeon E5-2680 v4，28物理核心/56线程，2NUMA | 43vCPU配置不等于43物理核或吞吐保证 |
| RAM | 本轮4×32GiB，EDAC CE/UE0；125GiB保守预算 | 物理修复/诊断由用户确认，长期稳定继续观察 |
| PVE | 初始pve-manager8.4.0、kernel6.8.12-9-pve；本轮可信SSH恢复 | 初始版本不是本轮所有包/固件版本复查 |
| 网卡 | eno1历史记录1Gbps全双工；本轮管理/服务入口可达 | 不据此承诺吞吐、零丢包或链路压力验收 |
| 存储 | H730 SSD RAID1与HDD RAID5当前Optl；应用挂载分项复核 | 控制器Optimal不替代逐文件/数据库一致性与备份恢复 |

## 4. RAID恢复历史与未确诊项保留

2026-11-06 05:17证据[raid-recovered.json](evidence/implementation/raid-recovered.json)记录控制器/VD0/VD1 Optimal，SSD RAID1约446.6GB、HDD RAID5约7.276TB，五盘Onln；槽32:3重建有结束和DEGRADED→OPTIMAL事件，当时BBU Optimal/100%。11月8日的新读数再确认两VD Optl，不再写成“仍48%重建”或“当前阵列未知”。

槽32:3曾无法访问/缺失、Offline并自动重建，盘、固件、链路、背板或供电的原根因没有被本次内存处理单独确诊。smartctl历史记录SAS槽32:2有11个重分配块，非Dell认证SSD兼容提示也保留；PERC media count与SMART计数不同，不能互相抹去。控制器历史时钟曾约差8小时，不用来校准本次BMC事件。

PERC板载缓存ECC与系统DIMM_B1属于不同层；缓存correctable/uncorrectable为0不能否认旧SEL多位错误。完整历史见[hardware-network-audit.json](evidence/implementation/hardware-network-audit.json)、[raid-controller.json](evidence/implementation/raid-controller.json)。本轮不删除或改写原JSON，不重复rebuild/force Online以掩盖异常。

## 5. 网络持久性已复核与本轮基础观察

当前架构仍为PVE21.22管理/L2，vmbr19无hostIP，独立190 WAN21.23/LAN19.1提供路由/DNS/DHCP/filter；190无NAT，OW21.1做互联网NAT，旧10.63四桥及PVE DNAT不恢复。

11月8日发现vmbr0 IPv4/IPv6 per-interface forward为1，主AI仅补3个owned文件并即时收敛，未reload网络，见[原回执](recovery/20261108/host-forwarding-restored.json)。**11月9日已实际读回跨重启持久性：**guard三个SHA与原回执相同，networking14:24:12→bridge/ExecStartPost成功14:24:15→pve-guests14:24:18，IPv4/IPv6 all/default/全部接口forward均0，唯一nft仍bridge ACL、无host NAT、vmbr19无hostIP。证据见[本轮PVE审计](completion/20261109/pve-audit.json)，不再仅称未验证候选。没有为本次文档同步再次重启或改网络。

- [11月9日核心审计](completion/20261109/core-audit.json)，14:42:56–14:43:40：三盘原UUID/rw、8容器healthy/RestartCount0，五台NTP同步/无failed，230/240无Java进程/旧五unit非enabled。
- [11月9日媒体审计](completion/20261109/media-audit.json)，14:43:07：221独立Nexus、250定制Penpot、260 NAS原UUID/镜像及基础健康保持；220没有移盘/加alias/启动Nexus。内容、认证写入及Penpot main更新未执行，实际ff提交保留。
- [11月9日Ops审计](completion/20261109/ops-audit.json)：15/15 targets UP、无活动告警、Lark unit active；没有新消息测试，不签本boot供应商送达。
- [11月8日宿主后检](recovery/20261108/host-network-postcheck.json)的6入口200保留作当时范围；11月9日PVE/媒体/Ops分别复核管理与原健康入口。自签HTTPS可达性不等于证书身份校验。
- [空闲iperf清理](completion/20261109/idle-iperf-disabled.json)，14:45:56：确认无测试连接后stop/disable常驻server，5201关闭，包保留；无网络改变或应用/来宾重启。
- [网络/CF后续核查](recovery/20261108/network-CF-followup.json)：直接向19.1用UDP/TCP查询，Penpot/制品/发布三A分别为19.50/31/30；CF实际20241端口ready200、连接2。先前网关OS resolver经OW得到Fake-IP和CF误用2000端口探针的失败原样保留，不作为服务故障；未验证Cloudflare公网origin全链路。

同机Ops与GW共享T630故障域，整机无法运行时不依赖内部Lark发失联通知。用户明确不需要Mac外部探针，已从现行方案和后续待办移除，仅保留历史停止/试验记录。

## 6. 当前检查结论与后续门禁

| ID | 可观察条件 | 本轮状态与限制 |
| --- | --- | --- |
| HW-01 | 事故/维修记录可追溯 | 原SEL/POST证据保留；现场维修诊断由用户确认，本轮未下载新SEL |
| HW-02 | POST恢复、诊断与有效容量 | 用户报告重新插拔/更换和诊断通过；OS可达、4×32GiB，助手未独立离线诊断 |
| HW-03 | 同hostkey/PVE及新鲜RAM/RAID状态 | 11月9日14:42–14:44再核EDAC0、两VD Optl；不保证长期稳定 |
| HW-04 | 原12来宾/15目标与原服务基础 | 11月9日fresh分范围通过，forward guard已跨重启保持；应用数据/认证/长期灾备另验 |
| HW-05 | 正式DB/Nacos自动备份 | VM200唯一nacos_prod/12表，首轮3301B/退出0、03:30 timer enabled；其他数据均排除，旧全机jobdisabled/旧档保留，无恢复 |

现行自动备份**仅限VM200正式MySQL数据库与完整Nacos外部元数据库**；当前唯一非系统库为`nacos_prod`（12张BASE TABLE、全InnoDB），正式业务schema尚未创建。新增非系统库不在显式白名单即拒绝并告警，需审核更新策略，不能静默漏备。PVE落点`/mnt/pve/store/dell-artifacts/prod-db-backups`，目录root700/文件600；首轮逻辑SQL gzip **3,301 bytes**已完成CRC/传输SHA校验、DDL锁释放和guest暂存清理，service退出0；03:30（Asia/Shanghai）timer已enabled，下一次2026-11-10 03:30，GFS最近3/每日7/每周4。见[新首轮与timer回执](completion/20261109-prod-db-scope/first-success-and-timer-enabled.json)及[当前中央入口](completion/20261109-prod-db-scope/README.md)。

其他数据均不纳入自动：不备VM/OS、测试数据、Redis/Rabbit、Nexus、Penpot、NAS、Ops或CF文件，220发布私钥继续只留220。旧11来宾全机job已disabled、旧whole-VM告警组已退役；原19,747,582,801 bytes全机归档和21回退档保留，不自动删除。新指标`dell_prod_db_backup_*`及三条db-only规则已原生校验/热载，原Prom身份、既有三告警名和Lark接收对象不变、无人工testsend，见[规则回执](completion/20261109-prod-db-scope/alerts-installed.json)。这是同机应用逻辑备份，不是VM快照；仅[该3301B Nacos小档已在VM210临时隔离恢复](completion/20261109-prod-db-restore/README.md)，完整业务恢复/RPO/RTO/异机DR未签；不迁移，Java不启、Nexus不合并、Mac外部探针不需要。

此前[11档全机首轮成功](completion/20261109/backup-first-success.json)及15:56启用是历史事实，已被用户最新“仅正式数据库/Nacos配置”范围取代；原`dell-local-nightly`不再启用，旧[pve-local实现](infra/backup/pve-local/README.md)退役不可重跑。CF历史档只留PVE，任何旧档/配置均不得因此导出。

OW完整规则仅本地保存，不触/不上传，也不push local-only分支。人工入口见[操作手册](19-manual-operations.md)。当前没有必要为了验证而反复重启、卸载真实数据盘、重装组件或清SEL；后续若出现新CE/UE、IO或服务异常，保留新鲜证据再安排精确处理。历史控制器工具路径`/root/dell-bootstrap/perccli-extracted/opt/MegaRAID/perccli/perccli64`只作只读show/query依据，不授权任何配置写入。

异常断电/内存事件期间的数据若有新写入，仍需逐应用按一致性方式复核；当前Optimal、HTTP200、EDAC0和旧备份SHA不能单独代替该结论。
