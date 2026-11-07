# T630 架构、职责与资源边界

更新：2026-11-07。**这是最后已验收架构和保留配置说明，不是当前在线声明。** 最后完整检查02:35、最后成功PVE同步02:44:29；之后管理不可达，控制台UEFI0058与历史DIMM_B1事件使服务器工作暂停。硬件处理及恢复复验完成前，不执行本文部署或扩容建议。状态入口：[当前状态](01-current-state.md)、[硬件发现](08-hardware-findings.md)。

## 1. 当前交付范围

本期交付基础设施、开发工具和家庭NAS。数据正式/测试独立；Java230/240各保留一台运行基础，**任何环境均不部署或启动Java业务程序**。唯一Java验收模板9011只含JDK/非root用户/监控与验收脚本，不带业务配置或凭据。真实交易、资金、券商及生产通知外发不因基础设施交付而获得许可。

```text
T630 / PVE21.22：虚拟化、存储、管理和二层桥，无host L3/NAT
├─ VM190 GW：WAN21.23 → OW21.1；LAN19.1，DNS/DHCP/filter/noNAT
├─ LXC100 CF19.5：受限隧道入口，凭据原位
├─ 正式数据：VM200 MySQL19.10 + VM201 Nacos/Redis/Rabbit19.11
├─ 测试数据：VM210 四组件19.20
├─ Java基础：VM23019.40 / VM24019.45，无业务程序
├─ VM220 发布基础19.30：受限身份，业务发布fenced
├─ VM221 Nexus19.31：仍是已验收服务所有者
├─ VM250 定制Penpot19.50
├─ VM260 OMV/SMB/Jellyfin19.60
└─ VM270 Ops19.70：四监控组件 + native Lark桥
停止模板：9001 Docker、9010 Linux、9011 Java验收
```

Nexus并入220仅为下一阶段已授权、已准备事项；尚未把31挂到220或把221退役。后续目标primary30+alias31和6CPU/8GiB不进入当前资源表，先过硬件门禁再迁移。

## 2. 资源与故障域

唯一预算来源是[plan.json](plan.json)：12运行角色的配置合计43vCPU、85GiB，硬件为28物理核心/56线程，内存保守预算125GiB、最低主机预留8GiB。完整逐角色表放在[当前状态](01-current-state.md)，避免第二份不一致清单。停止模板不持续占用声明CPU/内存；临时QA必须占位且完成后释放。

vCPU是调度配置，不等于物理核心；容器/JVM限额不等于整个VM内存。角色预算还包含OS、Docker、内核、JVM原生内存、缓存和日志。发布构建、媒体扫描、数据库及备份并行的性能SLO尚未证明，不能机械启动旧38/39条业务部署清单。

所有角色共享T630、供电、内存和存储故障域。多VM不提供跨物理机HA；当前POST故障正说明同机网络/数据库/NAS/Ops会一起失去可用性。RAID不替代独立备份，服务器内Lark也不承担整机无法开机时的外部告警。

## 3. 模板与Docker互补

模板创建操作系统实例，Docker/Compose维护选定VM内的应用，二者并行使用：

| 层 | 已采用用途 | 需要保存 |
| --- | --- | --- |
| PVE模板 | 9010 Linux、9001 Docker、9011 Java验收 | 制作清单、CI身份卫生、独立clone验证 |
| 独立VM | 正式/测试数据、工具、发布、NAS与网关 | 磁盘UUID、网络/权限、服务所属与资源 |
| Compose | 数据四组件、Nexus、Penpot、Jellyfin及Ops | 固定AMD64镜像/构建、受控配置、数据bind/volume、health |
| native/systemd | 网关、发布基础、OS采集、Lark适配 | 最小用户、挂载门禁、监听/启动顺序、日志 |

Docker有daemon、网络、日志和存储开销；数据库缓存、JVM及浏览器worker仍占各自资源。数据不放容器可写层，restart=no的角色由挂载受控systemd管理，防止缺盘时自动写根盘。

Docker模板9001保留其已验证overlayfs/live-restore基线；数据/定制应用离线归档曾按明确角色采用classic-overlay2。不能因某角色ConfigID兼容需求批量切换全部模板或现有业务节点的存储后端。版本和适用范围见角色包与plan。

## 4. 数据、工具和家庭功能

| 角色组 | 必要功能与已验收范围 | 仍保留的边界 |
| --- | --- | --- |
| 正式数据200/201 | MySQL、外部MySQL的Nacos元库、Redis持久化、RabbitMQ账号/vhost/拓扑；真实认证、隔离和fixture重启持久化 | 正式业务schema空，Mac真实数据仅测试；无生产业务上线 |
| 测试210 | 独立四组件、最小auth/system/coms测试schema和权限 | 不共用正式实例、账号或数据目录 |
| 发布220 | Git/JDK/构建基础、独立publisher身份及受限SSH传输 | 当前fenced，不能据历史B/A演练恢复业务发布 |
| Nexus221 | 独立仓库、49 GAV/234主制品SHA读取验收 | 尚未合并220；维护授权有效但硬件gate未过 |
| Penpot250 | 定制前端、backend、worker/import/MCP及DB/素材；3设计/973媒体验证 | 独立目标身份；真实SMTP/公网域名和更广负载另验 |
| NAS260 | OMV、media/games/incoming共享、权限与Jellyfin原媒体 | 不承诺主机网络运行游戏、GPU转码或作为正式灾备 |
| Ops270 | 10node+5Ops目标、主机/RAID/CF元数据、规则、Grafana与服务器内Lark | 最后15UP不是此刻可用；Mac外部probe停用，SLO/RPO未承诺 |

Nacos/Nexus/Penpot的实现可能使用JVM，这是基础组件，不是允许部署Finger业务服务的例外。Java基础与9011的完整边界见[模板与访问](03-templates-and-access.md)。

## 5. 网络：物理同网与逻辑隔离

当前架构只有vmbr0和内部vmbr19：PVE21.22管理，只有GW190 WAN21.23留在21网；vmbr19无PVE地址。PVE自身到19的客户端路由经21.23，不等于宿主启用L3。主机IPv4/IPv6 forward=0、无host NAT；190也不SNAT，互联网出口由OW NAT处理。

同一19/24的peer直接二层互通，不能靠GW190隔离。owned bridge ACL绑定每vNIC的MAC/IP，先检查身份和invalid，再按prod/test/tools/home关系放行；Docker发布端口的实际路径也须纳入角色边界。DNS/DHCP仅由190 LAN19.1提供，动态池19.200–239避开静态角色；IPv6/VLAN旁路拒绝；网关保留lo::1，WAN/LAN IPv6关闭。

用户知悉风险后明确把10.66.66.0/24列为受信VPN：允许到全部19网有效IPv4服务及网关21.23/19.1；认证要求不变，其它来源和peer规则不因此全放。普通21网按端口矩阵访问。访问失败还要分别区分路由/ACL、监听、服务认证；没有运行的Java业务端口不因放行变成服务。

OW现有代理返回198.18/15 Fake-IP；190仅保留已验证的普通DNS/web/NTP/ICMP及CF19.5的7844精确兼容，不静默换公共DNS绕过OW。10.63四区、PVE DNAT入口和14角色预算属于已退出的过渡阶段，不能恢复作现役“修复”。

## 6. 存储、备份和恢复

H730/store由PVE管理，OMV只独占NAS专用2TiB虚拟盘内文件系统；不将宿主sdb或整卡再交NAS挂载。各数据盘和应用配置需按真实UUID、source和mountpoint核对；相同路径目录存在不证明数据盘在线。

正式数据、Nacos元库、Redis、RabbitMQ消息/拓扑、Nexus、Penpot DB/素材与NAS个人文件有不同一致性边界。PVE来宾备份、逻辑/应用导出、合成fixture恢复分别留证，不能互相替代；Rabbit definitions不包含消息，Grafana SQLite备份不覆盖native Lark秘密。当前普通独立副本暂存Mac私有目录，正式备份周期/独立目的地及RPO/RTO仍需落实；CF备份只准PVE本机。

恢复前先过当前硬件/存储门禁。Nexus切换和同IP alias不能实现无缝旧TCP会话或数据库回滚；新目标有写入后必须应用一致性回迁，不能简单改回IP。关键人工入口见[服务与运维](12-service-access-and-operations.md)、[备份](infra/backup/README.md)，不要直接执行历史迁移脚本。
