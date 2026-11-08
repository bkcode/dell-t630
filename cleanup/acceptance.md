# 清理与基础恢复验收

更新：2026-11-08。用户报告内存重新插拔/更换且诊断通过；当前boot EDAC CE/UE0、RAIDOptl。12实例+3模板、15targets UP和6HTTP200已有[本次运行证据](../recovery/20261108/host-network-postcheck.json)。这不是完整硬件根因、所有原应用或灾备重验。

用户本轮只补齐既有基础服务并核多余项，**明确不迁移**。221继续独立Nexus、220仍standby；合并pending原因是用户延期，历史短停授权不覆盖最新范围。Mac外部探针用户明确不需要，保持停用并从现行/后续待办移除。

## 原清理结果

原10项保持9历史passed/1Nexus pending；历史真实操作不因本次基础健康自动重验。完整条件见[JSON](acceptance.json)。

| ID | 项目 | 状态 | 记录 |
| --- | --- | --- | --- |
| CLN-JAVA-001 | 正式测试各保留一个运行基础 | passed | PVE中230/240各一且无业务Java进程，231/232已归档清理；原生产测试隔离保持。 |
| CLN-BAK-001 | 21份受保护原/候选归档完整性 | passed | 15旧对象+3原core+3fish候选归档均zstd/VMA/SHA验证，root700/600，排除CF100与整机220。 |
| CLN-DEL-001 | 精确15旧对象依赖顺序清理 | passed | 15个确切对象已删，104先103，无force/skiplock或共享ISO删除。 |
| CLN-FISH-001 | 9运行来宾安装fish并保默认shell | passed | 190200201210220221230240260 fish4.0.2-1，默认Bash未改，CF/Penpot/Ops与PVEhost排除不动。 |
| CLN-TPL-001 | 三模板fish升级与独立QA | passed | 三独立candidate QA验证新机器/hostkey/DockerID、Java原基线和fish；原备份后恢复到9001/9010/9011，stopped/DHCP/genericCI。 |
| CLN-TMP-001 | 临时构建验收对象无残留 | passed | 本任务9040–9045已清除，PVE仅12运行+3模板，无额外停止VM。 |
| CLN-DNS-001 | 退役DNS与身份同步 | passed | 11退休名UDP/TCP NXDOMAIN、11保留A正确，artifact31/publisher30保留；WGfull/NATnone/hostforward0及MACIP/role隔离保持。 |
| CLN-OBS-001 | 10节点15目标与维护恢复 | passed | 15/15UP、221保留UP，10份catalog/installer配套；health/collector/业务身份不变，清理site静默仅本任务项解除，0activealerts/no testsend。 |
| CLN-REG-001 | 保留SSH与原应用入口回归 | passed | 10guest新strictSSH/唯一19地址/默认GW正确，五原web入口200、数据/身份未被fish/模板清理改变，Java业务不启动。 |
| CLN-NEXUS-001 | Nexus同机合并与源221退役 | pending | 11/08基础核查221仍独立19.31且原两容器healthy；220原standby未加31/未启Nexus。用户明确暂不迁移，合并pending原因是用户延期，不再以硬件暂停或同项授权未到为唯一阻塞。 |

## 原6项严格恢复合同

这6项保留pending，已有部分证据按下表说明；它们不作为本轮基础服务恢复的额外阻塞门禁，不为凑通过而降低原条件。

| ID | 状态/进度 | 观察与缺口 |
| --- | --- | --- |
| REC-HW-001 | pending / partial | 用户报告已重新插拔/更换内存且诊断通过；本boot EDAC CE/UE0、RAIDOptl和基础服务可达。未独立收集完整物理维护/离线诊断报告、根因隔离及长期稳定观察，原严格用例仍pending。 |
| REC-BAK-001 | pending / not-executed-user-deferred | 本轮明确不迁移，不停221、不做合并冷备或隔离恢复；旧归档完整性证据保留，本次未重签。 |
| REC-DATA-001 | pending / partial | 原挂载UUID、运行身份元数据、既有服务与容器健康已核，230/240无Java业务；未登录数据库核账号权限或重验Nexus全部GAV/EULA、Penpot设计素材/共享内容，因此完整数据身份用例仍pending。 |
| REC-NET-001 | pending / partial | PVE/190与19网络基本路径已核，带IP桥forwarding=1已通过3个owned guard文件纠正为全0，interfaces/routes/ACL未变，无network reload/guest restart。未重跑完整VPN/角色拒绝矩阵和新guard重启持久性，严格用例仍pending。 |
| REC-OBS-001 | pending / partial | 20:19:38读回15/15targets UP、Prom/AM alerts空、4容器healthy、Lark原unit active及textfile更新；未发送通知或重新验Lark端到端。Mac外部探针由用户明确不需要，已从当前/后续任务移除。 |
| REC-ROLL-001 | pending / not-executed-user-deferred | 本轮用户暂缓迁移，未执行Nexus移盘/IP接管、回退或退役；不把基础恢复验收当合并通过。 |

本次宿主forwardguard仅新增3个owned文件，将带IP桥被ifupdown2覆盖的双栈forwarding1纠正为0，原interfaces/routes/ACL不变，无network reload或guest restart。没有重跑installer、QA/fixture或迁移；没有重新认证读业务内容、发送Lark测试或扩大签收NAS真实设备/公网配置。

11/07 02:35:01完整验收、02:44:29最后PVE操作与UEFI0058/B1事故保留为历史，不覆盖本次采样，也不以旧passed当当前全面健康。CF归档仅PVE、私钥仅220、NAS不是正式唯一备份。进一步范围须读取[继续入口](../10-resume-after-approval.md)和当前用户指令。
