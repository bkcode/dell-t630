> 文档状态（2026-11-07）：本页为阶段实施/技术记录，文中“当前”、网段、角色数与通过结果以原执行时点为准。服务器现因UEFI0058内存错误暂停，Nexus合并已授权但未执行；当前配置入口见[访问清单](../../12-service-access-and-operations.md)，恢复门槛见[最新交接](../../11-live-handoff.md)。旧脚本、stage/commit或初始化步骤不得直接重跑。

# network19 Core交付

已完成所分配Data/Java基础/Publisher/Ops与12角色基线监控迁移。当前事实汇总为`runtime-status.json`，准确IP以root `network19/migration-plan.json`为准。Root负责OS/PVE/OW/VM power与全局plan/access/主文档；本子任务只在明确逐role窗口改服务配置/监控，未改OS或blind接受hostkey。

最新用户范围：**不部署Java业务程序，只保留root指定的单一验收模板/基础环境。** 240五应用stop/disable、无MainPID/cgroup进程、非root finger可读JDK21；active监控仅SSH/QGA/Node Exporter三项，无active HTTP。不可变root600旧制品/配置及已准备未部署候选私有保留，没有发布新Nacos dataId、activate release或业务E2E。Publisher两端仅公开IP合同迁新网络，240 baseline始终false，220私钥仅原机、hostkey alias与root可信240指纹匹配；没有业务发布请求。

Data20019.10/mysql healthy，20119.11/nacos-redis-rabbit healthy，21019.20四基础容器healthy；200/210 auto.cnf数据身份不变。201实际Nacos SQL连接来源19.11→200 ownDB已读回。密码/namespace/vhost和Nacos两个@%保留，不顺带硬化。三Java19.45 Host同plugin/auth/18逐表DML预增完成，但最新scope下未实际使用、不伪造新CURRENT_USER，旧Host保留、无retire。

Ops27019.70四容器healthy，12node新地址全UP，自组件5UP，共17targets；GrafanaDB正常、PVE QGA textfile新鲜。Java240的new-instance指标精确base3、无active HTTP series。long-lived Lark原PID40894/NRestart0、17218固定网络、public marker/policy/renderer/code与secret inode/mtime/owner/mode保持；没有读真实Webhook/token值、没有外发验证或测试消息。Site maintenance silence由root最后核稳态解除。

12role Node Exporter只监听本机各自19.x:9100；health/catalog/installer/listen配对更新、原timer状态保持、candidate不激活。OS后按原MAC/IP24/GW/DNS19.1与旧/新SHA门禁应用；native collector采样和本机metrics200逐role完成。Root计划内230/232 shutdown/reboot/可信key更正单列，恢复后最终12UP已证实。190/104未擅自加入12target。

已授权本地source只同步`infra/ops/guest-baseline`三文件范围：保留本地更完整role_health_profile，只改19/24 guard和Java-test空业务profile；target map为新12IP，collector同SHA未改。没有将旧guest版本倒灌丢掉Nexus/OMV/Lark逻辑，也不把source未来逻辑反推成live已部署。备份、最小diff与前后SHA在`source-sync-actual-evidence.json`和`source-sync-backups/`，初始inventory/evidence冻结保留。

## 关键证据

| 证据 | 内容 |
| --- | --- |
| role200/201/210-commit-start-evidence.json | 数据infra恢复、身份/配置不变 |
| data201-to200-identity-evidence.json | new19源Nacos到MySQL实际连接 |
| mysql210-add-new-parser-retry.json | 精确3Host/18DML/sameauth，旧保留 |
| java240-foundation-only-readback.json | JDK/nonroot/无app/基础监控/持续fenced |
| publisher240-fenced-readback-evidence.json | canonical新SHA/policy/from+samekey/native0 |
| publisher220-key-hostalias-final-readback.json | 私钥owner600/no bytes读取，新profile、trustedhost匹配 |
| monitoring*-window-evidence.json | 每role新9100+新鲜采样闭环；230单列apply/sample文件 |
| ops270-new-network-allup-readback.json | final12+5全部UP/PVEfresh/base-onlyJava/Larkactive无send |
| source-sync-actual-evidence.json | 授权source最小合并与fixtures |

失败未隐藏：MySQL初次parser错误把opaque auth正文中的TAB误作输出首列，补偿已回收全部新Host，原失效收据/只读无残留证据保留；优先完整CREATE USER的最小parser纠正、fakefixtures后仅一次成功，正文只在guest RAM。240公开合同最后用了错误sudoers文件名，实际路径为dell-publisher-test240；未改权限，随后global visudo/sshd和全部新SHA只读全通过，baseline一直false。Lark synthetic check首次fake token长度不符被正确拒绝，修fixture为64后parse0；没有碰真实凭据或调用send。

工具默认inspect/localstage。`apply-monitoring.py`应用要root600 OScommit收据与exactnewMAC/IP/GW/DNS，至多15秒等唯一新listener。`stage-commit-env.py`仅精确白名单键原子改、其它字节保留；`role-window.py`只在明确role/action窗口使用。`commit-publisher.py`当前scope拒绝baseline enable；Java staging文件保留作先前准备历史，不是最新执行授权。RUNBOOK中的旧Java上线章节已有显著scope覆盖，不得复用来启动业务。

本次未声明HTTP/TLS正式域名、真实业务SLO、资金/Broker/通知外发、异地灾备或用户Mac外部验收通过。全局最终验收与维护结束由root统一合并。
