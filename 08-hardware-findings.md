# 硬件发现、UEFI0058与恢复门禁

更新：2026-11-07。**当前主阻塞是用户截图的UEFI0058不可纠正内存错误/POST拦截，服务器工作已暂停。** PVE管理不可达，不能把故障前控制器Optimal或软件验收写成当前健康。本文件只整合本地证据，没有新远程读取、F1、重启、DIMM拆装或控制器操作。

## 1. 当前内存事件与证据强度

权威事故记录：[DIMM_B1-incident.json](cleanup/hardware/DIMM_B1-incident.json)。

| 证据 | 能确认什么 | 不能直接推导什么 |
| --- | --- | --- |
| 用户iDRAC recent-events/SEL截图 | B1曾有multi-bit memory error及correctable rate exceeded事件 | 单靠recent events不能证明具体关机机制或当前是某条内存独坏 |
| 用户开机控制台UEFI0058截图，10:23记录 | 固件报告不可纠正内存错误，停在F1/F2/F10/F11提示、正常OS启动前 | 截图自身没有点名槽位，B1来自此前SEL，不应混成同一现场定位结果 |
| 09:32后管理不可达及恢复尝试 | PVE21.22 SSH/UI和GW21.23未恢复可信访问；iDRAC是独立管理面 | iDRAC可达不等于OS/来宾已上线，不等于阵列/数据此刻已验 |
| 最后02:35软件验收、02:44:29 PVE同步 | 故障前保留配置/软件曾通过 | 无法证明当前RAM容量、文件系统一致性或应用在线 |

BMC显示时间`Sat Nov07 2026 00:02:38`的时区未核实，不能直接与本地09:32或OS时间做因果排序。DIMM_B1在既有事故分析按T630手册关联CPU2/channel0；嫌疑包括模块、接触、插槽、通道或内存控制器，未经隔离诊断不能直接判CPU或单条DIMM报废。

## 2. 用户暂停与硬件处理边界

当前不继续Nexus迁移、数据搬迁、压力/恢复演练，也不以按F1跳过POST当作修复。代理没有按F1、远程电源操作、清SEL或拆装内存。Nexus停机维护授权已具备，源/目标未由代理切换；当前硬件gate不能被“已有授权”替代。

后续由用户/合格维护人员先保留完整SEL/Lifecycle、POST截图和内存inventory，再按Dell机型规则离线评估B1相关路径、正确重插/替换及诊断。不得在日志未保存前清掉错误，也不为追求可启动反复强制上线硬件或忽略内存错误。实际有效容量若变化，必须重新算[plan.json](plan.json)预算，不继续假定125GiB可用。

本文件不提供未经现场验证的DIMM插拔顺序或“只换某条就保证恢复”的结论。已有事故记录引用Dell官方内存故障与T630手册，供现场人员按对应配置使用；这些链接不是本次已经执行硬件修复的证据。

## 3. 故障前硬件基线

初始盘点：[pve-audit-2026-11-05.json](evidence/pve-audit-2026-11-05.json)。

| 项目 | 已记录基线 | 当前限制 |
| --- | --- | --- |
| 型号 | Dell PowerEdge T630 | 未新增硬件inventory |
| CPU | 双Xeon E5-2680 v4，28物理核心/56线程，2 NUMA | vCPU配置不是物理核或吞吐承诺 |
| RAM | 当时约125.78GiB，规划保守125GiB | B1事件后有效/可用容量待现场复验 |
| PVE | 初始pve-manager8.4.0、kernel6.8.12-9-pve | 软件版本为采集时记录，不是当前启动成功证明 |
| 网卡 | eno1曾记录1Gbps全双工 | 当前链路/错误/负载需恢复后核对 |
| 存储 | H730管理SSD RAID1与HDD RAID5，store由PVE挂载 | 内存/IO异常后需读新控制器/文件系统证据 |

## 4. RAID恢复是历史事实，不覆盖当前DIMM故障

2026-11-06 05:17只读证据[raid-recovered.json](evidence/implementation/raid-recovered.json)确认：

- 控制器及VD0/VD1均Optimal；VD0为SSD RAID1约446.6GB，VD1为HDD RAID5约7.276TB。
- SSD槽32:0、32:1及HDD32:2、32:3、32:7均Onln；槽32:3重建结束并有完成/DEGRADED→OPTIMAL事件，不能只凭“无进度”判断。
- 当时BBU Optimal/100%、温度/电压正常；Controller Media/Other/Predictive计数没有观察到新增，缓存策略留证。

这是故障前采集，不应继续称“仍48%重建/RAID完全未知”，也不能称“当前阵列正常、可恢复迁移”。PERC板载缓存的correctable/uncorrectable计数与系统DIMM_B1不是同一存储/内存层，前者0不能否认后者SEL多位错误。

历史槽32:3曾出现无法访问/缺失、Offline并自动重建，盘/固件/链路/背板/供电根因未单独确定。smartctl曾记录SAS槽32:2有11个重分配块，和PERC media count不同；非Dell认证SSD兼容提示也保留。事件控制器时钟曾约差8小时，完成时间换算只作历史参考，不用来校准本次BMC事件。

旧过程完整保留：[hardware-network-audit.json](evidence/implementation/hardware-network-audit.json)、[raid-controller.json](evidence/implementation/raid-controller.json)。不删除或改写原JSON，不通过重复rebuild/force Online掩盖新异常。

## 5. 网络与物理层当前架构说明

最后验收已是PVE21.22管理/L2、vmbr19无hostIP、host IPv4/IPv6 forward0、无host NAT，旧10.63四桥和DNAT退出；独立190承担路由/DNS/DHCP/filter且自身无NAT，OW21.1做互联网NAT。[final-live-check](cleanup/final-live-check.json)记录12角色/三模板和15UP。

因此旧11月5日“只有vmbr0/规则空/CT100地址21.150”的深查是历史，不是当前目标网络。恢复时保留190先启动和二层ACL，不通过恢复PVE旧NAT/forward来假装应用修复。网关/服务器内Ops同属这台T630故障域，OS未启动时不能指望其自发Lark失联通知；Mac外部probe本期停用。

## 6. 恢复后逐级门禁

具体人工操作次序见[操作手册](19-manual-operations.md)，当前不执行这些步骤。

| ID | 前置/人工步骤 | 可观察通过条件 | 当前状态 |
| --- | --- | --- | --- |
| HW-01 | 用户保留SEL/Lifecycle/POST/内存inventory | 事件时间/槽位/硬件配置可追溯，未清旧日志 | 待现场 |
| HW-02 | 按Dell规则离线评估并修复相关路径 | POST不再被UEFI0058阻断，内存诊断通过、有效容量确认 | hardware-gate |
| HW-03 | OS/PVE恢复后可信只读采集 | 同hostkey/管理地址、CPU/RAM/存储/文件系统新鲜状态；无新增不可纠正事件 | pending，当前不远程 |
| HW-04 | 对照保留清单恢复软件 | GW先启、host无L3/NAT、数据UUID/服务、保留12角色及15目标实际健康 | pending-reacceptance |
| HW-05 | 基线恢复且新证据留齐后进入Nexus原维护窗口 | 源221健康/备份/目标220容量与硬件余量满足，再按已授权方案迁移 | 已授权，当前未开始 |

只读控制器工具的历史路径为`/root/dell-bootstrap/perccli-extracted/opt/MegaRAID/perccli/perccli64`；既有采集使用show/query命令，未改阵列参数、刷固件或清日志。后续远程采集也须用户恢复工作后执行，当前不把此路径当作立即操作指令。

硬件安全处理优先于软件迁移与验收。软件数据若在异常断电/内存错误期间产生新写入，必须逐应用复核，不能用旧备份SHA或05:17 Optimal替代当前数据一致性结论。
