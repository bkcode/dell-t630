> 最终只读复审：9/9成立，无阻断。首11verified/nativeOK/unit退出0、计划enabled/次日03:30、三规则同Prom容器HUP后healthy/inactive、15UP与22容器健康均有实际证据；220排除、CF归档与SHA不导出、无迁移/恢复/新真实通知。原38项与6REC未扩大签收。下文是首备完成前7/2阶段的审查历史。

# 2026-11-09 本期验收范围复核

复核方式：仅本地读取新合同、plan、校验器和带时间证据；没有连接服务器、轮询备份、执行hook/备份/恢复/通知或Git操作。新合同截至本次读取为9个required：7passed、SET-OBS-001与SET-BAK-001 pending。本文不更新任何用例状态。

## 结论

**范围划分适当，未发现把原迁移、业务或独立灾备pending偷签为通过。** 新本期范围是既有基础设施完成与用户选择的PVE本机自动快照，不等于原完整交付38项、6项严格REC、应用逻辑恢复或异机灾备全部完成。

- SET-HOST/NET只签本次硬件运行观察、自然启动后的守卫、管理与二层合同；明确EDAC0/RAIDOptimal不是助手独立物理诊断。11/09宿主证据有当前boot/顺序/守卫SHA等细节。
- SET-CORE只签8数据容器、挂载/网络/时间基础及Java不启业务；没有签数据库内容/账号全量、业务链、任务幂等或多实例性能。
- SET-TOOLS/NAS只签原部署基础健康及220/221独立、未更新源码/未迁移；未扩签设计/制品内容全量、真实TV/PS或转码。
- SET-CLEAN是限定空闲常驻测速清理，证据包含无活跃测试连接、5201关闭和不改来宾/网络；不由此授权批量删资源。
- SET-SCOPE明确不合并/迁移/退221、不启Java、无Macprobe及OW完整规则localonly，方向正确。OW不得随交付push，不能因存在本机分支便认为远端交付安全已证。
- SET-BAK继续pending正确：安装disabled job和部分归档verified都不能代替首11完整成功与实际启用读回。
- SET-OBS继续pending正确：旧15UP只证明原监控；新增备份指标、规则、白名单及加载结果需本轮配套证据。内部通知桥active不能冒称已重新发送并收到真实Lark成功。

原全局acceptance.json仍为26历史passed/12pending；cleanup中6REC均pending，带partial或未执行解释。它们不应随新本机快照阶段完成而自动改变。特别是REC-BAK/ROLL中的旧Nexus合并冷备/交接/回退与本轮PVE本机快照是不同任务，当前仍不迁移、不恢复覆盖用户数据。

## BAK/OBS最终签收前应补到本项证据

以下为后续最终核验建议，当前不执行、不改状态：

1. **SET-BAK**关联首轮最终收据：固定11集合恰为100/190/200/201/210/221/230/240/250/260/270，220始终排除；每档zstd、tar/vma与SHA验证成功，ledger整体verified，原生unit已退出且ExecMainStatus0。不能只看job-end、running时Result=success或部分档100%扫描。
2. 关联实际job enable/readback：03:30、实际串行/优先级/压缩/最新bwlimit策略、保留last3/daily7/weekly4、root700/600、原盘挂载UUID门禁、通知无额外外发、旧21档不在prune集合。仅`backup-install-receipt.json`是早期disabled安装证据，不能单独支持最终passed；需最新兼容修正与启用/最终验证证据。
3. 首轮历史CLI超时、LXC tmpdir/UMask失败、正常取消/thaw与新版重试保持独立记录。当前单ledger假设同一时刻只有一个run，不能在首轮未结束时并行手工触发或启用可能重叠的调度；未来并行需求须full-run互斥/run绑定设计。
4. **SET-OBS**关联新增指标最终fresh样本、Prom原生规则验证与实际加载、3告警规则/既有AM路由白名单读回及原15targets健康。测试为mock/合成路由/配置检查时如实写明，不把它写成真实新通知送达。没有用户要求的Macprobe继续排除。
5. **SET-SCOPE**最终Git交付应补非秘密Git安全/OW排除的准确证据。当前仅media-audit能支持机器未迁移/未合并，不能单独证明最终提交内容不含localonly规则；由最终Git安全门禁覆盖，禁止push --all或local规则分支。

本机快照只提供同主机、同store故障域的恢复点。它不是独立目的地，不保证应用事务/跨VM一致性，不包含内存checkpoint，也没有实际恢复启动或RPO/RTO实测。因此原独立备份/应用恢复条目保持pending，不扩签NAS为正式备份或把旧本机Mac临时副本当已落实独立策略。

## schema与状态引入

`validate_docs.py`仅在原固定current-manifest白名单增加`completion/20261109/acceptance.json`，沿用原有唯一ID、必填字段、证据存在、required统计一致性等检查；仍继续验证原38项Markdown/JSON状态、角色资源和机器来源。这个改动是新增当前阶段范围，没有取消旧门槛或把原pending改为passed。

当前校验器的证据存在/统计检查本身不证明运行语义，不能代替上述人工复核。建议最终证据中写具体实际命令类别、时间、结果与失败边界；新合同通用“核对证据”步骤由其详细审计文件补足，避免最终只留下安装文件或计划。

plan新增`backup_delivery`清楚写PVE-local/non-independent、restore_executed=false、migration=false、schedule_enabled=false及first-run in-progress，未夸大。最终同步时建议把旧`decisions.backup_destination=provisional Mac`明确标为历史临时副本，并将当前PVE本机选择放在同一现行口径；也要更新operational_state中仍为11/08的last_operation/live_state时间描述，避免as_of11/09却被误读为全部11/09操作均已签收。

## 此次不改动的状态

不修改新9项状态、原38项状态或cleanup历史；不签OBS/BAK通过，不替换原REC，不执行服务器动作或Git。新阶段只有在两个pending各自真正完成、由管理者复核后才可声明9/9；独立目的地、恢复/RPO/RTO、迁移、业务、物理设备与公网另行保留边界。
