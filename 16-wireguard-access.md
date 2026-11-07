> 2026-11-07状态：服务器因UEFI0058内存故障暂停。本文为既有VPN配置及历史验收，不代表当前在线；硬件处理后按[交接](11-live-handoff.md)复验。Nexus合并已授权、未执行。

# WireGuard受信网段访问全部服务器服务

2026-11-07（Asia/Shanghai）。当前有效范围是用户明确授权的 **10.66.66.0/24 → 192.168.19.0/24 全部有效IPv4服务端口**，并允许该VPN来源访问网关自身21.23、19.1。外网Mac Air已对提供的9个HTTP入口批量复测，确认“全部正常访问”。具体HTTP状态码未提供，不虚构逐项200；SSH登录、SMB认证、数据库授权仍按各服务原账号权限执行。

## 根因与最终配置

实际客户端10.66.66.3的SYN已到VM190 WAN，但原网关及bridge白名单只有21网段来源。前向路由为19网口，回程经OpenWrt21.1，局域网Penpot访问200；来源过滤是确定缺口，不需要加SNAT修复。

| 层次 | 当前配置 |
| --- | --- |
| 网关190 FORWARD | WAN来源10.66.66.0/24到LAN19/24全部有效IPv4，不限服务端口 |
| 网关自身INPUT | 该VPN来源到21.23与19.1的IPv4服务，原SSH仍key-only |
| PVE二层ACL | 该来源经已登记网关访问已登记server19；MAC/IP绑定及guest间role矩阵保留 |
| NAS三SMB共享 | 原21/19/127 hostsallow追加10.66.66/24，原用户/读写/guest策略不变 |
| Jellyfin | LocalNetworkSubnets追加10.66.66/24；RemoteAccess=false、UPnP=false保持 |
| PVE宿主 | 21.22管理/二层，forward0、无NAT，不恢复旧应用端口转发 |

本次没有改OpenWrt、客户端路由、peer密钥或账号。DNS/DHCP仍按原服务监听设计，不新增WAN DHCP。网络放行不会启动此前已停止的Java业务程序，也不替代各应用登录认证。

## WireGuard两端AllowedIPs

| 位置 | 应保持的含义 |
| --- | --- |
| OpenWrt服务端air peer | 10.66.66.3/32，识别该客户端并路由回它 |
| OpenWrt服务端phone peer | 10.66.66.2/32，各peer保持独立地址 |
| 外网客户端peer AllowedIPs | 决定目标流量走VPN，当前已包含21/24、19/24及默认路由 |

不要把19/24加到OpenWrt的air/phone服务端peer，也不要把两个peer都改成相同10.66.66/24。服务访问白名单与WireGuard加密路由是不同设置。

## 变更及验证记录

先前未获全服务明确授权时，宽范围尝试被自动审批拒绝且未执行；随后先落地了VPN全来源→Penpot9001窄规则并复测成功。用户在知悉宽范围含义后明确要求“10.66.66.0/24在23网关都放行”“保证访问服务器上所有服务”，本次据此升级全服务范围，见[新范围授权](network19/wireguard/full-access-authorization.json)。旧窄规则证据[verification.json](network19/wireguard/verification.json)保留为历史。

- 网关40项回归、原生解析及精确配置delta通过；新SSH/nonce确认，pending/watchdog均关闭。网关服务PID未变，无重启、无SNAT。
- full新流使用mark5并保留旧窄规则mark4回包；INPUT通用established排除mark5，已预检回退旧窄规则可撤销full试流。原规则备份留目标root私有目录，不全局flush。
- NAS首次stage因实际XML同行闭合格式安全拒绝，未停业务；8项转换fixture修正后新nonce提交成功。提交前播放/暂停/转码、SMB会话/锁均0；JF经原单元必要重启，官方Samba Salt也使smbd PID变化；Docker和VM未重启。身份、原文件SHA、UUID、原读写/匿名拒绝回归保持。
- 用户Mac Air已确认提供的Penpot、Nexus、OMV、Jellyfin、Grafana、Prometheus、Alertmanager、正式/测试Nacos共9个HTTP入口全部正常。具体HTTP码、远端SMB/SSH认证结果及可选网关DNS测试未分别提供，不能扩写为逐项认证验收。

最终证据：[全服务验证](network19/wireguard/full-access-verification.json)、[网关确认](network19/gateway/live-confirm.json)、[实际全服务规则](network19/gateway/WG-full-active-counter.json)、[NAS适配](network19/wireguard/media/apply-result.json)、[NAS读回](network19/wireguard/media/readback-result.json)。原局域网9入口也全部HTTP200，角色隔离/宿主管理模式保留。

最后整理验收时规模：1台物理T630，运行11台VM+1个CF LXC共12实例；只保留9001/9010/9011三份停止模板，旧模板/停止QA已备份清理。Java正式230与测试240各一，无业务程序。Nexus合并220已获维护授权，因硬件与用户暂停尚未执行，WireGuard信任范围不变，见[18整理结果](18-cleanup-and-consolidation.md)。
