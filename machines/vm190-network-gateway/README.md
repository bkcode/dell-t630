# VM190 network-gateway

**配置合同，不是当前在线导出。** 最后综合基线2026-11-07 02:35:01；T630因UEFI0058/B1内存路径故障暂停，当前runtime未复验。这里没有远程读取或改动。

本机资料：[配置合同](config.json)、[安全来源索引](config-sources.json)，资源/IP以[plan](../../plan.json)为准：2vCPU、512MiB、32GiB稀疏fullclone；WAN21.23/24 vmbr0、LAN19.1/24 vmbr19，按原MAC识别eth0/eth1。先于其它来宾启动的顺序合同在JSON中，当前不执行start。

## 路由、VPN与最新DNS

- 专用IPv4路由/防火墙、DNS/DHCP，**无NAT**；默认到OW21.1。PVE21.22只管理/L2，见[PVE](../pve/README.md)。同19东西向不经本机，不能用网关规则代替PVE bridge ACL。
- 已批准完整WireGuard10.66.66.0/24访问19有效IPv4服务及21.23/19.1，应用账号权限保持；不是历史只放Penpot9001的窄规则。peer终止在OpenWrt且各/32，本机不保存peer私钥。细节见[VPN合同](../../16-wireguard-access.md)。
- 02:31最新DNS-only清理已验证：保留11服务名、删除11退休记录，UDP/TCP正确，退休名NXDOMAIN；publish-service30与artifact-service31继续独立，Nexus尚未合并。索引指向[DNS summary](../../cleanup/network/dns-runtime/summary.json)，未复制旧22记录preview冒充现役。
- DNS仅LAN19.1 TCP/UDP53，上游21.1；DHCP池19.200–239/1h、GW/DNS19.1。租约内容不读取或复制。LAN真实DORA有旧证据，不外推全部WAN DHCP反向验证。

当前没有保存整份runtime nft/网络导出，因为bundles/candidates有阶段属性；只索引能追溯的公开资料。恢复先读[交接](../../11-live-handoff.md)与[人工手册](../../19-manual-operations.md)，不重放stage/commit，不清日志、重置DHCP租约或缩模板盘。默认Bash不变，fish只安装。
