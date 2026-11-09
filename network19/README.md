> 文档状态（2026-11-08）：本页为阶段实施/技术记录，旧网段、角色数和通过结果按原时点解释。基础已恢复；本轮仅补齐与清理，用户暂不迁移/合并，Mac外部探针不需要。当前配置见[访问清单](../12-service-access-and-operations.md)，范围与恢复证据见[最新交接](../11-live-handoff.md)；旧初始化器不得重跑。

# network19当前网络与验收

11月9日23:34最终只读核查见[LAN全访问收尾](lan-trusted-20261109/final-postcheck.json)：普通LAN `192.168.21.0/24` 已受信访问server19整个`192.168.19.0/24`的IPv4服务及网关自身21.23/19.1，现有SSH/应用认证继续生效。网关与PVE桥两层规则均已确认，WG10.66.66/24全服务许可保持；网关无NAT，PVE IPv4/IPv6 forwarding均0。服务PID未变，事务pending=false、rollback timer inactive。[实际抽测](lan-trusted-20261109/LAN-positive-tests.json)含19.20的SSH/MySQL/Nacos与19.11的Nacos及19.20 ICMP；未重新执行Air全服务端口遍历，不把这些抽测外推成所有服务认证验收。

本地canonical `migration-plan.json`、gateway bundle和bridge current已按该实际版本同步；[本地复现验证](lan-trusted-20261109/canonical-sync.json)区分离线检查与历史native应用回执。早前Nacos-only的负测只代表扩权前时点，当前不再据此声称普通LAN的MySQL/SSH/ICMP被拒。旧执行器、stage/commit或初始化脚本不应为刷新日期而重跑。

实际网络已迁入192.168.19.0/24。OW静态route经192.168.21.23（VM190 WAN），虚拟网关LAN19.1；PVE21.22只管理/二层交换，旧四桥/NAT已清除，宿主IPv4/IPv6 forwarding全部0，vmbr19无宿主IP。

最新范围：**不部署或启动Java业务程序，测试五服务也已停用，Publisher保持fenced；只保留一份9011 Java验收模板。** Linux9010/Docker9001两个核心模板与NAS独立安装方式不变。

当前阅读入口：[交付与边界](../15-network19-delivery.md)、[访问与操作](../12-service-access-and-operations.md)、[网络验收](audit/network19-acceptance.md)、[Java模板](java-template/README.md)、[active plan](../plan.json)。迁移历史与失败/修正回执保留，不能把旧10.63证据当当前网络证据。

同19/24东西向流量由PVE bridge-family ACL精确绑定MAC/IP与role矩阵，原生rule预检及实际正负/反欺骗发包已验。网关不对LAN之间SNAT；OW负责上游分流，保留实际Fake-IP代理DNS兼容。旧104与101、七个停止QA都已实际启动确认19地址再恢复停机。

秘密不进镜像/普通文档；CF归档只在PVE，publisher私钥只在220，Mac外部探针仍停用。CF只验新网注册，未知remote ingress与公网域名仍未签。PVE14:24自然重启后的guard持久性已在11月9日核查；断电、真实TV/主机、长期SLO与独立灾备仍未签收。
