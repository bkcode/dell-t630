> 2026-11-09现行网络：基础服务恢复、宿主forward守卫跨自然重启保持；新增普通21网到测试Nacos19.20 TCP8848/9848专属许可，其他边界保持。不迁移/合并/启Java，无Mac外部探针；原迁网与历史故障证据按各自时点保留。

# server19 网络交付与当前配置

更新：2026-11-09，Asia/Shanghai。本文区分现行网络许可与历史迁网验收；11月7日UEFI0058是历史故障，基础服务已恢复。现场恢复条件见[交接](11-live-handoff.md)，人工操作见[手册](19-manual-operations.md)。

## 拓扑与地址所有权

```text
外网Mac/手机：WireGuard 10.66.66.0/24
                  |
OpenWrt主路由 192.168.21.1（WireGuard终点、上游分流）
  静态路由 192.168.19.0/24 → 192.168.21.23
                  |
交换机/光电链路 ─ PVE vmbr0
  PVE 192.168.21.22：SSH22 / UI8006，仅管理与二层桥
  VM190 WAN192.168.21.23 → LAN192.168.19.1
                              |
                      PVE vmbr19（宿主无IP）
                              |
                  全部应用/数据/家庭来宾19.x
```

PVE旧vmbr10/20/30/40、10.63地址、宿主应用DNAT及专用NAT/filter表已移除，旧加载器masked，IPv4/IPv6宿主forwarding全部0。宿主19/24经21.23路由仅供宿主客户端访问来宾，不等于为其它设备转发。

普通交换机不分配这个新子网地址。19网在PVE内部，由190负责路由/DNS/DHCP，网关不做NAT；OpenWrt继续负责上游分流。所有服务用真实19地址访问，不再走21.22端口映射。

## 最后验收的角色

| VMID | 地址 | 作用 |
| --- | --- | --- |
| 190 | WAN21.23 / LAN19.1 | 路由、DNS、DHCP、防火墙 |
| 100 | 19.5 | 原Cloudflare Tunnel LXC |
| 200 / 201 | 19.10 / 19.11 | 正式MySQL / Redis+RabbitMQ+Nacos |
| 210 | 19.20 | 测试数据组件 |
| 220 / 221 | 19.30 / 19.31 | 发布基础 / 独立Nexus，尚未合并 |
| 230 / 240 | 19.40 / 19.45 | 正式/测试JDK基础各1，无业务程序 |
| 250 | 19.50 | 定制Penpot |
| 260 | 19.60 | OMV/SMB/Jellyfin |
| 270 | 19.70 | 监控及内部Lark |

全部19地址前缀为192.168；来宾默认网关和DNS均19.1。现有12实例、3停止模板（9001/9010/9011）。旧101/104、重复231/232及旧QA已在清理阶段退役；原迁移证据里出现这些ID不代表仍保留。

同19网东西向由 `bridge dell19_acl` 做端口MAC/IP绑定和角色隔离；仅网关防火墙不能隔离同子网来宾。未知clone须先分配唯一IP并登记MAC/IP ACL，模板本身不启动为服务机。正式/测试/家庭隔离边界继续保留。

DNS由19.1转OpenWrt21.1，兼容原Fake-IP代理；原公共协议和CF7844例外按已验配置保留，不绕过OW分流。跨子网广播发现不保证，SMB/电视请直接填写NAS地址。

## 普通LAN到测试Nacos：两层专属规则

新增范围严格为`192.168.21.0/24 → 192.168.19.20 TCP {8848,9848}`，让普通LAN/Wi-Fi客户端使用现有测试Nacos控制台/API与客户端gRPC。之前普通客户端不在21.22/21.116管理例外内；这不是Nacos数据、namespace或密码故障，不通过重启服务/改认证来修复。

1. GW190的owned规则允许上述WAN→LAN转发，hot事务后独立核验确认，现役服务PID未变。[网关回执](network19/lan-nacos-20261109/gateway-confirmed.json)、[独立核查](network19/lan-nacos-20261109/gateway-independent-check.json)。
2. PVE桥的owned表仅新增1条同source/destination/twoports许可，仍先执行原MAC/IP身份与invalid检查；hostforward保持全0，无NAT，未把宿主变成三层网关。[桥回执](network19/lan-nacos-20261109/bridge-confirmed.json)、[精确规则核查](network19/lan-nacos-20261109/bridge-independent-check.json)。

| 来源与路径 | 已观察结果/边界 |
| --- | --- |
| Studio 192.168.21.230 → test19.20:8848/9848 | HTTP200、TCP9848成功；保留Nacos认证/namespace权限 |
| 同Studio → test19.20:3306/22/9849 | 实际timeout，未随NacosLAN许可开放 |
| 同Studio → prod19.11:8848/9848 | 实际timeout，正式环境未放开 |
| Air Wi-Fi | 用户明确反馈成功；没有逐项HTTP/nc输出，不能补造更细验收 |
| 原21.22/21.116管理例外 | 原有管理许可保留，Studio普通来源负测不能覆盖这些特例 |
| VPN10.66.66/24 | 原全服务合同保持，每peer/32与应用认证不变 |

[LAN负测](network19/lan-nacos-20261109/LAN-negative-tests.json)记录PVE看到的来源21.230；[Air确认](network19/lan-nacos-20261109/Air-user-confirmation.json)单列用户反馈及其证据限制。本次不新增ICMP放行，ping不通不代表HTTP/gRPC不可用；使用目标TCP/HTTP和认证结果分别判定。没有更改OW、DNS、数据、namespace、密码或业务profile，不新增公网入口。凭据只经既有私有渠道，不把具体值或私有凭据文件加入Git。

## WireGuard 范围

用户明确授权 `10.66.66.0/24` 访问19/24全部有效IPv4服务端口及网关自身入口；账号认证与文件读写权限保留。网关与NAS来源规则已配套，不做SNAT；OpenWrt每peer仍独立/32，客户端AllowedIPs和服务防火墙来源白名单各有作用，不能相互替代。详见[VPN访问](16-wireguard-access.md)。

## Java、模板与监控

- 唯一Java验收模板9011无业务JAR/配置/秘密；Linux9010、Docker9001也保留，三者均带fish且默认Bash。
- 230/240无Java业务，测试五服务已停止/禁自启；publisher fenced，不因恢复网络而自动上线业务。
- 最后综合验收10node+5Ops=15/15UP。较早网络证据中的14角色/17targets属清理前快照；Nexus合并后预期11实例/14targets，当前尚未达到该目标。
- Mac外部探针保持停用；公网CF域名、真实电视/PS、长期备份SLO等未因内网网络通过而自动签收。

## 历史证据索引

下列文件保留原执行时的ID、数量与结果，不修改成今日数据：

| 核验 | 证据 |
| --- | --- |
| 原网络迁移、来宾身份 | [最终网络身份快照](network19/evidence/final-live-network-identity.json) |
| 当时管理端口与真实应用入口 | [Mac复测](network19/evidence/Mac-final-management-and-services.json) |
| 网关正常重启持久化 | [网关重启](network19/gateway/reboot-evidence.json) |
| DHCP四阶段 | [专用QA发包](network19/evidence/DHCP-real-QA-native-capture.json) |
| 未受信WAN负例 | [有限负测](network19/evidence/WAN-untrusted-source-negative.json) |
| Java模板 | [模板说明](network19/java-template/README.md)、[克隆](network19/java-template/clone-evidence.json) |
| 整理后的最终部署/监控数量 | [02:35综合验收](cleanup/final-live-check.json) |

原网络验收历史见[网络验收](network19/audit/network19-acceptance.md)，本次LAN-Nacos新增许可以上方独立回执/负测及用户确认为准；后续操作仍需fresh核查，不重放旧stage/commit刷新日期。
