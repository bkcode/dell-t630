# 2026-11-09 PVE只读基础审计

采集：2026-11-09T06:42:26.737128+00:00（UTC，等同北京时间14:42），补充：2026-11-09T06:43:50.070970+00:00。完成：2026-11-09T14:44:45.994878+08:00。本轮只写本JSON/Markdown，没有host/guest变更、压力测速或重启。

## 结论

- 12个保留来宾全部running，9001/9010/9011三模板stopped；onboot/startup逐项匹配plan，190最先，失败单元0。
- 宿主IPv4/IPv6 all/default/全部接口forward均0，唯一nft表为bridge dell19_acl，无旧应用NAT文件；vmbr19无host地址，19客户端路由经21.23。
- 昨日forwardguard三个公开文件SHA完全保持；本次boot实际观察到networking14:24:12→bridge和ExecStartPost成功14:24:15→pve-guests14:24:18，持久顺序已读回，不是仅静态推断。
- RAID1/RAID5均Optl，5盘Onln、BBUOptimal40C；EDAC4个MC的CE/UE全0，当前boot内核未匹配不可纠正/MCE/EDAC/FSIO错误分类。
- iperf3为enabled开机常驻daemon，当前PID1415（此前1418不是当前PID），两次仅*:5201 LISTEN，无活跃测试连接。建议root最终确认空闲后stop+disable服务，保留包以备将来按需测试；本agent未停用。

## 本次硬件/启动观察

bootID `c2320079-38f6-4c05-bb3f-7502ee3f8f97`，boot时间 `2026-11-09 14:24:03`，PVE8.4.0/kernel6.8.12-9。MemTotal约125.781GiB，MemAvailable约101.830GiB；8GiBswap空闲。SMBIOS为A1/A2/B1/B2各32GB/DDR4/2133MT/s，名义128GB，不与125GiB规划额度混淆。

EDAC0/短期运行无错误不单独证明此前B1模块/接触/槽位/通道已完全排除故障。用户此前报告重新插拔/更换并诊断通过属于外部维修事实；本机缺ipmitool/racadm，本audit没有新增SEL/Lifecycle确认、更没有清日志。当前boot是被动读取，不是本agent执行新reboot验收。

## 自启与现态

| VMID | 名称 | 当前状态 | onboot | startup | plan一致 |
| --- | --- | --- | --- | --- | --- |
| 100 | cf-tunnel | running | 1 | order=5,up=10,down=60 | True |
| 190 | network-gateway | running | 1 | order=1,up=30,down=120 | True |
| 200 | data-prod-db | running | 1 | order=10,up=60,down=120 | True |
| 201 | data-prod-infra | running | 1 | order=11,up=90,down=120 | True |
| 210 | data-test | running | 1 | order=12,up=90,down=120 | True |
| 220 | publish-service | running | 1 | order=30,up=15,down=60 | True |
| 221 | artifact-service | running | 1 | order=21,up=90,down=180 | True |
| 230 | java-prod-01 | running | 1 | order=40,up=15,down=120 | True |
| 240 | java-test-01 | running | 1 | order=43,up=30,down=180 | True |
| 250 | penpot-service | running | 1 | order=22,up=90,down=180 | True |
| 260 | nas-media | running | 1 | order=50,up=30,down=120 | True |
| 270 | ops-service | running | 1 | order=20,up=30,down=60 | True |
| 9001 | tpl-docker-base | stopped template | 0 | — | True |
| 9010 | tpl-linux-base | stopped template | 0 | — | True |
| 9011 | tpl-java-acceptance | stopped template | 0 | — | True |

## Forwardguard持久性与顺序

| 公开文件 | SHA256 | 权限 |
| --- | --- | --- |
| `/usr/local/sbin/dell-management-forwarding-off` | `96b0b6d8b5bb137a7599f3afe3ff86c1c3a6986b4ecb8cad106ba06fb55a6c05` | root 0o755 |
| `/etc/network/if-up.d/dell-management-forwarding-off` | `bda534462bc2b1bb87acfa9ade706dc5604e8b022da1a27b9ab9fcd7a781ae2e` | root 0o755 |
| `/etc/sysctl.d/99-z-dell-management-only.conf` | `541cd07b995e8d7d537591bf0cf4a4c6daf8f5f89efa64bd5e18afe95d9f4e97` | root 0o644 |
| `/etc/systemd/system/dell-network19-bridge.service` | `e543479d9297740e197e41476fe5813eeec0c4dd95d2d4442ee6a6d498bf6cb0` | root 0o644 |
| `/etc/systemd/system/dell-network19-bridge.service.d/20-management-only.conf` | `a42bfddfa94cefa54c44d9daf979b3644f6906f96ca64fb800d5319bfd1c2674` | root 0o644 |

三新增guard与11/08receipt逐SHA匹配。if-up hook只在IFACE=vmbr0运行；关闭脚本写全部family/interface forwarding与全局IPv4off；bridgeunit After network.target/Before pve-guests，pve-guests还Requires/After bridge。ExecStartPost当前boot记录exit0。原interfaces SHA仍`5099020d…`，没有改vmbr0地址、路由或ACL。不能为以后ifupdown行为重新启hostforward/NAT。

## 宿主服务与指标定时器

pveproxy/pvedaemon/pvestatd均active，systemctlfailed清单为空。dell-pve-metrics.timer为enabled/activewaiting，最近14:41:30触发；service Resultsuccess/NRestarts0。oneshot此刻inactive/dead是正常完成后的状态，不当作故障，不重复启动采集。此audit不验证Ops端freshseries/服务应用或发送Lark，那些由主AI独立协调。

## iperf3归属与建议

| 项 | 实测 |
| --- | --- |
| 当前PID | 1415 |
| 所属cgroup | /system.slice/iperf3.service |
| 二进制/包 | /usr/bin/iperf3；3.12-1+deb12u1 |
| unit | /lib/systemd/system/iperf3.service，User=iperf3，Type=simple，enabled |
| 启动 | /usr/bin/iperf3 --server --interval0；14:24:13与本boot同步 |
| 自动恢复 | Restart=always，RestartSec15；不是一次性client测试 |
| 配置flag | /etc/default/iperf3中START_DAEMON=yes |
| TCP5201 | 两样本只有LISTEN，无ESTAB/活跃UDP测试 |

可按减少无用监听的目标建议由root在最终同一窗口再核连接为空后正常stop+disable iperf3.service，不需要卸载、mask或改网络；仅killPID会被Restartalways拉起。此建议不说明过去/未来从来没人测，也不授权本agent执行。保留软件包便于以后明确按需单次测速；当前不跑任何iperfclient。

## 边界与来源

- 数据来自strictSSH PVE21.22：官方pvesh配置白名单、/proc/sys及EDAC、公开guard与systemd状态、PERC只读/c0showJ、SMBIOS容量/槽位和ss进程元数据。没有完整CI/env、220key或CF含tokenunit读取。
- 本次不迁Nexus/数据、不退221、不启Java业务、不恢复Macprobe；没有获取或Git提交OpenWrt完整规则。
- RAIDquickshow不是完整数据一致性/恢复/压力/RPO_RTO验收；硬件修复可信度与真实业务范围不扩大。
- 若root随后停用iperf3或补其它服务，必须引用其新收据；本JSON保留此采样时点，不静默改成已停用。
