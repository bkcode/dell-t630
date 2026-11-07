# PVE物理宿主pve

**硬件暂停，非live配置导出。** 合同来自[plan](../../plan.json)，最后综合验收2026-11-07 02:35:01；02:44:29仅规划同步。当前UEFI0058拦截POST，先前SEL指向DIMM_B1，实际DIMM/接触/槽位/通道尚未隔离确诊。当前不连接服务器，不按F1/清日志/远程powercycle，也不因旧验收通过自动恢复。

本机资料：[配置合同](config.json)、[安全来源索引](config-sources.json)。56是宿主逻辑处理器，28物理核；125GiB是保守规划额度，故障后容量必须重验，不能当当前实测。iDRAC独立管理面21.21能访问不代表PVE/来宾已上线。

## 网络与存储合同

- vmbr0管理21.22/24，eno1，默认21.1；SSH22/UI8006。vmbr19为无宿主IPv4/IPv6的纯L2桥，只有190WAN使用21.23。
- hostforward全部0、无应用NAT；bridge dell19_acl继续负责同19网MAC/IP/角色隔离。宿主19客户端路由via21.23不是给其它设备三层转发。网关见[VM190](../vm190-network-gateway/README.md)。
- H730管理SSD RAID1/HDD RAID5；历史05:17Optimal不覆盖当前内存故障后的控制器/文件系统健康。PVE拥有阵列/store，不能给NAS重复挂同一已挂块设备。
- 最后快照12运行实例（11VM+1LXC）+3停止模板，43vCPU/85GiB配置额、15UP均为历史，不是现在在线宣告。

恢复必须遵守[交接](../../11-live-handoff.md)、[硬件发现](../../08-hardware-findings.md)和[人工手册](../../19-manual-operations.md)。Nexus维护授权已具备但未执行，当前暂停仍优先。此目录只索引公开合同/旧证据，没有复制可能过时的nft/10.63配置、凭据或盘归档。
