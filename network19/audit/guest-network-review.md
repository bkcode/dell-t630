> 文档状态（2026-11-07）：本页为阶段实施/技术记录，文中“当前”、网段、角色数与通过结果以原执行时点为准。服务器现因UEFI0058内存错误暂停，Nexus合并已授权但未执行；当前配置入口见[访问清单](../../12-service-access-and-operations.md)，恢复门槛见[最新交接](../../11-live-handoff.md)。旧脚本、stage/commit或初始化步骤不得直接重跑。

# guest-network.py 只读精确复核

复核时间：2026-11-06T16:29:51.500909+08:00。代码SHA256 `6057557ff4cb953ab5c4db13584e1ca80636f0bdd73c9ef78176449fef35dca4`，当时87行。只读11个明确新QEMU角色：200/201/210/220/221/230/231/232/240/250/270；原12角色中的NAS260走独立OMV流程，190/CT100/旧VM/模板均排除。没有stage/apply/reconfigure或任何来宾写入。

## 实际renderer与文件优先级结论

11/11均为networkd+resolved active，MAC精确命中eth0；NetworkManager和networking均not-found，无ifupdown文件。当前Network File全部为`/run/systemd/network/10-netplan-eth0.network`，Link File为同目录10-netplan-eth0.link。没有`/etc/systemd/network/*.network`，/usr仅80-*虚拟接口默认文件。当前源是`/etc/netplan/50-cloud-init.yaml`，各自固定MAC、set-name eth0、旧静态/24、唯一oldGW、DNS1.1.1.1。

`/etc/systemd/network/00-dell-server19.network`的文件名先于10-netplan匹配；networkd只使用第一个匹配.network，因此只要MAC不变且00确实被选中，不会把旧10-netplan的Address/Gateway/DNS与新文件叠加。仍保留的50-cloud-init源/10-netplan生成文件是回退资料，不等于旧IP继续活跃。新增cloud-init disable阻止后续cloud-init生成覆盖，但不是清除旧netplan文件；00必须长期保留。实际切换应核对Network File=00，不能仅凭预计优先级标完成。[Debian13 systemd.network官方手册](https://manpages.debian.org/trixie/systemd/systemd.network.5.en.html)

| VMID | 实际接口 | 当前默认GW | 实际DNS | networkd/resolved |
| --- | --- | --- | --- | --- |
| 230 | eth0，已按MAC核对 | 10.63.10.1 | 1.1.1.1 | active / active |
| 200 | eth0，已按MAC核对 | 10.63.10.1 | 1.1.1.1 | active / active |
| 201 | eth0，已按MAC核对 | 10.63.10.1 | 1.1.1.1 | active / active |
| 210 | eth0，已按MAC核对 | 10.63.20.1 | 1.1.1.1 | active / active |
| 220 | eth0，已按MAC核对 | 10.63.30.1 | 1.1.1.1 | active / active |
| 221 | eth0，已按MAC核对 | 10.63.30.1 | 1.1.1.1 | active / active |
| 231 | eth0，已按MAC核对 | 10.63.10.1 | 1.1.1.1 | active / active |
| 232 | eth0，已按MAC核对 | 10.63.10.1 | 1.1.1.1 | active / active |
| 240 | eth0，已按MAC核对 | 10.63.20.1 | 1.1.1.1 | active / active |
| 250 | eth0，已按MAC核对 | 10.63.30.1 | 1.1.1.1 | active / active |
| 270 | eth0，已按MAC核对 | 10.63.30.1 | 1.1.1.1 | active / active |

所有`/etc/resolv.conf`均指向resolved stub（127.0.0.53）。11/11未发现全局DNS=/FallbackDNS=/Domains覆盖，也没有显式全局KeepConfiguration/ManageForeignRoutes覆盖；仅vendor关闭mDNS。故脚本切换per-link DNS19.1符合当前实际DNS所有者。stub地址保留127.0.0.53是正常现象，不能要求resolv.conf直接出现19.1。19.1 DNS是否真正能解析仍须网关与外部验证，`resolvectl dns`读回只证明配置，不证明解析成功。

## 当前修订已解决的问题

- 行27–32 stage保存per-link DNS与3个接口IPv6实时值；stage只写root私有journal，不改网络。
- 行38–44 reconfigure后等待newIP+newGW，避免把异步配置尚未收敛误判为失败。行45–50显式清除oldIP/oldGW并要求唯一新默认路由；当前11台没有额外IPv4/默认GW，所以对本范围的最终断言覆盖了旧地址/默认路由残留。
- 行51–56等待per-link DNS恰为19.1，解决“文件写了但resolved仍旧DNS”的验证缺失。
- 行60–78回退恢复3个文件、实时V6和DNS，而不是仅恢复文件。原`disable_ipv6=0, accept_ra=0, autoconf=0`均有真实快照。

## 仍需主AI修正或在编排层严格补验的两项

1. **P2：rollback成功状态缺少最后的网络读回。** 行71–73按旧地址/GW执行修复，但行77–79最终仅验证DNS/V6，未再次读取地址、默认路由和实际Network File。`ip route replace default via oldGW`成功不等于其它metric/额外默认已消失；在新配置异步过渡中也可能删后再加回。建议在写restored状态前限时确认接口IPv4仅oldIP、无newIP，默认仅oldGW/dev eth0，Network File已回到stage记录的原10-netplan文件，再核DNS/V6。当前无证据发生残留，这是恢复成功声明的覆盖缺口。

2. **P2：stage/apply未核对真实匹配Network File，guard未显式要求resolved active。** 行13–19仅检查networkd，行21–33未保存实际Network File，apply行39–56虽检查IP/GW/DNS但未检查被选文件。当前11台已独立实测resolved active且无00前序文件，所以不是本次renderer不兼容阻塞；建议把此次已知事实变为事务内前置/读回保护，防后续换renderer/更早.network/drop-in时静默偏离。stage也应核给定old_gateway与实际唯一oldGW一致；本次audit已证明映射中的旧GW，但代码本身没有采集/验证。

其它边界：各run最长30秒，外层50/30秒轮询是soft期限，不是总进程绝对时限，QGA编排timeout要留足；失败只输出failed而不自动rollback，符合由主AI协调桥hotmove+OS恢复的责任边界，但外层必须检查退出码并调用明确回退。回退前后NIC桥也需主AI恢复，脚本不负责PVE桥，这一点没有误实现。

本次不要求额外引入全网renderer抽象、换接口名或更换SSHkey。230作为无业务canary的networkd/byMAC现实前提成立；stage成功仅代表journal准备好，不能标切换或恢复通过。

## 证据

- `guest-renderer-state.json`：11台byMAC接口、实际Network File、network services、路由、网络配置白名单、CloudInit网络禁用设置、V6状态。
- `guest-dns-global-state.json`：11台全局resolved/DNS来源与networkd保留设置白名单。
- `systemd-network-man.json`、`systemd-networkctl-man.json`、`systemd-resolved-man.json`：Debian13官方手册主源与检索定位；无完整文档复制。
- 所有读取均排除Env、认证信息、user-data、私钥、token和cloud-init秘密。
