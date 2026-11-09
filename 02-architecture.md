# T630 服务目标架构、部署快照与资源边界

更新：2026-11-10。**新增资源VM280，当前13角色合同；Nexus合并仍未实施。** 用户明确正式/测试共用同一资源目录，NFS双客户端与VM280重启持久性已验；不启HTTP/Java、不迁文件、不扩自动备份。此前测试Nacos36配置/Puyu两库迁移按单独授权完成，不能把旧“不迁移”泛称覆盖这些已完成例外。资源预算45vCPU/87GiB、3停止模板，[00:20最终后检](completion/20261109-resources/final-postcheck.json)已签16/16目标UP。[资源native验收](completion/20261109-resources/native-acceptance.json)、[仅280重启与fsync文件持久性](completion/20261109-resources/reboot-exercise.json)、[资源server回执](completion/20261109-resources/server-installed.json)、[280机器目录](machines/vm280-resource-service/README.md)、[使用手册](completion/20261109-resources/usage-manual.md)。

11月9日14:24自然重启后的[PVE审计](completion/20261109/pve-audit.json)12running/3模板、[Ops](completion/20261109/ops-audit.json)15UP是新增280前实际历史，forward guard跨重启全0已验。正式DB/Nacos自动备份范围保持，仅[该3301B小档隔离恢复](completion/20261109-prod-db-restore/README.md)已签，完整业务恢复/RPO/RTO/异机DR未签。

## 1. 当前交付范围

本期交付基础设施、开发工具和家庭NAS。数据正式/测试独立；Java230/240各保留一台运行基础，**任何环境均不部署或启动Java业务程序**。唯一Java验收模板9011只含JDK/非root用户/监控与验收脚本，不带业务配置或凭据。真实交易、资金、券商及生产通知外发不因基础设施交付而获得许可。

### 保留的合并目标架构：本轮不实施

```text
T630 / PVE21.22：虚拟化、存储、管理和二层桥，无host L3/NAT
├─ VM190 网关：WAN21.23 / LAN19.1，路由、DNS、DHCP、防火墙
├─ LXC100 CF19.5：Cloudflare Tunnel
├─ 正式数据：VM200 MySQL19.10 + VM201 Nacos/Redis/Rabbit19.11
├─ 测试数据：VM210 四组件19.20
├─ VM220 publish-service：6vCPU / 8GiB，一台VM承担两项职责
│  ├─ 管理/构建/受限发布：主IP19.30
│  └─ Nexus制品仓库：同NIC服务alias19.31:8081
├─ Java基础：VM23019.40 / VM24019.45，无业务程序
├─ VM250 定制Penpot19.50
├─ VM260 OMV/SMB/Jellyfin19.60
├─ VM270 Ops19.70：监控与服务器内部Lark
└─ VM280 resource-service19.80：统一NFS目录，230/240挂/mnt/resources，无HTTP
合并目标加入资源角色后：12实例（11VM+1LXC），3模板9001/9010/9011
```

**`artifact-service`不再作为该合并目标中的独立服务器，但当前仍是VM221现役身份。** 只有将来用户明确恢复迁移任务并完成数据、身份、网络及监控核验后，才考虑退役221、将31逻辑入口交220。本轮不执行这项切换；两个服务职责不等于两台机器。完整保留合同见[发布与制品合并架构](17-publish-artifact-consolidation.md)。

### 本轮恢复后的实际架构：合并尚未执行

本轮[媒体工具审计](completion/20261109/media-audit.json)确认220仍为19.30（4CPU/4GiB）、没有31或active Nexus；221独立19.31、两容器healthy。新增资源280之前，12实例、15监控目标在11月9日14:42–14:44观察正常。220只完成准备，未移盘/加alias/启动Nexus，本轮也不实施；实际清单见[01](01-current-state.md)，不得把上方目标图当上线证明。

## 2. 资源与故障域

唯一预算来源是[plan.json](plan.json)：新增资源280后13角色配置合计45vCPU、87GiB，硬件为28物理核心/56线程，内存保守预算125GiB、最低主机预留8GiB。完整实机快照放在[当前状态](01-current-state.md)。保守125GiB减来宾87GiB余38GiB（含主机/缓存预留）。加入资源角色后的合并目标为12角色，220承接两台原额度成为6vCPU/8GiB，总45vCPU/87GiB不变；不是额外释放4GiB。停止模板不持续占用声明CPU/内存；临时QA必须占位且完成后释放。

vCPU是调度配置，不等于物理核心；容器/JVM限额不等于整个VM内存。角色预算还包含OS、Docker、内核、JVM原生内存、缓存和日志。发布构建、媒体扫描、数据库及备份并行的性能SLO尚未证明，不能机械启动旧38/39条业务部署清单。

所有角色共享T630、供电、内存和存储故障域。多VM不提供跨物理机HA；历史POST故障说明同机网络/数据库/NAS/Ops会一起失去可用性。RAID不替代独立备份，服务器内Lark也不承担整机无法开机时的外部告警。

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

表内认证/隔离/fixture/内容为对应历史功能验收，不表示本轮全部重做。本轮新鲜健康状态分别见[核心审计](completion/20261109/core-audit.json)、[媒体工具审计](completion/20261109/media-audit.json)、[Ops审计](completion/20261109/ops-audit.json)，完整限制放在[04](04-services-and-migration.md)。

| 角色组 | 必要功能与已验收范围 | 仍保留的边界 |
| --- | --- | --- |
| 正式数据200/201 | MySQL、外部MySQL的Nacos元库、Redis持久化、RabbitMQ账号/vhost/拓扑；真实认证、隔离和fixture重启持久化 | 正式业务schema空，Mac真实数据仅测试；无生产业务上线 |
| 测试210 | 独立四组件、最小auth/system/coms测试schema和权限 | 不共用正式实例、账号或数据目录 |
| 发布220 / 制品221（实际） | 220构建/受限发布基础；221独立Nexus，原URL31:8081不变 | publisher仍fenced；合并目标暂不实施，不把31写成220现役alias |
| Penpot250 | 定制前端、backend、worker/import/MCP及DB/素材；历史3设计/973媒体验证，本轮11容器healthy | 实际Git仍历史ff1783e clean，未更新main；本轮未重验MCP/内容，真实SMTP/域名/负载另验 |
| 资源280 | NFSv4.1统一/srv/resources，230/240共用/mnt/resources，resources附属组2980 | 双客户端/280重启持久性已验；无HTTP、不迁文件、不入自动备份 |
| NAS260 | OMV、media/games/incoming共享、权限与Jellyfin原媒体 | 不承诺主机网络运行游戏、GPU转码或作为正式灾备 |
| Ops270 | 主机/RAID/CF元数据、规则、Grafana与服务器内Lark；新增资源前10node+5Ops=15UP | 新增280后实际16/16目标UP，资源5项服务指标UP；用户不需要Mac外部probe，已移出现行方案与待办，历史保留 |

Nacos/Nexus/Penpot的实现可能使用JVM，这是基础组件，不是允许部署Finger业务服务的例外。Java基础与9011的完整边界见[模板与访问](03-templates-and-access.md)。

## 5. 网络：物理同网与逻辑隔离

当前应用网络使用vmbr0和内部vmbr19：PVE21.22管理，只有GW190 WAN21.23留在21网；vmbr19无PVE地址。PVE自身到19的客户端路由经21.23，不等于宿主启用L3。主机IPv4/IPv6 forward=0、无host NAT；190也不SNAT，互联网出口由OW NAT处理。OW完整规则仅本地保存，本轮不触/不上传。11月8日发现forward漂移后仅补3个owned文件，11月9日自然重启后的SHA/执行顺序与全部forward0已由[PVE审计](completion/20261109/pve-audit.json)实际读回，证明这次跨重启保持；原桥/路由/ACL无变化，不恢复PVE路由/NAT。

同一19/24的peer直接二层互通，不能靠GW190隔离。owned bridge ACL绑定每vNIC的MAC/IP，先检查身份和invalid，再按prod/test/tools/home关系放行；Docker发布端口的实际路径也须纳入角色边界。DNS/DHCP按合同仅由190 LAN19.1提供，动态池19.200–239避开静态角色；本轮[直接UDP/TCP DNS复核](recovery/20261108/network-CF-followup.json)三静态A正确，CF ready200/连接2，但不签公网origin E2E；IPv6/VLAN旁路拒绝；网关保留lo::1，WAN/LAN IPv6关闭。

用户知悉风险后明确把10.66.66.0/24列为受信VPN：允许到全部19网有效IPv4服务及网关21.23/19.1；认证要求不变，其它来源和peer规则不因此全放。普通21网192.168.21.0/24已按用户新授权受信访问19/24全IPv4服务及网关自身21.23/19.1；NFS仍另受精确exports/guest输入白名单限制。访问失败还要分别区分路由/ACL、监听、服务认证；没有运行的Java业务端口不因放行变成服务。

OW现有代理返回198.18/15 Fake-IP；190保留原已验证的普通DNS/web/NTP/ICMP及CF19.5的7844精确兼容，不静默换公共DNS绕过OW。10.63四区、PVE DNAT入口和14角色预算属于已退出的过渡阶段，不能恢复作现役“修复”。

## 6. 存储、备份和恢复

H730/store仍由PVE管理，OMV只独占NAS专用2TiB虚拟盘；资源280另独占100GiB虚拟盘导出唯一NFS文件系统；数据按真实UUID和挂载核验，不把根盘目录当在线数据盘。

现行自动备份**仅限VM200正式MySQL数据库与完整Nacos外部元数据库**；当前唯一非系统库为`nacos_prod`（12张BASE TABLE、全InnoDB），正式业务schema尚未创建。新增非系统库不在显式白名单即拒绝并告警，需审核更新策略，不能静默漏备。PVE落点`/mnt/pve/store/dell-artifacts/prod-db-backups`，目录root700/文件600；首轮逻辑SQL gzip **3,301 bytes**已完成CRC/传输SHA校验、DDL锁释放和guest暂存清理，service退出0；03:30（Asia/Shanghai）timer已enabled，下一次2026-11-10 03:30，GFS最近3/每日7/每周4。见[新首轮与timer回执](completion/20261109-prod-db-scope/first-success-and-timer-enabled.json)及[当前中央入口](completion/20261109-prod-db-scope/README.md)。

其他数据均不纳入自动：不备VM/OS、测试数据、Redis/Rabbit、Nexus、Penpot、NAS、Ops或CF文件，220发布私钥继续只留220。旧11来宾全机job已disabled、旧whole-VM告警组已退役；原19,747,582,801 bytes全机归档和21回退档保留，不自动删除。新指标`dell_prod_db_backup_*`及三条db-only规则已原生校验/热载，原Prom身份、既有三告警名和Lark接收对象不变、无人工testsend，见[规则回执](completion/20261109-prod-db-scope/alerts-installed.json)。这是同机应用逻辑备份，不是VM快照；仅[该3301B Nacos小档已在VM210临时隔离恢复](completion/20261109-prod-db-restore/README.md)，完整业务恢复/RPO/RTO/异机DR未签；不迁移，Java不启、Nexus不合并、Mac外部探针不需要。

此前[11档全机首轮成功](completion/20261109/backup-first-success.json)及15:56启用是历史事实，已被用户最新“仅正式数据库/Nacos配置”范围取代；原`dell-local-nightly`不再启用，旧[pve-local实现](infra/backup/pve-local/README.md)退役不可重跑。CF历史档只留PVE，任何旧档/配置均不得因此导出。

原MySQL/Nacos/Redis/Rabbit合成恢复、Grafana SQLite及模板QA只证明对应历史范围，不能替代新逻辑备份的完整恢复。任何未来迁移或恢复仍须准确白名单、隔离、拒覆盖现役数据；本轮不执行。
