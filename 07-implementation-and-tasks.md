# 实施顺序、任务管理与交接

> 2026-11-10最新覆盖：用户已明确恢复Nexus合并并移除独立artifact-service；当前合并和最终核验已完成，旧“不合并/不退役221”只代表此前阶段。完成后为VM220 6CPU8GiB、primary19.30+Nexus alias19.31，保留原build卷并承接原Nexus100GiB卷；12来宾/3模板、45CPU87GiB、15targets已按最终回执验证。详细状态见[本次交付](completion/20261110-nexus-merge/README.md)。Java业务不启、旧链fenced、私有MCP/APIkey与备份边界保持。


更新：2026-11-08（Asia/Shanghai）。用户确认内存已重新插拔/更换且诊断通过；本boot EDAC CE/UE0、RAIDOptl。现已分范围核验既有基础服务恢复，当前不是11/07的POST停机状态；完整物理诊断报告、根因隔离和长期稳定性没有因此自动签收。

本轮范围已由用户恢复Nexus合并与独立221退役扩充；真实数据/身份/网络/监控通过后才收尾，其他业务迁移不扩围，Java业务不部署。Mac外部探针明确不需要，从当前/后续待办移除并保持停用。

## 当前任务合同

| 工作 | 已有结果 | 边界与后续 |
| --- | --- | --- |
| 基础恢复核查 | 12运行实例+3模板；数据/Java基础/媒体工具/Ops分范围只读核验，15targets UP、6HTTP200 | 只证明采样时基础运行，不扩大为全部应用内容或原用例全量重测 |
| 宿主管理边界 | ifupdown2带IP桥将forwarding置1的偏差已定位；3owned guard文件恢复双栈全0 | interfaces/routes/ACL不变，无network reload/guest restart；未以重启扩大验收 |
| 清理、fish与模板 | 原9项清理历史通过，fish9guest+3tpl、默认Bash；本次盘点未发现需立即删除的额外对象 | 不重跑旧destroy、模板封版、初始化或installer |
| Java | 230正式/240测试各一运行基础、无Java业务进程；唯一验收模板9011 | publisher fenced，不激活旧五服务或Nacos候选 |
| Nexus | 已停源/冷备/原盘与31移交，220目标完整核验及受控重启通过，221已退役 | 最终数据/身份/网络/15targets和221退役已按本次回执验证，禁止重放旧计划 |
| 严格恢复6项 | 硬件、数据、网络、监控有部分运行证据；冷备/回退未执行 | 原完整用例pending不伪签，不作为本轮基础恢复额外门禁 |
| Git与交接 | 本地文档/规则/状态同步后经检查交付 | 实际提交/推送见[交接](20-git-and-handoff.md)及交付证据，不等同服务器全部验收 |

## 证据与执行顺序

1. 先读[plan](plan.json)、[当前恢复证据](recovery/20261108/host-network-postcheck.json)、[任务](tasks.json)和[人工手册](19-manual-operations.md)，区分历史、当前采样和未来候选。
2. 本次恢复观察：数据三台挂载/容器基础健康；230/240只验JDK/账号存在与无业务；媒体/Nexus只验健康/身份元数据；Ops仅GET、unit与textfile，没有Lark测试外发。各自限制在证据中保留。
3. 如今后发现具体缺项，先限定对象和影响再最小修复，不因一次启动延迟重部署。当前未发现需要额外重启或重新部署的基础服务。
4. 用户已明确恢复Nexus迁移，按新鲜全量基线/冷备/唯一盘/IP31交接及最终验收执行；旧49GAV234主件不覆盖当前全量，不把本地文档当现场完成。
5. 新passed必须来自实际步骤和观察。原38项26历史passed/12pending及原清理结果保留，本次运行恢复不覆盖它们。

## 权限与保留

PVE写、VMID/IP/盘归属和物理维护协调仍集中处理。CF归档仅PVE；publisher私钥仅220，不wholebackup220、不输出凭据或复制客户端私钥。NAS不是正式唯一备份目标。源Mac数据与业务工作树保留。

11/07 02:35:01完整验收与02:44:29最后PVE操作保留为事故前历史；11/08的分范围运行证据另记，不改写旧失败。物理内存根因和独立长期RPO/RTO、业务SLO、真实家庭设备仍未验；Mac外部探针不列入这些后续项目。

## 11月9日后续精确授权

较早“不迁移”范围之后，用户已分别明确授权测试Nacos选定36配置、Puyu实际两库迁往210，以及整个21/24作为受信LAN。Nacos配置见[已签收4项](completion/20261109-nacos-config-import/acceptance.json)，Puyu见[已签收8项](completion/20261109-puyu-db-migration/acceptance.json)；源保留、没有业务启动/应用连接切换、没有Nexus合并。LAN双层已确认，入口[访问规则](network19/lan-trusted-20261109/README.md)。测试凭据以用户再次指定并要求保持的三组件设置为准，实际同步验收见[独立记录](completion/20261109-test-credentials/README.md)，不把原迁移未改密码的历史声明误读为后续没有获准同步。
