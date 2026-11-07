> 文档状态（2026-11-07）：本页为阶段实施/技术记录，文中“当前”、网段、角色数与通过结果以原执行时点为准。服务器现因UEFI0058内存错误暂停，Nexus合并已授权但未执行；当前配置入口见[访问清单](../../../12-service-access-and-operations.md)，恢复门槛见[最新交接](../../../11-live-handoff.md)。旧脚本、stage/commit或初始化步骤不得直接重跑。

# 190 DNS-only 退休记录清理：已实际完成

2026-11-07主AI开放独立190 DNS-only窗口。当前Nexus221仍运行，本次没有合并Nexus、停Nexus或修改220/221/CF；PVE/OW与其它来宾没有本子任务写操作。

## 实际结果

- 当前mplan经已CAS本地compiler编译，`dns_delta.py`只允许删除审定退休静态记录。旧主conf22个host-record减为11，artifact-service31、publish-service30及全部保留节点A记录保持。
- 11个退休名称（101/104、231/232、9000、9002..9006、9020对应名称）UDP/TCP都返回NXDOMAIN；11个保留名称UDP/TCP都返回预期A。临时9040..9045不进入长期DNS。
- native `dnsmasq --test`以dnsmasq身份exit0；原子persist两个owned文件，只重启`dell-gateway19-dnsmasq.service`，DNS PID822→3139。
- 五个非DNSunit（FW、ready、networkd、SSH、resolved）的PID/启动时间完全不变；规范化实际nft、期望nft bytes、WireGuard full10、route/MAC/IPv4地址、三forward1、SSH认证、DNS监听与UID/三cap保持。
- 租约文件没有被本工具读取内容、覆写、清空或轮换；只核owner/group/mode不变，允许dnsmasq自然回收expired lease。此次size前后均0不是内容或“token”恒定性证明。
- 新strict SSH再次check通过。只读比较备份与现役conf确认所有非host-record选项逐行相同。

## 文件与权限

实际只写190的`/etc/dell-gateway19/config.json`（root600）和`dnsmasq.conf`（root644），另外产生受控临时syntax文件（已删除）与root私有backup/receipt。原文件备份仅190：

`/var/lib/dell-gateway19/dns-cleanup/c30b6546fb0942a181f87460469e300a`

backup目录700、两文件600；没有复制到普通证据。公开证据只记录审查结果、hash、状态、角色IP和进程metadata，不含凭据。

| 文件 | 作用 |
| --- | --- |
| manager.py | 从current live snapshot和current mplan编译、严格gate、CAS调用、fresh strictSSH |
| remote.py | 190/MAC/owned config guard，私有backup、native test、两文件atomic write、仅DNSrestart；失败原文件恢复+仅DNSrestart |
| preflight.json | 审定delta及expected nft bytes/WG等价 |
| receipt.json | before/after非DNS不变、全部正/负DNS查询与backup路径 |
| fresh-strict-SSH-check.json | 新连接pubkey/hostname/forward1/WGfull/服务状态检查 |
| non-host-option-proof.json | 原conf与新conf所有非host-record选项完全相同、backup700/600 |
| prepared-config.json / prepared-dnsmasq.conf | 本次编译公开策略输入，**不是可反复执行的现役脚本** |

主conf中的host-record变更必须由DNS进程重读。本次按已审方式restart DNS，没有使用“仅HUP就已生效”的错误替代，也没有重启networkd/FW/ready或改变转发。原hot兼容策略guard没有被放宽。

## 验收

| ID | 前置/步骤 | 可观察条件 | 证据 | 状态 |
| --- | --- | --- | --- | --- |
| DNS-01 | current live CAS与strict delta | 仅删批准存在的11host；artifact31/publisher30保留；expected nft相等/WG不变 | preflight.json | 通过 |
| DNS-02 | 私有backup/native test | backup700/600；非rootsyntax exit0；lease不被工具清空 | receipt/non-host-option-proof | 通过 |
| DNS-03 | 两文件persist/仅DNSrestart | 仅DNSPID变化，非DNS进程/route/MAC/nft/3forward/认证保持 | receipt.json | 通过 |
| DNS-04 | DNS packet查询/新SSH | 11 retained A与11 retired NXDOMAIN都UDP/TCP正确，新strictSSHcheck通过 | receipt/fresh-strict-SSH-check | 通过 |

此次已执行成功，不要为重复签收再次运行manager；未来新的DNS维护需要新的窗口和current live CAS。失败会恢复这两个文件并仅重启同DNSunit，不重建lease、不临时放宽FW、不启PVE L3/NAT。
