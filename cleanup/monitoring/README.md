> 文档状态（2026-11-07）：本页为阶段实施/技术记录，文中“当前”、网段、角色数与通过结果以原执行时点为准。服务器现因UEFI0058内存错误暂停，Nexus合并已授权但未执行；当前配置入口见[访问清单](../../12-service-access-and-operations.md)，恢复门槛见[最新交接](../../11-live-handoff.md)。旧脚本、stage/commit或初始化步骤不得直接重跑。

# 监控拓扑精简：仅准备，未部署

目标11个永久角色：CF100/GW190沿用PVE/QGA元数据路径，9个node exporter VMID为200/201/210/220/230/240/250/260/270。删除221/231/232 scrape；220只scrape19.30:9100一次，19.31是同机Nexus业务alias，不再单独scrape。保留Ops原5个目标不变，总数14。此工作不修改包安装、Fish/Bash选择、WireGuard10/24信任、hostforward0、数据账号/权限、Nexus/publisher身份或业务配置。

## 真实基线与最小diff

`live-source-inventory.json`记录220/270真实root-owned文件SHA、Prom目标和Nexus原MAC地址。collector两机同SHA且与本地source一致，**完全不改collector**。当前live installer比本地source旧：运行候选仅从live旧版最小改ROLES12→9/配套catalog长度/合并publisherNexus profile；source候选独立从当前新版最小改，不倒灌旧代码，Ops Lark与Java无业务的新逻辑保留。diff在`diffs/`，精确old/newSHA在`manifest.json`。

catalog与installer必须成对更新，禁止只减catalog而留`len==12/ROLES12`，否则现有ExecCondition会失败。当前工具只覆盖已读基线220/270；其它7个保留guest的旧12-catalog/12-installer仍是相互匹配的既有配置，不在本次prepare中虚报已统一更新。未来若需同步它们，先读各自SHA再按主AI明确窗口处理。

原220只有19.30、Nexus inactive，不能假装31已属于本机。`candidates/profiles/unit-only`只追加dell-nexus.service；`full`再追加31:8081/status。两种应用都要求Nexus已active且现有容器稳定healthy，full还必须31在**原MACbc:24:11:2a:01:ad**接口上及本机status200。前检只传实际MAC地址集合∩批准{30,31}+loopback，不使用整个19CIDR；外部/其它VM/带认证query URL拒绝。collector原实现已经支持真实local alias，旧helper用{primary,127}才会误拒31；不为它扩大validator。

本轮本地验证：unit-only语法有效；full在当前无31时被真实validator拒绝（正确fail-closed），只有批准预期模型才通过。未做guest写或source覆盖。

## 原生Prom检查与边界

`native-check.py`在270**现有**Prom容器通过STDIN传等价配置：只把guest-node的file_sd替换为9候选static groups，其它job/rules保持原路径。实际promtool check config及check service-discovery都exit0，准确9地址，Prom主PID/StartedAt/health不变。无guest文件写、无container创建/重启。`native-check.json`明确这是prepare nativeparser证据，**不代表实际file_sd已提交或14UP**。

部署后`deploy.py`对真实file_sd路径再次做native config/SD检查，再等Prom API精确9node+5own=14全部UP。file_sd更新不用重启Prometheus。原生检查command来自本机已安装promtool帮助，参数与基线都已读回。

## 未来主AI部署最小工具（本轮未执行）

1. 先由Nexus owner完成迁移，确认221停止、alias31已转220、Nexus2容器healthy与新实例功能验收通过。不得让两VM同时持有31；本工具绝不设置alias或启动Nexus。
2. `python3 cleanup/monitoring/deploy.py plan`仅本地展示，不连接/写guest。
3. 根工作区dell下，主AI批准窗口后：`python3 cleanup/monitoring/deploy.py apply --vmid 220 --profile full --execute`。如确需先只单位监控可选unit-only，但同样不得在Nexus inactive时激活失败指标。
4. 然后`python3 cleanup/monitoring/deploy.py apply --vmid 270 --execute`。工具会先通过管理通道只读核220真实alias/Nexusstatus，防Nexus迁移前移除221目标。
5. 工具仅修改manifest三文件/guest，原字节备份在guest `/root/dell-monitor-cleanup/<nonce>`0700/0600。只暂停guest-health timer并等正在运行collector退出，成对原子替换文件；运行**仅**installer `--check-private-ip`、collector `--check`和已有collector一次，恢复原timer active状态。绝不调用generic installer install-only/activate、mask服务、restart exporter/Docker/业务或daemon-reload。业务/SSHD/exporter PID启动时间与所有container身份前后须同。
6. 任一失败恢复原文件，记root journal/result；若SSH断或结果未确认不blindrepeat，主AI先看journal。显式回退：`python3 cleanup/monitoring/deploy.py rollback --vmid VMID --nonce NONCE --execute`；若文件已被其它窗口改变，拒绝覆盖。回退可能恢复旧17目标（含已停/删目标），需保持维护管理并审查，不恢复VM或网络。
7. source-candidates三个文件由`sync-source.py`维护独立oldSHA守卫；默认仅plan。主AIactive plan已正式变11物理VMID后才可`--execute`本地同步，不改mainplan。其它prepare程序未运行，严禁在旧mainplan下重跑Ops prepare覆盖回12target。

以上mutating模式均为未来明确执行，当前仅AST/本地逻辑与read-only native-check验证；`deploy.py plan`是本轮唯一调用的部署入口。

## 后置签收

- Prom真实14/14UP、9个node精确VMID且不存在31:9100重复series；其余5 Ops jobs/labels不变。
- 220 metrics在role=publish-service下含dell-nexus active1及full模式nexus-status up1/status200，base3保留；无需独立Nexus exporter或新proxylistener。
- 270 Lark/监控服务和既有alert rules SHA保持；适配退休目标，不改hook/Env/秘密，不以工具重发真实通知。
- PVE push实际源码见`PVE-push-readonly-review.json`，自动枚举clusterVM、QGA270投递、原CF100专门健康项保留，不改代码/不运行它；hostforward实测0。
- 本期仍全部Java业务停用；Shell偏好pending默认Bash，Ops仅不装Fish，不影响必要监控配置。WireGuard全10/24的现有信任在网络owner范围，这里无nft/route/sysctl或认证操作。
