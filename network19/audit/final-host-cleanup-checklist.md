> 文档状态（2026-11-07）：本页为阶段实施/技术记录，文中“当前”、网段、角色数与通过结果以原执行时点为准。服务器现因UEFI0058内存错误暂停，Nexus合并已授权但未执行；当前配置入口见[访问清单](../../12-service-access-and-operations.md)，恢复门槛见[最新交接](../../11-live-handoff.md)。旧脚本、stage/commit或初始化步骤不得直接重跑。

# 旧10.63路由/NAT/host-forward最终清理核对清单

主AI已于2026-11-06 17:51完成清理；本audit仅核收据。最终18:09身份/host与18:11维护解除均已核：四旧桥/旧NAT_filter消失、全部forward0，保留bridge ACL、vmbr0管理与19客户端路由。下面保留核对方法作签收依据，不是要求重复运行清理脚本或停机。早期forward1快照只属历史过渡态。

## 原清理前硬条件（现有收据已满足本期范围）

- 迁移表中的永久角色、CF100、旧101/104、全部停止QA和6模板的NIC最终均vmbr19；只有190 WAN留vmbr0。其它19 NIC为firewall=0直连tap/veth；旧br2001/vmbr10/20/30/40无遗留guest引用。
- 运行来宾实际/持久网络仅批准19地址，默认19.1/DNS19.1；CI配置一致。停止旧OS内部未核项必须明确保持隔离/pending，不能用停止/CloudInit字段假装已清理。模板首克隆身份与DHCP策略独立验收。
- 数据基础组件、Nacos namespace、现有账号/身份边界、Penpot/Nexus/NAS与Ops本机collector/服务器Lark完成本期新IP验证。Java不部署或启动任何业务，测试五服务inactive/非enabled、仅base监控，Publisher必须fenced；Java验收模板无业务配置/凭据。CF只签注册，原remote origin未获时明确不宣称公网业务全通。Mac外部probe保持停用。
- 19同L2允许/拒绝、反欺骗及host弱主机模型测试已过。没有为了切换留下全通或伪装源IP的临时规则；old Ops10.63例外如用过须列出并准备删除。
- root@21.22/8006、可信QGA和控制台均可救援；PVE-only原配置/规则备份可读，CF秘密备份不得导出。

## 宿主清理与只读签收（root执行变更，audit只核结果）

| 项 | 只读核对方法 | 最终通过条件 |
| --- | --- | --- |
| 旧启动加载器 | systemctl show/is-enabled dell-network.service；只读其已审核配置引用 | 禁用且不再开机执行旧apply；仅disable服务不会自动删除其已经写下的nft/forward，须另核实时值 |
| 旧配置 | 核/etc/network/interfaces.d/dell-internal及旧nft/forward持久来源，保留受控备份 | 不再配置四旧桥地址/启动旧NAT；没有其它启用单元或sysctl配置重新开启host forward。不可全局grep历史备份要求零旧IP |
| 旧桥/路由 | ip -j addr、ip -j route show table all、bridge -j link及全部qm/pct NIC白名单 | 四旧桥不再带10.63地址/connected routes且无guest引用；不残留相关策略路由。删除桥前须无port，不动vmbr0/eno1 |
| 旧nft/NAT | nft -j list ruleset；必要iptables/ip6tables-save选网络规则 | 删除仅inet dell_filter与ip dell_nat及等价旧规则；没有19→21/外网借PVE SNAT，旧21.22应用DNAT不生效。绝不flush ruleset，保留bridge dell19_acl及其它已审核表 |
| forward | /proc/sys/net/ipv4/ip_forward与IPv6 all.forwarding；核相关all/default/vmbr0/vmbr19的有效forward值与启动持久性 | PVE三层forward关闭；网关190 IPv4 forward开启由另份GW验收证明；不能误把bridge二层转发当host L3 forward |
| host地址 | ip -j -4/-6 addr show vmbr19，vmbr0配置/默认路由 | vmbr19宿主IPv4/IPv6均无地址；PVE21.22管理与默认21.1保持，不增加PVE19.1或其它19地址 |
| host客户端路由 | ip route get一个已批准19来宾地址，源21.22 | 19/24 via21.23 devvmbr0，属于本机管理客户端路由，不是connected route或host router；它须持久可恢复 |
| 旧PVE应用入口 | LAN客户端精确测21.22的9001/8081/9080/8096/9999/19999；同时测22/8006正控 | 旧应用入口不再转发，管理仍可达；仅ss无监听不能证明DNAT已删除，须结合规则与实际probe |
| 新ACL持久化 | nft table bridge dell19_acl、服务与pve-guests.service依赖 | 已批准规则在VM自启之前加载；MAC/IP注册表正确，未知clone fail-closed；不能因停旧loader顺手停新bridge ACL |
| hostkey/CloudInit | per-installed-VM snippet布尔、可信rotation ledger、身份元数据 | 已部署13VM只改ssh_deletekeys false；模板保持独立首clone策略。230已发生rotation要保留真实记录，不能写原指纹不变 |

## 清理后的路径证明与实际签收

1. 重跑最小正控：管理SSH/PVE UI、PVE经21.23到19角色严格SSH、19 guest经19.1 DNS/TLS出网、LAN到本期基础服务入口（不含已停Java业务）、同19授权数据peer流量。
2. 重跑新19的prod/test/home拒绝矩阵及rule/counter旁证。旧10.63成功证据只作为历史，不能替代新矩阵。
3. guest route get外网的下一跳为19.1，PVE自身route get19为21.23；GW forward计数增加，帧TTL/MAC/源地址与无PVE NAT一致。物理数据帧仍经PVE Linux bridge，不能写成物理上完全不经PVE。
4. 仅在主AI授权的受控窗口，可停/恢复网关一次验证无host fallback：PVE管理21.22仍通，跨19/21和外网失败，已授权同19 peer literal-IP连接仍受ACL正常工作，网关恢复后DNS/本期基础服务/隧道重连；不得为此启动Java业务。当前只读任务不执行这一步。
5. 重启持久性必须区分：guest正常重启不等于PVE宿主重启通过；如未重启host，记录systemd启动依赖/持久文件静态核对，host reboot验收仍pending，不能写已证明断电恢复/RPO。

每项保存时间、具体网络白名单命令、exit/结果和限制；不输出credential、Env、完整cloud-init profile或CF token。失败先保管理/QGA救援，不自动全局回滚或重新开启host NAT掩盖问题。

## 已核收据与未实演边界

- host-management-only-retirement.json：phase complete，旧四桥/两旧专用表消失，all/default/各接口IPv4IPv6 forward均0，旧loader masked，backup PVE-only；保留bridge dell19_acl。
- Mac-final-management-and-services.json：实际21.116客户端确认PVE22/8006通，旧7应用/共享入口关闭，新Penpot/Nexus/OMV/Jellyfin/Grafana五入口HTTP200。
- final-live-network-identity.json：12角色严格ub、new19/default/DNS；14永久实例运行、7模板、临时9012已清理；vmbr19无host地址，host客户端route经21.23，hostforward0。
- maintenance-ended.json：仅本site限时silence解除，17UP，无未处理Prom/Alertmanager活跃告警，Mac外部probe仍disabled；不宣称迁网后新发了Lark vendor测试通知。
- Java模板9011真实clone/清洁度/JDK非root/DHCP与严格SSH验收通过，QA9012删除且232恢复；Java业务全部停用、Publisherfenced。

本期network19验收25项passed；CF原remote ingress/public业务仍独立pending。WAN仅一条TEST-NET源SYN负例精确drop+1，WAN DHCP反向/全端口覆盖未实演。host reboot/断电/RPO_RTO未实演，不能从静态持久配置、来宾reboot或当前全0读回推导已通过整机灾备。完整状态见network19-acceptance.json/md。
