# T630 当前状态、最后验收与暂停边界

更新：2026-11-07（Asia/Shanghai）。**当前服务器工作已按用户要求暂停，PVE/来宾不能认定在线。** 用户开机控制台截图显示`UEFI0058`不可纠正内存错误并停在POST提示；此前SEL指向DIMM_B1。硬件处理与恢复复验完成前，不继续迁移、停启、压测或Nexus合并。本次文档整理只读本地证据，没有重新连接服务器。

## 1. 时间线和证据层级

| 时间（+08:00） | 已记录事实 | 如何使用 |
| --- | --- | --- |
| 2026-11-07 02:35:01 | 清理后的独立验收通过：12运行角色、3停止模板，15监控目标UP、0活动告警及主要HTTP入口200 | [最后完整验收](cleanup/final-live-check.json)，是历史成功快照，不是此刻在线证明 |
| 2026-11-07 02:44:29 | 最后成功PVE plan同步 | [同步记录](cleanup/PVE-plan-synced.json)，不代表09:32以后仍正常 |
| 2026-11-07 09:32起 | PVE管理网络不可达，后续尝试未恢复可信SSH/UI | 当前运行状态未知，不把“助手未停源”写成“源仍在线” |
| 2026-11-07 10:23记录 | 用户控制台截图UEFI0058，正常OS启动前停住；截图本身未标出具体DIMM | [B1事故记录](cleanup/hardware/DIMM_B1-incident.json)，结合历史SEL安排离线硬件评估 |
| 当前 | 用户暂停服务器工作，先整理文档与人工手册 | 只维护本地知识；恢复需用户安排硬件处理后再验 |

[plan.json](plan.json)是保留角色、地址和配置预算的机器可读来源；其deployment_status描述已实施结果，不能覆盖当前硬件故障和网络不可达。当前暂停原因见[硬件发现](08-hardware-findings.md)，人工恢复次序见[操作手册](19-manual-operations.md)。

## 2. 最后验收时的保留角色

以下12角色为**02:35最后观察到运行**的清单：11个VM和1个LXC。当前实际运行情况待硬件恢复后重新读取。

| ID | 角色 | 地址 | vCPU / GiB | 已交付职责与边界 |
| --- | --- | --- | ---: | --- |
| 100 | cf-tunnel，LXC | 19.5 | 1 / 0.5 | cloudflared；token留原位，备份仅PVE；account-side origin全链路仍另验 |
| 190 | network-gateway | WAN21.23、LAN19.1 | 2 / 0.5 | 19↔21/公网路由、LAN DNS/DHCP、无NAT、防火墙、先于其它来宾启动 |
| 200 | data-prod-db | 19.10 | 6 / 16 | MySQL正式基础，业务schema保持空，不导入Mac真实业务数据 |
| 201 | data-prod-infra | 19.11 | 4 / 8 | 正式Nacos/Redis/RabbitMQ，外部MySQL元库、独立身份与权限 |
| 210 | data-test | 19.20 | 2 / 4 | 独立测试MySQL/Nacos/Redis/RabbitMQ及最小测试schema |
| 220 | publish-service | 19.30 | 4 / 4 | 构建/受限发布基础；当前业务发布fenced；Nexus合并仅准备 |
| 221 | artifact-service | 19.31 | 2 / 4 | 当前Nexus来源节点，49 GAV/234主制品SHA核对；尚未迁入220 |
| 230 | java-prod-01 | 19.40 | 6 / 16 | 正式Java运行基础，无Java业务程序 |
| 240 | java-test-01 | 19.45 | 4 / 8 | 测试Java运行基础，旧五服务已停用，不部署业务程序 |
| 250 | penpot-service | 19.50 | 6 / 16 | 定制Penpot全套、3份设计/973媒体与MCP验收 |
| 260 | nas-media | 19.60 | 4 / 4 | OMV、SMB三共享及Jellyfin家庭媒体；不作为正式业务备份目标 |
| 270 | ops-service | 19.70 | 2 / 4 | Prometheus/Grafana/Alertmanager/Blackbox及服务器内Lark |
| **合计** | **12角色** | 均为192.168.* | **43 / 85** | 配置预算，非负载或吞吐承诺 |

三份保留停止模板是`9001 tpl-docker-base`、`9010 tpl-linux-base`、`9011 tpl-java-acceptance`。旧模板102/103/105/106、重复Java231/232、旧101/104和已完成QA/临时builder均在受保护备份后清理；完整ID和备份入口见[清理结果](18-cleanup-and-consolidation.md)。不能再按原14角色、三台prod Java或旧模板清单执行部署。

## 3. 最后完成的功能检查

- 数据组件：正式/测试独立VM、账号/namespace/vhost；认证、健康与专用fixture持久化已验。Nacos/Nexus/Penpot自身可能使用JVM，不属于“Java业务程序”；禁止用所有`java`进程数判断Finger应用是否启动。
- 工具：Penpot设计/媒体/MCP、Nexus制品读取、发布链受限身份和fence分别留证。Nexus220目标包未启动，221未由助手停服；当前故障后两者实际状态未知。
- 家庭：OMV/SMB权限、Jellyfin原媒体与重启挂载依赖已验；真实电视/主机、多路转码与混合负载仍待人工验收。
- 网络：专用190完成同key重启、DNS/DHCP与路由验证，PVE仅管理和二层桥；同19网依靠bridge MAC/IP/role ACL隔离。
- 远程：用户已明确授权`10.66.66.0/24`访问整个19网及网关两个本机IPv4地址，服务认证不变；最终远程验证入口见[网络交付](15-network19-delivery.md)。
- 监控：清理后10个guest node目标加5个Ops目标，最后15/15 UP、0告警。Lark为服务器内通知，整台T630不能启动时不能依靠同机发出失联通知；Mac外部探测本期停用。
- fish：9个Linux来宾及3模板仅安装4.0.2，root/ub默认仍Bash；CF100、Penpot250、Ops270排除，PVE未安装或改shell。

## 4. 管理、网络与存储基线

PVE管理地址`192.168.21.22`，BMC/iDRAC记录地址`192.168.21.21`；GW190管理WAN为21.23。PVE的vmbr19无宿主IP，host IPv4/IPv6转发为0，无宿主NAT，旧四个10.63桥和应用DNAT已退出；主机自身到19的客户端路由经21.23。19网来宾网关/DNS为19.1，公网出口NAT由OW21.1负责。

硬件已识别为双E5-2680 v4，28物理核心/56线程；观察内存约125.78GiB，规划预算保守125GiB。85GiB来宾配置约留40GiB给主机/余量，最低保留8GiB，不能以配置空闲推导当前DIMM健康或容量SLO。

H730暴露SSD RAID1和HDD RAID5，PVE管理`local/local-lvm/store`；2026-11-06 05:17曾验证控制器/VD Optimal。那是故障前证据，当前内存POST事件不允许据此认定阵列、文件系统或应用数据此刻正常。NAS只管理专用虚拟盘，不能再挂载PVE的sdb/store或直通承载宿主存储的整卡。

## 5. 当前阻塞和恢复后核查

Nexus合并已取得明确维护授权，目标是220承载primary30+服务alias31、计划6CPU/8GiB；尚未停221或启动220目标，当前阻塞是硬件/可达性门禁，不应再要求用户重复同一授权。恢复后先检查硬件日志、有效内存、存储、可信SSH和原服务/数据，再进入该合并窗口。

02:35验收JSON标题中的“merge pending approval”是当时旧状态，后续用户已明确授权，不覆盖现在的硬件阻塞结论。

当前不执行F1、重启、DIMM拆装、clear SEL、强制阵列Online或迁移。用户/合格维护人员保留SEL/Lifecycle和POST证据、离线评估B1相关路径；故障修复和诊断通过后，按人工手册复核：PVE管理、Gateway先启与无host L3/NAT、数据盘UUID/服务健康、12角色实际状态、15目标及应用正反路径。不能从历史验收直接恢复“当前全部在线”的结论。

初始11月5日盘点、10.63过渡网络、旧模板/Java五服务试验均只作历史证据保留，不再占本文当前清单。旧资料见[evidence](evidence/)、[实施日志](09-implementation-progress.md)，不要重跑已完成bootstrap。
