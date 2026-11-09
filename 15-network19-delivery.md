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

## 普通LAN21到server19：两层受信访问

最新用户授权已扩为`192.168.21.0/24 → 192.168.19.0/24`全IPv4协议，并允许访问网关自身21.23/19.1；SSH仍为key-only，应用账号/namespace/数据库权限和各服务监听条件保留。网关owned hot规则与PVE bridge owned表均已确认，桥上仍先核MAC/目标IP绑定与invalid，不放开任意来源、IPv6或来宾间角色矩阵。PVE hostforward仍全0、网关与PVE均无NAT，WG10.66.66/24全服务许可不变。[网关确认](network19/lan-trusted-20261109/gateway-confirmed.json)、[桥确认](network19/lan-trusted-20261109/bridge-confirmed.json)、[23:34最终后检](network19/lan-trusted-20261109/final-postcheck.json)。

[实际LAN抽测](network19/lan-trusted-20261109/LAN-positive-tests.json)已观察ub严格SSH到19.20和21.23、19.20 TCP3306/8848/9848、19.11 TCP8848及19.20 ping成功。hot未重启网关服务、PID保持；最终无pending事务、rollback timer inactive。Air宽范围没有重新逐项输出，不补造整网全端口或应用认证验收；ping只能帮助判断路径，仍须用目标TCP/HTTP和认证结果确认服务可用。

早前[Nacos-only专属回执与负测](network19/lan-nacos-20261109/LAN-negative-tests.json)及[Air当时反馈](network19/lan-nacos-20261109/Air-user-confirmation.json)保留为扩权前历史：当时Studio到MySQL/SSH/正式Nacos超时，不能再表述为当前拒绝边界。本次没有更改OW、DNS、数据、密码、SSH认证或业务profile，也未新增公网入口。凭据只经私有渠道，不把具体值或凭据文件加入Git。

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

原网络验收历史见[网络验收](network19/audit/network19-acceptance.md)，本次LAN21受信访问以上方lan-trusted独立回执与最终后检为准；后续操作仍需fresh核查，不重放旧stage/commit刷新日期。
