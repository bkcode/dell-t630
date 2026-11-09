> 更新：2026-11-09（Asia/Shanghai）。本轮基础fresh审计已复核；当日实时收尾状态统一见[11月9日交付记录](../../completion/20261109-prod-db-scope/README.md)。本页仅本地同步带时点证据，不执行服务器操作；不迁移数据、不合并Nexus、不启动Java业务、不升级Penpot，不需要Mac外部探针。

# VM190 network-gateway

## 本轮只读状态与备份归属

15:26:47只读采样：WAN21.23/LAN19.1保持，gateway firewall/ready/dnsmasq均active/success、IPv4 forward1；三静态DNS分别19.50/31/30。未新做DORA、外网VPN或公网origin E2E，不修改网关/OW。 证据：[本机分项审计](../../completion/20261109/network-audit.json)。

本机VM/OS及应用数据不纳入现行自动备份；不因旧whole-VM名单而重新启用。 现行仅正式DB/Nacos逻辑SQL导出（非VM snapshot），PVE落点`/mnt/pve/store/dell-artifacts/prod-db-backups` root700/600；新未列白名单数据库拒绝告警、需更新。03:30/GFS最近3＋每日7＋每周4，首轮3301B与timer见[新回执](../../completion/20261109-prod-db-scope/first-success-and-timer-enabled.json)，实际监控/收尾统一见[新中央入口](../../completion/20261109-prod-db-scope/README.md)。旧11来宾job已disabled、原19,747,582,801B档与21回退档保留不自动删；未restore/无异机DR，不迁移/合并/启Java、无Mac探针。

**配置合同及带时点元数据，不是完整runtime导出。** 11月7日综合基线与UEFI0058/B1事故为历史；11月9日已按顶部网络审计fresh复核地址、单元、forward与静态DNS。本页仅本地同步，无远程修改；不签未执行的公网origin或外部VPN端到端。

本机资料：[配置合同](config.json)、[安全来源索引](config-sources.json)，资源/IP以[plan](../../plan.json)为准：2vCPU、512MiB、32GiB稀疏fullclone；WAN21.23/24 vmbr0、LAN19.1/24 vmbr19，按原MAC识别eth0/eth1。先于其它来宾启动的顺序合同在JSON中，当前不执行start。

## 路由、VPN与最新DNS

- 专用IPv4路由/防火墙、DNS/DHCP，**无NAT**；默认到OW21.1。PVE21.22只管理/L2，见[PVE](../pve/README.md)。同19东西向不经本机，不能用网关规则代替PVE bridge ACL。
- 已批准完整WireGuard10.66.66.0/24访问19有效IPv4服务及21.23/19.1，应用账号权限保持；不是历史只放Penpot9001的窄规则。peer终止在OpenWrt且各/32，本机不保存peer私钥。细节见[VPN合同](../../16-wireguard-access.md)。
- 11月7日02:31历史DNS-only清理已验证：保留11服务名、删除11退休记录，UDP/TCP正确，退休名NXDOMAIN；publish-service30与artifact-service31继续独立，Nexus尚未合并。索引指向[DNS summary](../../cleanup/network/dns-runtime/summary.json)，未复制旧22记录preview冒充现役。
- DNS仅LAN19.1 TCP/UDP53，上游21.1；DHCP池19.200–239/1h、GW/DNS19.1。租约内容不读取或复制。LAN真实DORA有旧证据，不外推全部WAN DHCP反向验证。

当前没有保存整份runtime nft/网络导出，因为bundles/candidates有阶段属性；只索引能追溯的公开资料。维护先读[交接](../../11-live-handoff.md)与[人工手册](../../19-manual-operations.md)，不重放stage/commit，不清日志、重置DHCP租约或缩模板盘。默认Bash不变，fish只安装。
