# 局域网有线/Wi-Fi访问测试Nacos：已放行

2026-11-09。用户Air Wi-Fi来源192.168.21.164能访问Penpot但测试Nacos超时；PVE和210本机Nacos均200、12来宾持续运行。原因是190路由防火墙和PVE二层桥都仅允许旧管理源21.22/21.116访问8848/9848，静态路由19/24 via21.23正确。ping默认未向普通LAN放行，ICMP Redirect是下一跳提示，不能据ping超时判断关机。

用户明确要求Nacos放行。现仅新增192.168.21.0/24→192.168.19.20 TCP8848/9848；正式19.11、testDB3306/SSH22/9849等旧限制保留，不新增NAT、端口映射、L3转发或应用权限。

## 实施与回退

[网关差异](policy.diff)和[桥差异](bridge-policy.diff)均仅+1accept/no删除；config只有WAN_to_LAN及声明hash变化，其余11hosts/规则保持。原本机bundle22条旧host记录不能直接重放；候选以live11hosts为基准，主计划只清过时退役地址记录使未来编译同现行，原主计划保留master-before.json，DNS运行内容未变化。nativepolicy SHA bd237...从实际服务器取证并保持，未拿本地不同版本覆盖。

网关CAS只扩展精确append的hot-delta校验，5越界负例拒绝。复用原hot/nativechecks/atomicowninettable/180s回退和独立SSH确认，不重启网络/DNS/SSH；PVE桥也仅自己table原子加载、独立180s回退，hostforward保持0。试用既有FLOW_MARK，若回退只恢复规则/阻止新连接，已建立流可能持续到关闭，未flush conntrack或夸称即时全部撤销。

[网关确认](gateway-confirmed.json)、[桥确认](bridge-confirmed.json)、[最终网关](final-gateway.json)、[最终桥](final-bridge.json)核持久化与watchdog/pending已解除，WG10.66.66/24全server19授权和无NAT保持。

## 实际验证

- Studio来源192.168.21.230访问testNacos8848 HTTP200、nc9848 succeeded；[桥独立计数](bridge-independent-check.json)新增规则命中，PVEforward全0。
- [反向检查](LAN-negative-tests.json)：testDB3306/SSH22/9849与prodNacos11的8848/9848仍timeout。
- [Air用户确认](Air-user-confirmation.json)：用户答“已经成功”，没有提供逐项HTTP/nc原始输出，不冒称已归档单项结果。
- [本地门禁](local-validation.json)及gateway/test_gateway.py 42项离线测试通过；旧duplicate地址测试改为显式active200/100，避免index1变gateway后被skip的错误fixture。

Nacos仍需原账号认证/namespace授权。用户索要的测试凭据仅存本机private目录700/600，不在此文档或Git。此次只改可达性，不改Nacos配置项、namespace、账号或业务数据；随后用户另行选择的配置导入是独立任务。
