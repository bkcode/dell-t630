> 文档状态（2026-11-08）：本页为阶段实施/技术记录，旧网段、角色数和通过结果按原时点解释。基础已恢复；本轮仅补齐与清理，用户暂不迁移/合并，Mac外部探针不需要。当前配置见[访问清单](../../12-service-access-and-operations.md)，范围与恢复证据见[最新交接](../../11-live-handoff.md)；旧初始化器不得重跑。

# server19 实包验收计划与有限窗口结果

最初为只读准备；其后主AI明确开放有限窗口，已执行的子集见packet-acceptance.json。不启动服务监听器、不改NIC/IP/MAC、不reset counters、不启动/停止来宾。未执行项须再由主AI确认前置后执行。测试地址/身份只取`network19/migration-plan.json`、`contracts/`和`evidence/migrated-access.json`；230在08:55Z采样时为主AI计划停机，不开故障调查，之后恢复以主AI新读回为准。不要根据旧SSH target或准备文件判断某角色已完成迁移。

## 前置与证据方法

- 主AI先选**已运行、无业务的**230/231/232之一作为source。230须在其计划性shutdown结束后使用；本轮不启动它。记录源hostname、MAC、唯一19地址、bridge port直连tap/veth且firewall=0。PVE vmbr19没有IPv4/IPv6地址，bridge-nf调用仍0，bridge ACL存在。
- 只用可信管理入口/QGA和当前fingerprint；230本阶段发生过已核验rotation，不能继续拿迁移前旧fingerprint作现行标准，更不能关StrictHostKeyChecking。
- 读`nft -j list table bridge dell19_acl`中rule handle/comment/counter前后差，**不清零**；记录同一测试窗口、独特TCP source port/ICMP identifier及3个固定合成包。必要时主AI在source tap与gateway tap190i1做精确过滤的header-only捕获，不保存pcap/应用正文，不使用tcpdump -A/-X。
- 负向TCP结果必须同时有：目标已迁到新IP、QGA确认目标端口LISTEN、来自授权source的同期正向连接成功、拒绝rule计数/路径旁证。timeout/closed本身不是ACL通过。
- 合成SYN不发认证/SQL/HTTP业务payload。`socket.create_connection((literal_ip,port),timeout=3)`只记录连接成败/errno类别，成功即close；MySQL会主动发握手，但不读取/记录它。不要对Nacos管理员/业务密码再做试错。

## 可立即分阶段执行的用例

| ID | source → destination / 操作 | 通过标准 / 对应证据 |
| --- | --- | --- |
| N19-PKT-001 | 管理PVE21.22、管理PC21.116 → 已运行canary19地址:22；使用当前可信SSH | 严格SSH成功、hostname/IP匹配；非管理LAN不得因此获得数据管理端口。仅从QGA看到IP不能代替这项 |
| N19-PKT-002 | canary →19.1 UDP53/TCP53，固定匿名DNS请求；再正常TLS访问deb.debian.org固定README | DNS响应可解析、HTTPS证书校验正常且HTTP200；仅resolvectl DNS配置值不算解析通过，失败分开定位不自动改规则 |
| N19-PKT-003 | root已迁Ops19.70 → canary19.40/41/42:9100 | 先目标ss确认newIP监听，再TCP/匿名GET /metrics仅计状态/样本数；未迁Ops时保持pending，不能用旧Ops超时判失败 |
| N19-PKT-004 | prod Java19.40/41/42 → prod DB19.10:3306；prodinfra19.11 →19.10:3306 | 200/201已ready后真实连接成功；peer tuple计数增加，GW LAN forward不应承载这次同19 peer流量 |
| N19-PKT-005 | test Java19.45 → test data19.20的3306/6379/5672/8848/9848 | 必要角色已迁并真实LISTEN，五端口成功；然后用同target做home/tools未经授权反向拒绝 |
| N19-PKT-006 | test19.45/home19.60/普通tools19.31 → prod19.10:3306及19.11四数据端口 | 同期授权prod连接成功；本组timeout且bridge east-west-denied有匹配增量，绝不发DB认证内容 |
| N19-PKT-007 | canary使用真实MAC/IP但原始Ethernet目的改为vmbr19宿主MAC，IPv4目的21.22，TCP SYN22/8006 | PVE服务同期从管理LAN可达；host_input drop计数增加、没有SYNACK，说明没有利用Linux弱主机模型跳过GW。**普通OS connect经GW被拒绝不能替代此L2测试** |
| N19-PKT-008 | canary真实接口发送3个小ICMP帧到19.1；Ethernet source改为未登记测试MAC，IPv4 source仍自己的真实IP | unknown-port-or-source-MAC增量、源tap见包但gateway tap不见此identifier；不改接口MAC，不用其它真实角色MAC |
| N19-PKT-009 | canary真实Ethernet source，IPv4 source改为主AI保留的未使用QA测试IP，目的19.1 | guest-source-IP-binding增量、gateway tap不见该identifier；必须先确认该测试IP没有运行对象/租约。因为伪source不接回复，不能用无echo reply单独判断DROP |
| N19-PKT-010 | ARP request SPA0.0.0.0→19.1，Ethernet source真、ARP SHA改为独立测试MAC | ARP-SHA-source-binding增量。SPA0避免在规则缺陷时污染真实角色IP的邻居缓存。合法SHA的同类ARP probe作为正控 |
| N19-PKT-011 | ARP reply SPA0.0.0.0、真实SHA/MAC、目的GW；对照合法真实SPA ARP | 非法reply的ARP-source-IP-spoof计数增加，合法真实SPA可通过。若要试冒用真实GW/prod SPA，必须另外隔离QA网络，不能在当前真实19网赌规则无缺陷 |
| N19-PKT-012 | canary原始IPv6 frame、单层802.1Q/802.1ad frame，各3个，内层仅合成诊断数据 | no-ipv6-vlan-bypass计数与source capture对应、gateway tap无该frame。此处证明ethertype机制拒绝，不把下游无IPv6/VLAN服务当隔离证据 |
| N19-PKT-013 | canary发合法源MAC/IP的IPv4帧，目的IP为已ready同19数据peer，但Ethernet目的故意设GW LAN MAC | no-peer-hairpin-through-gateway增量、GW入口没有这组packet；对照同source直peer MAC的授权连接能通，防止借GW绕过L2 peer矩阵 |
| N19-PKT-014 | 主AI用已注册MAC的专用QA/raw DHCP client发DISCOVER，不运行dhclient、不改网卡配置 | gateway OFFER的server-id19.1、chaddr/XID匹配、yiaddr属于批准保留/动态池；只记录metadata。DISCOVER/OFFER不等于REQUEST/ACK持久租约验收 |
| N19-PKT-015 | 静态、无DHCP客户端的两个QA之间发送固定XID的伪server OFFER（不使用任一真实客户端XID），来源普通port | 不到接收tap，匹配bridge drop计数；合法gateway OFFER可到。同网广播/67→68不应被普通来宾冒充。若下游只因UDP68 closed不回应不算通过 |

## 原始帧发送边界

这些反欺骗测试应由主AI用AF_PACKET或已审核工具发**固定3帧**，不使用`ip addr add`、`ip link set address`、iptables/nft变更等方式模拟。以实际接口MAC构造Ethernet、IPv4/ICMP/TCP及正确checksum；所有payload为固定合成标记。MAC spoof使用与所有已注册MAC不同的本地管理unicast测试MAC，IP spoof使用主AI预留且已确认未运行/无租约的QA地址，不能替真实业务地址作ARP宣告。

在规则意外放行时停止本组，不再扩大到真实ARP欺骗/其它主机，先保留精确counter/capture元数据交主AI。没有现成raw工具时，不临时装整套扫描/渗透工具；先审核一个最小固定帧sender，再授权运行。不扫描整个LAN，不注入业务协议数据。

## DHCP证据不能混用

现有`gateway/lease-probe-evidence.json`是同UID写lease文件权限与dnsmasq --test，明确`DNS_DHCP_bound_by_probe=false`；它不是线上的DORA包验收。若本期要求完整DHCP租约，另由主AI在专用QA上跑REQUEST/ACK，并核lease文件/重启持久性；这会改变QA网络/lease状态，超出本次只读准备。未知模板/clone即便取得offer/lease也保持DHCP-only，登记VMID/MAC/IP/role后才能获业务权限。

## 结果分类

每例记录：开始时间、前置就绪证据、源/目的身份、live rule handle/comment、probe元数据、counter前后、目标监听/授权正控、结果passed/failed/inconclusive/pending。不满足前置一律pending/inconclusive。实际有限窗口已完成：PVE→230/23122与9100四正控，230/231共8项peerSSH/exporter及经GW到host22/8006拒绝；3个unicast UDP（DNS正控/错MAC/错srcIP）及1个source真实的直发hostMAC SYN，0ARP、0持久变更。原始帧案例按主AI批准改为UDP，不声称执行过本表其它ICMP/ARP/VLAN/DHCP用例。MAC/IP专用drop各+1；host_input共享counter+10有背景噪声，不写精确+1归因。PVE被动快照readiness-passive-state.json中230为计划停机，随后主AI恢复后才执行本窗口。其它用例仍pending。
