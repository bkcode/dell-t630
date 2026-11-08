# 硬件发现、历史UEFI0058与恢复观察

更新：2026-11-08（Asia/Shanghai）。**用户确认内存已重新插拔/更换并通过诊断，服务器恢复；本轮范围是检查补齐现有基础服务和清理确认多余项，不迁移。** 主AI20:12严格SSH只读读取到4×32GiB、当前boot EDAC计数0与RAID Optimal；物理处理/诊断来自用户，本轮没有代理独立离线诊断或压力测试。UEFI0058与DIMM_B1事故保留为历史，不再描述为当前POST拦截。本文只同步本地证据，没有发起新远程操作。

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

## 5. 本轮网络与软件恢复观察

当前架构仍为PVE21.22管理/L2，vmbr19无hostIP，独立190 WAN21.23/LAN19.1提供路由/DNS/DHCP/filter；190无NAT，OW21.1做互联网NAT，旧10.63四桥及PVE DNAT不恢复。

开机发现vmbr0 IPv4/IPv6 per-interface forward为1，而all/default及其余接口为0。主AI仅新增/补齐3个owned持久文件并即时收敛，未reload网络、未重启来宾，原interfaces、桥/路由/ACL保持；[修复回执](recovery/20261108/host-forwarding-restored.json)与[20:20:48后检](recovery/20261108/host-network-postcheck.json)确认各接口forward全0、无宿主NAT。该补丁的再次重启持久性未在本轮单独演练，不以语法检查冒签。

- [核心审计](recovery/20261108/core-services-audit.json)，20:16:13–20:18:22：200/201/210原数据UUID/rw、8容器healthy；230/240 JDK基础与无业务状态通过。
- [媒体工具审计](recovery/20261108/media-tools-audit.json)，20:19:39：221独立Nexus、250定制Penpot、260 NAS基础服务恢复；220没有移盘、加alias或启动Nexus。内容、认证写入及Penpot main更新未执行。
- [Ops审计](recovery/20261108/ops-audit.json)，20:19:38：15/15 targets UP，无活动告警，Lark unit active；没有新消息测试，不能据此签本boot供应商送达。
- [宿主后检](recovery/20261108/host-network-postcheck.json)，20:20:48：12来宾运行、6主要入口200。PVE自签HTTPS只做可达性检查，不是证书身份校验。
- [网络/CF后续核查](recovery/20261108/network-CF-followup.json)：直接向19.1用UDP/TCP查询，Penpot/制品/发布三A分别为19.50/31/30；CF实际20241端口ready200、连接2。先前网关OS resolver经OW得到Fake-IP和CF误用2000端口探针的失败原样保留，不作为服务故障；未验证Cloudflare公网origin全链路。

同机Ops与GW共享T630故障域，整机无法运行时不依赖内部Lark发失联通知。用户明确不需要Mac外部探针，已从现行方案和后续待办移除，仅保留历史停止/试验记录。

## 6. 当前检查结论与后续门禁

| ID | 可观察条件 | 本轮状态与限制 |
| --- | --- | --- |
| HW-01 | 事故/维修记录可追溯 | 原SEL/POST证据保留；现场维修诊断由用户确认，本轮未下载新SEL |
| HW-02 | POST恢复、诊断与有效容量 | 用户报告重新插拔/更换和诊断通过；OS可达、4×32GiB，助手未独立离线诊断 |
| HW-03 | 同hostkey/PVE及新鲜RAM/RAID状态 | 20:12严格SSH成功，当前boot EDAC0、两VD Optl；不保证长期稳定 |
| HW-04 | 原12来宾/15目标与原服务基础 | 20:16–20:20分范围通过；应用数据/认证/长期灾备不能由健康状态替代 |
| HW-05 | 只补齐和清理确认多余项 | 用户本轮不迁移，不进Nexus窗口、不退役221、不启动Java业务；每个新清理项先核依赖与回退 |

人工入口见[操作手册](19-manual-operations.md)。当前没有必要为了验证而反复重启、卸载真实数据盘、重装组件或清SEL；后续若出现新CE/UE、IO或服务异常，保留新鲜证据再安排精确处理。历史控制器工具路径`/root/dell-bootstrap/perccli-extracted/opt/MegaRAID/perccli/perccli64`只作只读show/query依据，不授权任何配置写入。

异常断电/内存事件期间的数据若有新写入，仍需逐应用按一致性方式复核；当前Optimal、HTTP200、EDAC0和旧备份SHA不能单独代替该结论。
