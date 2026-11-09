# publish-service：发布与制品仓库合并架构

更新：2026-11-09。本文保留此前选定的**未来合并目标合同**，不是当前执行计划。用户已确认内存重插/更换并诊断通过，服务器已恢复基础服务；本轮明确**暂不迁移、不合并Nexus**。当前VM220发布机与VM221制品仓库继续独立，历史同机目标不覆盖现役角色。

当前事实：VM221仍独立19.31，原盘与身份未向220移交；220仍4CPU/4GiB、仅19.30及待机材料。11月9日fresh核对仍为12running/3tpl与15UP，相关证据见[当日交付入口](completion/20261109-prod-db-scope/README.md)及[媒体审计](completion/20261109/media-audit.json)。硬件故障与历史维护许可均保留，但当前不执行合并的原因是用户本轮范围明确排除迁移，不能因SSH恢复自动开始。

## 1. 未来合并后的服务结构（本轮不执行）

```text
VM220：publish-service                         6 vCPU / 8 GiB
管理、构建与发布主地址：192.168.19.30
│
├─ 构建与发布
│   ├─ Git / JDK / 构建工具
│   ├─ 构建盘：/srv/dell-build
│   └─ publisher 受限身份 → Java测试基础19.45
│      当前业务发布仍冻结，不启动Java业务
│
└─ Nexus制品仓库
    ├─ 同一网卡的服务地址：192.168.19.31:8081
    ├─ Docker / Compose，由dell-nexus.service监督
    └─ 独立Nexus数据盘：/srv/nexus，应用数据/srv/nexus/data

VM221：artifact-service → 数据与身份核验通过后退役
```

以下仅说明未来目标：两个IP将属于同一VM220；`.19.31`不是第二台VM、第二个网关或第二个监控节点。保留`.19.31:8081`用于兼容现有Maven/Gradle配置、下载地址和书签，管理SSH继续使用`.19.30`。

## 2. 名称、地址与职责

| 项目 | 合并后的约定 |
| --- | --- |
| 虚拟机标识 | VM220，PVE名称与OS hostname均为`publish-service` |
| 发布职责 | Git拉取、构建、受限传输/发布基础；当前publisher仍fenced |
| 制品职责 | Nexus仓库、账号权限、组件与元数据，由同一VM内的独立应用栈管理 |
| 管理/发布来源地址 | `192.168.19.30`，去测试19.45的实际源IP仍须为30 |
| Nexus服务地址 | 同NIC alias `192.168.19.31`，原HTTP端口8081保持 |
| `artifact-service`名称 | 仅作原VM221的历史名称及既有服务DNS兼容名称，不再计为独立VM |
| SSH身份 | 沿用VM220自己的host key；不复制VM221 host key，不用`dell-vm221`信任别名连接新220 |
| 网关/DNS | 均为`192.168.19.1`，PVE21.22仍不做应用转发 |

原`artifact-service`服务DNS若保留，可继续解析到31，但其底层服务所有者变为220。服务URL兼容不代表SSH身份兼容；直接SSH访问31将看到220的公钥，应按真实归属核验。

## 3. 资源、数据和权限边界

| 项目 | 最后验收快照 | 合并目标 |
| --- | --- | --- |
| 发布机 | 220，4vCPU / 4GiB | 220，6vCPU / 8GiB |
| Nexus独立VM | 221，2vCPU / 4GiB | 核验通过后退役 |
| 全部实例 | 12（11VM+1LXC） | 11（10VM+1LXC） |
| 模板 | 9001 / 9010 / 9011，共3份 | 保持3份 |
| 全部CPU/内存配置总额 | 43vCPU / 85GiB | 保持43vCPU / 85GiB |
| 监控目标 | 10node+5Ops=15 | 9node+5Ops=14 |

若将来完成该合并，将减少一个OS实例和管理对象，**不释放原221的4GiB配置额度**；它与原220额度一起分给新220。构建与仓库竞争同一VM资源，首期建议单构建并发；并行构建与仓库负载仍需另验。

构建盘与Nexus数据盘各自独立，不将仓库写进构建缓存或容器可写层。原Nexus100GiB卷、文件系统UUID `239dc45a-b1f3-408b-a8ef-7afa77b52204` 及数据身份保留，原盘只允许一个VM写。发布专用私钥继续只留220，publisher不加入docker组，受限SSH/源IP30与业务发布冻结策略不放宽。

现行自动备份仅VM200正式MySQL/Nacos外部元库，当前唯一`nacos_prod`12表、正式业务schema未创建；Nexus221制品数据/系统和其他数据不自动备份。新增未列白名单库直接失败告警、需更新策略。PVE逻辑档落`/mnt/pve/store/dell-artifacts/prod-db-backups` root700/600，首轮3301B、03:30 timer enabled/GFS3-7-4，见[新中央入口](completion/20261109-prod-db-scope/README.md)与[新首轮回执](completion/20261109-prod-db-scope/first-success-and-timer-enabled.json)。

旧11来宾全机方案曾成功，但当前job已disabled、旧规则组退役；19,747,582,801B档与21回退档保留，不自动删除。旧CF档只留PVE、发布key只220。新db-only三规则已[热载](completion/20261109-prod-db-scope/alerts-installed.json)，原Prom identity/三名/接收对象保持、无testsend。本机逻辑备份仅[该3301B Nacos小档已在VM210临时隔离恢复](completion/20261109-prod-db-restore/README.md)，完整业务恢复/RPO/RTO/异机DR未签，也不等于未来Nexus迁移源停服冷备；本轮不迁移/合并/启Java，无Mac探针。

备份仍需应用一致性与明确白名单；不能因为同机合并就对220做包含发布私钥的整机备份/快照导出。独立221源冷备和原OS盘在最终核验前保留，不能删除唯一回退点。

## 4. 迁移状态与切换验收

| 阶段 | 状态 |
| --- | --- |
| 历史同机方案与短停维护授权 | 已确定且历史许可保留；本轮用户明确不迁移 |
| 220 Docker/两镜像/私有standby | 已准备；11月9日fresh核仍无active Nexus或31 alias |
| 内存处理与基础服务恢复 | 用户报告重插/更换并诊断通过；本boot EDAC0/RAIDOptl，持续观察保留 |
| 源Nexus停服、221关机、冷备校验 | 尚未执行 |
| 原盘与31地址唯一移交、220应用启动 | 尚未执行 |
| 数据/身份/网络/监控验收、221退役 | 尚未执行 |

仅在将来用户明确恢复迁移任务后，切换验收至少包含：

1. 内存、存储与原应用稳定，冻结源Nexus新鲜只读基线；历史49GAV/234主件不能替代当前全量。
2. 停原unit、正常关机221、对已停止源做PVE受保护冷备并验证，确认仍off；再停220并唯一移交原盘。
3. 220同NIC持久30+31、发布流量源30、bridge ACL/IPAM/DNS及严格SSH一致，221不再占31或挂原盘写入。
4. 原Nexus数据SHA、EULA、账号/权限、原URL及匿名拒绝均通过；publisher仍受限，Java业务保持停用。
5. 监控仅抓220的30:9100一个节点，并在该节点检查Nexus unit/本机31 HTTP；移除221节点后14targets通过，再退役221并更新现役清单。

人工命令、检查点和回退步骤统一见[人工手册第7节](19-manual-operations.md)、[恢复清单](cleanup/nexus/resume-preflight.md)与[技术实施计划](cleanup/nexus/PLAN.md)。本文不替代逐项操作门禁，不新增一键迁移入口。

## 5. 文档怎样区分目标与现场

[架构文档](02-architecture.md)以合并后目标说明职责，[当前状态](01-current-state.md)保留最后实机快照。`plan.json`的`roles`仍保存未移交的220/221配置，`Nexus_consolidation`描述本目标；不能只为让文档看起来已合并而提前删除221角色或把31声明为220现役地址。

将来用户明确恢复迁移任务、完成fresh基线与合并验收后，才同步现役roles、IPAM/ACL、监控、启停清单和凭据归属说明。未完成前，文档与Git提交都不代表服务器已变更。

本轮继续基础与仅正式数据库/Nacos逻辑备份，不迁移数据或合并Nexus；Java业务不部署，Penpot保持已验历史ff1783e，不因main文档更新而升级应用。Mac外部探针用户明确不需要，不作为现行或后续待配置能力。OW完整规则只留本地，本轮不触碰或上传。
