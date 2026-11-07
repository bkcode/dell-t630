> 文档状态（2026-11-07）：本页为阶段实施/技术记录，文中“当前”、网段、角色数与通过结果以原执行时点为准。服务器现因UEFI0058内存错误暂停，Nexus合并已授权但未执行；当前配置入口见[访问清单](../../12-service-access-and-operations.md)，恢复门槛见[最新交接](../../11-live-handoff.md)。旧脚本、stage/commit或初始化步骤不得直接重跑。

# vmbr19 bridge-family ACL候选与阶段补充

此文件补充根任务已推进后的状态，初始current-inventory.json/inventory.md保留原时点事实。主AI已创建无IP vmbr19、移动旧104 NIC并改CI为19.104，已克隆190为32G thin/512MiB双网卡；迁移IP唯一来源改为上级 `network19/migration-plan.json`。这里没有分配或修改任何IP/来宾/宿主。

## 本次只读实测结论

`bridge-nf-stage.json`（2026-11-06 08:03:11Z）显示：

- 内核6.8.12-9-pve；BRIDGE_NETFILTER内建=y，故lsmod没有br_netfilter不能理解成无功能。
- 全局bridge-nf-call-iptables/ip6tables/arptables均0，各vmbr0/19/10/20/30/40的nf_call_*也均0。
- inet dell_filter forward实际policy为ACCEPT；末尾DROP仅匹配managed旧桥。iptables/ip6tables FORWARD也是ACCEPT。新vmbr19不在旧managed集合。
- 所以目前vmbr19普通桥接IP帧**不依靠旧inet过滤**，旧managed DROP不会保护19东西向。无需为了“绕过旧DROP”添加大范围inet ACCEPT或开启桥netfilter。
- CONFIG_NF_TABLES_BRIDGE、NFT_BRIDGE_META、NFT_BRIDGE_REJECT、NF_CONNTRACK_BRIDGE均为m。`nft list tables bridge`成功、无表。这证明内核构建支持/查询可用；本审计未modprobe、未做可能触发模块加载的nft-c。实际bridge+ct规则须主AI做预检与受控应用。

## 离线候选生成

`render-bridge-acl.py`只读本地已脱敏NIC快照和主AIIP表，输出`bridge19-acl-candidate.nft/.json`，不SSH或apply。此次29个LAN身份（28原对象+190 LAN），枚举每NIC direct tap/veth及旧PVE fwpr名称供盘点；本阶段主AI确定所有目标使用firewall=0/direct tap-veth，190 WAN明确排除。模板及未登记的新VMID只获得绑定MAC的DHCP隔离，不按名称或DHCP租约自动授予prod权限。

候选要点：

1. 只创建`table bridge dell19_acl`。forward hook中仅vmbr19流量进入默认拒绝的专用链；其它桥的forward不改。本阶段host INPUT/OUTPUT仅拒绝vmbr19本机终结，防止Linux弱主机模型接受发向其它本机IP（21.22）的桥帧；不提前guard旧fwbr100等，保持CT100迁移前旧LAN访问不受这部分新规则干扰。PVE自身管理访问19仍必须经GW WAN。
2. IPv6、802.1Q、802.1ad先DROP；每输入端口校验Ethernet源MAC，ARP额外校验SHA/SPA，普通IPv4严格绑定端口/IP；这些检查在ct established之前。不能让带已知IP的其它端口冒充既有角色。
3. 网关LAN单独处理：MAC必须匹配190 LAN，但IP源允许承载合法21/互联网回复；禁止网关冒充其它19角色。来宾禁止把同19目的IP交给网关MAC来绕过东西向规则。
4. DHCP只在普通端口→190 LAN与190 LAN→普通端口间开放；未知/模板身份除此之外默认DROP。ARP 0.0.0.0只放正常地址探测，不能宣告其它角色IP。源MAC/IP仍由PVE可信配置/主AI登记控制，不能信任guest提交的角色或租约自动提升权限。
5. ct invalid DROP、合法established/related回复放行，然后精确角色TCP集合：prod201→200 MySQL；prod Java→prod数据；test240→210五数据端口；publisher220→test240 SSH；批准构建客户端→Nexus8081；Ops270→批准来宾9100。WAN→LAN七条规则逐条直接读取主AIgateway_policy，包含21.22与21.116管理源的SSH、数据管理、Nacos/监控端口及普通LAN公开入口，不另维护冲突的缩减名单；guest新会话到21管理LAN默认拒绝，已建立的LAN服务回复可回去。
6. 普通公网egress端口/ICMP、RFC1918目的排除及CF/publisher例外直接读取主AIgateway_policy，CF额外TCP/UDP7844，publisher额外公网SSH22；网关自身还要按其WAN/LAN策略过滤。CF内网origin未知，候选**不**授予CF任意prod/管理/公开服务访问，必须由主AI补精确origin集合。工具间原同区任意SSH不自动保留，必须复核实际需要。

## PVE旧firewall标志/动态生命周期

主AI已决定迁NIC时全部设firewall=0直接接vmbr19，保留MAC；本阶段这是应用硬条件。PVE防火墙本来disabled，由专用bridge表接管。候选只guard vmbr19，不启prospective fwbr100等host guard，避免提前影响仍在旧LAN的CT100。旧firewall=1的7个盘点警告必须在各目标激活前消除；若未来保留/新增fwbr，需单独补充子桥弱主机INPUT旁路防护并重新验证，不能套用本阶段通过结论。

动态操作应为：可信PVE配置/NIC快照→对照主AIVMID/IP/role注册表→离线渲染→`nft -c`→原子替换**仅本专用表**→核对规则/计数→记录证据。所有clone/start/hot-NIC、IP角色变更前须刷新，服务启动也须重建同一规则。未登记端口默认拒绝；新clone即便拿到DHCP也不得自动复用prod角色，主AI核对MAC/QGA/分配后再登记。切换事务保留旧表回退，不使用flush ruleset、不改bridge-nf sysctl。只有主AI可写host。

## 应用硬门槛

当前候选尚未在Linux内核做语法预检，**不是可直接宣称通过的生产规则**。主AI需要：

- 在所有真实数据迁移前先使用一个专用QA，验证direct tap/veth及如保留fwbr时的iif/oif/ibrname/obrname可见性与计数。确认所有已激活目标均为direct tap/veth、无旧fwbr路径；检查nf_tables_bridge/NFT_BRIDGE_META/NF_CONNTRACK_BRIDGE实际加载支持、conntrack回复及普通大包，不修改其它表。
- 明确bootstrap顺序：规则先于guest有机会在19网络发包；QGA/控制台不依赖L2规则，可回退。
- 先测管理21.22→QA SSH、DNS/DHCP及允许端口；再测test/home/QA→正式已监听端口DROP与计数，源MAC/IP/ARP伪造、同19目的经GW MAC绕行、IPv6/VLAN旁路、本机21.22弱主机INPUT拒绝。
- 迁移期间如需旧Ops10.63.30.40→新9100，可显式生成`--allow-old-ops-during-cutover`候选，且旧host/GW的临时路径也须分别审核；最终生成默认false并删除所有旧10.63例外。该开关不代表已经配置任何路径。
- 验收后确认server19→LAN/外网由190路由，PVE forward仍可置0；桥包经过PVE内核L2是预期，不能声称物理帧不经过PVE。
