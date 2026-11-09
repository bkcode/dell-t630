# LAN21受信访问server19：实际交付与本地canonical收口

用户在11月9日明确授权普通LAN `192.168.21.0/24` 访问server19整个 `192.168.19.0/24` 的IPv4服务及网关自身21.23/19.1。网关190与PVE桥两层规则已实际确认；SSH key-only、各应用认证/账号权限、IPv6禁用及角色间peer矩阵保留。PVE仍只管理/L2、v4/v6 forwarding均0，网关与PVE均无NAT；既有WG10.66.66/24全服务许可不变。

[5项验收清单](acceptance.json)记录本阶段范围；[23:34最终只读后检](final-postcheck.json)核实际配置SHA、两层规则、三网关unit active、事务pending=false、rollback timer inactive。本目录普通证据不含账号密码、SQL或业务配置正文。

| 项目 | 实际证据 | 已观察结果与限制 |
| --- | --- | --- |
| 网关hot事务 | [确认回执](gateway-confirmed.json) | 受信LAN mark6；独立SSH确认，三unit active，PID保持，无NAT |
| PVE桥 | [确认回执](bridge-confirmed.json)、[已应用候选](bridge-candidate.nft) | 精确LAN21/24→19/24许可，位于原MAC/目标IP绑定及invalid之后；原WG/peer规则保留 |
| LAN路径抽测 | [positive tests](LAN-positive-tests.json) | ub SSH到19.20及21.23成功，test3306/8848/9848与prod19.11:8848 TCP成功，19.20 ICMP2/2 |
| 最终收尾 | [final postcheck](final-postcheck.json) | 网关配置SHA `32c84b7b941ceaec56a74a499acbb3b0e51dbbf7814e5059cb879e27bd21a843`；桥持久SHA `a6910d08db278527566e0b343c8a12b57989f7ba10b2df1b0d498e969e120bc0` |
| 本地canonical复现 | [canonical sync](canonical-sync.json) | migration-plan与实际master语义相同，bundle config与bridge current/candidate逐字节一致；网关45项、桥5项离线回归通过。本次收口没有远程连接或服务重启 |

Air没有为这次全范围提供逐项新输出，不能补造Air全服务验收；TCP通、ping通也不代表应用登录/业务可用。早前[Nacos-only负测](../lan-nacos-20261109/LAN-negative-tests.json)保留为扩权前历史，不能再据此称LAN到MySQL/SSH/正式Nacos仍被网络规则拒绝。不改变OW、DNS/DHCP监听、应用账号或配置。

本地生成入口为[网关prepare](../gateway/prepare.py)与[桥renderer](../audit/render-bridge-acl.py)。renderer默认使用[15身份当前NIC快照](../audit/nic-registry-current.json)，含12角色与3模板，未知/模板身份仍隔离；不使用29对象旧stage作为默认来源。[当前网关policy](../gateway/policy.py)保留后续已审的退休记录/alias过滤，未用本目录旧candidate源代码覆盖它。`master-candidate.json`、`policy-candidate.py`和实际回执作为应用时点证据保留；不要重放stage/commit来刷新日期。

离线复验可运行 `python3 -B dell/network19/gateway/test_gateway.py` 与 `python3 -B dell/network19/audit/test_trusted_lan.py`。历史`cleanup/network/test_candidates.py`另有1项将旧候选renderer与当前mark6安全guard比较字节的时点漂移，已在[本地报告](canonical-sync.json)记录，未为使旧比较通过而删除当前安全guard；本轮50项现役canonical回归均通过。native nft/systemd检查来自实际应用回执，本地Mac收口未重新运行native检查。
