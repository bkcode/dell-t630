> 文档状态（2026-11-07）：本页为阶段实施/技术记录，文中“当前”、网段、角色数与通过结果以原执行时点为准。服务器现因UEFI0058内存错误暂停，Nexus合并已授权但未执行；当前配置入口见[访问清单](../12-service-access-and-operations.md)，恢复门槛见[最新交接](../11-live-handoff.md)。旧脚本、stage/commit或初始化步骤不得直接重跑。

# network19当前网络与验收

实际网络已迁入192.168.19.0/24。OW静态route经192.168.21.23（VM190 WAN），虚拟网关LAN19.1；PVE21.22只管理/二层交换，旧四桥/NAT已清除，宿主IPv4/IPv6 forwarding全部0，vmbr19无宿主IP。

最新范围：**不部署或启动Java业务程序，测试五服务也已停用，Publisher保持fenced；只保留一份9011 Java验收模板。** Linux9010/Docker9001两个核心模板与NAS独立安装方式不变。

当前阅读入口：[交付与边界](../15-network19-delivery.md)、[访问与操作](../12-service-access-and-operations.md)、[网络验收](audit/network19-acceptance.md)、[Java模板](java-template/README.md)、[active plan](../plan.json)。迁移历史与失败/修正回执保留，不能把旧10.63证据当当前网络证据。

同19/24东西向流量由PVE bridge-family ACL精确绑定MAC/IP与role矩阵，原生rule预检及实际正负/反欺骗发包已验。网关不对LAN之间SNAT；OW负责上游分流，保留实际Fake-IP代理DNS兼容。旧104与101、七个停止QA都已实际启动确认19地址再恢复停机。

秘密不进镜像/普通文档；CF归档只在PVE，publisher私钥只在220，Mac外部探针仍停用。CF只验新网注册，未知remote ingress与公网域名仍未签。PVE宿主整机重启、断电/真实TV主机/SLO/长期独立备份属于明确后续范围。
