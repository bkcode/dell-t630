> 文档状态（2026-11-08）：本页为阶段实施/技术记录，旧网段、角色数和通过结果按原时点解释。基础已恢复；本轮仅补齐与清理，用户暂不迁移/合并，Mac外部探针不需要。当前配置见[访问清单](../../12-service-access-and-operations.md)，范围与恢复证据见[最新交接](../../11-live-handoff.md)；旧初始化器不得重跑。

# 全部来宾与模板NIC只读盘点

后续主AI已推进190/104/vmbr19创建与改网；本表保留初始采集时点，不代表最新执行状态。阶段更新见[bridge-family-implementation.md](bridge-family-implementation.md)及上级migration-plan.json。

采集：2026-11-06T07:51:14.900092+00:00，PVE 8.4.0，192.168.21.22。共28对象：27 QEMU（其中6个template=1）、1 CT。190空闲；本审计未分配或创建。

| VMID | 名称 | 类型/状态 | 当前桥 | 当前地址/CloudInit | 19网迁移要求 |
| --- | --- | --- | --- | --- | --- |
| 101 | data-docker-base-tpl | QEMU / stopped | vmbr0 | 无PVE CloudInit地址；停机内部配置未验证 | 迁vmbr19；停机内部网络/CloudInit缓存待核，不启动 |
| 102 | data-docker-tpl2 | QEMU模板 / stopped | vmbr0 | 无PVE CloudInit地址；停机内部配置未验证 | 迁vmbr19；停机内部网络/CloudInit缓存待核，不启动 |
| 103 | publish-base-tpl | QEMU模板 / stopped | vmbr0 | 无PVE CloudInit地址；停机内部配置未验证 | 迁vmbr19；停机内部网络/CloudInit缓存待核，不启动 |
| 104 | publish | QEMU / stopped | vmbr0 | ip=192.168.21.23/24,gw=192.168.21.1 | 旧21.23冲突，先隔离/改CI与来宾内部网络，再启GW21.23 |
| 105 | java-running-base-tpl | QEMU模板 / stopped | vmbr0 | 无PVE CloudInit地址；停机内部配置未验证 | 迁vmbr19；停机内部网络/CloudInit缓存待核，不启动 |
| 106 | windoge-template | QEMU模板 / stopped | br2001 | 无PVE CloudInit地址；停机内部配置未验证 | 迁vmbr19；停机内部网络/CloudInit缓存待核，不启动 |
| 200 | data-prod-db | QEMU / running | vmbr10 | ip=10.63.10.10/24,gw=10.63.10.1 | 迁vmbr19；新IP待主AI，保留MAC与原身份 |
| 201 | data-prod-infra | QEMU / running | vmbr10 | ip=10.63.10.11/24,gw=10.63.10.1 | 迁vmbr19；新IP待主AI，保留MAC与原身份 |
| 210 | data-test | QEMU / running | vmbr20 | ip=10.63.20.10/24,gw=10.63.20.1 | 迁vmbr19；新IP待主AI，保留MAC与原身份 |
| 220 | publish-service | QEMU / running | vmbr30 | ip=10.63.30.10/24,gw=10.63.30.1 | 迁vmbr19；新IP待主AI，保留MAC与原身份 |
| 221 | artifact-service | QEMU / running | vmbr30 | ip=10.63.30.20/24,gw=10.63.30.1 | 迁vmbr19；新IP待主AI，保留MAC与原身份 |
| 230 | java-prod-01 | QEMU / running | vmbr10 | ip=10.63.10.20/24,gw=10.63.10.1 | 迁vmbr19；新IP待主AI，保留MAC与原身份 |
| 231 | java-prod-02 | QEMU / running | vmbr10 | ip=10.63.10.21/24,gw=10.63.10.1 | 迁vmbr19；新IP待主AI，保留MAC与原身份 |
| 232 | java-prod-03 | QEMU / running | vmbr10 | ip=10.63.10.22/24,gw=10.63.10.1 | 迁vmbr19；新IP待主AI，保留MAC与原身份 |
| 240 | java-test-01 | QEMU / running | vmbr20 | ip=10.63.20.20/24,gw=10.63.20.1 | 迁vmbr19；新IP待主AI，保留MAC与原身份 |
| 250 | penpot-service | QEMU / running | vmbr30 | ip=10.63.30.30/24,gw=10.63.30.1 | 迁vmbr19；新IP待主AI，保留MAC与原身份 |
| 260 | nas-media | QEMU / running | vmbr40 | ip=10.63.40.10/24,gw=10.63.40.1 | 迁vmbr19；新IP待主AI，保留MAC与原身份 |
| 270 | ops-service | QEMU / running | vmbr30 | ip=10.63.30.40/24,gw=10.63.30.1 | 迁vmbr19；新IP待主AI，保留MAC与原身份 |
| 9000 | dell-template-inspect | QEMU / stopped | vmbr0 | ip=dhcp | 迁vmbr19；停机内部网络/CloudInit缓存待核，不启动 |
| 9001 | tpl-docker-base | QEMU模板 / stopped | vmbr0 | ip=dhcp | 迁vmbr19；停机内部网络/CloudInit缓存待核，不启动 |
| 9002 | dell-linux-clone-test | QEMU / stopped | vmbr0 | ip=dhcp | 迁vmbr19；停机内部网络/CloudInit缓存待核，不启动 |
| 9003 | dell-docker-clone-test | QEMU / stopped | vmbr0 | ip=dhcp | 迁vmbr19；停机内部网络/CloudInit缓存待核，不启动 |
| 9004 | dell-docker-clone-a | QEMU / stopped | vmbr0 | ip=dhcp | 迁vmbr19；停机内部网络/CloudInit缓存待核，不启动 |
| 9005 | dell-linux-clone-b | QEMU / stopped | vmbr0 | ip=dhcp | 迁vmbr19；停机内部网络/CloudInit缓存待核，不启动 |
| 9006 | dell-docker-clone-b | QEMU / stopped | vmbr0 | ip=dhcp | 迁vmbr19；停机内部网络/CloudInit缓存待核，不启动 |
| 9010 | tpl-linux-base | QEMU模板 / stopped | vmbr0 | ip=dhcp | 迁vmbr19；停机内部网络/CloudInit缓存待核，不启动 |
| 9020 | dell-restore-baseline | QEMU / stopped | vmbr0 | ip=dhcp | 迁vmbr19；停机内部网络/CloudInit缓存待核，不启动 |
| 100 | cf-tunnel | CT / running | vmbr0 | 192.168.21.150/24（运行实测DHCP） | 迁vmbr19；新IP待主AI，保留MAC与原身份 |

101名称带tpl但实际template标志不是1，应按普通停止VM处理。106模板引用br2001，当前宿主无该运行网桥；同样必须迁移，不能遗漏。15个对象仍配置vmbr0，12个新角色配置旧10.63桥，1模板引用br2001。

未启动任何停止实例；没有读取sshkeys、cipassword、token、args、来宾用户数据或Cloudflare凭据。对运行12 QEMU仅调用QGA network-get-interfaces；CT100仅读ip地址。停止实例内部是否还存静态21地址属于后续隔离维护验证条件，不能根据CloudInit或停机状态直接宣称已清除。

## 宿主当前状态

- vmbr0=192.168.21.22/24，唯一物理端口eno1，默认网关192.168.21.1。
- vmbr10/20/30/40分别持有10.63.10/20/30/40.1/24，宿主IPv4 forward=1、IPv6 forward=0。
- nft当前专用表为inet dell_filter、ip dell_nat；现有10.63跨区和应用DNAT仍由PVE处理。
- 两个防火墙service显示active，但pve-firewall真实状态为disabled/running，cluster/host防火墙配置文件不存在；active不能作为vNIC规则已生效的证据。
- 当前125.781GiB MemTotal；预算以125GiB保守上限计算。
- LinuxBase9010的root scsi0为32G，不能直接安全缩到8G。

原始白名单证据：current-inventory.json、ct-firewall-supplement.json、backend-template-supplement.json。
