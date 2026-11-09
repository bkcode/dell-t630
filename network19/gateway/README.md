> 文档状态（2026-11-08）：本页为阶段实施/技术记录，旧网段、角色数和通过结果按原时点解释。基础已恢复；本轮仅补齐与清理，用户暂不迁移/合并，Mac外部探针不需要。当前配置见[访问清单](../../12-service-access-and-operations.md)，范围与恢复证据见[最新交接](../../11-live-handoff.md)；旧初始化器不得重跑。

# VM190 server19 独立网关

当前状态（2026-11-09 23:34）：网关190已运行在19网络，正常重启持久性与后续Fake-IP/WireGuard更新有独立历史回执。本次LAN21受信访问的[hot确认](../lan-trusted-20261109/gateway-confirmed.json)与[最终只读核查](../lan-trusted-20261109/final-postcheck.json)证明实际配置SHA与本地bundle一致，三自有unit active、无pending事务/活动rollback timer、无NAT。`192.168.21.0/24`可访问`192.168.19.0/24`全IPv4服务及网关自身21.23/19.1，原应用认证保留；WG10.66.66/24许可保持。只在网关和PVE桥两层已批准规则上扩权，PVE仍只管理/L2、IPv4/IPv6 forwarding全0。本轮canonical同步仅本地生成，无远程变更或重启；Air宽范围尚未重新逐项复测。

以下最初stage/canary/失败回退说明按实施时点保留；不能把旧“packet pending/旧应用原网”阶段读成当前网络状态。

资源与地址唯一来源是上级`migration-plan.json`：VM190/network-gateway，从9010全克隆，2vCPU、512MiB、**32GiB sparse虚拟盘**，没有缩盘或创建新PVE模板。WAN `192.168.21.23/24`、默认路由`192.168.21.1`；LAN `192.168.19.1/24`。两NIC固定MAC为`02:63:19:01:90:00/01`，运行期以MAC定位实际接口，不依赖eth0/eth1；目前恰好观测为eth0/eth1。

## 实现与安全边界

- `policy.py`严格编译主AI给定的gateway_policy与地址清单。基础管理例外保留PVE21.22和Mac21.116；后续明确受信LAN21/24与WG10.66.66/24可访问网关自身21.23/19.1的IPv4服务，SSH仍须原认证。19来宾不能SSH网关。SSH只保留pubkey认证，原ub与host key不轮换，客户端私钥留Mac。
- `systemd-networkd`以`[Match] MACAddress`应用双静态IP；只有WAN默认路由。原backend已实际确认networkd，没有切换未知renderer。CloudInit后续不覆盖网络，原生成网络文件保留作为回退。
- 自有`inet dell_gateway19`仅3条filter链：input/forward默认drop、output允许网关自身正常OS出站；**无NAT/SNAT/DNAT**，公网NAT归OW。禁止`nft flush ruleset`，发现外来表拒绝接管。
- WAN→LAN按主计划矩阵与明确的受信LAN21/24、WG10.66.66/24全IPv4特性，19→公网排除私网/保留地址，只允许指定DNS/web/NTP/ICMP；CF19.5额外保留TCP/UDP7844，通用443仍有，publisher19.30可出公网SSH22。CF对旧21网origin兼容只限计划列出的6个端口，未知account-side origins不是全放依据，origin E2E仍未验。
- new-flow批准后写专用ct mark，established/related仅接受该标记；同LAN→同LAN经网关绕行直接drop，不能用网关绕过PVE bridge东西向隔离。真正同19/24流量通常不经网关，必须由主AI的bridge/vNIC ACL保护。
- boot先all+WAN+LAN IPv4 forwarding全0并原子加载filter。networkd文件不设置IPv4Forwarding，防止网络管理器提前打开入接口转发；ready核对路由/filter/IPv6后才开启all+WAN+LAN全1并重新hardening。停止FW/ready执行quiesce三者全0。
- IPv6仅WAN/LAN接口关闭，默认新接口关闭；不改kernel ipv6.disable或all.disable_ipv6，lo恢复`::1/128`。实际审计IPv6地址仅有lo::1。

## LAN DNS/DHCP

dnsmasq仅LAN19.1的TCP/UDP53，DHCP池19.200–239（40个、1h），router/DNS均19.1；全部静态地址低于200。WAN和lo排除DHCP/DNS绑定，upstream21.1，不读取任意hosts，不记录query日志，不开启RA/DHCPv6。

实际身份解析为dnsmasq UID999、primary group nogroup GID65534；自有unit从此非root身份启动，Ambient/Bounding仅NET_BIND_SERVICE、NET_RAW、NET_ADMIN（实际CapEff/CapAmb=0x3400），NoNewPrivileges、ProtectSystem=strict，MemoryMax64MiB/Tasks32。发行版lease文件`/var/lib/misc/dnsmasq.leases`属999:65534、600，只给该精确文件ReadWritePaths，整个misc目录原root755不改。现有非空lease文件不会被覆盖；后续维护需另行审查现有租约，不可强制清空。

首次应用在旧自定义lease目录失败（启动UID0、目录DNS用户750，不能创建文件），原事务实际自动回退：all/两接口转发0、旧networkd及strict SSH恢复。没有观察到该路径AppArmor DENIED，未关闭或放宽AppArmor。最小修订改默认lease路径、非root同UID/三cap；独立transient文件FD零写+dnsmasq --test通过后才第二次stage。首失败、诊断及rollback证据保留，未盲重试。

## 事务与命令

nft通过一次`nft -f`原子替换**自有表**。地址、sysctl和systemd不能成为一个内核原子操作，因此使用备份/独立apply单元/三分钟回滚watchdog与确认事务，不将跨组件操作误称为瞬时原子。

```bash
# 本地只编译/测试，不改变网关
python3 dell/network19/gateway/prepare.py
python3 dell/network19/gateway/test_gateway.py
# 仅已获主AI190 standby窗口时，native解析不加载规则
python3 dell/network19/gateway/validate-native.py

# 只有主AI完整190 apply窗口才运行；新SSH check后用该次新nonce确认
python3 dell/network19/gateway/manager.py stage --reviewed-190-apply-window
python3 dell/network19/gateway/manager.py check
python3 dell/network19/gateway/manager.py confirm --nonce <本次32hex>
# 若未确认/失败，保留原watchdog或由主AI明确调用rollback，不能宽泛放行
```

stage预先快照自有文件/表、全部被hardening触及的sysctl、原unit状态，校验nft/dnsmasq/systemd语法。独立timer同时用OnActiveSec=180s和UTC OnCalendar/Persistent保护当前boot断联与重启漏触发；apply在独立systemd单元运行，不因SSH断联取消。confirm必须新strict SSH验证ub/hostname/原host key、匹配该次nonce和actual check，才关闭watchdog。外层stage/apply/confirm/rollback共用锁，boot/ready子单元不抢同一锁，避免依赖死锁。

rollback先quiesce全0，停止自有DNS/ready/FW，只恢复/删除自有nft表、原文件、原networkd及所有记录sysctl，并逐键readback；原管理静态地址/默认路由恢复。包、公开恢复代码和已产生租约保留，不删业务数据；任何异常由主AIQGA/控制台救援，不回到PVE临时NAT冒充成功。首次应用阶段未自行重启；后来已由主AI授权正常重启并验收，见[实际重启回执](reboot-evidence.json)。

## 验收标准与实际证据

证据在本目录；MAC/IP不是秘密，文档/日志不含客户端私钥、CF token或其它业务凭据。

| ID | 前置 | 步骤 | 可观察通过条件 | 证据 | 状态 |
| --- | --- | --- | --- | --- | --- |
| GW19-01 | 主AI创建190并给trusted target | 验hostname、两MAC/地址、Debian13、pubkey SSH | 仅190，双静态地址与主计划相同，原key严格复连 | 上级evidence/gateway-initial-access.json | 通过 |
| GW19-02 | 仅190 standby授权 | 临时policy-rc.d抑制maintainer，apt最小nftables/dnsmasq，默认unit前后mask | policy恢复，默认服务停放，无DNS/DHCP/forward提前启用 | standby-evidence.json | 通过 |
| GW19-03 | 本地合成输入 | 负向parser/MAC/port/DHCP冲突、boot先0/失败复0、snapshot逐键恢复 | 26项回归通过，不操作真实网络 | validation.json | 通过（离线） |
| GW19-04 | 190 standby | nft-c、dnsmasq --test、systemd verify | 全exit0，前后all/两iface0，kernel表空；同UID/三cap精确leaseFD写可用 | native-parse-evidence.json、lease-probe-evidence.json | 通过 |
| GW19-05 | 完整apply授权 | 第一失败触发原事务rollback，修订后新stage/check/confirm | 原失败安全恢复；第二次新nonce/新SSH成功，pending与timer关闭 | first-attempt-live-stage/check、first-apply-diagnostic、live-stage/check/confirm.json | 通过 |
| GW19-06 | 已确认配置 | 查filter/route/forward/IPv6/实际DNS身份及短UDP/TCP查询 | 三filter链、input/forward drop、无NAT、唯一WANdefault、三forward1、lo-onlyIPv6；静态域A正确 | active-audit.json | 通过（网关本机） |
| GW19-07 | 主AI迁首台230 canary | 真实19客户端到21/公网、DNS/DHCP和WAN拒绝测试 | 实际packet/count/源地址证明经GW无SNAT，授权通/禁止drop、DHCP只LAN | [实际跨网验收](../audit/network19-acceptance.md) | 已另行留证（不外推公网origin） |
| GW19-08 | 主AI明确190 reboot窗口 | 重启190再验启动顺序与持久性 | FW先于转发，MAC/IPv6/默认路由/服务恢复，PVE不接管L3 | [网关重启回执](reboot-evidence.json) | 已另行通过 |

## 官方机制来源

[nftables原子规则替换](https://wiki.nftables.org/wiki-nftables/index.php/Atomic_rule_replacement)解释`-f`单事务；[Debian13 dnsmasq手册](https://manpages.debian.org/trixie/dnsmasq-base/dnsmasq.8.en.html)提供bind/interface、listen-address、DHCP范围和`--test`；[Debian13 systemd.network](https://manpages.debian.org/trixie/systemd/systemd.network.5.en.html)明确MAC匹配、IPv4Forwarding可按接口设置且未指定时不修改；[Linux IP sysctl文档](https://docs.kernel.org/networking/ip-sysctl.html)指出ip_forward变化会重置router默认参数，因此本包重新hardening并完整备份/恢复相关键。

## OW Fake-IP 精确兼容热更新

230 canary已由主AI验证strict SSH、DNS19.1和exporter；随后发现OW现有代理将deb.debian.org/one.one.one.one返回198.18/15，原保留地址排除阻断域名TLS。主计划新增OW_fake_IP_proxy_compatibility后，190只热更新自有nft表与持久compiled config：源19/24→目的198.18/15，TCP53/80/443、UDP53/123、ICMP。NONPUBLIC集合仍保留该范围，只有这3条精确分支例外；其它private排除、反欺骗、默认drop、无NAT保持，OW与上游DNS未改。

Fake-IP新流用独立ctmark0x19000002，启用时return-state允许mark1/2；保存的旧规则仅接受mark1，因此rollback也能撤销试运行Fake-IP已建流。热回退仅原子恢复旧config/nft，不停网络/DNS或改地址/sysctl。watchdog仍是3分钟独立单元，必须新strictSSH+nonce确认。

首hot因systemd-run Type=oneshot等待与父事务锁冲突，未激活新规则；原hot回退恢复旧策略、无pending且服务正常，证据first-hot-failed-stage.json/hot-first-rollback-proof.json保留。最小修--no-block与回归后，用新nonce f70b480afb5946658b7d111bb6f443c0完成hot-stage/check/confirm。26回归与active状态native nft-c通过；live-confirm.json证明热更新中6个persistent unit的PID/启动时间完全相同，forward三者仍1，DNS/LAN/IPv6状态保持。域名TLS实际结果由主AI230复测证据确认，本子任务不把配置通过当作TLS成功。

当前源码冻结SHA：policy.py `ce613212995b93da14f44e80a3cddd5fc753b316545b66b80a2383970a220bee`；manage.py `50b22b884bbb9f49a901532938f09af993b55404b30fabaf974d84aadce71694`。完整manifest在validation.json，初始配置/nonce审计归档在initial-confirmed-*。

## CF Fake-IP补充与重启持久性

主AI诊断CF region1/region2由OW DNS返回198.18.5.144/145且7844超时后，在canonical plan新增仅CF19.5→198.18/15 TCP/UDP7844。本包仅增加这两分支，独立ctmark0x19000003；旧普通Fake-IP mark2和一般mark1保持。新strictSSH nonce10c24105ac9a4dbb87db9f209529c054确认，六persistent unit PID/启动时间相同，无DNS/OW/其它角色改动，28离线回归及nft-c通过。主AI随后已证CF active/running/注册；这不代替未知account-side origin E2E。

CF完成后按主AI独立窗口正常reboot190：reboot-evidence.json中bootID改变、同ED25519指纹不变、config/policy/manage SHA与规范化nft/路由/MAC/双IP相同；三forward1、DNSUDP/TCP、lo-only IPv6、无NAT/failed/pending/timer通过，实际单调时序FW→networkd→ready→DNS正确。未更新knownhosts或跳过key检查。初次postboot NTP尚未同步，后续仅只读等待已NTP=yes/NTPSynchronized=yes（postboot-NTP.json），未改时钟/服务。主AI230真实DNS/SSH/exporter/FakeIP域名HTTPS200已有正证；完整DHCP及WAN negative按主AI全网验收记录。

## 历史：WireGuard → Penpot 窄范围阶段（2026-11-07，已被新授权升级）

该阶段现役扩展只有`WireGuard_client_access`：**源10.66.66.0/24 → 目的192.168.19.50 TCP9001**，WAN→LAN一条ct-new forward规则，专用ctmark0x19000004及counter/comment `WG-Penpot-TCP9001`。没有GW INPUT、ICMP、其它目标/端口、全协议或目标19/24扩展；原mgmt/FakeIP/CF/默认drop/反欺骗/IPv6与无NAT边界保持。OpenWrt及其server peer /32未由本子任务改动。

原whole-server/all-protocol方向被自动审批拒绝，PVE调用在进程启动前被拒；本地曾准备的broad代码已完全收窄，未上传190、未生成/执行broad candidate。主AI向用户解释后采用当前问题的materially-safer目标端口范围，root独立应用同一exact bridge规则后才授权本包hot。

现役SHA先与本地82b0676.../3971c7a...核无drift、无pending，再做34项回归与active nft-c/delta检查。hot新nonce5b997e98f8eb497eb83d04cd5c85fa32经新strictSSH check/confirm，6个persistent unit PID/启动时间相同、无服务restart，pending/watchdog均false，return mark集合只在feature存在时加入mark4；旧原始nft/config按既有hot rollback恢复即可撤销试流，不存在broad INPUT或额外重渲染回退。

证据：WG-before-baseline.json、hot-native-check.json、live-hot-stage.json、live-check.json、live-confirm.json、WG-active-counter.json。确认后专用counter初次采样packets0/bytes0，**远端MacAir HTTP结果仍待用户复测**，不能用配置/本地LAN200代替远端成功。有效URL为`http://192.168.19.50:9001`；只读复核counter/comment可归因新的VPN请求。

## 当前：知悉风险后的受信VPN全服务器授权（2026-11-07）

在先前broad范围被拒、窄范围已交付后，用户获知全服务器/全协议风险，重新明确要求10.66.66.0/24在23网关全放行并可访问服务器所有服务。主AI更新canonical并审核应用对应bridge规则，本包基于当时确认narrow的owned SHA核无drift后实施新的独立授权，不复用或绕过旧被拒操作。

当前`WireGuard_client_access`精确为源10.66.66.0/24→目的192.168.19.0/24全部有效IPv4协议；来自WAN的该源也可访问网关本机**仅192.168.21.23与192.168.19.1**的IPv4服务。invalid/反欺骗/IPv6禁用、其它peer矩阵、DNS/DHCP监听与SSH认证未改，仍无NAT。网络放行不创建服务、不提供账户或绕过既有认证；本期Java业务仍不运行。

新full流用mark0x19000005；旧narrow mark4返回仍保留，已有Penpot会话不被切断。INPUT通用established明确排除mark5，full专用输入规则才接收5；回退时从旧narrow config重新渲染安全等价的nft并预先nft-c，仅增加对旧策略原本不可能产生的mark5的排除，旧raw表也原样归档。这样full forward与本机INPUT试流都不被回退后的通用state规则继续接受；其它mark0/1/2/3/4行为保持。

40项本地回归、exact oldnarrow→full delta与native nft-c通过。实际新strictSSH/nonce51b88f705606416eb2679482c9af1ab4确认，六persistent unit PID/启动时间全部不变，无restart；pending/watchdog=false。policy SHA `bd237ff8c6417306af7cf0a9e3106d0426f5ca6bb54f072984dd9e89638708da`，manage SHA `cc0a50258dbf4abf2621cb7b06b5637413a38462aacd5640ab1ce5a1b9a79074`。

`WG-full-active-counter.json`实际forward handle31、INPUT handle15，comment分别WG-TrustedVPN-Server19-IPv4/WG-TrustedVPN-Gateway-IPv4；return集合mark1..5，INPUT guard!=5，SSH仍pubkeyyes/passwordno/kbdno。首次counter均0包0字节；已建forward流优先命中return-state，所以counter不代表每个数据包。用户Air批量服务访问仍待实测，不能将配置通过当成远端全部服务登录成功。OpenWrt peer各自/32、地址/DNS/路由与其它VM均未由本子任务改变。

首full stage在事务前因check局部变量guard遮蔽身份函数而失败；pending始终false、旧narrow策略仍运行。最小重命名mark5_guard并新增必须实际进入身份guard的回归后完成上述新nonce事务；失败诊断与receipt留WG-full-first-stage-diagnostic.json/WG-full-first-guard-failed-stage.json。
