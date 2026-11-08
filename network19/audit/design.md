> 文档状态（2026-11-08）：本页为阶段实施/技术记录，旧网段、角色数和通过结果按原时点解释。基础已恢复；本轮仅补齐与清理，用户暂不迁移/合并，Mac外部探针不需要。当前配置见[访问清单](../../12-service-access-and-operations.md)，范围与恢复证据见[最新交接](../../11-live-handoff.md)；旧初始化器不得重跑。

# server19 网络迁移设计（尚未实施）

本目录只读盘点/设计，不修改plan、PVE、来宾或OpenWrt。用户目标为：PVE仅保留21.22管理；新网关VM外侧21.23、内侧19.1；全部现有来宾、CT、停止QA和模板NIC迁到server19。除这些固定地址外，新地址由主AI统一分配，本设计不指定尾号。全部数量及当前配置见[inventory.md](inventory.md)。

## 目标拓扑与预算

- PVE `vmbr0` 保持 `192.168.21.22/24`、eno1、默认路由 `192.168.21.1`。最终接在vmbr0的来宾NIC只允许新网关WAN；不把vmbr19接到eno1或vmbr0。
- 新建纯二层 `vmbr19`，`bridge-ports none`，没有PVE IPv4地址、默认网关或NAT。还需明确关闭该桥IPv6地址生成/RA自动配置，验收时IPv4/IPv6均无宿主地址；仅写`inet manual`不能当作IPv6也无地址的证明。
- 候选VM190：Debian13 LinuxBase软件基线，2vCPU、512MiB、期望8GiB，net0=WAN(vmbr0,21.23/24)、net1=LAN(vmbr19,19.1/24)，接口须按MAC确认，不假定eth0/ens18名称。默认路由只在WAN，经21.1。仅网关负责19↔21的三层转发；无Docker、无业务应用。
- 190在本次28对象清单及resource索引均空闲，实际创建前仍须主AI重检。现LinuxBase9010根盘为32G；8G应从已经校验的官方Debian13 cloud镜像新导入并套用相同ub/SSH公钥/QGA基线，不缩9010。若选32G thin clone，应明确记32G虚拟容量，不能标成8G。
- 保守内存预算125GiB − 现有角色116.5GiB − 网关0.5GiB = **8.0GiB**预留，恰好满足8GiB下限。当前MemTotal125.781GiB不是扩张预算依据。停止QA/旧VM同时启动会额外消耗内存，必须单独占位/串行；512MiB仍需实测路由、连接跟踪、日志上限及内存峰值，不能承诺吞吐SLO。

## 路由归属与NAT

OpenWrt须配置 `192.168.19.0/24 via 192.168.21.23`，并核对LAN→LAN转发、策略路由/代理及WAN出站规则。PVE自身另设同一条**客户端路由**经21.23，源仍21.22；PVE默认路由不改为新网关。这样现有root@21.22的SSH ProxyCommand可从PVE本机发起19网管理连接，PVE不需要19地址或开启forward。OpenWrt静态路由的接口与UCI实际值由主AI结合现网核定。[OpenWrt官方静态路由说明](https://openwrt.org/docs/guide-user/network/routing/routes_configuration)

19↔21优先保持纯路由、不SNAT，保留真实客户端/角色源地址。互联网出口优先由OW既有WAN NAT覆盖19网；是否已覆盖须实际检查。只有OW不能直接处理19源网段且主AI另行选择时，才在网关做限定互联网方向的NAT，不能把19→21管理/家庭流量一并伪装。LAN客户端经OW到网关的请求，返回可能由网关WAN直接回到同一21网段客户端，形成OW仅见单向的路径；不能把OW conntrack/日志当成这两方向的完整证据。LAN客户端也可自行直接路由到21.23绕过OW，故网关自身策略与vNIC ACL必须独立成立。

固定21.23当前属于**停止的旧104 CloudInit**。在新网关WAN启用前，先将104 NIC移出vmbr0并更改其旧CI/内部地址；未验证时保持link-down隔离。停机不是地址冲突已解决的证明。CT100当前21.150/DHCP必须迁移；保留cloudflared凭据原位，不读/导出token。其新地址/网关/DNS及远程管理的origin是否引用旧地址，需要主AI另行核对，历史日志未提供路由不等于没有路由。

## 同一19/24的隔离

19网两台来宾会ARP对方并直接通过vmbr19二层互通，不经19.1、21.23或OW。现有按10.63网段区分prod/test/tools/home的宿主路由规则不能原样保护它们。Linux bridge本身是二层转发设备；桥上netfilter钩子被观察到也不等于宿主参与三层路由。[Linux bridge官方文档](https://docs.kernel.org/networking/bridge.html)

采用两层防护，先验证，再把互不信任角色放进同一L2：

1. **PVE每张vNIC边界**：使用当前8.x支持的VM/CT IN/OUT规则、明确启用VM规则与NIC firewall标志，配每NIC固定MAC/IP反欺骗和角色IP集合。运行采集显示PVE防火墙为`disabled/running`，两个daemon active不代表生效。需审核全局启用时对宿主管理22/8006的影响，先保留管理访问和QGA/控制台回退。优先保留稳定legacy后端，不为本次迁移顺便启用8.x文档标为tech preview的nft后端；legacy的host FORWARD/VNet规则不能当作可用替代。`ipfilter-netN`用于源IP限制，DHCP例外及MAC-derived IPv6默认允许需显式检查。[PVE8防火墙官方说明](https://pve.proxmox.com/pve-docs-8/chapter-pve-firewall.html)
2. **来宾自身策略**：SSH、node_exporter及本机应用接口只接受批准角色/管理来源。Docker发布端口经过DNAT/FORWARD，单设guest INPUT不足；须覆盖实际Docker转发路径（例如经验证的DOCKER-USER或等价专用nft forward钩子），保留容器内部、回复与必要DNS/出站流量。不得清空Docker或PVE管理的规则集。

不启用server19 IPv6业务时，阻断其vNIC IPv6越权及RA/DHCPv6，不能仅关闭网关IPv6 forward：同桥link-local照样可能直连。DHCP/DNS只允许网关提供（具体保留地址/租约由主AI定），禁止普通来宾伪造网关ARP、DHCP或源IP。若无法可靠落地每NIC ACL/反欺骗，就不能把原隔离网合并后仍宣称原隔离保持。

| 来源角色 | 允许目标/端口（新IP待主AI） | 默认拒绝重点 |
| --- | --- | --- |
| prod Java230-232 | prod200 MySQL3306；prod201 Redis6379/MQ5672/Nacos8848+9848；必要artifact221端口 | test/home对prod数据无权；正式业务仍不启动 |
| test Java240 | test210上述数据端口；实际本测试服务链 | prod200/201数据端口 |
| publisher220 | 已审核测试240受限SSH22、artifact221 | 任意生产SSH或开放root命令 |
| Ops270 | 各来宾9100及已审核本地监控/通知出口 | 非必要数据/任意管理端口 |
| NAS260/home | 批准家庭客户端的SMB445/Jellyfin8096、管理组的OMV | prod数据、发布权限 |
| CF100 | 必需DNS、Cloudflare隧道出口及明确origin | 任意prod数据/宿主管理；不能因为Tunnel角色就全放通 |
| QA/旧实例/模板新克隆 | 网关基础网络及本次显式验收目标；未验证先隔离 | 默认不可访问prod/test数据或假冒既有角色 |
| 管理来源 | PVE21.22经网关的限定SSH及主AI批准管理客户端 | 家庭LAN全员获得所有服务管理权 |

该表是迁移设计，不是已下发ACL。实际开放集合必须从旧30例允许/拒绝矩阵和新IP表生成；19同区并不等于“全部允许”。

## 迁移顺序与回退

1. **冻结地址契约**：主AI给28对象及GW的唯一IP/MAC/角色清单、DHCP范围、新服务URL/issuer/回调。保留可信SSH别名和原fingerprint；变IP不等于轮换host key。备份当前NIC/CI、网络、专用nft和应用配置，秘密按现有私有边界保存，CF备份仍只在PVE本机。
2. **增加而不替换**：只新增无地址vmbr19；保留vmbr0管理与四旧桥，不重启整套networking或删除默认路由。先隔离104的21.23冲突，再由主AI创建/验证190与OW路由。此时旧网络仍是回退路径，不能宣称切换完成。
3. **先落隔离**：按新IP审核并预装vNIC/guest/Docker-forward规则，验证管理通路、正确流量及带drop证据的拒绝。新GW服务出口、DNS、QGA/ub严格登录、512MiB余量均通过后再切应用。
4. **维护窗口切依赖**：建议按完整依赖组受控暂停/换网，而不是长期给数据来宾双网卡/双默认网关。同步VM NIC、CloudInit和OS实际持久网络，应用bind/compose/env/精确IP guard、Nacos discovery/config、DB账号host、Java issuer/jwks/回调、publisher from/固定policy、Ops scrape/collector private_ip、OMV网络所有者配置、CF origins。UUID、凭据和数据不因改网而轮换或重建；不要用全局sed篡改旧验收历史或含秘密备份。先data，再测试Java/工具、Ops/NAS、CF，正式仍只基础环境。跨组迁移的临时流量如确需放通须单列，不能临时全开网络。
5. **全部28收口**：15个vmbr0引用、12旧桥引用、106 br2001全部改vmbr19；只有190 WAN留vmbr0。停止QA/模板保持停止/onboot原约束。104旧CI不得残留21.23。无CI的旧Linux/Windows和模板内部缓存地址未核前，NIC保持隔离；后续由主AI通过隔离启动/控制台/QGA完成内部配置，不能凭配置清单冒充内部已清理。
6. **最后撤旧路由器职责**：先确认全部服务新地址与ACL通过，再禁用旧`dell-network.service`的开机apply，移除/隔离`/etc/network/interfaces.d/dell-internal`与`/etc/nftables.d/dell.nft`，只删除`inet dell_filter`和`ip dell_nat`专用表，移除四旧桥IPv4地址/connected routes及旧应用DNAT，持久设置宿主IPv4/IPv6 forward=0。旧脚本会主动重开forward=1，所以只写一次sysctl不够。保留vmbr0管理与PVE新的vNIC防火墙；禁止`nft flush ruleset`。19客户端路由经21.23保留，它不是宿主路由器功能。
7. **回退**：任何阶段先保住root@21.22/8006。QGA走宿主-来宾通道，网络错误时由主AI从PVE下发精确网络恢复；CT100用pct exec/控制台，不依赖已失效的21/19 SSH。无QGA或停止来宾保持隔离，通过控制台/离线修复。按角色将NIC/CI/OS持久网络、应用绑定/账号host/可信目标IP一起恢复，旧宿主路由/nft恢复必须过滤先于forward。记录回退影响，不偷偷重开host NAT作为“成功”路径。

QGA本身不替代配置备份，agent失效/客机无法启动时必须有PVE控制台。该通道与客机IP网络相对独立，是网络切换救援手段。[PVE QEMU Guest Agent官方说明](https://pve.proxmox.com/pve-docs-8/chapter-qm.html#qm_qemu_agent)

## 最终验收：证明三层转发在网关

以下均为**待实施验证**，本次没有创建新拓扑，不能标通过。

| ID | 观察/步骤 | 通过条件 |
| --- | --- | --- |
| N19-INV | 再枚举全部qm/pct/模板/停止QA NIC与CI | 除190 WAN外没有vmbr0引用；其它均vmbr19；104无21.23；28既有对象全覆盖 |
| N19-ADDR | 比较PVE、GW、全部运行来宾IPv4/IPv6及停机配置 | PVE vmbr19无任何IP；来宾实际/持久配置无21网地址；停止内部未核对象继续明确pending/隔离 |
| N19-ROUTE | guest到外网`route get`、PVE自身到19的route、OW静态route | guest默认19.1；PVE客户端经21.23；OW19/24经21.23；PVE默认21.1未改 |
| N19-HOST | 检查host sysctl、routes、nft及启动单元；受控复核持久性 | host forward双0，四10.63 connected routes和旧DNAT/NAT不再有效，旧apply不再开机恢复；管理22/8006可达 |
| N19-PATH | 从LAN/PVE/19角色做匹配路径采样、网关nft计数、MAC/TTL抓取 | OW→GW(或PVE客户端直GW)→19；外网第一跳19.1；PVE21.22不是三层hop；没有PVE SNAT。物理帧经过PVE二层桥属于预期 |
| N19-ACL | 新IP重复原30项数据正反矩阵，加同19 prod/test/home/QA/IPv6/source-spoof测试 | 授权端口真实监听时allow通、deny有规则/计数旁证；禁止把端口closed冒充ACL drop |
| N19-APPS | 五测试服务、数据认证/namespace、publisher受限status、Penpot/Nexus/NAS、17监控目标/服务器Lark | 新地址正常，正式业务未启动；旧PVE21.22应用端口不再作为服务入口；Mac外部探测保持停用 |
| N19-FAIL | 仅主AI批准后做网关短时故障/恢复 | 管理21.22仍通；19↔21/外网失败且无host fallback，允许的同19 peer流量仍按ACL；恢复后各服务/隧道重连 |

不能以“PVE某FORWARD计数为0”单独证明没有三层路径：桥接netfilter可观察二层包；反之桥上看到流量也不能认定宿主在路由。地址、路由、forward开关、NAT缺失、下一跳/MAC/TTL及网关策略计数须相互一致。
